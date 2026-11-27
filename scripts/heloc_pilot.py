"""Run one local HELOC audit pilot or register the original B handoff fixture."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
from time import perf_counter

from web3 import Web3

from credit_audit.chain import compile_registry, deploy, verify
from credit_audit.mvp import load_fixture
from credit_audit.records import canonical_serialize, commitments, create_record
from credit_audit.storage import connect, get, save

ROOT = Path(__file__).resolve().parents[1]


def prepare_heloc(args):
    executable = args.author_python or args.author_repo / ".venv" / "Scripts" / "python.exe"
    command = [
        str(executable), str(ROOT / "scripts" / "prepare_heloc_pilot.py"),
        str(args.author_repo), str(args.test_offset),
    ]
    handoff = json.loads(subprocess.check_output(command, encoding="utf-8"))
    record, raw = create_record(handoff["dataset_id"], handoff["prediction"], handoff["explanation"])
    return record, raw, handoff["configuration"] | {"synthetic": False}


def prepare_fixture(directory):
    summary = json.loads((directory / "taiwan_smoke_summary.json").read_text(encoding="utf-8"))
    synthetic = summary["synthetic"]
    if not isinstance(synthetic, bool):
        raise ValueError("The Role B summary is missing its fixture type")
    fixture = load_fixture(directory, synthetic=synthetic)
    return fixture.record, fixture.canonical_bytes, {"synthetic": synthetic, "shap_residual": summary["shap_residual"]}


def register(args, record, raw):
    rpc = f"http://127.0.0.1:{args.port}"
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10}))
    if not w3.is_connected() or w3.eth.chain_id != 31337 or not w3.client_version.lower().startswith("anvil/"):
        raise RuntimeError("A local Anvil node with chain ID 31337 is required")
    compiled = compile_registry(ROOT / "contracts" / "DecisionRegistry.vy")
    writer = w3.eth.accounts[0]
    registry = deploy(w3, compiled, writer)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "decision_record.json").write_bytes(raw)
    decision_id = record["decision_id"]
    id_bytes = bytes.fromhex(decision_id)
    with closing(connect(args.output / "audit.sqlite3")) as db:
        save(db, record, raw)
        saved = get(db, decision_id)
        if saved["canonical_bytes"] != raw:
            raise RuntimeError("SQLite did not retain the canonical bytes")
        record_hash, model_hash = commitments(saved["record"], saved["canonical_bytes"])
        start = perf_counter()
        tx = registry.functions.register_record(id_bytes, record_hash, model_hash).transact({"from": writer})
        with db:
            db.execute("UPDATE decisions SET tx_hash=?, chain_id=? WHERE decision_id=?",
                       (w3.to_hex(tx), w3.eth.chain_id, decision_id))
        receipt = w3.eth.wait_for_transaction_receipt(tx, timeout=30)
        state = "CONFIRMED" if receipt.status == 1 else "TRANSACTION_FAILED"
        with db:
            db.execute("UPDATE decisions SET block_number=?, status=? WHERE decision_id=?",
                       (receipt.blockNumber, state, decision_id))
        confirmation_ms = (perf_counter() - start) * 1000
        if receipt.status != 1:
            raise RuntimeError("Registry transaction failed")
        events = registry.events.RecordRegistered().process_receipt(receipt)
        if len(events) != 1 or dict(events[0].args) != {
            "decision_id": id_bytes, "record_hash": record_hash, "model_version_hash": model_hash, "writer": writer,
        }:
            raise RuntimeError("RecordRegistered event did not match the submitted commitments")
        status = verify(db, registry, w3, decision_id)
        if status != "VERIFIED":
            raise RuntimeError(f"Original record verification returned {status}")
        (args.output / "receipt.json").write_text(w3.to_json(receipt) + "\n", encoding="utf-8")
        with closing(sqlite3.connect(":memory:")) as copy:
            db.backup(copy)
            altered = dict(record)
            altered["risk_probability"] = "0.00000000" if record["risk_probability"] != "0.00000000" else "1.00000000"
            with copy:
                copy.execute("UPDATE decisions SET display_json=?, canonical_bytes=? WHERE decision_id=?",
                             (json.dumps(altered), canonical_serialize(altered), decision_id))
            changed_status = verify(copy, registry, w3, decision_id)
        if changed_status != "MISMATCH":
            raise RuntimeError(f"Altered record verification returned {changed_status}")
    return {
        "rpc_port": args.port, "anvil_version": w3.client_version, "abi": compiled["abi"],
        "chain_id": w3.eth.chain_id, "contract_address": registry.address,
        "runtime_bytecode_sha256": sha256(w3.eth.get_code(registry.address)).hexdigest(),
        "tx_hash": w3.to_hex(tx), "block_number": receipt.blockNumber, "gas_used": receipt.gasUsed,
        "gas_price_wei": receipt.effectiveGasPrice, "fee_wei": receipt.gasUsed * receipt.effectiveGasPrice,
        "confirmation_ms": round(confirmation_ms, 3),
        "record_hash": record_hash.hex(), "model_version_hash": model_hash.hex(),
        "verification": status, "altered_copy_verification": changed_status,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-repo", type=Path, default=ROOT / "artifacts" / "cheon_iclr2025")
    parser.add_argument("--author-python", type=Path, help="Python from the pinned author environment")
    parser.add_argument("--test-offset", type=int, default=0)
    parser.add_argument("--fixture-dir", type=Path, help="Anchor a supplied synthetic or HELOC Role B fixture")
    parser.add_argument("--port", type=int, default=18545)
    parser.add_argument("--output", type=Path, required=True, help="A new directory for the SQLite and receipt evidence")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("--output must be a new directory")
    record, raw, configuration = prepare_fixture(args.fixture_dir) if args.fixture_dir else prepare_heloc(args)
    summary = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "configuration": configuration, "decision_id": record["decision_id"],
        "dataset_id": record["dataset_id"], "schema_version": record["schema_version"],
        "model_version": record["model_version"], "model_artifact_sha256": record["model_artifact_sha256"],
        "features_explained": len(record["shap_explanation"]["feature_contributions"]),
        "risk_probability": record["risk_probability"], "canonical_byte_count": len(raw),
    } | register(args, record, raw)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "abi"}, indent=2))


if __name__ == "__main__":
    main()
