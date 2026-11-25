"""Rebuild the HELOC split and prepare one LR explanation in the author environment."""

from contextlib import redirect_stdout
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import runpy
import subprocess
import sys

from replicate_cheon import EXPECTED_COMMIT, load_module

SEED = 2338
FOLD = "K05N01"
TEST_FOLD = 5
MODEL_SHA = "b9b7a30f8afaec886c9255527c966c25e105af599f0835206c1e91b79b31e654"
SOURCE_SHA = "65cf152304303b80c26c33808f7c2400e9b77f9222cc8160213d6893b11ee2a4"
HELPER_SHA = "66f6b37a2ac875fab087c3268680a4e6b1feaa0db55cd653189a37b9d34775e6"


def checked_bytes(path, expected):
    content = path.read_bytes()
    if sha256(content).hexdigest() != expected:
        raise ValueError(f"Checksum mismatch for {path.name}")
    return content


def prepare(repo, test_offset):
    import dill
    import numpy as np
    import sklearn
    from scipy.special import expit

    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    changes = subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"], text=True,
    ).strip()
    if commit != EXPECTED_COMMIT or changes or sklearn.__version__ != "1.5.2":
        raise RuntimeError("Use the clean pinned author checkout and scikit-learn 1.5.2")
    paper = repo / "research" / "iclr2025"
    sys.path.insert(0, str(repo))
    load_module("responsiveness.paths", paper / "src" / "paths.py")
    import responsiveness.paths as author_paths
    load_module("responsiveness.ext.utils", paper / "src" / "utils.py")
    from responsiveness.ext import fileutils

    model_name = "fico_complex_nD_logreg_processed.model"
    model_bytes = checked_bytes(paper / "results" / model_name, MODEL_SHA)
    with TemporaryDirectory(prefix="heloc-pilot-") as temporary:
        root = Path(temporary)
        source_root = root / "fico"
        source_root.mkdir()
        for name, expected in (("fico_data.csv", SOURCE_SHA), ("fico_helper.csv", HELPER_SHA)):
            source = paper / "data" / "fico" / name
            (source_root / name).write_bytes(checked_bytes(source, expected))
        original_data_dir = author_paths.data_dir
        author_paths.data_dir = root
        try:
            with redirect_stdout(sys.stderr):
                runpy.run_path(str(paper / "experiment" / "setup_dataset_actionset_fico.py"))
            data = fileutils.load(root / "fico_complex_nD.data")
        finally:
            author_paths.data_dir = original_data_dir

    data.split(fold_id=FOLD, fold_num_test=TEST_FOLD)
    train, test = data.training.X, data.test.X
    if train.shape != (4674, 43) or test.shape != (1168, 43) or not 0 <= test_offset < len(test):
        raise ValueError("Unexpected HELOC split or held-out position")
    artifact = dill.loads(model_bytes)["data"]
    if (artifact["seed"], artifact["fold_id"], artifact["fold_num_test"]) != (SEED, FOLD, TEST_FOLD):
        raise ValueError("Artifact split metadata differs from the rebuilt split")
    pipeline = artifact["model"]
    profile = test[test_offset:test_offset + 1]
    scaler, classifier = pipeline.named_steps["scaler"], pipeline.named_steps["clf"]
    if tuple(classifier.classes_) != (-1, 1):
        raise ValueError("Expected author labels Bad = -1 and Good = +1")
    if not np.allclose(scaler.mean_, train.mean(axis=0), atol=1e-12, rtol=0):
        raise ValueError("Saved scaler disagrees with the training split")
    background_rows = np.random.default_rng(SEED).choice(len(train), size=100, replace=False)
    background_mean = scaler.transform(train[background_rows]).mean(axis=0)
    transformed = scaler.transform(profile)
    probability = float(pipeline.predict_proba(profile)[0, 0])
    coefficients = -classifier.coef_[0]
    contributions = coefficients * (transformed[0] - background_mean)
    base = float(-classifier.intercept_[0] + coefficients @ background_mean)
    raw = float(-classifier.decision_function(transformed)[0])
    residual = abs(float(base + contributions.sum() - raw))
    probability_error = abs(float(expit(raw)) - probability)
    if not np.isfinite([residual, probability_error]).all() or max(residual, probability_error) > 1e-6:
        raise ValueError("Bad-class SHAP additivity or probability check failed")

    return {
        "dataset_id": "fico_heloc_iclr2025",
        "prediction": {
            "risk_probability": probability,
            "model_version": "cheon2025-fico-complex-nd-logreg-2338",
            "model_artifact_sha256": MODEL_SHA,
        },
        "explanation": {
            "method": "linear_interventional_shap_formula",
            "output_space": "raw",
            "base_value": base,
            "model_output": raw,
            "feature_contributions": [
                {"feature": name, "value": float(value)}
                for name, value in zip(data.X_df.columns, contributions, strict=True)
            ],
        },
        "configuration": {
            "author_commit": commit, "source_sha256": SOURCE_SHA, "seed": SEED,
            "fold_id": FOLD, "test_fold": TEST_FOLD, "held_out_position": test_offset,
            "train_rows": len(train), "test_rows": len(test), "features": train.shape[1],
            "background_rows": len(background_rows), "model_version_sklearn": sklearn.__version__,
            "shap_residual": residual, "probability_error": probability_error,
        },
    }


if __name__ == "__main__":
    repo, test_offset = sys.argv[1:]
    print(json.dumps(prepare(Path(repo).resolve(), int(test_offset)), allow_nan=False))
