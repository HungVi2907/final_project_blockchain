"""Small Taiwan integration model; not the final E1 model search."""
from hashlib import sha256
from pathlib import Path
import json

import joblib
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from credit_audit.data import FEATURES, TARGET


def train_smoke(train, val, test, out_dir: Path):
    pipeline = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    pipeline.fit(train[list(FEATURES)], train[TARGET])
    val_p = pipeline.predict_proba(val[list(FEATURES)])[:, 1]
    candidates = np.unique(np.r_[0.01, np.arange(0.05, 0.96, 0.01), 0.99])
    threshold = float(max(candidates, key=lambda t: (f1_score(val[TARGET], val_p >= t), -t)))
    test_p = pipeline.predict_proba(test[list(FEATURES)])[:, 1]
    metrics = {
        "validation_pr_auc": float(average_precision_score(val[TARGET], val_p)),
        "threshold": threshold,
        "test_pr_auc": float(average_precision_score(test[TARGET], test_p)),
        "test_roc_auc": float(roc_auc_score(test[TARGET], test_p)),
        "test_f1": float(f1_score(test[TARGET], test_p >= threshold)),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "taiwan_lr_smoke.joblib"
    joblib.dump(pipeline, model_path)
    manifest = {
        "dataset_id": "taiwan_uci350", "model_version": "taiwan-lr-smoke-v1",
        "model_artifact_sha256": sha256(model_path.read_bytes()).hexdigest(),
        "feature_names": list(FEATURES), "threshold": threshold, "metrics": metrics,
        "scope": "integration smoke only; LR without RF/XGBoost search",
    }
    (out_dir / "taiwan_lr_smoke.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return pipeline, manifest


def predict(pipeline, manifest: dict, feature_dict: dict) -> dict:
    import pandas as pd
    if manifest["dataset_id"] != "taiwan_uci350" or set(feature_dict) != set(FEATURES):
        raise ValueError("Dataset/feature schema mismatch")
    ordered = pd.DataFrame([{f: feature_dict[f] for f in FEATURES}])
    p = float(pipeline.predict_proba(ordered)[0, 1])
    return {
        "risk_probability": p, "predicted_label": int(p >= manifest["threshold"]),
        "model_version": manifest["model_version"],
        "model_artifact_sha256": manifest["model_artifact_sha256"],
        "transformed_features": pipeline[:-1].transform(ordered)[0],
    }

