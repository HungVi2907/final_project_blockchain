"""Generate a synthetic SHAP record for C's local Anvil smoke test."""

from contextlib import closing
from hashlib import sha256
import json
from math import exp, fsum
from pathlib import Path
from statistics import mean

from credit_audit.records import commitments, create_record
from credit_audit.storage import connect, get, save


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "role_b_smoke"
FEATURES = ("feature_a", "feature_b")
BACKGROUND = ((0, 2), (2, 4), (4, 6), (6, 8))
EXAMPLE = (5, 3)


def main() -> None:
    model = {"features": FEATURES, "coefficients": (0.5, -0.25), "intercept": -0.5}
    model_bytes = json.dumps(model, sort_keys=True, separators=(",", ":")).encode("utf-8")
    weights = model["coefficients"]
    center = tuple(mean(column) for column in zip(*BACKGROUND))
    base = model["intercept"] + fsum(weight * value for weight, value in zip(weights, center))
    margin = model["intercept"] + fsum(weight * value for weight, value in zip(weights, EXAMPLE))
    contributions = [
        {"feature": name, "value": weight * (value - average)}
        for name, weight, value, average in zip(FEATURES, weights, EXAMPLE, center)
    ]
    prediction = {
        "risk_probability": 1 / (1 + exp(-margin)),
        "model_version": "synthetic-linear-smoke-v1",
        "model_artifact_sha256": sha256(model_bytes).hexdigest(),
    }
    explanation = {
        "method": "linear_interventional_shap_formula",
        "output_space": "raw",
        "base_value": base,
        "model_output": margin,
        "feature_contributions": contributions,
    }
    # The v1 dataset enum uses the Taiwan ID for this synthetic compatibility fixture.
    record, canonical_bytes = create_record("taiwan_uci350", prediction, explanation)
    decision_id = record["decision_id"]
    record_hash, model_hash = commitments(record, canonical_bytes)

    with closing(connect(OUTPUT / "audit.sqlite3")) as db:
        save(db, record, canonical_bytes)
        saved = get(db, decision_id)
        if saved["canonical_bytes"] != canonical_bytes:
            raise RuntimeError("SQLite did not preserve the canonical bytes")
        if commitments(saved["record"], saved["canonical_bytes"]) != (record_hash, model_hash):
            raise RuntimeError("SQLite round-trip changed the commitments")

    summary = {
        "synthetic": True,
        "dataset_id": record["dataset_id"],
        "decision_id": decision_id,
        "record_hash": record_hash.hex(),
        "model_version_hash": model_hash.hex(),
        "risk_probability": record["risk_probability"],
        "shap_residual": base + fsum(item["value"] for item in contributions) - margin,
    }
    (OUTPUT / "model.json").write_bytes(model_bytes)
    (OUTPUT / "decision_record.json").write_bytes(canonical_bytes)
    summary_json = json.dumps(summary, indent=2)
    (OUTPUT / "taiwan_smoke_summary.json").write_text(summary_json + "\n", encoding="utf-8")
    print(summary_json)


if __name__ == "__main__":
    main()
