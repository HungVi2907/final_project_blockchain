"""Vyper compilation, local deployment and dual-hash verification."""
from pathlib import Path

from credit_audit.records import canonical_serialize, commitments
from credit_audit.storage import get


def compile_registry(path: Path):
    from vyper import compile_code
    source = path.read_text(encoding="utf-8")
    return compile_code(source, output_formats=["abi", "bytecode"])


def deploy(w3, compiled, sender: str):
    factory = w3.eth.contract(abi=compiled["abi"], bytecode=compiled["bytecode"])
    tx = factory.constructor().transact({"from": sender})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    if receipt.status != 1:
        raise RuntimeError("Contract deployment failed")
    return w3.eth.contract(address=receipt.contractAddress, abi=compiled["abi"])


def verify(db, registry, w3, decision_id: str, min_confirmations: int = 1) -> str:
    saved = get(db, decision_id)
    chain_hash, chain_model, exists = registry.functions.get_record(bytes.fromhex(decision_id)).call()
    if saved is None or not exists:
        return "NOT_FOUND"
    if saved["status"] == "TRANSACTION_FAILED":
        return "TRANSACTION_FAILED"
    if not saved["tx_hash"]:
        return "PENDING"
    try:
        receipt = w3.eth.get_transaction_receipt(saved["tx_hash"])
    except Exception:
        return "PENDING"
    if receipt.status != 1:
        return "TRANSACTION_FAILED"
    if w3.eth.block_number - receipt.blockNumber + 1 < min_confirmations:
        return "PENDING"
    try:
        record = saved["record"]
        if canonical_serialize(record) != saved["canonical_bytes"]:
            return "MISMATCH"
        local_hash, local_model = commitments(record, saved["canonical_bytes"])
        return "VERIFIED" if local_hash == chain_hash and local_model == chain_model else "MISMATCH"
    except (ValueError, TypeError, KeyError):
        return "MISMATCH"

