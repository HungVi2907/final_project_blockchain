"""Local audit dashboard for the Anvil demonstration."""
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3

import streamlit as st
from web3 import Web3

from credit_audit.chain import (
    DEFAULT_RPC, RPC_ERRORS, connect_anvil, decision_bytes, inspect_decision, submit_saved,
)
from credit_audit.demo import create_demo_decision
from credit_audit.storage import connect, get

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"


def load_registry(manifest_path, rpc_url):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    w3 = connect_anvil(rpc_url)
    address = Web3.to_checksum_address(manifest["contract_address"])
    if w3.eth.chain_id != manifest["chain_id"]:
        raise ValueError("RPC network disagrees with the deployment manifest")
    if sha256(w3.eth.get_code(address)).hexdigest() != manifest["runtime_bytecode_sha256"]:
        raise ValueError("Registry bytecode disagrees with the deployment manifest")
    registry = w3.eth.contract(address=address, abi=manifest["abi"])
    return w3, registry, manifest


def audit(decision_id, db_path, manifest_path, rpc_url):
    decision_bytes(decision_id)
    w3, registry, manifest = load_registry(manifest_path, rpc_url)
    with closing(sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("BEGIN")
        result = inspect_decision(
            db, registry, w3, decision_id, manifest["min_confirmations"],
            expected_chain_id=manifest["chain_id"],
        )
        record = get(db, decision_id)["record"] if result.status == "VERIFIED" else None
    return result, record


def main():
    st.set_page_config(page_title="Super Bells · Kiểm toán tín dụng")
    st.title("Kiểm toán quyết định tín dụng")
    st.caption("Super Bells · Anvil local")
    source = st.radio("Nguồn bản ghi", ["Dữ liệu giả lập", "Taiwan"], horizontal=True)
    demo = source == "Dữ liệu giả lập"
    manifest = ARTIFACTS / ("anvil_demo_deployment.json" if demo else "anvil_deployment.json")
    database = ARTIFACTS / ("anvil_demo.sqlite3" if demo else "audit.sqlite3")
    rpc_url = os.environ.get("RPC_URL", DEFAULT_RPC)
    new_decision = None
    if demo and st.button("Tạo và đăng ký bản ghi giả lập"):
        try:
            w3, registry, config = load_registry(manifest, rpc_url)
            with closing(connect(database)) as db:
                new_decision = create_demo_decision(db)
                st.session_state["audit_decision"] = new_decision
                submit_saved(
                    db, registry, w3, new_decision, w3.eth.accounts[0],
                    expected_chain_id=config["chain_id"],
                )
        except (ValueError, sqlite3.Error, KeyError, IndexError, *RPC_ERRORS):
            st.error("Không thể hoàn tất gửi bản ghi. Kiểm tra Anvil và manifest triển khai.")
    with st.form("audit"):
        decision_id = st.text_input("Decision ID", placeholder="64 ký tự hex", key="audit_decision")
        submitted = st.form_submit_button("Xác minh trên Anvil", type="primary")
    if not submitted and new_decision is None:
        return
    try:
        result, record = audit(decision_id.strip().lower(), database, manifest, rpc_url)
    except ValueError as error:
        st.error(f"UNAVAILABLE · {error}")
        return
    except (sqlite3.Error, KeyError, *RPC_ERRORS):
        st.error("UNAVAILABLE · Kiểm tra Anvil, manifest triển khai và tệp SQLite.")
        return
    status_view = {
        "VERIFIED": st.success,
        "PENDING": st.info,
        "NOT_FOUND": st.warning,
        "MISMATCH": st.error,
        "TRANSACTION_FAILED": st.error,
        "UNAVAILABLE": st.error,
    }
    status_view[result.status](f"{result.status} · {result.reason}")
    if result.tx_hash:
        st.code(result.tx_hash, language=None)
    if result.block_number is not None:
        block, gas, confirmations = st.columns(3)
        block.metric("Block", result.block_number)
        gas.metric("Gas sử dụng", result.gas_used)
        confirmations.metric("Số xác nhận", result.confirmations)
    if record:
        st.subheader("Kết quả đã xác minh")
        st.metric("Xác suất rủi ro", f'{float(record["risk_probability"]):.2%}')
        st.caption(f'{record["dataset_id"]} · {record["model_version"]}')
        explanation = record["shap_explanation"]
        st.caption(f'{explanation["method"]} · {explanation["output_space"]}')
        st.text("\n".join(
            f'{item["feature"]}: {item["value"]}'
            for item in explanation["feature_contributions"]
        ))


if __name__ == "__main__":
    main()
