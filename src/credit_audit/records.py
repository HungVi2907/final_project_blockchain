"""Canonical v1 decision records and cryptographic commitments."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from hashlib import sha256
import json
import math
import re
import secrets
import unicodedata

DATASETS = {"taiwan_uci350", "home_credit_2018"}
FIELDS = {"schema_version", "dataset_id", "decision_id", "input_reference", "model_version", "model_artifact_sha256", "risk_probability", "shap_explanation", "timestamp_utc", "nonce"}
SHAP_FIELDS = {"method", "output_space", "base_value", "model_output", "feature_contributions"}
DECIMAL8 = re.compile(r"^-?(?:0|[1-9][0-9]*)\.[0-9]{8}$")
UTC_SECOND = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


def fixed8(value) -> str:
    if not math.isfinite(float(value)):
        raise ValueError("Non-finite number")
    result = Decimal(str(value)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
    return "0.00000000" if result == 0 else format(result, ".8f")


def _normalize(value):
    if isinstance(value, str):
        result = unicodedata.normalize("NFC", value)
        result.encode("utf-8", errors="strict")
        return result
    if isinstance(value, dict):
        return {_normalize(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, float):
        raise ValueError("Float must be converted to fixed8 before serialization")
    return value


def canonical_serialize(record: dict) -> bytes:
    if set(record) != FIELDS or record["schema_version"] != "1" or record["dataset_id"] not in DATASETS:
        raise ValueError("Invalid v1 record fields")
    if set(record["shap_explanation"]) != SHAP_FIELDS:
        raise ValueError("Invalid SHAP fields")
    if len(record["decision_id"]) != 64 or len(record["nonce"]) != 32 or len(record["input_reference"]) != 32:
        raise ValueError("Invalid ID length")
    for key in ("decision_id", "nonce", "input_reference", "model_artifact_sha256"):
        size = 64 if key in ("decision_id", "model_artifact_sha256") else 32
        if len(record[key]) != size or any(c not in "0123456789abcdef" for c in record[key]):
            raise ValueError(f"Invalid {key}")
    if not isinstance(record["risk_probability"], str) or not DECIMAL8.fullmatch(record["risk_probability"]) or record["risk_probability"] == "-0.00000000":
        raise ValueError("Invalid probability format")
    if not (Decimal("0") <= Decimal(record["risk_probability"]) <= Decimal("1")):
        raise ValueError("Invalid probability")
    if not UTC_SECOND.fullmatch(record["timestamp_utc"]):
        raise ValueError("Invalid UTC timestamp")
    if record["shap_explanation"]["output_space"] not in {"raw", "probability"}:
        raise ValueError("Invalid output space")
    normalized = _normalize(record)
    if len(normalized) != len(record):
        raise ValueError("Unicode-normalized duplicate key")
    shap = normalized["shap_explanation"]
    for key in ("base_value", "model_output"):
        if not isinstance(shap[key], str) or not DECIMAL8.fullmatch(shap[key]) or shap[key] == "-0.00000000":
            raise ValueError(f"Invalid {key} format")
    contributions = normalized["shap_explanation"]["feature_contributions"]
    if not contributions:
        raise ValueError("Empty contributions")
    if any(set(item) != {"feature", "value"} for item in contributions):
        raise ValueError("Invalid contribution")
    names = [item["feature"] for item in contributions]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate feature")
    if any(not isinstance(item["value"], str) or not DECIMAL8.fullmatch(item["value"]) or item["value"] == "-0.00000000" for item in contributions):
        raise ValueError("Invalid contribution value")
    normalized["shap_explanation"]["feature_contributions"] = sorted(contributions, key=lambda x: x["feature"])
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def create_record(dataset_id: str, prediction: dict, explanation: dict, input_reference: str | None = None) -> tuple[dict, bytes]:
    if dataset_id not in DATASETS:
        raise ValueError("Unknown dataset")
    contributions = explanation["feature_contributions"]
    if abs(explanation["base_value"] + sum(v["value"] for v in contributions) - explanation["model_output"]) > 1e-5:
        raise ValueError("SHAP additivity failed")
    shap = {
        "method": explanation["method"], "output_space": explanation["output_space"],
        "base_value": fixed8(explanation["base_value"]), "model_output": fixed8(explanation["model_output"]),
        "feature_contributions": [{"feature": c["feature"], "value": fixed8(c["value"])} for c in contributions],
    }
    record = {
        "schema_version": "1", "dataset_id": dataset_id, "decision_id": secrets.token_hex(32),
        "input_reference": input_reference or secrets.token_hex(16),
        "model_version": prediction["model_version"], "model_artifact_sha256": prediction["model_artifact_sha256"],
        "risk_probability": fixed8(prediction["risk_probability"]), "shap_explanation": shap,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "nonce": secrets.token_hex(16),
    }
    return record, canonical_serialize(record)


def commitments(record: dict, canonical_bytes: bytes) -> tuple[bytes, bytes]:
    normalized = json.loads(canonical_bytes)
    if canonical_serialize(record) != canonical_bytes:
        raise ValueError("Record disagrees with canonical bytes")
    return (sha256(canonical_bytes).digest(), sha256((normalized["model_version"] + "|" + normalized["model_artifact_sha256"]).encode("utf-8")).digest())

