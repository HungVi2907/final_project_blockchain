from contextlib import closing
from hashlib import sha256
import json

import pytest
from requests.exceptions import ConnectionError

import credit_audit.chain as chain
from credit_audit.chain import inspect_decision, register, submit_saved
from credit_audit.records import canonical_serialize, commitments, create_record
from credit_audit.storage import connect, save


@pytest.fixture
def decision(tmp_path):
    record, raw = create_record(
        "taiwan_uci350",
        {"risk_probability": 0.72, "model_version": "synthetic-v1", "model_artifact_sha256": "a" * 64},
        {"method": "synthetic", "output_space": "probability", "base_value": 0.4,
         "model_output": 0.72, "feature_contributions": [{"feature": "demo", "value": 0.32}]},
    )
    with closing(connect(tmp_path / "audit.sqlite3")) as db:
        save(db, record, raw)
        yield db, record, raw


def mine(w3):
    w3.manager.request_blocking("evm_mine", [])


def test_pending_retry_confirmed_and_reorg(anvil, registry, decision):
    w3, _ = anvil
    db, record, raw = decision
    decision_id = record["decision_id"]
    sender = w3.eth.accounts[0]
    expected_record = sha256(raw).digest()
    expected_model = sha256(("synthetic-v1|" + "a" * 64).encode()).digest()
    assert inspect_decision(db, registry, w3, "f" * 64).status == "NOT_FOUND"
    assert inspect_decision(db, registry, w3, decision_id).status == "PENDING"
    snapshot = w3.manager.request_blocking("evm_snapshot", [])
    w3.manager.request_blocking("evm_setAutomine", [False])
    try:
        tx = submit_saved(db, registry, w3, decision_id, sender, expected_chain_id=31337)
        assert inspect_decision(db, registry, w3, decision_id).status == "PENDING"
        assert submit_saved(db, registry, w3, decision_id, sender, expected_chain_id=31337) == tx
        mine(w3)
        assert inspect_decision(db, registry, w3, decision_id, min_confirmations=2).status == "PENDING"
        mine(w3)
        result = inspect_decision(db, registry, w3, decision_id, min_confirmations=2)
        assert result.status == "VERIFIED"
        assert result.tx_hash == tx and result.confirmations == 2
        assert registry.functions.get_record(bytes.fromhex(decision_id)).call() == [expected_record, expected_model, True]
        assert w3.manager.request_blocking("evm_revert", [snapshot])
        assert inspect_decision(db, registry, w3, decision_id).status == "PENDING"
    finally:
        w3.manager.request_blocking("evm_setAutomine", [True])


@pytest.mark.parametrize("wrong_hash", ["record", "model"])
def test_each_commitment_must_match(anvil, registry, decision, wrong_hash):
    w3, _ = anvil
    db, record, raw = decision
    decision_id = record["decision_id"]
    record_hash, model_hash = commitments(record, raw)
    if wrong_hash == "record":
        record_hash = b"r" * 32
    else:
        model_hash = b"m" * 32
    tx = register(registry, w3.eth.accounts[0], bytes.fromhex(decision_id), record_hash, model_hash)
    with db:
        db.execute("UPDATE decisions SET tx_hash=?, chain_id=? WHERE decision_id=?",
                   (w3.to_hex(tx), 31337, decision_id))
    assert inspect_decision(db, registry, w3, decision_id).status == "MISMATCH"


def test_tampering_and_rpc_outage(anvil, registry, decision, monkeypatch):
    w3, _ = anvil
    db, record, _ = decision
    decision_id = record["decision_id"]
    submit_saved(db, registry, w3, decision_id, w3.eth.accounts[0], expected_chain_id=31337)
    assert inspect_decision(db, registry, w3, decision_id).status == "VERIFIED"
    assert inspect_decision(db, registry, w3, decision_id, expected_chain_id=1).status == "UNAVAILABLE"
    changed = record | {"risk_probability": "0.99000000"}
    with db:
        db.execute("UPDATE decisions SET display_json=?, canonical_bytes=? WHERE decision_id=?",
                   (json.dumps(changed), canonical_serialize(changed), decision_id))
    assert inspect_decision(db, registry, w3, decision_id).status == "MISMATCH"

    def offline(_):
        raise ConnectionError("RPC offline")

    monkeypatch.setattr(w3.eth, "get_transaction_receipt", offline)
    assert inspect_decision(db, registry, w3, decision_id).status == "UNAVAILABLE"


def test_reverted_receipt_and_unrelated_success(anvil, registry, decision):
    w3, _ = anvil
    db, record, raw = decision
    decision_id = record["decision_id"]
    admin, non_writer = w3.eth.accounts[:2]
    args = (bytes.fromhex(decision_id), *commitments(record, raw))
    failed = registry.functions.register_record(*args).transact({"from": non_writer, "gas": 150_000})
    assert w3.eth.wait_for_transaction_receipt(failed).status == 0
    with db:
        db.execute("UPDATE decisions SET tx_hash=?, chain_id=? WHERE decision_id=?",
                   (w3.to_hex(failed), 31337, decision_id))
    assert inspect_decision(db, registry, w3, decision_id).status == "TRANSACTION_FAILED"
    register(registry, admin, *args)
    unrelated = registry.functions.grant_writer(non_writer).transact({"from": admin})
    with db:
        db.execute("UPDATE decisions SET tx_hash=? WHERE decision_id=?", (w3.to_hex(unrelated), decision_id))
    assert inspect_decision(db, registry, w3, decision_id).status == "MISMATCH"


def test_rpc_failure_during_submit_keeps_reservation(anvil, registry, decision, monkeypatch):
    w3, _ = anvil
    db, record, _ = decision
    decision_id = record["decision_id"]
    sender = w3.eth.accounts[0]

    def send_then_disconnect(*args):
        register(*args)
        raise ConnectionError("Lost the response after sending")

    monkeypatch.setattr(chain, "register", send_then_disconnect)
    with pytest.raises(ConnectionError):
        submit_saved(db, registry, w3, decision_id, sender, expected_chain_id=31337)
    nonce = w3.eth.get_transaction_count(sender)
    assert registry.functions.get_record(bytes.fromhex(decision_id)).call()[2]
    with pytest.raises(ValueError, match="needs audit"):
        submit_saved(db, registry, w3, decision_id, sender, expected_chain_id=31337)
    assert w3.eth.get_transaction_count(sender) == nonce
    result = inspect_decision(db, registry, w3, decision_id)
    assert result.status == "PENDING"
    assert "needs audit" in result.reason
