"""Run the registered seven-seed HELOC prediction experiment (T1-01)."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from replicate_cheon import EXPECTED_COMMIT, load_module


PAPER_AUC = {"logreg": 0.788, "rf": 0.790, "xgb": 0.785}
SEEDS = range(2338, 2345)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author-repo", type=Path, default=Path("artifacts/cheon_iclr2025"))
    parser.add_argument("--bundle", type=Path, default=Path("artifacts/SuperBells_HELOC_XAI"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    import numpy as np
    import pandas as pd
    from scipy.stats import t
    import sklearn
    from sklearn.metrics import roc_auc_score
    import xgboost

    if (sklearn.__version__, xgboost.__version__) != ("1.5.2", "2.1.4"):
        parser.error("Use the HELOC handoff's scikit-learn 1.5.2 and XGBoost 2.1.4.")
    repo = args.author_repo.resolve()
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    changes = subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"], text=True
    ).strip()
    if commit != EXPECTED_COMMIT or changes:
        parser.error("Use the clean pinned author checkout.")

    paper = repo / "research/iclr2025"
    sys.path.insert(0, str(repo))
    load_module("responsiveness.paths", paper / "src/paths.py")
    load_module("responsiveness.ext.utils", paper / "src/utils.py")
    from responsiveness.ext import fileutils, training
    from responsiveness.paths import get_data_file

    manifest = json.loads((args.bundle / "manifest.json").read_bytes())
    fold_id, test_fold = manifest["fold_id"], manifest["test_fold"]
    features = manifest["feature_order"]
    expected = {split: pd.read_csv(args.bundle / "data" / f"{split}.csv") for split in ("train", "test")}
    data_file = get_data_file(data_name="fico", action_set_name="complex_nD")
    args.output.mkdir(parents=True, exist_ok=False)
    results = []
    for name in PAPER_AUC:
        for seed in SEEDS:
            data = fileutils.load(data_file)
            data.split(fold_id=fold_id, fold_num_test=test_fold)
            for split, partition in (("train", data.training), ("test", data.test)):
                np.testing.assert_array_equal(partition.X, expected[split][features].to_numpy())
                np.testing.assert_array_equal(partition.y, expected[split]["label"].to_numpy())

            x, y = data.test.X.copy(), data.test.y.copy()
            start = perf_counter()
            fitted = training.train_model(
                data, model_type=name, seed=seed, rescale=name == "logreg",
                label_encoding=(0, 1) if name == "xgb" else None,
            )
            elapsed = perf_counter() - start
            model = fitted["model"]
            bad_index = list(model.classes_).index(0 if name == "xgb" else -1)
            p_bad = model.predict_proba(x)[:, bad_index]
            auc = float(roc_auc_score(y == -1, p_bad))
            estimator = model.named_steps["clf"] if name == "logreg" else model
            chosen = estimator.get_params()
            result = {
                "model": name, "seed": seed, "test_auc": auc, "paper_auc": PAPER_AUC[name],
                "delta": auc - PAPER_AUC[name], "fit_seconds": elapsed,
                "parameters": {key: chosen[key] for key in training.CLF_MAP[name][1]},
            }
            (args.output / f"{name}-{seed}.json").write_text(
                json.dumps(result, indent=2, default=lambda value: value.item()) + "\n", encoding="utf-8"
            )
            results.append(result)
            print(f"{name} {seed}: AUC {auc:.6f} in {elapsed:.1f} s", flush=True)

    intervals = {}
    for name, paper_auc in PAPER_AUC.items():
        scores = np.array([row["test_auc"] for row in results if row["model"] == name])
        mean = float(scores.mean())
        half_width = float(t.ppf(0.975, df=len(scores) - 1) * scores.std(ddof=1) / np.sqrt(len(scores)))
        low, high = mean - half_width, mean + half_width
        intervals[name] = {
            "mean_auc": mean, "ci95": [low, high], "paper_auc": paper_auc,
            "passes": paper_auc - 0.02 <= low <= high <= paper_auc + 0.02,
        }
    summary = {
        "author_commit": commit, "fold_id": fold_id, "test_fold": test_fold, "fits": len(results),
        "train_rows": len(expected["train"]), "test_rows": len(expected["test"]),
        "scikit_learn": sklearn.__version__, "xgboost": xgboost.__version__,
        "confidence_interval": "Student t across seven training seeds on the same split",
        "models": intervals,
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
