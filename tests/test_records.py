import copy
from hashlib import sha256

import pytest

from credit_audit.records import canonical_serialize, commitments, create_record


def example():
    prediction = {"risk_probability": 0.72, "model_version": "taiwan-lr-v1", "model_artifact_sha256": "a" * 64}
    explanation = {"method": "linear_interventional_shap_formula", "output_space": "raw", "base_value": 0.2, "model_output": 0.72, "feature_contributions": [{"feature": "z", "value": 0.4}, {"feature": "a", "value": 0.12}]}
    return create_record("taiwan_uci350", prediction, explanation)


def test_canonical_stability_and_tampering():
    record, raw = example()
    assert raw == canonical_serialize(record)
    assert raw.index(b'"feature":"a"') < raw.index(b'"feature":"z"')
    original, model = commitments(record, raw)
    changed = copy.deepcopy(record)
    changed["risk_probability"] = "0.73000000"
    changed_raw = canonical_serialize(changed)
    assert sha256(changed_raw).digest() != original
    assert commitments(changed, changed_raw)[1] == model
    changed["model_version"] = "taiwan-lr-v2"
    changed_raw = canonical_serialize(changed)
    assert commitments(changed, changed_raw)[1] != model


def test_additivity_and_invalid_decimal():
    record, _ = example()
    record["risk_probability"] = "0.72"
    with pytest.raises(ValueError):
        canonical_serialize(record)
    with pytest.raises(ValueError):
        create_record("taiwan_uci350", {"risk_probability": 0.72, "model_version": "v", "model_artifact_sha256": "a" * 64}, {"method": "m", "output_space": "raw", "base_value": 0, "model_output": 1, "feature_contributions": []})


def test_heloc_uses_v2_without_allowing_cross_version_dataset_ids():
    prediction = {"risk_probability": 0.5, "model_version": "heloc-lr", "model_artifact_sha256": "a" * 64}
    explanation = {
        "method": "linear_interventional_shap_formula", "output_space": "raw",
        "base_value": 0, "model_output": 0,
        "feature_contributions": [{"feature": f"feature_{index}", "value": 0} for index in range(43)],
    }
    record, raw = create_record("fico_heloc_iclr2025", prediction, explanation)
    assert record["schema_version"] == "2"
    assert canonical_serialize(record) == raw
    with pytest.raises(ValueError):
        canonical_serialize(record | {"schema_version": "1"})
    with pytest.raises(ValueError):
        canonical_serialize(record | {"dataset_id": "taiwan_uci350"})
