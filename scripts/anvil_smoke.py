"""Register a v1 decision on disposable Anvil and verify tamper detection."""
import argparse
from pathlib import Path
import json
import sqlite3

from web3 import Web3

from credit_audit.chain import compile_registry, deploy, verify
from credit_audit.records import canonical_serialize, commitments
from credit_audit.storage import connect, get

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "artifacts")
    artifact_dir = parser.parse_args().artifact_dir

    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545", request_kwargs={"timeout": 10}))
    if not w3.is_connected() or w3.eth.chain_id != 31337:
        raise RuntimeError("Local Anvil at chain 31337 is required")
    admin = w3.eth.accounts[0]
    non_writer = w3.eth.accounts[1]
    summary = json.loads((artifact_dir / "taiwan_smoke_summary.json").read_text(encoding="utf-8"))
    db = connect(artifact_dir / "audit.sqlite3")
    decision_id = summary["decision_id"]
    saved = get(db, decision_id)
    if saved is None:
        raise RuntimeError(f"Decision {decision_id} from the smoke summary is missing from SQLite")
    record_hash, model_hash = commitments(saved["record"], saved["canonical_bytes"])
    if (record_hash.hex(), model_hash.hex()) != (summary["record_hash"], summary["model_version_hash"]):
        raise RuntimeError("SQLite commitments do not match the smoke summary")
    registry = deploy(w3, compile_registry(ROOT / "contracts/DecisionRegistry.vy"), admin)
    assert verify(db, registry, w3, decision_id) == "NOT_FOUND"
    try:
        registry.functions.register_record(bytes.fromhex(decision_id), record_hash, model_hash).transact({"from": non_writer})
    except Exception:
        pass
    else:
        raise AssertionError("Non-writer was allowed to register")
    tx = registry.functions.register_record(bytes.fromhex(decision_id), record_hash, model_hash).transact({"from": admin})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    assert receipt.status == 1
    db.execute("UPDATE decisions SET tx_hash=?, chain_id=?, block_number=?, status=? WHERE decision_id=?", (tx.hex(), w3.eth.chain_id, receipt.blockNumber, "CONFIRMED", decision_id))
    db.commit()
    assert verify(db, registry, w3, decision_id) == "VERIFIED"
    audit_copy = sqlite3.connect(":memory:")
    db.backup(audit_copy)
    tampered = saved["record"].copy()
    tampered["risk_probability"] = "0.99999999"
    audit_copy.execute("UPDATE decisions SET display_json=? WHERE decision_id=?", (json.dumps(tampered), decision_id))
    audit_copy.commit()
    assert verify(audit_copy, registry, w3, decision_id) == "MISMATCH"
    audit_copy.execute("UPDATE decisions SET canonical_bytes=? WHERE decision_id=?", (canonical_serialize(tampered), decision_id))
    audit_copy.commit()
    assert verify(audit_copy, registry, w3, decision_id) == "MISMATCH"
    result = {
        "chain_id": w3.eth.chain_id, "contract_address": registry.address,
        "decision_id": decision_id, "tx_hash": tx.hex(), "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed, "verification": "VERIFIED", "tampered_verification": "MISMATCH",
        "local_record_and_hash_tampering_detected": True, "non_writer_rejected": True,
    }
    (artifact_dir / "anvil_smoke_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

