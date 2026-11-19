"""Compare saved ICLR 2025 author-code model outputs with paper Table 11."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--author-repo", type=Path, default=Path("artifacts/cheon_iclr2025"))
    parser.add_argument(
        "--paper-csv", type=Path, default=Path("docs/references/CHEON_2025_TABLE11_AUC.csv")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("docs/references/CHEON_2025_REPLICATION_COMPARISON.csv")
    )
    args = parser.parse_args()

    import dill
    import sklearn
    import xgboost

    repo = args.author_repo.resolve()
    sys.path.insert(0, str(repo))
    model_names = {"LR": "logreg", "XGB": "xgb", "RF": "rf"}
    code_datasets = {"heloc": "fico", "german": "german", "givemecredit": "givemecredit"}
    tuned_keys = {
        "LR": ("penalty", "solver", "max_iter"),
        "XGB": (
            "learning_rate", "max_depth", "n_estimators", "min_child_weight", "gamma",
            "booster", "subsample", "grow_policy", "reg_alpha", "reg_lambda",
        ),
        "RF": (
            "n_estimators", "max_depth", "min_samples_split", "min_samples_leaf",
            "max_features", "bootstrap",
        ),
    }
    rows = []
    with args.paper_csv.open(newline="", encoding="utf-8") as stream:
        paper_rows = list(csv.DictReader(stream))
    for paper in paper_rows:
        model_file = (
            repo / "research" / "iclr2025" / "results"
            / f"{code_datasets[paper['dataset']]}_complex_nD_{model_names[paper['model']]}_processed.model"
        )
        row = {
            "dataset": paper["dataset"],
            "model": paper["model"],
            "paper_train_auc": paper["train_auc_paper"],
            "paper_test_auc": paper["test_auc_paper"],
            "run_train_auc": "",
            "run_test_auc": "",
            "delta_test_auc": "",
            "train_n": "",
            "test_n": "",
            "seed": "",
            "fold_id": "",
            "fold_num_test": "",
            "fold_num_validation": "",
            "rebalance": "",
            "selected_params_json": "",
            "status": "not_run",
            "model_sha256": "",
            "model_saved_utc": "",
            "sklearn_version": sklearn.__version__,
            "xgboost_version": xgboost.__version__,
        }
        if model_file.exists():
            with model_file.open("rb") as stream:
                result = dill.load(stream)["data"]
            test_auc = float(result["test"]["auc"])
            estimator = result["model"]
            if hasattr(estimator, "named_steps"):
                estimator = estimator.named_steps["clf"]
            model_params = estimator.get_params()
            selected_params = {key: model_params[key] for key in tuned_keys[paper["model"]]}
            row.update(
                run_train_auc=f"{float(result['train']['auc']):.4f}",
                run_test_auc=f"{test_auc:.4f}",
                delta_test_auc=f"{test_auc - float(paper['test_auc_paper']):+.4f}",
                train_n=result["train"]["n"],
                test_n=result["test"]["n"],
                seed=result["seed"],
                fold_id=result["fold_id"],
                fold_num_test=result["fold_num_test"],
                fold_num_validation=result["fold_num_validation"] or "",
                rebalance=result["sample_processing_args"]["rebalance"] or "",
                selected_params_json=json.dumps(
                    selected_params,
                    default=lambda value: value.item() if hasattr(value, "item") else str(value),
                    sort_keys=True,
                ),
                status="completed",
                model_sha256=hashlib.sha256(model_file.read_bytes()).hexdigest(),
                model_saved_utc=datetime.fromtimestamp(
                    model_file.stat().st_mtime, timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"saved {len(rows)} comparison rows to {args.output}")
    for row in rows:
        print(
            f"{row['dataset']:13} {row['model']:3} "
            f"paper={row['paper_test_auc']} run={row['run_test_auc'] or 'pending'} "
            f"delta={row['delta_test_auc'] or 'pending'}"
        )


if __name__ == "__main__":
    main()
