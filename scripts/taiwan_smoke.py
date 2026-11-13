"""Train a small LR baseline and save one complete SHAP-backed decision."""
from pathlib import Path
import json


from credit_audit.data import FEATURES, load_taiwan, split_taiwan
from credit_audit.ml import predict, train_smoke
from credit_audit.records import create_record, commitments
from credit_audit.storage import connect, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "data/raw/default of credit card clients.xls"
    frame = load_taiwan(source)
    train, val, test = split_taiwan(frame, source, ROOT / "artifacts/taiwan_split.json")
    pipeline, manifest = train_smoke(train, val, test, ROOT / "artifacts")
    input_row = test.iloc[0][list(FEATURES)].to_dict()
    prediction = predict(pipeline, manifest, input_row)
    background = pipeline[:-1].transform(train[list(FEATURES)].sample(n=200, random_state=42))
    # Interventional linear SHAP in log-odds space: phi_i = beta_i * (x_i - E[X_i]).
    model = pipeline.named_steps["model"]
    contributions = model.coef_[0] * (prediction["transformed_features"] - background.mean(axis=0))
    base_value = float(model.intercept_[0] + model.coef_[0] @ background.mean(axis=0))
    raw_output = float(pipeline.named_steps["model"].decision_function(prediction["transformed_features"].reshape(1, -1))[0])
    explanation = {
        "method": "linear_interventional_shap_formula", "output_space": "raw", "base_value": base_value,
        "model_output": raw_output,
        "feature_contributions": [{"feature": name, "value": float(value)} for name, value in zip(FEATURES, contributions)],
    }
    record, canonical_bytes = create_record("taiwan_uci350", prediction, explanation)
    db = connect(ROOT / "artifacts/audit.sqlite3")
    save(db, record, canonical_bytes)
    record_hash, model_hash = commitments(record, canonical_bytes)
    summary = {"rows": len(frame), "split": [len(train), len(val), len(test)], "metrics": manifest["metrics"], "decision_id": record["decision_id"], "record_hash": record_hash.hex(), "model_version_hash": model_hash.hex(), "shap_residual": explanation["base_value"] + sum(v["value"] for v in explanation["feature_contributions"]) - raw_output}
    (ROOT / "artifacts/taiwan_smoke_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

