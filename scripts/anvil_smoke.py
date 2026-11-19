"""Measure the local B2 flow using synthetic decisions, or verify an existing Taiwan fixture."""
import argparse
from contextlib import closing
from dataclasses import asdict
import json
import math
import os
import platform
import sqlite3
from statistics import median
from time import perf_counter

from credit_audit.chain import ANVIL_CHAIN_ID, DEFAULT_RPC, connect_anvil, inspect_decision, submit_saved
from credit_audit.demo import create_demo_decision
from credit_audit.records import canonical_serialize
from credit_audit.storage import connect, get
from deploy_anvil import MANIFEST, ROOT, deploy_local

DEMO_DB = ROOT / "artifacts/anvil_demo.sqlite3"
DEMO_MANIFEST = ROOT / "artifacts/anvil_demo_deployment.json"


def run_sample(db, registry, w3, sender, decision_id=None):
    start = perf_counter()
    decision_id = decision_id or create_demo_decision(db)
    submit_started = perf_counter()
    tx_hash = submit_saved(db, registry, w3, decision_id, sender, expected_chain_id=ANVIL_CHAIN_ID)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=15, poll_latency=0.05)
    confirmed = perf_counter()
    result = inspect_decision(db, registry, w3, decision_id, expected_chain_id=ANVIL_CHAIN_ID)
    verified = perf_counter()
    if result.status != "VERIFIED":
        raise RuntimeError(f"{result.status}: {result.reason}")
    return {
        **asdict(result), "decision_id": decision_id,
        "fee_wei": receipt.gasUsed * receipt.effectiveGasPrice,
        "confirmation_ms": (confirmed - submit_started) * 1000,
        "total_ms": (verified - start) * 1000,
    }


def check_tampering(db, registry, w3, decision_id):
    saved = get(db, decision_id)
    changed = saved["record"] | {"risk_probability": "0.99999999"}
    with closing(sqlite3.connect(":memory:")) as copy:
        db.backup(copy)
        copy.execute("UPDATE decisions SET display_json=? WHERE decision_id=?", (json.dumps(changed), decision_id))
        for replace_bytes in (False, True):
            if replace_bytes:
                copy.execute("UPDATE decisions SET canonical_bytes=? WHERE decision_id=?",
                             (canonical_serialize(changed), decision_id))
            result = inspect_decision(copy, registry, w3, decision_id, expected_chain_id=ANVIL_CHAIN_ID)
            if result.status != "MISMATCH":
                raise RuntimeError(f"Expected MISMATCH, got {result.status}")


def summarize(samples):
    result = {}
    for key in ("gas_used", "fee_wei", "confirmation_ms", "total_ms"):
        values = sorted(sample[key] for sample in samples)
        result[key] = {"median": median(values), "p95": values[math.ceil(0.95 * len(values)) - 1]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc", default=DEFAULT_RPC)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--taiwan", action="store_true", help="Use the existing local Taiwan smoke record once")
    options = parser.parse_args()
    if options.runs < 1 or options.warmup < 0 or (options.taiwan and (options.runs != 1 or options.warmup)):
        parser.error("Use runs >= 1 and warmup >= 0; --taiwan uses exactly one run and no warm-up")
    w3 = connect_anvil(options.rpc)
    db_path = ROOT / "artifacts/audit.sqlite3" if options.taiwan else DEMO_DB
    manifest = MANIFEST if options.taiwan else DEMO_MANIFEST
    sender = w3.eth.accounts[0]
    with closing(connect(db_path)) as db:
        decision_id = None
        if options.taiwan:
            source = ROOT / "artifacts/taiwan_smoke_summary.json"
            if not source.is_file():
                parser.error("Generate a Taiwan smoke record first")
            decision_id = json.loads(source.read_text(encoding="utf-8"))["decision_id"]
            saved = get(db, decision_id)
            if saved is None or saved["tx_hash"] or saved["status"] != "PENDING":
                parser.error("Generate a fresh Taiwan smoke record first")
        registry = deploy_local(w3, manifest)
        for _ in range(options.warmup):
            run_sample(db, registry, w3, sender)
        samples = [run_sample(db, registry, w3, sender, decision_id) for _ in range(options.runs)]
        check_tampering(db, registry, w3, samples[-1]["decision_id"])

    result = {
        "network": w3.client_version, "platform": platform.platform(), "python": platform.python_version(),
        "machine": platform.machine(), "logical_cpus": os.cpu_count(), "min_confirmations": 1,
        "chain_id": ANVIL_CHAIN_ID, "contract_address": registry.address, "decision_id": samples[-1]["decision_id"],
        "source": "taiwan_smoke" if options.taiwan else "synthetic_demo", "baseline": "B2",
        "runs": options.runs, "warmup": options.warmup, "summary": summarize(samples),
        "tampered_verification": "MISMATCH", "samples": samples,
    }
    output = ROOT / "artifacts/anvil_smoke_summary.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "samples"}, indent=2))


if __name__ == "__main__":
    main()
