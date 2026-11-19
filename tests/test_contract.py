import pytest
from web3.exceptions import ContractLogicError

from credit_audit.chain import register

ID = bytes.fromhex("12" * 32)
RECORD = bytes.fromhex("34" * 32)
MODEL = bytes.fromhex("56" * 32)
ZERO = bytes(32)


def test_writer_grant_revoke_and_registration_events(anvil, registry):
    w3, _ = anvil
    admin, writer = w3.eth.accounts[:2]
    assert registry.functions.admin().call() == admin
    assert registry.functions.writers(admin).call()
    assert registry.functions.get_record(ID).call() == [ZERO, ZERO, False]
    assert not registry.functions.verify_record_hash(ID, ZERO).call()

    with pytest.raises(ContractLogicError, match="writer only"):
        register(registry, writer, ID, RECORD, MODEL)
    for action in (registry.functions.grant_writer, registry.functions.revoke_writer):
        with pytest.raises(ContractLogicError, match="admin only"):
            action(writer).transact({"from": writer})
    with pytest.raises(ContractLogicError, match="zero writer"):
        registry.functions.grant_writer("0x" + "00" * 20).transact({"from": admin})

    grant = registry.functions.grant_writer(writer).transact({"from": admin})
    event, = registry.events.WriterUpdated().process_receipt(w3.eth.wait_for_transaction_receipt(grant))
    assert dict(event.args) == {"writer": writer, "allowed": True}
    assert registry.functions.writers(writer).call()
    receipt = w3.eth.wait_for_transaction_receipt(register(registry, writer, ID, RECORD, MODEL))
    assert receipt.status == 1
    event, = registry.events.RecordRegistered().process_receipt(receipt)
    assert dict(event.args) == {
        "decision_id": ID, "record_hash": RECORD, "model_version_hash": MODEL, "writer": writer,
    }
    assert registry.functions.verify_record_hash(ID, RECORD).call()
    assert not registry.functions.verify_record_hash(ID, MODEL).call()

    revoke = registry.functions.revoke_writer(writer).transact({"from": admin})
    event, = registry.events.WriterUpdated().process_receipt(w3.eth.wait_for_transaction_receipt(revoke))
    assert dict(event.args) == {"writer": writer, "allowed": False}
    assert not registry.functions.writers(writer).call()
    with pytest.raises(ContractLogicError, match="writer only"):
        register(registry, writer, MODEL, RECORD, ID)
    with pytest.raises(ContractLogicError, match="duplicate id"):
        register(registry, admin, ID, MODEL, RECORD)
    assert registry.functions.get_record(ID).call() == [RECORD, MODEL, True]


@pytest.mark.parametrize(
    ("args", "reason"),
    [((ZERO, RECORD, MODEL), "zero id"), ((ID, ZERO, MODEL), "zero record hash"),
     ((ID, RECORD, ZERO), "zero model hash")],
)
def test_zero_commitments_revert(anvil, registry, args, reason):
    w3, _ = anvil
    with pytest.raises(ContractLogicError, match=reason):
        register(registry, w3.eth.accounts[0], *args)
    assert not registry.functions.get_record(args[0]).call()[2]
