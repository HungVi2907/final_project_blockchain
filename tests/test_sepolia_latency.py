import io
import json
from types import SimpleNamespace
from unittest.mock import Mock

from web3 import Web3
from web3.exceptions import TimeExhausted

from scripts.sepolia_latency import SETTLEMENT_TIMEOUT, send, summarize


def test_late_receipt_settles_without_resubmission():
    signed = SimpleNamespace(hash=b"h" * 32, raw_transaction=b"signed")
    signer = Mock(address="writer")
    signer.sign_transaction.return_value = signed
    call = Mock()
    call.estimate_gas.return_value = 50_000
    w3 = Mock(to_hex=Web3.to_hex)
    w3.eth.get_balance.return_value = 100_000
    w3.eth.get_transaction_count.return_value = 0
    w3.eth.send_raw_transaction.return_value = signed.hash
    receipt = SimpleNamespace(status=1, blockNumber=42, gasUsed=50_000, effectiveGasPrice=1)
    w3.eth.wait_for_transaction_receipt.side_effect = [TimeExhausted(), receipt]
    journal = io.StringIO()

    result, details = send(w3, call, signer, "register", {"maxFeePerGas": 1}, journal)

    assert result is receipt
    assert details["within_timeout"] is False
    w3.eth.send_raw_transaction.assert_called_once_with(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt.assert_called_with(signed.hash, timeout=SETTLEMENT_TIMEOUT, poll_latency=1)
    entries = [json.loads(line) for line in journal.getvalue().splitlines()]
    assert [entry["status"] for entry in entries] == ["SUBMITTING", "TIMEOUT", "CONFIRMED_LATE"]
    assert {entry["tx_hash"] for entry in entries} == {Web3.to_hex(signed.hash)}


def test_summary_retains_timeouts_in_sample_count_and_tail_rank():
    assert summarize([*range(1, 29), None, None]) == {
        "samples": 30, "confirmed": 28, "timeouts": 2,
        "median_seconds": 15.5, "p95_seconds": None,
    }
    assert summarize([*range(1, 30), None])["p95_seconds"] == 29
