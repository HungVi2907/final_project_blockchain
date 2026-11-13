# @version 0.4.3

struct Commitment:
    record_hash: bytes32
    model_version_hash: bytes32
    exists: bool

event RecordRegistered:
    decision_id: indexed(bytes32)
    record_hash: bytes32
    model_version_hash: bytes32
    writer: indexed(address)

event WriterUpdated:
    writer: indexed(address)
    allowed: bool

admin: public(address)
writers: public(HashMap[address, bool])
records: HashMap[bytes32, Commitment]

@deploy
def __init__():
    self.admin = msg.sender
    self.writers[msg.sender] = True

@external
def grant_writer(writer: address):
    assert msg.sender == self.admin, "admin only"
    assert writer != empty(address), "zero writer"
    self.writers[writer] = True
    log WriterUpdated(writer=writer, allowed=True)

@external
def revoke_writer(writer: address):
    assert msg.sender == self.admin, "admin only"
    self.writers[writer] = False
    log WriterUpdated(writer=writer, allowed=False)

@external
def register_record(decision_id: bytes32, record_hash: bytes32, model_version_hash: bytes32):
    assert self.writers[msg.sender], "writer only"
    assert decision_id != empty(bytes32), "zero id"
    assert record_hash != empty(bytes32), "zero record hash"
    assert model_version_hash != empty(bytes32), "zero model hash"
    assert not self.records[decision_id].exists, "duplicate id"
    self.records[decision_id] = Commitment(record_hash=record_hash, model_version_hash=model_version_hash, exists=True)
    log RecordRegistered(decision_id=decision_id, record_hash=record_hash, model_version_hash=model_version_hash, writer=msg.sender)

@external
@view
def get_record(decision_id: bytes32) -> (bytes32, bytes32, bool):
    item: Commitment = self.records[decision_id]
    return item.record_hash, item.model_version_hash, item.exists

@external
@view
def verify_record_hash(decision_id: bytes32, candidate_hash: bytes32) -> bool:
    item: Commitment = self.records[decision_id]
    return item.exists and item.record_hash == candidate_hash

