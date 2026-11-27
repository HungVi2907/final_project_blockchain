"""Super Bells Streamlit dashboard for decision records and audit evidence."""

from contextlib import closing
import csv
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from html import escape
import json
import math
import os
from pathlib import Path
import sqlite3

import streamlit as st

from credit_audit.chain import DEFAULT_RPC, RPC_ERRORS, Verification, decision_bytes
from credit_audit.mvp import (
    MAX_AUDIT_UPLOAD_BYTES, Fixture, audit, audit_uploaded_record, load_audit_json,
    load_fixture, read_only, register_fixture,
)
from credit_audit.pilot import load_pilot
from credit_audit.records import canonical_serialize, commitments, create_record
from credit_audit.storage import get

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
AUC_PATH = ROOT / "docs/references/CHEON_2025_REPLICATION_COMPARISON.csv"
RESEARCH_PATH = ROOT / "docs/references/HELOC_RESEARCH_SUMMARY.json"
APP_ERRORS = (ValueError, KeyError, TypeError, IndexError, RuntimeError, sqlite3.Error, *RPC_ERRORS)
DATASETS = {
    "fico_heloc_iclr2025": "FICO HELOC",
    "taiwan_uci350": "Taiwan Credit · smoke test",
    "home_credit_2018": "Home Credit · smoke test",
}
STATUS = {
    "VERIFIED": ("Đã xác minh", "Giao dịch đủ xác nhận và cả hai hash đều khớp.", "good", "✓"),
    "MISMATCH": ("Phát hiện sai lệch", "Bản ghi hoặc giao dịch không khớp với cam kết đã đăng ký.", "bad", "!"),
    "PENDING": ("Chờ xác nhận", "Kiểm tra lại khi giao dịch đã vào block.", "wait", "…"),
    "NOT_FOUND": ("Không tìm thấy", "Kiểm tra Decision ID và nguồn hồ sơ đang chọn.", "neutral", "–"),
    "TRANSACTION_FAILED": ("Giao dịch thất bại", "Kiểm tra giao dịch và quyền writer trên Anvil.", "bad", "!"),
    "UNAVAILABLE": ("Chưa thể xác minh", "Kiểm tra Anvil, cấu hình triển khai và dữ liệu SQLite rồi thử lại.", "neutral", "?"),
}
PAIR_LABELS = ("Hash bản ghi", "Hash phiên bản mô hình")


def make_offline_fixture():
    base, contributions = -0.15, [0.62, -0.21, 0.15]
    output = base + sum(contributions)
    record, raw = create_record(
        "fico_heloc_iclr2025",
        {"risk_probability": 1 / (1 + math.exp(-output)), "model_version": "offline-demo-v2",
         "model_artifact_sha256": sha256(b"Super Bells offline demonstration").hexdigest()},
        {"method": "synthetic_demo", "output_space": "raw", "base_value": base, "model_output": output,
         "feature_contributions": [
             {"feature": name, "value": value}
             for name, value in zip(("Mức sử dụng tín dụng", "Lịch sử thanh toán", "Số lần tra cứu"), contributions)
         ]},
    )
    record_hash, model_hash = (value.hex() for value in commitments(record, raw))
    return Fixture(record, raw, record_hash, model_hash)


def demo_verification(fixture, decision_id, modified):
    if decision_id != fixture.decision_id:
        return Verification("NOT_FOUND", "No matching simulated commitment")
    original = (fixture.record_hash, fixture.model_hash)
    candidate = original
    if modified:
        record = fixture.record | {"risk_probability": "0.20000000"}
        candidate = tuple(value.hex() for value in commitments(record, canonical_serialize(record)))
    status = "VERIFIED" if candidate == original else "MISMATCH"
    return Verification(status, "Offline comparison", local_commitments=candidate, on_chain_commitments=original)


def code_value(label, value):
    st.caption(label)
    st.code(str(value), language=None, wrap_lines=True)


def render_table(label, headers, rows):
    headings = "".join(f'<th scope="col">{escape(header)}</th>' for header in headers)
    body = "".join(f"<tr>{''.join(f'<td>{escape(cell)}</td>' for cell in row)}</tr>" for row in rows)
    st.html(f'''<div class="audit-table-scroll" tabindex="0" role="region" aria-label="{escape(label)}">
        <table class="audit-table"><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table></div>''')


def render_result(result, *, offline, modified, checked_at, uploaded=False):
    title, description, tone, symbol = STATUS[result.status]
    if result.reason == "Decision has no submitted transaction":
        title = "Chưa đăng ký"
        description = "Đăng ký hồ sơ trong tab Hồ sơ rồi chạy lại phép xác minh."
    elif result.reason == "Submission is in progress or needs audit":
        description = "Giao dịch đang được gửi hoặc cần đối soát trên Anvil."
    elif result.status == "MISMATCH" and modified and result.local_commitments:
        description = "Bản sao có xác suất đã sửa. Hash bản ghi thay đổi, hash phiên bản mô hình giữ nguyên."
    elif offline and result.status == "VERIFIED":
        description = "Hai hash của hồ sơ khớp với cam kết mô phỏng trong bộ nhớ."
    elif result.reason == "Decision is outside the selected pilot":
        description = "Decision ID không thuộc lượt pilot đang chọn. Hãy chọn đúng lượt pilot hoặc kiểm tra lại ID."
    elif result.reason == "Decision commitment is missing on chain":
        description = "Decision ID này chưa có cam kết trên registry Anvil đang dùng."
    elif uploaded and result.status == "UNAVAILABLE":
        description = "Kiểm tra kết nối Anvil và cấu hình registry rồi thử lại."
    status_label = f"Mô phỏng · {result.status}" if offline else result.status
    st.html(f'''<section class="audit-status {tone}" role="status">
      <div><span class="status-icon" aria-hidden="true">{symbol}</span>
      <strong>{title}</strong><code class="status-code">{status_label}</code></div>
      <p>{description}</p></section>''')
    candidate = "Tệp đã nạp" if uploaded else "Bản sao đã sửa" if modified else "Bản ghi gốc"
    st.caption(f"{candidate} · Kiểm tra lúc {checked_at:%H:%M:%S UTC · %d/%m/%Y}")

    if result.local_commitments and result.on_chain_commitments:
        st.subheader("Đối chiếu hai cam kết")
        chain_label = "Cam kết mô phỏng" if offline else "Cam kết trên Anvil"
        for label, local, anchored in zip(PAIR_LABELS, result.local_commitments, result.on_chain_commitments):
            with st.container(border=True):
                st.markdown(f"**{label}** · {'Khớp' if local == anchored else 'Sai lệch'}")
                off_chain, on_chain = st.columns(2)
                with off_chain:
                    code_value("Hash off-chain", local)
                with on_chain:
                    code_value(chain_label, anchored)

    if result.tx_hash:
        with st.expander("Biên nhận giao dịch trên Anvil", expanded=True):
            code_value("Mã giao dịch", result.tx_hash)
            metrics = [(label, value) for label, value in (
                ("Block", result.block_number), ("Gas sử dụng", result.gas_used),
                ("Số xác nhận", result.confirmations),
            ) if value is not None]
            if metrics:
                for column, (label, value) in zip(st.columns(len(metrics)), metrics):
                    column.metric(label, value)


def render_explanation(record):
    explanation = record["shap_explanation"]
    rows = sorted(
        [(entry["feature"], Decimal(entry["value"])) for entry in explanation["feature_contributions"]],
        key=lambda row: abs(row[1]), reverse=True,
    )
    maximum = max(abs(value) for _, value in rows) or 1
    bars = []
    for feature, value in rows[:10]:
        direction = "raised" if value > 0 else "lowered"
        width = 50 * abs(value) / maximum
        bars.append(f'''<div class="shap-row">
            <code>{escape(feature)}</code><span class="shap-track" aria-hidden="true">
              <span class="shap-bar {direction}" style="width:{width:.3f}%"></span></span>
            <strong>{value:+.4g}</strong></div>''')
    if explanation["output_space"] == "probability":
        units = "xác suất"
    elif explanation["method"] == "linear_interventional_shap_formula" or explanation["method"] == "synthetic_demo":
        units = "log-odds của lớp Bad"
    else:
        units = "đầu ra thô"
    base, output = (Decimal(explanation[key]) for key in ("base_value", "model_output"))
    count = len(rows)
    visible = f"{min(count, 10)}/{count} đặc trưng"
    st.html(f'''<section class="explanation" aria-labelledby="shap-heading">
      <h2 id="shap-heading">Đóng góp SHAP</h2>
      <p>{visible} theo độ lớn tuyệt đối · đơn vị {units}</p>
      <div class="shap-legend"><span>− Giảm đầu ra</span><span>+ Tăng đầu ra</span></div>
      <div class="shap-list">{''.join(bars)}</div>
      <div class="shap-total"><span>Giá trị nền <strong>{base:+.4g}</strong></span>
        <span>Đầu ra mô hình <strong>{output:+.4g}</strong></span></div>
      </section>''')
    with st.expander(f"Chi tiết SHAP · {count} đặc trưng"):
        st.caption(f"Phương pháp lưu trong hồ sơ: {explanation['method']}.")
        st.caption("SHAP mô tả đóng góp vào đầu ra của mô hình. Diễn giải nguyên nhân cần bằng chứng riêng.")
        residual = output - base - sum(value for _, value in rows)
        st.caption(f"Sai số cộng trên các giá trị đã làm tròn: {residual:+.2E}.")
        render_table("Bảng đóng góp SHAP", ("Đặc trưng", "Đóng góp"),
                     [(name, f"{value:+.8f}") for name, value in rows])


def render_profile(fixture, mode, database, manifest, rpc_url, *, can_register):
    record = fixture.record
    dataset = escape(DATASETS.get(record["dataset_id"], record["dataset_id"]))
    if mode == "offline":
        dataset += " (mô phỏng)"
    probability = f'{Decimal(record["risk_probability"]):.2%}'.replace(".", ",")
    risk, explanation = st.columns([1, 1.65], gap="large")
    with risk:
        st.html(f'''<section class="risk-panel" aria-labelledby="risk-heading">
          <p class="record-source">{dataset} · schema v{escape(record["schema_version"])}</p>
          <h2 id="risk-heading">Xác suất lớp Bad</h2><div class="risk-number">{probability}</div>
          <p class="risk-context">Khả năng hồ sơ thuộc nhóm rủi ro theo mô hình.</p>
          <div class="risk-model"><span>Phiên bản mô hình</span>
            <code>{escape(record["model_version"])}</code></div></section>''')
    with explanation:
        render_explanation(record)

    with st.expander("Bản ghi và hai hash off-chain"):
        code_value("Decision ID", fixture.decision_id)
        st.caption(f"Tạo lúc {record['timestamp_utc']} · P(Bad) lưu trong hồ sơ: {record['risk_probability']}")
        code_value(PAIR_LABELS[0], fixture.record_hash)
        code_value(PAIR_LABELS[1], fixture.model_hash)
        code_value("SHA-256 của hiện vật mô hình", record["model_artifact_sha256"])
        with st.expander("Xem JSON canonical"):
            st.code(fixture.canonical_bytes.decode("utf-8"), language="json", wrap_lines=True)
        st.download_button("Tải JSON canonical", fixture.canonical_bytes,
                           file_name=f"decision-{fixture.decision_id}.json",
                           mime="application/json", on_click="ignore")

    if can_register:
        with st.container(border=True):
            st.subheader("Đăng ký hồ sơ trên Anvil")
            st.caption("Hành động này gửi Decision ID và hai hash lên Anvil cục bộ.")
            saved = None
            if database.is_file():
                try:
                    with closing(read_only(database)) as db:
                        saved = get(db, fixture.decision_id)
                except APP_ERRORS:
                    st.warning("Không đọc được thông tin giao dịch trong SQLite.")
                    return
            if saved and saved["tx_hash"]:
                code_value("Mã giao dịch đã lưu", saved["tx_hash"])
                st.info("Mở tab Xác minh để kiểm tra biên nhận và hai cam kết.")
            elif saved and saved["status"] == "SUBMITTING":
                st.warning("Đang gửi hoặc cần đối soát giao dịch trên Anvil trước khi thử lại.")
            elif st.button("Đăng ký trên Anvil", type="primary", key="register-handoff"):
                try:
                    with st.spinner("Đang gửi giao dịch tới Anvil…"):
                        register_fixture(fixture, database, manifest, rpc_url)
                except APP_ERRORS:
                    st.error("Chưa hoàn tất đăng ký. Kiểm tra Anvil và manifest triển khai rồi thử lại.")
                else:
                    st.session_state.pop("last_audit", None)
                    st.rerun()


def render_verification(fixture, selection, pilot, database, manifest, rpc_url):
    offline = selection == "offline"
    uploaded = selection == "uploaded"
    st.subheader("Xác minh cam kết")
    if pilot:
        st.caption(f"Registry của lượt pilot · Chain ID {pilot.summary['chain_id']}")
        code_value("Địa chỉ registry đã lưu", pilot.summary["contract_address"])
    st.caption("Xác minh kiểm tra tính toàn vẹn bản ghi. Độ đúng của dữ liệu và mô hình cần được đánh giá riêng.")
    with st.container(border=True):
        if uploaded:
            entered = fixture.decision_id
            code_value("Decision ID trong tệp", entered)
            verify_original = st.button("Xác minh bản ghi", type="primary", key="verify-original")
            verify_modified = False
        else:
            entered = st.text_input("Decision ID", value=fixture.decision_id,
                                    key=f"decision-id:{selection}:{fixture.decision_id}",
                                    help="Mã định danh 64 ký tự hex của bản ghi.").strip().lower()
            original, alternate = st.columns(2)
            verify_original = original.button("Xác minh bản ghi", type="primary", key="verify-original")
            verify_modified = pilot is None and alternate.button("Thử trên bản sao đã sửa", key="verify-copy")
    registry_context = tuple(pilot.summary.get(field) for field in (
        "chain_id", "contract_address", "runtime_bytecode_sha256",
    )) if pilot else None
    context = (selection, entered, fixture.record_hash, fixture.model_hash, registry_context)
    last = st.session_state.get("last_audit")
    if last and last[0] != context:
        st.session_state.pop("last_audit")
        last = None
    if verify_original or verify_modified:
        try:
            decision_bytes(entered)
        except ValueError:
            st.warning("Nhập đúng 64 ký tự hex (0–9, a–f) trong trường Decision ID.")
            return
        with st.spinner("Đang đối chiếu hai cam kết…"):
            try:
                if offline:
                    result = demo_verification(fixture, entered, verify_modified)
                elif uploaded:
                    result = audit_uploaded_record(fixture, manifest, rpc_url)
                elif pilot:
                    result = pilot.verify(entered)
                else:
                    result = audit(fixture, database, manifest, rpc_url, entered, simulate_change=verify_modified)
            except APP_ERRORS:
                result = Verification("UNAVAILABLE", "The chain or working copy is unavailable")
        last = (context, result, verify_modified, datetime.now(timezone.utc))
        st.session_state["last_audit"] = last
    if last:
        _, result, modified, checked_at = last
        render_result(result, offline=offline, modified=modified, checked_at=checked_at, uploaded=uploaded)
    else:
        st.info("Chưa kiểm tra. Bấm Xác minh bản ghi để đối chiếu hai cam kết.")


def render_historical_auc(dataset):
    st.caption("Bảng lịch sử đối chiếu giá trị đã lưu trong artifact với Table 11 của Cheon et al. (ICLR 2025).")
    try:
        with AUC_PATH.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            required = {"dataset", "model", "paper_test_auc", "run_test_auc", "delta_test_auc", "status"}
            if not required.issubset(reader.fieldnames or ()):
                raise ValueError("Missing ROC-AUC fields")
            results = [result for result in reader if result["dataset"] == dataset]
    except (OSError, ValueError, csv.Error):
        st.info("Chưa đọc được bảng đối chiếu tại docs/references/CHEON_2025_REPLICATION_COMPARISON.csv.")
        return
    if not results:
        st.info("Chưa có kết quả cho bộ dữ liệu này.")
        return
    rows = []
    for result in results:
        model, paper = result["model"] or "—", result["paper_test_auc"] or "—"
        if result["status"] == "completed":
            rows.append((model, paper, result["run_test_auc"] or "—", result["delta_test_auc"] or "—"))
        else:
            rows.append((model, paper, "Chưa có kết quả", "—"))
    render_table("Đối chiếu test ROC-AUC", ("Mô hình", "Cheon et al.", "AUC lưu", "Chênh lệch"), rows)
    if dataset == "givemecredit":
        st.caption("Mã tác giả áp dụng oversampling cả trên tập đánh giá của Give Me Some Credit.")


def local_number(value, decimals=0):
    return f"{value:,.{decimals}f}".translate(str.maketrans(",.", ".,"))


def render_heloc_auc(auc):
    rows = [
        (row["model"], local_number(row["paper"], 3), local_number(row["pilot"], 4), local_number(row["mean"], 4))
        for row in auc["models"]
    ]
    st.caption(
        f"ROC-AUC từ P(Bad) trên {local_number(auc['test_rows'])} hồ sơ test · "
        f"{auc['fold']}, fold {auc['test_fold']} · Pilot dùng seed {auc['pilot_seed']}."
    )
    render_table("ROC-AUC trên tập test HELOC",
                 ("Mô hình", "Table 11", "Pilot · 1 seed", f"Trung bình · {len(auc['training_seeds'])} seed"), rows)


def render_e3(e3, measured_on):
    total = e3["anchors"]
    baseline_labels = {
        "B0": "B0 · SQLite", "B1": "B1 · SQLite + hash local", "B2": "B2 · Cam kết trên Anvil",
    }
    rows = [
        (baseline_labels[row["name"]], f"{row['detected']}/{total}", f"{row['false_alerts']}/{total}")
        for row in e3["baselines"]
    ]
    median_gas = local_number(e3["b2_registration_gas_median"])
    receipt_median = local_number(e3["b2_receipt_ms_median"], 1)
    receipt_p95 = local_number(e3["b2_receipt_ms_p95"], 1)
    st.caption(
        f"Đã đo {measured_on} trên {e3['network']} · {e3['groups']} nhóm × {e3['profiles_per_group']} lượt "
        f"({e3['distinct_profiles']} hồ sơ khác nhau). Kịch bản sửa đồng thời bản ghi và hash local."
    )
    render_table("Kết quả E3", ("Baseline", "Phát hiện sửa đổi", "Cảnh báo sai"), rows)
    render_table("Chi phí đăng ký B2 trên Anvil", ("Chỉ số B2", "Trung vị", "P95"), [
        ("Gas mỗi lượt đăng ký", median_gas, local_number(e3["b2_registration_gas_p95"])),
        ("Thời gian gửi đến biên nhận", f"{receipt_median} ms", f"{receipt_p95} ms"),
    ])


def render_research(pilot):
    st.subheader("Kết quả tái lập ROC-AUC")
    labels = {"heloc": "FICO HELOC", "german": "German Credit", "givemecredit": "Give Me Some Credit"}
    dataset = st.selectbox("Bộ dữ liệu tái lập", labels, format_func=labels.__getitem__)
    try:
        evidence = json.loads(RESEARCH_PATH.read_bytes())
    except APP_ERRORS:
        evidence = {}
    if dataset == "heloc":
        try:
            render_heloc_auc(evidence["auc"])
        except APP_ERRORS:
            st.info("Chưa đọc được số liệu ROC-AUC HELOC đã kiểm chứng.")
    else:
        render_historical_auc(dataset)

    st.divider()
    st.subheader("Thử nghiệm toàn vẹn B0/B1/B2")
    try:
        render_e3(evidence["e3"], evidence["measured_on"])
    except APP_ERRORS:
        st.info("Chưa đọc được số liệu E3 đã lưu.")
    if pilot and pilot.summary.get("verification"):
        with st.expander("Kết quả đã lưu của lượt pilot"):
            st.caption("Đọc từ summary.json của lượt đã chọn. Dùng tab Xác minh để kiểm tra lại trên Anvil.")
            st.write("Bản ghi gốc", pilot.summary["verification"])
            if changed := pilot.summary.get("altered_copy_verification"):
                st.write("Bản sao đã sửa", changed)


def read_uploaded_source():
    uploaded = st.file_uploader(
        "Tệp JSON chuẩn hóa", type=["json"],
        help="Dùng tệp từ nút Tải JSON canonical ở tab Hồ sơ. Kích thước tối đa 1 MB.",
        key="audit-json",
    )
    if uploaded is None:
        return None
    if uploaded.size > MAX_AUDIT_UPLOAD_BYTES:
        st.error("Tệp vượt quá 1 MB. Hãy chọn một bản ghi JSON chuẩn hóa.")
        return None
    try:
        fixture = load_audit_json(uploaded.getvalue())
    except ValueError:
        st.error("Tệp chưa đúng định dạng bản ghi JSON chuẩn hóa. Hãy chọn lại tệp đã tải từ tab Hồ sơ.")
        return None
    st.caption("Đã đọc tệp. Mở tab Xác minh để kiểm tra cam kết trên Anvil.")
    return fixture


def main():
    st.set_page_config(page_title="Super Bells | Kiểm toán tín dụng", layout="wide")
    st.html(Path(__file__).with_name("audit.css"))
    st.html('''<header class="audit-hero">
      <div class="audit-brand"><span class="brand-mark" aria-hidden="true"></span>Super Bells</div>
      <h1>Kiểm toán tín dụng</h1>
      <p>Đọc dự đoán, xem đóng góp SHAP và đối chiếu cam kết của bản ghi.</p>
      <div class="ledger-art" aria-hidden="true"></div>
    </header>''')
    fixture_dir = Path(os.environ.get("ROLE_B_FIXTURE_DIR", ARTIFACTS / "role_b_smoke"))
    heloc_root = Path(os.environ.get("ROLE_B_HELOC_DIR", ARTIFACTS / "role_b_heloc/handoff"))
    heloc_paths = {}
    for position in range(3):
        directory = heloc_root / f"position-{position}"
        if directory.is_dir():
            heloc_paths[f"heloc:{position}"] = directory
    runtime = Path(os.environ.get("ROLE_C_MVP_DIR", ARTIFACTS / "role_c_mvp"))
    database, manifest = runtime / "audit.sqlite3", runtime / "deployment.json"
    rpc_url = os.environ.get("RPC_URL", DEFAULT_RPC)
    pilot_root = Path(os.environ.get("CREDIT_AUDIT_PILOT_DIR", ARTIFACTS / "heloc_pilot"))
    pilot_dirs = sorted(path.parent for path in pilot_root.glob("*/summary.json"))
    if (pilot_root / "summary.json").is_file() or ("CREDIT_AUDIT_PILOT_DIR" in os.environ and not pilot_dirs):
        pilot_dirs = [pilot_root]
    pilot_paths = {f"pilot:{directory.resolve()}": directory for directory in pilot_dirs}
    sources = {key: f"FICO HELOC · Hồ sơ {directory.name.removeprefix('position-')}"
               for key, directory in heloc_paths.items()}
    if fixture_dir.is_dir() or "ROLE_B_FIXTURE_DIR" in os.environ:
        synthetic_source = {"handoff": "Gói bàn giao B · dữ liệu giả lập trên Anvil"}
        sources = synthetic_source | sources if "ROLE_B_FIXTURE_DIR" in os.environ else sources | synthetic_source
    sources.update({key: f"Lượt pilot · {path.name}" for key, path in pilot_paths.items()})
    sources["offline"] = "Mô phỏng ngoại tuyến"
    sources["uploaded"] = "Nạp JSON để kiểm toán"
    selection = st.selectbox("Nguồn hồ sơ", sources, format_func=sources.__getitem__, key="audit-source")
    pilot, fixture = None, None
    can_register = selection == "handoff" or selection in heloc_paths
    try:
        if selection == "handoff":
            fixture = load_fixture(fixture_dir)
            st.caption("Hồ sơ giả lập của B · Anvil cục bộ.")
        elif selection in heloc_paths:
            fixture = load_fixture(heloc_paths[selection], synthetic=False)
            st.caption("Hồ sơ test FICO HELOC của B · Anvil cục bộ.")
        elif selection == "uploaded":
            fixture = read_uploaded_source()
            if fixture is None:
                st.session_state.pop("last_audit", None)
        elif selection == "offline":
            if "offline_fixture" not in st.session_state:
                st.session_state["offline_fixture"] = make_offline_fixture()
            fixture = st.session_state["offline_fixture"]
            st.caption("Hồ sơ minh họa · Đối chiếu trong bộ nhớ, không gọi RPC.")
        else:
            pilot = load_pilot(pilot_paths[selection])
            fixture = pilot.fixture
            mode = "Dữ liệu giả lập" if pilot.summary.get("configuration", {}).get("synthetic") else "Hồ sơ đã lưu"
            st.caption(f"{mode} · Pilot Anvil cục bộ · Chỉ đọc.")
    except APP_ERRORS:
        st.session_state.pop("last_audit", None)
        st.error("Không đọc được nguồn hồ sơ. Kiểm tra các tệp của cùng lượt chạy hoặc chọn mô phỏng ngoại tuyến.")

    profile, verification, research = st.tabs(["Hồ sơ", "Xác minh", "Kết quả nghiên cứu"])
    if fixture:
        with profile:
            render_profile(fixture, selection, database, manifest, rpc_url, can_register=can_register)
        with verification:
            render_verification(fixture, selection, pilot, database, manifest, rpc_url)
    with research:
        render_research(pilot)


if __name__ == "__main__":
    main()
