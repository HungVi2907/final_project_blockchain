"""Vyper deployment, transaction submission and dual-hash verification."""
from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

from hexbytes import HexBytes
from requests.exceptions import RequestException
from web3 import Web3
from web3.exceptions import BlockNotFound, TransactionNotFound, Web3Exception
from web3.logs import DISCARD

from credit_audit.records import commitments
from credit_audit.storage import get

RPC_ERRORS = (Web3Exception, RequestException, OSError)
DEFAULT_RPC = "http://127.0.0.1:8545"
ANVIL_CHAIN_ID = 31337


@dataclass(frozen=True)
class Verification:
    status: str
    reason: str
    tx_hash: str | None = None
    block_number: int | None = None
    gas_used: int | None = None
    confirmations: int | None = None


def decision_bytes(decision_id: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{64}", decision_id):
        raise ValueError("Decision ID must be 64 lowercase hex characters")
    return bytes.fromhex(decision_id)


def connect_anvil(rpc_url: str):
    url = urlsplit(rpc_url)
    if (
        url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}
        or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}
    ):
        raise ValueError("Use a local HTTP Anvil endpoint without credentials")
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 5}))
    if w3.eth.chain_id != ANVIL_CHAIN_ID or "anvil" not in w3.client_version.lower():
        raise ValueError("Expected a local Anvil node on chain 31337")
    return w3


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


def register(registry, sender: str, decision_id: bytes, record_hash: bytes, model_version_hash: bytes):
    return registry.functions.register_record(
        decision_id, record_hash, model_version_hash
    ).transact({"from": sender})


def submit_saved(db, registry, w3, decision_id: str, sender: str, *, expected_chain_id: int) -> str:
    """Submit an existing decision once. Return the stored tx hash on subsequent calls."""
    record_id = decision_bytes(decision_id)
    chain_id = w3.eth.chain_id
    if chain_id != expected_chain_id or not w3.eth.get_code(registry.address):
        raise ValueError("Configured registry is unavailable on the expected chain")
    with db:
        db.execute("BEGIN IMMEDIATE")
        saved = get(db, decision_id)
        if saved is None:
            raise ValueError("Decision is missing from SQLite")
        if saved["chain_id"] not in (None, chain_id):
            raise ValueError("Decision belongs to a different chain")
        if saved["tx_hash"]:
            return saved["tx_hash"]
        if saved["status"] != "PENDING":
            raise ValueError("Decision needs audit before another submission")
        if saved["record"]["decision_id"] != decision_id:
            raise ValueError("Decision ID disagrees with saved record")
        args = (record_id, *commitments(saved["record"], saved["canonical_bytes"]))
        call = registry.functions.register_record(*args)
        # Preflight catches rejected writes before reserving the submission.
        call.estimate_gas({"from": sender})
        db.execute(
            "UPDATE decisions SET chain_id=?, status='SUBMITTING' WHERE decision_id=?",
            (chain_id, decision_id),
        )
    # Keep the reservation if the RPC fails after the request may have been sent.
    tx_hash = w3.to_hex(register(registry, sender, *args))
    with db:
        db.execute(
            "UPDATE decisions SET tx_hash=?, status='PENDING' WHERE decision_id=?",
            (tx_hash, decision_id),
        )
    return tx_hash


def inspect_decision(
    db, registry, w3, decision_id: str, min_confirmations: int = 1,
    *, expected_chain_id: int | None = None,
) -> Verification:
    if min_confirmations < 1:
        raise ValueError("At least one confirmation is required")
    record_id = decision_bytes(decision_id)
    try:
        saved = get(db, decision_id)
    except sqlite3.Error:
        return Verification("UNAVAILABLE", "Cannot read SQLite")
    except (ValueError, TypeError):
        return Verification("MISMATCH", "Saved record is invalid")
    if saved is None:
        return Verification("NOT_FOUND", "Decision is missing from SQLite")
    tx_hash = saved["tx_hash"]
    if not tx_hash:
        if saved["status"] == "TRANSACTION_FAILED":
            return Verification("TRANSACTION_FAILED", "Submission failed")
        if saved["status"] == "SUBMITTING":
            return Verification("PENDING", "Submission is in progress or needs audit")
        return Verification("PENDING", "Decision has no submitted transaction")
    try:
        tx_id = HexBytes(tx_hash)
    except (ValueError, TypeError):
        return Verification("MISMATCH", "Saved transaction hash is invalid", tx_hash)
    if len(tx_id) != 32:
        return Verification("MISMATCH", "Saved transaction hash is invalid", tx_hash)
    try:
        chain_id = w3.eth.chain_id
        if chain_id != saved["chain_id"] or expected_chain_id not in (None, chain_id):
            return Verification("UNAVAILABLE", "RPC chain does not match the decision", tx_hash)
        receipt = w3.eth.get_transaction_receipt(tx_id)
        if receipt.transactionHash != tx_id:
            return Verification("MISMATCH", "Receipt does not match the saved transaction hash", tx_hash)
        block = w3.eth.get_block(receipt.blockNumber)
        if block.hash != receipt.blockHash:
            return Verification("PENDING", "Receipt is no longer in the canonical block", tx_hash)
        confirmations = w3.eth.block_number - receipt.blockNumber + 1
        details = (tx_hash, receipt.blockNumber, receipt.gasUsed, confirmations)
        if confirmations < min_confirmations:
            return Verification("PENDING", "Waiting for block confirmations", *details)
        if (receipt.to or "").lower() != registry.address.lower():
            return Verification("MISMATCH", "Transaction targets a different registry", *details)
        if receipt.status != 1:
            return Verification("TRANSACTION_FAILED", "Transaction reverted on chain", *details)
        chain_hash, chain_model, exists = registry.functions.get_record(record_id).call()
        if not exists:
            return Verification("NOT_FOUND", "Decision commitment is missing on chain", *details)
        events = registry.events.RecordRegistered().process_receipt(receipt, errors=DISCARD)
        registered = any(
            event.address.lower() == registry.address.lower()
            and event.args.decision_id == record_id
            and event.args.record_hash == chain_hash
            and event.args.model_version_hash == chain_model
            for event in events
        )
        if not registered:
            return Verification("MISMATCH", "Receipt does not register this commitment", *details)
        if w3.eth.get_block(receipt.blockNumber).hash != receipt.blockHash:
            return Verification("PENDING", "Receipt block changed during verification", tx_hash)
    except (TransactionNotFound, BlockNotFound):
        return Verification("PENDING", "Receipt is pending or no longer on chain", tx_hash)
    except RPC_ERRORS:
        return Verification("UNAVAILABLE", "Cannot read the configured chain", tx_hash)

    try:
        record = saved["record"]
        if record["decision_id"] != decision_id:
            raise ValueError("Decision ID disagrees with saved record")
        local_hash, local_model = commitments(record, saved["canonical_bytes"])
    except (ValueError, TypeError, KeyError):
        return Verification("MISMATCH", "Saved record disagrees with canonical bytes or ID", *details)
    if local_hash != chain_hash or local_model != chain_model:
        return Verification("MISMATCH", "At least one local hash differs from the registry", *details)
    return Verification("VERIFIED", "Confirmed registration and both hashes match", *details)


def verify(db, registry, w3, decision_id: str, min_confirmations: int = 1) -> str:
    return inspect_decision(db, registry, w3, decision_id, min_confirmations).status

