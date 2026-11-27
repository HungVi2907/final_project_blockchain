"""Read saved pilot evidence without writing to the pilot database or registry."""

from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path

from credit_audit.chain import Verification, decision_bytes, inspect_decision
from credit_audit.mvp import Fixture, read_only, validated_registry
from credit_audit.records import commitments
from credit_audit.storage import get


@dataclass(frozen=True)
class Pilot:
    directory: Path
    summary: dict
    fixture: Fixture

    @property
    def database(self) -> Path:
        return self.directory / "audit.sqlite3"

    def verify(self, decision_id: str) -> Verification:
        if decision_id != self.fixture.decision_id:
            return Verification("NOT_FOUND", "Decision is outside the selected pilot")
        port = int(self.summary["rpc_port"])
        if not 1 <= port <= 65_535:
            raise ValueError("Invalid pilot RPC port")
        w3, registry = validated_registry(self.summary, f"http://127.0.0.1:{port}")
        with closing(read_only(self.database)) as db:
            return inspect_decision(db, registry, w3, decision_id, expected_chain_id=self.summary["chain_id"])


def load_pilot(directory: Path) -> Pilot:
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    if not isinstance(summary.get("configuration", {}), dict):
        raise ValueError("Invalid pilot configuration")
    if not isinstance(summary["chain_id"], int) or not isinstance(summary["contract_address"], str):
        raise ValueError("Invalid pilot registry metadata")
    decision_id = summary["decision_id"]
    decision_bytes(decision_id)
    with closing(read_only(directory / "audit.sqlite3")) as db:
        saved = get(db, decision_id)
    if saved is None or saved["record"]["decision_id"] != decision_id:
        raise ValueError("The selected pilot has no corresponding SQLite record")
    record, raw = saved["record"], saved["canonical_bytes"]
    record_hash, model_hash = (value.hex() for value in commitments(record, raw))
    return Pilot(directory, summary, Fixture(record, raw, record_hash, model_hash))
