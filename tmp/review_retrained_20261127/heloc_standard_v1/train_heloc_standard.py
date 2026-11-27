"""Train and evaluate a new HELOC model version from the frozen data export."""

import argparse
import hashlib
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from zipfile import ZipFile

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, brier_score_loss, confusion_matrix, f1_score,
    log_loss, precision_recall_curve, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


SEED = 2338
BOOTSTRAP_REPEATS = 1000
ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("numpy", "pandas", "scipy", "scikit-learn", "xgboost", "joblib")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def read_source(bundle):
    with ZipFile(bundle) as archive:
        root = "SuperBells_HELOC_XAI/"
        manifest = json.loads(archive.read(root + "manifest.json"))
        if manifest["dataset_id"] != "fico_heloc_iclr2025" or manifest["test_fold"] != 5:
            raise ValueError("Expected the pinned FICO HELOC fold 5 bundle")
        frames = {}
        from io import BytesIO
        for split in ("train", "test"):
            name = f"data/{split}.csv"
            raw = archive.read(root + name)
            if digest(raw) != manifest["sha256"][name]:
                raise ValueError(f"Checksum mismatch: {name}")
            frame = pd.read_csv(BytesIO(raw))
            if list(frame) != ["split_position", "label", *manifest["feature_order"]]:
                raise ValueError(f"Unexpected column order in {name}")
            if set(frame["label"]) != {-1, 1} or frame.isna().any().any():
                raise ValueError(f"Unexpected missing values or labels in {name}")
            if len(frame) != manifest[f"{split}_rows"] or not frame["split_position"].is_unique:
                raise ValueError(f"Unexpected row count or duplicated positions in {name}")
            frame = frame.rename(columns={"split_position": "source_position"})
            frame["label"] = (frame["label"] == -1).astype(int)
            frames[split] = frame
    return manifest, frames["train"], frames["test"]


def searches():
    return {
        "LR": (
            Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(max_iter=3000, random_state=SEED))]),
            {"model__C": [0.01, 0.1, 1, 10]},
        ),
        "RF": (
            RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=1),
            {"max_depth": [8, 16, None], "min_samples_leaf": [4, 12]},
        ),
        "XGB": (
            XGBClassifier(random_state=SEED, n_jobs=1, tree_method="hist", eval_metric="logloss"),
            {"max_depth": [2, 4], "learning_rate": [0.03, 0.1], "n_estimators": [100, 250]},
        ),
    }


def choose_threshold(labels, probabilities):
    precision, recall, thresholds = precision_recall_curve(labels, probabilities)
    total = precision[:-1] + recall[:-1]
    f1 = np.divide(2 * precision[:-1] * recall[:-1], total, out=np.zeros_like(total), where=total > 0)
    # Thresholds are ascending. Choose the highest exact tie.
    return float(thresholds[np.flatnonzero(f1 == f1.max())[-1]])


def metrics(labels, probabilities, threshold):
    predicted = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    return dict(
        rows=len(labels), bad_count=int(np.sum(labels)), threshold=threshold,
        roc_auc=roc_auc_score(labels, probabilities), average_precision=average_precision_score(labels, probabilities),
        log_loss=log_loss(labels, probabilities, labels=[0, 1]), brier_score=brier_score_loss(labels, probabilities),
        precision=precision_score(labels, predicted, zero_division=0), recall=recall_score(labels, predicted),
        f1=f1_score(labels, predicted), tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp),
    )


def bootstrap_intervals(labels, probabilities):
    rng = np.random.default_rng(SEED)
    labels = np.asarray(labels)
    negative, positive = np.flatnonzero(labels == 0), np.flatnonzero(labels == 1)
    scores = []
    for _ in range(BOOTSTRAP_REPEATS):
        sample = np.r_[rng.choice(negative, len(negative)), rng.choice(positive, len(positive))]
        scores.append([roc_auc_score(labels[sample], probabilities[sample]),
                       average_precision_score(labels[sample], probabilities[sample])])
    lower, upper = np.quantile(scores, [0.025, 0.975], axis=0)
    return dict(roc_auc_ci_low=lower[0], roc_auc_ci_high=upper[0],
                average_precision_ci_low=lower[1], average_precision_ci_high=upper[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "artifacts/SuperBells_HELOC_XAI.zip")
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    source, development, test = read_source(args.bundle)
    fit, validation = train_test_split(development, test_size=0.2, random_state=SEED, stratify=development["label"])
    splits = {"train": fit.sort_index(), "validation": validation.sort_index(), "test": test}
    features = source["feature_order"]
    args.output.mkdir(parents=True, exist_ok=False)
    for name in ("data", "models", "results"):
        (args.output / name).mkdir()
    for name, frame in splits.items():
        frame.to_csv(args.output / "data" / f"{name}.csv", index=False)
    fit, validation = splits["train"], splits["validation"]
    cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=SEED)
    folds = np.empty(len(fit), dtype=int)
    for fold, (_, holdout) in enumerate(cv.split(fit[features], fit["label"]), start=1):
        folds[holdout] = fold
    fit[["source_position"]].assign(cv_fold=folds).to_csv(args.output / "data/cv_folds.csv", index=False)
    models, thresholds, tuning, selection = {}, {}, {}, {}
    for name, (estimator, grid) in searches().items():
        search = GridSearchCV(estimator, grid, scoring={"ap": "average_precision", "auc": "roc_auc"},
                              refit="ap", cv=cv, n_jobs=2, error_score="raise")
        search.fit(fit[features], fit["label"])
        model = search.best_estimator_
        probability = model.predict_proba(validation[features])[:, list(model.classes_).index(1)]
        thresholds[name] = choose_threshold(validation["label"], probability)
        selection[name] = metrics(validation["label"], probability, thresholds[name])
        tuning[name] = {"best_params": search.best_params_, "best_cv_ap": float(search.best_score_)}
        pd.DataFrame(search.cv_results_).to_csv(args.output / "results" / f"cv_{name}.csv", index=False)
        models[name] = model
    selected = sorted(models, key=lambda name: (-selection[name]["average_precision"],
                                                 -selection[name]["roc_auc"], name))[0]
    write_json(args.output / "selection.json", {
        "selected_model": selected, "criterion": "validation AP, then ROC-AUC, then model name",
        "threshold_rule": "maximize validation F1 for Bad, choose highest threshold on exact ties",
        "validation": selection, "tuning": tuning,
    })
    all_metrics, all_predictions = [], []
    for name, model in models.items():
        joblib.dump(model, args.output / "models" / f"{name}.joblib", compress=3)
        for split, frame in splits.items():
            probability = model.predict_proba(frame[features])[:, list(model.classes_).index(1)]
            threshold = thresholds[name]
            row = dict(model=name, split=split, selected=name == selected, **metrics(frame["label"], probability, threshold))
            if split == "test":
                row.update(bootstrap_intervals(frame["label"], probability))
            all_metrics.append(row)
            all_predictions.append(frame[["source_position", "label"]].assign(
                split=split, model=name, p_bad=probability, predicted_bad=(probability >= threshold).astype(int)
            ))
    pd.DataFrame(all_metrics).to_csv(args.output / "results/metrics.csv", index=False)
    pd.concat(all_predictions, ignore_index=True).to_csv(args.output / "results/predictions.csv", index=False)
    background = fit.sample(n=100, random_state=SEED)
    background.to_csv(args.output / "data/xai_background.csv", index=False)
    (args.output / "requirements.txt").write_text("".join(f"{p}=={version(p)}\n" for p in PACKAGES), encoding="utf-8")
    write_json(args.output / "manifest.json", {
        "dataset_id": source["dataset_id"], "author_commit": source["author_commit"],
        "source_bundle_sha256": digest(args.bundle.read_bytes()), "source_split_sha256": {
            k: v for k, v in source["sha256"].items() if k in ("data/train.csv", "data/test.csv")
        }, "source_test_fold": source["test_fold"], "seed": SEED, "feature_order": features,
        "label_mapping": {"0": "Good", "1": "Bad"}, "selected_model": selected,
        "selected_model_path": f"models/{selected}.joblib", "selected_threshold": thresholds[selected],
        "training_script_sha256": digest(Path(__file__).read_bytes()),
        "row_counts": {name: len(frame) for name, frame in splits.items()}, "bootstrap_repeats": BOOTSTRAP_REPEATS,
        "python": sys.version, "platform": platform.platform(),
        "sha256": {p.relative_to(args.output).as_posix(): digest(p.read_bytes())
                   for p in sorted(args.output.rglob("*")) if p.is_file()},
    })
    print(pd.DataFrame(all_metrics).loc[lambda frame: frame.split != "train", [
        "model", "split", "roc_auc", "average_precision", "precision", "recall", "f1", "threshold",
    ]].to_string(index=False))
    print(f"Selected on validation: {selected}")


if __name__ == "__main__":
    main()
