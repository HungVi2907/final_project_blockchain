"""Read the B handoff and manage a separate local audit database."""
from contextlib import closing
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from web3 import Web3

from credit_audit.chain import Verification, connect_anvil, decision_bytes, inspect_decision, submit_saved
from credit_audit.records import canonical_serialize, commitments
from credit_audit.storage import connect, get, save


HELOC_MODEL_SHA256 = "b9b7a30f8afaec886c9255527c966c25e105af599f0835206c1e91b79b31e654"
MAX_AUDIT_UPLOAD_BYTES = 1024 * 1024


@dataclass(frozen=True)
class Fixture:
    record: dict
    canonical_bytes: bytes
    record_hash: str
    model_hash: str

    @property
    def decision_id(self) -> str:
        return self.record["decision_id"]


def read_only(path: Path):
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def load_fixture(directory: Path, *, synthetic: bool = True) -> Fixture:
    summary = json.loads((directory / "taiwan_smoke_summary.json").read_text(encoding="utf-8"))
    decision_id = summary["decision_id"]
    decision_bytes(decision_id)
    with closing(read_only(directory / "audit.sqlite3")) as db:
        saved = get(db, decision_id)
    if saved is None or summary.get("synthetic") is not synthetic:
        raise ValueError("The handoff does not contain the expected decision type.")
    record, raw = saved["record"], saved["canonical_bytes"]
    record_hash, model_hash = (value.hex() for value in commitments(record, raw))
    if (
        record["decision_id"] != decision_id
        or raw != (directory / "decision_record.json").read_bytes()
        or (record_hash, model_hash) != (summary["record_hash"], summary["model_version_hash"])
    ):
        raise ValueError("The B handoff files disagree. Use files from the same run.")
    if synthetic:
        if sha256((directory / "model.json").read_bytes()).hexdigest() != record["model_artifact_sha256"]:
            raise ValueError("The synthetic model disagrees with the record.")
    elif (
        record["dataset_id"] != "fico_heloc_iclr2025"
        or record["schema_version"] != "2"
        or summary.get("dataset_id") != record["dataset_id"]
        or summary.get("schema_version") != record["schema_version"]
        or record["model_artifact_sha256"] != HELOC_MODEL_SHA256
        or len(record["shap_explanation"]["feature_contributions"]) != 43
    ):
        raise ValueError("The HELOC handoff does not match the frozen Role A model.")
    return Fixture(record, raw, record_hash, model_hash)


def load_audit_json(raw: bytes) -> Fixture:
    """Load an exported decision record without changing its bytes."""
    if len(raw) > MAX_AUDIT_UPLOAD_BYTES:
        raise ValueError("Audit JSON exceeds 1 MiB")
    try:
        record = json.loads(raw.decode("utf-8"))
        explanation = record["shap_explanation"]
        contributions = explanation["feature_contributions"]
        if (
            not isinstance(record["model_version"], str)
            or not isinstance(explanation["method"], str)
            or not isinstance(contributions, list)
            or any(not isinstance(item["feature"], str) for item in contributions)
        ):
            raise ValueError("Invalid model or SHAP metadata")
        record_hash, model_hash = (value.hex() for value in commitments(record, raw))
    except (ValueError, KeyError, TypeError, RecursionError) as error:
        raise ValueError("Expected the canonical JSON of a decision record") from error
    return Fixture(record, raw, record_hash, model_hash)


def open_registry(manifest_path: Path, rpc_url: str):
    config = json.loads(manifest_path.read_text(encoding="utf-8"))
    w3, registry = validated_registry(config, rpc_url)
    return w3, registry, config


def validated_registry(config: dict, rpc_url: str):
    w3 = connect_anvil(rpc_url)
    address = Web3.to_checksum_address(config["contract_address"])
    bytecode = w3.eth.get_code(address)
    if (
        w3.eth.chain_id != config["chain_id"] or not bytecode
        or sha256(bytecode).hexdigest() != config["runtime_bytecode_sha256"]
    ):
        raise ValueError("The deployment manifest does not match the running Anvil node.")
    return w3, w3.eth.contract(address=address, abi=config["abi"])


def register_fixture(fixture: Fixture, database: Path, manifest: Path, rpc_url: str) -> str:
    w3, registry, config = open_registry(manifest, rpc_url)
    with closing(connect(database)) as db:
        try:
            save(db, fixture.record, fixture.canonical_bytes)
        except sqlite3.IntegrityError:
            db.rollback()
        local = get(db, fixture.decision_id)
        if local is None or local["record"] != fixture.record or local["canonical_bytes"] != fixture.canonical_bytes:
            raise ValueError("The demo copy differs from the B handoff.")
        return submit_saved(db, registry, w3, fixture.decision_id, w3.eth.accounts[0],
                            expected_chain_id=config["chain_id"])


def audit_uploaded_record(fixture: Fixture, manifest: Path, rpc_url: str) -> Verification:
    """Look up receipt evidence for the supplied Decision ID in the current registry."""
    w3, registry, config = open_registry(manifest, rpc_url)
    decision_id = fixture.decision_id
    record_id = decision_bytes(decision_id)
    _, _, exists = registry.functions.get_record(record_id).call()
    if not exists:
        return Verification("NOT_FOUND", "Decision commitment is missing on chain")
    events = registry.events.RecordRegistered().get_logs(
        argument_filters={"decision_id": record_id}, from_block=0, to_block="latest",
    )
    if len(events) != 1:
        return Verification("UNAVAILABLE", "Cannot locate a unique registration receipt")
    with closing(connect(Path(":memory:"))) as db:
        save(db, fixture.record, fixture.canonical_bytes)
        with db:
            db.execute("UPDATE decisions SET tx_hash=?, chain_id=? WHERE decision_id=?",
                       (w3.to_hex(events[0].transactionHash), config["chain_id"], decision_id))
        return inspect_decision(db, registry, w3, decision_id, config["min_confirmations"],
                                expected_chain_id=config["chain_id"])


def audit(fixture: Fixture, database: Path, manifest: Path, rpc_url: str,
          decision_id: str, *, simulate_change=False) -> Verification:
    decision_bytes(decision_id)
    if not database.is_file():
        if decision_id == fixture.decision_id:
            return Verification("PENDING", "Decision has no submitted transaction")
        return Verification("NOT_FOUND", "Decision is missing from SQLite")
    with closing(read_only(database)) as db:
        try:
            if get(db, decision_id) is None:
                if decision_id == fixture.decision_id:
                    return Verification("PENDING", "Decision has no submitted transaction")
                return Verification("NOT_FOUND", "Decision is missing from SQLite")
        except (ValueError, TypeError):
            return Verification("MISMATCH", "Saved record is invalid")
        w3, registry, config = open_registry(manifest, rpc_url)
        if not simulate_change:
            return inspect_decision(db, registry, w3, decision_id, config["min_confirmations"],
                                    expected_chain_id=config["chain_id"])
        with closing(sqlite3.connect(":memory:")) as sample:
            db.backup(sample)
            saved = get(sample, decision_id)
            change = "0.20000000" if saved["record"]["risk_probability"] != "0.20000000" else "0.42000000"
            changed = saved["record"] | {"risk_probability": change}
            sample.execute("UPDATE decisions SET display_json=?, canonical_bytes=? WHERE decision_id=?",
                           (json.dumps(changed), canonical_serialize(changed), decision_id))
            return inspect_decision(sample, registry, w3, decision_id, config["min_confirmations"],
                                    expected_chain_id=config["chain_id"])
