"""Synthetic v1 decision used by the Anvil demo and benchmark."""
from credit_audit.records import create_record
from credit_audit.storage import save


def create_demo_decision(db) -> str:
    record, raw = create_record(
        "taiwan_uci350",
        {"risk_probability": 0.42, "model_version": "synthetic-demo-v1", "model_artifact_sha256": "ab" * 32},
        {"method": "synthetic_demo", "output_space": "probability", "base_value": 0.4,
         "model_output": 0.42, "feature_contributions": [{"feature": "synthetic_feature", "value": 0.02}]},
    )
    save(db, record, raw)
    return record["decision_id"]
