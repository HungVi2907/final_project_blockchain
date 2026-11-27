from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from credit_audit.chain import register
from credit_audit.mvp import HELOC_MODEL_SHA256
from credit_audit.records import canonical_serialize, commitments, create_record
from credit_audit.storage import connect, get, save

APP = Path(__file__).resolve().parents[1] / "src/credit_audit/app.py"


def contains(app, text):
    return any(text in element.proto.body for element in app.get("html"))


def write_deployment(runtime, w3, registry):
    runtime.mkdir()
    (runtime / "deployment.json").write_text(json.dumps({
        "contract_address": registry.address, "chain_id": 31337, "min_confirmations": 1,
        "runtime_bytecode_sha256": sha256(w3.eth.get_code(registry.address)).hexdigest(),
        "abi": registry.abi,
    }), encoding="utf-8")


def test_handoff_registration_and_tamper_demo(tmp_path, anvil, registry, monkeypatch):
    w3, rpc = anvil
    source = tmp_path / "handoff"
    source.mkdir()
    model = b'{"coef":[1]}'
    record, raw = create_record(
        "taiwan_uci350",
        {"risk_probability": 0.42, "model_version": "fixture-v1", "model_artifact_sha256": sha256(model).hexdigest()},
        {"method": "fixture", "output_space": "raw", "base_value": 0.2,
         "model_output": 0.3, "feature_contributions": [{"feature": "demo", "value": 0.1}]},
    )
    (source / "model.json").write_bytes(model)
    (source / "decision_record.json").write_bytes(raw)
    record_hash, model_hash = commitments(record, raw)
    decision_id = record["decision_id"]
    (source / "taiwan_smoke_summary.json").write_text(json.dumps({
        "synthetic": True, "decision_id": decision_id,
        "record_hash": record_hash.hex(), "model_version_hash": model_hash.hex(),
    }), encoding="utf-8")
    with closing(connect(source / "audit.sqlite3")) as db:
        save(db, record, raw)
    original = (source / "audit.sqlite3").read_bytes()

    runtime = tmp_path / "runtime"
    write_deployment(runtime, w3, registry)
    monkeypatch.setenv("ROLE_B_FIXTURE_DIR", str(source))
    monkeypatch.setenv("ROLE_C_MVP_DIR", str(runtime))
    monkeypatch.setenv("CREDIT_AUDIT_PILOT_DIR", str(runtime))
    monkeypatch.setenv("RPC_URL", rpc)

    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not contains(app, "VERIFIED")
    app.button(key="verify-original").click().run()
    assert contains(app, "Chưa đăng ký")
    app.button(key="register-handoff").click().run()
    assert not app.error and not app.exception
    assert not contains(app, "VERIFIED")
    app.button(key="verify-original").click().run()
    assert contains(app, "VERIFIED")
    app.button(key="verify-copy").click().run()
    assert contains(app, "MISMATCH")
    assert any("Sai lệch" in entry.value for entry in app.markdown)
    app.button(key="verify-original").click().run()
    assert not contains(app, "MISMATCH")
    app.text_input[0].set_value("a" * 64).run()
    assert not contains(app, "VERIFIED")
    app.button(key="verify-original").click().run()
    assert contains(app, "NOT_FOUND")
    with closing(connect(runtime / "audit.sqlite3")) as db:
        assert get(db, decision_id)["record"] == record
    assert (source / "audit.sqlite3").read_bytes() == original

    config = json.loads((runtime / "deployment.json").read_text(encoding="utf-8"))
    config.update(decision_id=decision_id, rpc_port=w3.provider.endpoint_uri.rsplit(":", 1)[1],
                  configuration={"synthetic": True}, verification="VERIFIED")
    (runtime / "summary.json").write_text(json.dumps(config), encoding="utf-8")
    before = (runtime / "audit.sqlite3").read_bytes()
    app.run()
    app.selectbox(key="audit-source").select(f"pilot:{runtime.resolve()}").run()
    assert not app.exception and not contains(app, "NOT_FOUND") and not contains(app, "VERIFIED")
    assert {button.key for button in app.button} == {"verify-original"}
    app.button(key="verify-original").click().run()
    assert contains(app, "VERIFIED")
    assert (runtime / "audit.sqlite3").read_bytes() == before

    config["runtime_bytecode_sha256"] = "0" * 64
    (runtime / "summary.json").write_text(json.dumps(config), encoding="utf-8")
    app.button(key="verify-original").click().run()
    assert contains(app, "UNAVAILABLE") and not contains(app, "VERIFIED")


def test_offline_comparison_is_labelled_and_works_without_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("ROLE_B_FIXTURE_DIR", str(tmp_path / "missing-handoff"))
    monkeypatch.setenv("CREDIT_AUDIT_PILOT_DIR", str(tmp_path / "missing-pilot"))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert app.error and not app.exception
    app.selectbox(key="audit-source").select("offline").run()
    assert not app.error and not app.exception and not contains(app, "VERIFIED")
    assert {button.key for button in app.button} == {"verify-original", "verify-copy"}
    app.button(key="verify-original").click().run()
    assert contains(app, "Mô phỏng · VERIFIED")
    app.button(key="verify-copy").click().run()
    assert contains(app, "Mô phỏng · MISMATCH")
    assert not contains(app, "Mô phỏng · VERIFIED")


def test_heloc_sources_research_and_audit(tmp_path, anvil, registry, monkeypatch):
    w3, rpc = anvil
    source = tmp_path / "heloc"
    originals = {}
    for position in range(3):
        directory = source / f"position-{position}"
        directory.mkdir(parents=True)
        record, raw = create_record(
            "fico_heloc_iclr2025",
            {"risk_probability": 0.5, "model_version": "cheon2025-fico-complex-nd-logreg-2338",
             "model_artifact_sha256": HELOC_MODEL_SHA256},
            {"method": "linear_interventional_shap_formula", "output_space": "raw", "base_value": 0,
             "model_output": 0, "feature_contributions": [
                 {"feature": f"feature_{index}", "value": 0} for index in range(43)
             ]},
        )
        digest, model_digest = commitments(record, raw)
        (directory / "decision_record.json").write_bytes(raw)
        (directory / "taiwan_smoke_summary.json").write_text(json.dumps({
            "synthetic": False, "dataset_id": record["dataset_id"], "schema_version": "2",
            "decision_id": record["decision_id"], "record_hash": digest.hex(),
            "model_version_hash": model_digest.hex(),
        }), encoding="utf-8")
        database = directory / "audit.sqlite3"
        with closing(connect(database)) as db:
            save(db, record, raw)
        originals[database] = (record["decision_id"], database.read_bytes())

    runtime = tmp_path / "runtime"
    write_deployment(runtime, w3, registry)
    monkeypatch.delenv("ROLE_B_FIXTURE_DIR", raising=False)
    monkeypatch.setenv("ROLE_B_HELOC_DIR", str(source))
    monkeypatch.setenv("ROLE_C_MVP_DIR", str(runtime))
    monkeypatch.setenv("CREDIT_AUDIT_PILOT_DIR", str(tmp_path / "no-pilot"))
    monkeypatch.setenv("RPC_URL", rpc)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert app.selectbox(key="audit-source").value == "heloc:0"
    assert contains(app, "schema v2") and contains(app, "10/43 đặc trưng")
    assert contains(app, "Pilot · 1 seed") and contains(app, "Trung bình · 7 seed")
    assert contains(app, "0,7882") and not contains(app, "0,7775")
    assert contains(app, "200/200") and contains(app, "93.507") and contains(app, "83,1 ms")

    app.button(key="verify-original").click().run()
    assert contains(app, "Chưa đăng ký")
    for position, (decision_id, _) in enumerate(originals.values()):
        app.selectbox(key="audit-source").select(f"heloc:{position}").run()
        assert app.text_input[0].value == decision_id
        assert not contains(app, "VERIFIED")
        app.button(key="register-handoff").click().run()
        assert not app.error and not app.exception
        app.button(key="verify-original").click().run()
        assert contains(app, "VERIFIED")
        app.button(key="verify-copy").click().run()
        assert contains(app, "MISMATCH")
        assert any("Hash bản ghi** · Sai lệch" in item.value for item in app.markdown)
        assert any("Hash phiên bản mô hình** · Khớp" in item.value for item in app.markdown)
    assert all(path.read_bytes() == raw for path, (_, raw) in originals.items())


def test_upload_audits_against_registry_without_saved_sqlite(tmp_path, anvil, registry, monkeypatch):
    w3, rpc = anvil
    runtime = tmp_path / "runtime"
    write_deployment(runtime, w3, registry)
    manifest = runtime / "deployment.json"
    config = json.loads(manifest.read_bytes())
    config["min_confirmations"] = 2
    manifest.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("ROLE_B_FIXTURE_DIR", str(tmp_path / "missing-synthetic"))
    monkeypatch.setenv("ROLE_B_HELOC_DIR", str(tmp_path / "missing-heloc"))
    monkeypatch.setenv("ROLE_C_MVP_DIR", str(runtime))
    monkeypatch.setenv("CREDIT_AUDIT_PILOT_DIR", str(tmp_path / "missing-pilot"))
    monkeypatch.setenv("RPC_URL", rpc)
    record, raw = create_record(
        "fico_heloc_iclr2025",
        {"risk_probability": 0.5, "model_version": "upload-v2", "model_artifact_sha256": "a" * 64},
        {"method": "linear_interventional_shap_formula", "output_space": "raw", "base_value": 0,
         "model_output": 0, "feature_contributions": [{"feature": "fixture", "value": 0}]},
    )
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.selectbox(key="audit-source").select("uploaded").run()
    assert not app.error and not app.button
    app.file_uploader(key="audit-json").upload("decision.json", raw, "application/json").run()
    assert not app.error and not app.text_input
    assert {button.key for button in app.button} == {"verify-original"}
    assert any(code.value == record["decision_id"] for code in app.code)
    app.button(key="verify-original").click().run()
    assert contains(app, "NOT_FOUND")

    tx = register(registry, w3.eth.accounts[0], bytes.fromhex(record["decision_id"]), *commitments(record, raw))
    app.button(key="verify-original").click().run()
    assert contains(app, "PENDING")
    w3.manager.request_blocking("evm_mine", [])
    app.button(key="verify-original").click().run()
    assert contains(app, "VERIFIED")
    assert any(code.value == w3.to_hex(tx) for code in app.code)

    changed = canonical_serialize(record | {"risk_probability": "0.20000000"})
    app.file_uploader(key="audit-json").clear().upload("changed.json", changed, "application/json").run()
    assert not contains(app, "VERIFIED")
    app.button(key="verify-original").click().run()
    assert contains(app, "MISMATCH")
    assert any("Hash bản ghi** · Sai lệch" in item.value for item in app.markdown)
    assert any("Hash phiên bản mô hình** · Khớp" in item.value for item in app.markdown)
    app.file_uploader(key="audit-json").clear().upload("bad.json", raw + b"\n", "application/json").run()
    assert app.error and not app.button and not contains(app, "MISMATCH")
    assert not (runtime / "audit.sqlite3").exists()
