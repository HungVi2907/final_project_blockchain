"""Measure one of the two registered T5-02 latency windows on Sepolia."""

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import ceil
import os
from pathlib import Path
from secrets import token_bytes
from statistics import median
from time import monotonic
from urllib.parse import urlsplit

from requests.exceptions import RequestException
from web3 import Web3
from web3.exceptions import TimeExhausted, Web3Exception

from credit_audit.chain import compile_registry


ROOT = Path(__file__).resolve().parents[1]
CHAIN_ID = 11155111
SAMPLES = 15
RECEIPT_TIMEOUT = 120
SETTLEMENT_TIMEOUT = 120
GAS_BUDGET = {"grant": 55_000, "register": 105_000, "revoke": 35_000}


def save_json(path, value):
    with path.open("x", encoding="utf-8") as file:
        json.dump(value, file, indent=2)
        file.write("\n")


def estimate_limit(call, signer):
    estimated = call.estimate_gas({"from": signer.address})
    return (estimated * 11 + 9) // 10


def send(w3, call, signer, operation, fees, journal):
    gas_limit = estimate_limit(call, signer)
    if w3.eth.get_balance(signer.address) < gas_limit * fees["maxFeePerGas"]:
        raise ValueError(f"Insufficient Sepolia balance for {operation} at the current gas estimate")
    tx = call.build_transaction({
        "from": signer.address, "chainId": CHAIN_ID, "gas": gas_limit,
        "nonce": w3.eth.get_transaction_count(signer.address, "pending"), **fees,
    })
    signed = signer.sign_transaction(tx)
    record = {
        "operation": operation, "tx_hash": w3.to_hex(signed.hash),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "gas_limit": gas_limit,
    }

    def log(status, **details):
        journal.write(json.dumps(record | {"status": status} | details) + "\n")
        journal.flush()

    log("SUBMITTING")
    start = monotonic()
    timed_out = False
    try:
        if w3.eth.send_raw_transaction(signed.raw_transaction) != signed.hash:
            raise RuntimeError("RPC returned a different transaction hash")
        remaining = max(0, RECEIPT_TIMEOUT - (monotonic() - start))
        try:
            receipt = w3.eth.wait_for_transaction_receipt(signed.hash, timeout=remaining, poll_latency=1)
        except TimeExhausted:
            timed_out = True
            log("TIMEOUT", timeout_seconds=RECEIPT_TIMEOUT)
            if operation == "deploy":
                raise
            # The next write depends on the current registry state. Wait for this
            # same transaction to settle before attempting it.
            receipt = w3.eth.wait_for_transaction_receipt(signed.hash, timeout=SETTLEMENT_TIMEOUT, poll_latency=1)
    except TimeExhausted:
        log("UNSETTLED")
        raise RuntimeError(f"{operation} is still unconfirmed. Check the recorded transaction before starting a new run") from None
    except Exception as error:
        log("RPC_ERROR", error_type=type(error).__name__)
        raise RuntimeError(f"{operation} could not be confirmed. Check the recorded transaction") from None
    elapsed = monotonic() - start
    within_timeout = not timed_out and elapsed <= RECEIPT_TIMEOUT
    if not within_timeout and not timed_out:
        log("TIMEOUT", timeout_seconds=RECEIPT_TIMEOUT)
    details = {
        "received_at": datetime.now(timezone.utc).isoformat(), "latency_seconds": elapsed,
        "within_timeout": within_timeout,
        "block": receipt.blockNumber, "gas": receipt.gasUsed,
        "fee_wei": receipt.gasUsed * receipt.effectiveGasPrice,
    }
    if receipt.status != 1:
        log("REVERTED", **details)
        raise RuntimeError(f"{operation} reverted")
    log("CONFIRMED" if within_timeout else "CONFIRMED_LATE", **details)
    return receipt, details


def run_samples(w3, registry, admin, writer, fees, journal, *, samples=SAMPLES):
    timings = {key: [] for key in ("grant", "register", "revoke")}
    for _ in range(samples):
        decision = (token_bytes(32), token_bytes(32), token_bytes(32))
        for name, signer, call in (
            ("grant", admin, registry.functions.grant_writer(writer.address)),
            ("register", writer, registry.functions.register_record(*decision)),
            ("revoke", admin, registry.functions.revoke_writer(writer.address)),
        ):
            _, result = send(w3, call, signer, name, fees, journal)
            timings[name].append(result["latency_seconds"] if result["within_timeout"] else None)
            if name == "register" and tuple(registry.functions.get_record(decision[0]).call()) != (*decision[1:], True):
                raise RuntimeError("The registered commitments disagree with the receipt")
        if registry.functions.writers(writer.address).call():
            raise RuntimeError("Writer permission was not revoked")
    return timings


def summarize(values):
    ordered = sorted(value for value in values if value is not None)
    count = len(values)
    center = (count - 1) // 2
    upper_center = count // 2
    tail = ceil(0.95 * count) - 1
    return {
        "samples": count, "confirmed": len(ordered), "timeouts": count - len(ordered),
        "median_seconds": median(ordered[center:upper_center + 1]) if upper_center < len(ordered) else None,
        "p95_seconds": ordered[tail] if 0 <= tail < len(ordered) else None,
    }


def run_window(w3, admin, writer, fees, output, window, provider):
    if w3.eth.chain_id != CHAIN_ID or admin.address == writer.address:
        raise ValueError("Use chain 11155111 and two distinct testnet accounts")
    compiled = compile_registry(ROOT / "contracts/DecisionRegistry.vy")
    if window == 1:
        factory = w3.eth.contract(abi=compiled["abi"], bytecode=compiled["bytecode"])
        constructor = factory.constructor()
        deploy_gas = estimate_limit(constructor, admin)
    else:
        deploy_gas = 0
    fee_cap = fees["maxFeePerGas"]
    admin_gas = SAMPLES * (GAS_BUDGET["grant"] + GAS_BUDGET["revoke"]) + deploy_gas
    for role, signer, gas in (("admin", admin, admin_gas), ("writer", writer, SAMPLES * GAS_BUDGET["register"])):
        if w3.eth.get_balance(signer.address) < gas * fee_cap:
            raise ValueError(f"Sepolia {role} balance is below the maximum fee budget for this window")

    registry_path = output / "registry.json"
    setup = {"admin": admin.address, "writer": writer.address, "fees_wei": fees, "provider": provider, "chain_id": CHAIN_ID}
    if window == 2:
        first = json.loads((output / "window-1/summary.json").read_bytes())
        if datetime.now(timezone.utc) - datetime.fromisoformat(first["finished_at"]) < timedelta(hours=6):
            raise ValueError("Wait at least six hours after window 1 finishes")
        saved = json.loads(registry_path.read_bytes())
        if any(saved[key] != value for key, value in setup.items()):
            raise ValueError("Use the same provider, test accounts and fee policy as window 1")
        code = w3.eth.get_code(saved["address"])
        if not code or sha256(code).hexdigest() != saved["runtime_bytecode_sha256"]:
            raise ValueError("On-chain registry does not match the window 1 deployment")
        registry = w3.eth.contract(address=saved["address"], abi=compiled["abi"])
        if registry.functions.admin().call() != admin.address or registry.functions.writers(writer.address).call():
            raise ValueError("Unexpected registry roles before window 2")

    destination = output / f"window-{window}"
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "transactions.jsonl").open("x", encoding="utf-8") as journal:
        if window == 1:
            receipt, _ = send(w3, constructor, admin, "deploy", fees, journal)
            registry = w3.eth.contract(address=receipt.contractAddress, abi=compiled["abi"])
            save_json(registry_path, setup | {
                "address": registry.address, "runtime_bytecode_sha256": sha256(w3.eth.get_code(registry.address)).hexdigest(),
            })
        started = datetime.now(timezone.utc).isoformat()
        block = w3.eth.get_block("latest")
        results = run_samples(w3, registry, admin, writer, fees, journal)
    save_json(destination / "summary.json", {
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "start_block": block.number, "base_fee_at_start_wei": block.baseFeePerGas,
        "measured_by_operation": {key: summarize(values) for key, values in results.items()},
        "latencies_seconds": results,
    })
    if window == 2:
        combined = {key: summarize(first["latencies_seconds"][key] + values) for key, values in results.items()}
        register = combined["register"]
        save_json(output / "summary.json", {
            "windows": ["window-1/summary.json", "window-2/summary.json"], "combined": combined,
            "passes": register["confirmed"] >= 27 and register["median_seconds"] <= 30,
        })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-fee-gwei", type=int, required=True)
    parser.add_argument("--priority-fee-gwei", type=int, required=True)
    args = parser.parse_args()
    if not 0 < args.priority_fee_gwei <= args.max_fee_gwei:
        parser.error("Specify positive EIP-1559 caps with priority fee no higher than max fee.")
    names = ("SEPOLIA_RPC_URL", "SEPOLIA_ADMIN_KEY", "SEPOLIA_WRITER_KEY")
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        parser.error(f"Missing environment variables: {', '.join(missing)}")
    url = os.environ[names[0]]
    endpoint = urlsplit(url)
    if endpoint.scheme != "https" or not endpoint.hostname:
        parser.error("Use an HTTPS Sepolia RPC endpoint.")
    fees = {"maxFeePerGas": Web3.to_wei(args.max_fee_gwei, "gwei"),
            "maxPriorityFeePerGas": Web3.to_wei(args.priority_fee_gwei, "gwei")}
    w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 8}))
    try:
        admin, writer = (w3.eth.account.from_key(os.environ[name]) for name in names[1:])
    except ValueError:
        parser.error("Use valid private keys for the two funded testnet accounts.")
    try:
        run_window(w3, admin, writer, fees, args.output, args.window, endpoint.hostname)
    except (Web3Exception, RequestException) as error:
        parser.exit(1, f"Sepolia RPC request failed ({type(error).__name__}).\n")
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
