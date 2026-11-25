"""Read-only Streamlit verification for a saved local pilot run."""

from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3

import streamlit as st
from web3 import Web3
from web3.exceptions import Web3Exception

from credit_audit.chain import verify


def main():
    st.title("Kiểm toán bản ghi tín dụng")
    st.caption("Super Bells · Pilot Anvil")
    run_dir = Path(os.environ.get("CREDIT_AUDIT_PILOT_DIR", "artifacts/heloc_pilot/run-01"))
    try:
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        rpc = f"http://127.0.0.1:{int(summary['rpc_port'])}"
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 5}))
        address = Web3.to_checksum_address(summary["contract_address"])
        if (
            w3.eth.chain_id != summary["chain_id"]
            or sha256(w3.eth.get_code(address)).hexdigest() != summary["runtime_bytecode_sha256"]
        ):
            raise ValueError("Registry trên Anvil không khớp với hồ sơ pilot")
        registry = w3.eth.contract(address=address, abi=summary["abi"])
        decision_id = summary["decision_id"]
        with closing(sqlite3.connect((run_dir / "audit.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)) as db:
            status = verify(db, registry, w3, decision_id)
    except (OSError, ValueError, KeyError, sqlite3.Error, Web3Exception):
        st.error("UNAVAILABLE · Kiểm tra thư mục pilot và phiên Anvil đã chạy giao dịch.")
        return

    if status == "VERIFIED":
        st.success(status)
    else:
        st.warning(status)
    st.write(f"Dataset: {summary['dataset_id']} · Schema v{summary['schema_version']}")
    st.code(decision_id, language=None)
    st.write("Mã giao dịch")
    st.code(summary["tx_hash"], language=None)
    st.metric("Gas đã dùng", summary["gas_used"])


if __name__ == "__main__":
    main()
