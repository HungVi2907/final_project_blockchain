"""Run the paired B0/B1/B2 HELOC experiment on a fresh local Anvil registry."""

import argparse
from contextlib import ExitStack, closing
import csv
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from time import perf_counter

from prepare_heloc_pilot import MODEL_SHA, SEED


ROOT = Path(__file__).resolve().parents[1]
SEEDS = tuple(range(2338, 2343))
BASELINES = ("B0", "B1", "B2")
PROFILES_PER_SEED = 40


def prepare(bundle, output):
    import dill
    import numpy as np
    import pandas as pd
    from scipy.special import expit
    import sklearn

    manifest = json.loads((bundle / "manifest.json").read_bytes())
    expected = ("fico_heloc_iclr2025", SEED, "K05N01", 5)
    if (manifest["dataset_id"], manifest["seed"], manifest["fold_id"], manifest["test_fold"]) != expected:
        raise ValueError("Unexpected HELOC dataset or split")
    model_file = manifest["models"]["LR"]
    model_bytes = (bundle / model_file).read_bytes()
    if sha256(model_bytes).hexdigest() != MODEL_SHA or sklearn.__version__ != "1.5.2":
        raise ValueError("Use the pinned LR artifact and scikit-learn 1.5.2")
    for name in ("train", "test", "lr_pilot_background_positions", "test_predictions"):
        path = f"data/{name}.csv"
        if sha256((bundle / path).read_bytes()).hexdigest() != manifest["sha256"][path]:
            raise ValueError(f"Changed handoff file: {path}")

    features = manifest["feature_order"]
    train, test = (pd.read_csv(bundle / "data" / f"{split}.csv") for split in ("train", "test"))
    for frame, rows in ((train, 4674), (test, 1168)):
        if frame.shape != (rows, 45) or list(frame) != ["split_position", "label", *features]:
            raise ValueError("Unexpected data dimensions or feature order")
        np.testing.assert_array_equal(frame["split_position"], np.arange(rows))
    background = pd.read_csv(bundle / "data/lr_pilot_background_positions.csv")["train_split_position"]
    np.testing.assert_array_equal(background, np.random.default_rng(SEED).choice(len(train), size=100, replace=False))
    reference = pd.read_csv(bundle / "data/test_predictions.csv")
    for key in ("split_position", "label"):
        np.testing.assert_array_equal(reference[key], test[key])

    model = dill.loads(model_bytes)["data"]["model"]
    scaler, classifier = model.named_steps["scaler"], model.named_steps["clf"]
    if list(classifier.classes_) != [-1, 1]:
        raise ValueError("Unexpected Bad and Good class ordering")
    test_x = test[features].to_numpy()
    transformed = scaler.transform(test_x)
    background_mean = scaler.transform(train.iloc[background][features].to_numpy()).mean(axis=0)
    weights = -classifier.coef_[0]
    base = float(-classifier.intercept_[0] + background_mean @ weights)
    contributions = (transformed - background_mean) * weights
    log_odds = -classifier.decision_function(transformed)
    p_bad = model.predict_proba(test_x)[:, 0]
    np.testing.assert_allclose(p_bad, reference["p_bad_LR"], atol=1e-10, rtol=0)
    np.testing.assert_allclose(expit(log_odds), p_bad, atol=1e-6, rtol=0)
    np.testing.assert_allclose(base + contributions.sum(axis=1), log_odds, atol=1e-6, rtol=0)

    sets = {}
    for seed in SEEDS:
        positions = np.random.default_rng(seed).choice(len(test), size=PROFILES_PER_SEED, replace=False)
        sets[str(seed)] = [
            {
                "test_position": int(index),
                "risk_probability": float(p_bad[index]),
                "model_output": float(log_odds[index]),
                "contributions": contributions[index].tolist(),
            }
            for index in positions
        ]
    payload = {
        "dataset_id": manifest["dataset_id"], "author_commit": manifest["author_commit"],
        "fold_id": manifest["fold_id"], "test_fold": manifest["test_fold"],
        "model_version": "cheon2025-fico-complex-nd-logreg-2338", "model_artifact_sha256": MODEL_SHA,
        "features": features, "base_value": base, "background_rows": len(background),
        "max_shap_residual": float(np.max(np.abs(base + contributions.sum(axis=1) - log_odds))),
        "sets": sets,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, allow_nan=False)


def measure(verdict):
    start = perf_counter()
    status = verdict()
    return status, (perf_counter() - start) * 1000


def latency(values):
    import numpy as np

    return {"median": median(values), "p95": float(np.percentile(values, 95))}


def paired_interval(differences):
    from scipy.stats import beta

    # Bonferroni bounds for the two discordant-pair probabilities.
    n = len(differences)
    bounds = []
    for direction in (1, -1):
        count = differences.count(direction)
        low = float(beta.ppf(0.0125, count, n - count + 1)) if count else 0.0
        high = float(beta.ppf(0.9875, count + 1, n - count)) if count < n else 1.0
        bounds.append((low, high))
    return [bounds[0][0] - bounds[1][1], bounds[0][1] - bounds[1][0]]


def summarize(trials):
    results = {}
    for arm in BASELINES:
        rows = [row for row in trials if row["baseline"] == arm]
        originals = [row for row in rows if row["condition"] == "original"]
        changed = [row for row in rows if row["condition"] == "changed"]
        results[arm] = {
            "detected": sum(row["status"] == "MISMATCH" for row in changed),
            "changed": len(changed),
            "false_alerts": sum(row["status"] == "MISMATCH" for row in originals),
            "originals": len(originals),
            "covered": sum(row["status"] in ("ACCEPTED", "VERIFIED", "MISMATCH") for row in rows),
            "verdicts": len(rows),
            "verification_ms": {
                "original": latency([row["verification_ms"] for row in originals]),
                "changed": latency([row["verification_ms"] for row in changed]),
            },
        }
    return results


def run_seed(payload, seed, output, rpc_url):
    from credit_audit.chain import compile_registry, connect_anvil, deploy, inspect_decision, submit_saved
    from credit_audit.records import canonical_serialize, commitments, create_record
    from credit_audit.storage import connect, get, save

    w3 = connect_anvil(rpc_url)
    chain_id, writer_account = w3.eth.chain_id, w3.eth.accounts[0]
    registry = deploy(w3, compile_registry(ROOT / "contracts/DecisionRegistry.vy"), writer_account)
    profiles = payload["sets"][str(seed)]
    if len(profiles) != PROFILES_PER_SEED or len({row["test_position"] for row in profiles}) != len(profiles):
        raise ValueError(f"Expected {PROFILES_PER_SEED} distinct test positions for seed {seed}")
    output.mkdir(parents=True, exist_ok=False)
    trials, registrations = [], []
    with ExitStack() as stack:
        stores = {
            arm: stack.enter_context(closing(connect(output / f"{arm.lower()}.sqlite3")))
            for arm in BASELINES
        }
        stores["B1"].execute("CREATE TABLE local_hashes (decision_id TEXT PRIMARY KEY, record_hash BLOB, model_hash BLOB)")
        for profile in profiles:
            prediction = {key: payload[key] for key in ("model_version", "model_artifact_sha256")}
            prediction["risk_probability"] = profile["risk_probability"]
            explanation = {
                "method": "linear_interventional_shap_formula", "output_space": "raw",
                "base_value": payload["base_value"], "model_output": profile["model_output"],
                "feature_contributions": [
                    {"feature": feature, "value": value}
                    for feature, value in zip(payload["features"], profile["contributions"], strict=True)
                ],
            }
            original, raw = create_record(payload["dataset_id"], prediction, explanation)
            decision_id = original["decision_id"]
            for db in stores.values():
                save(db, original, raw)
            with stores["B1"]:
                stores["B1"].execute("INSERT INTO local_hashes VALUES (?, ?, ?)", (decision_id, *commitments(original, raw)))
            b2 = stores["B2"]
            start = perf_counter()
            tx = submit_saved(b2, registry, w3, decision_id, writer_account, expected_chain_id=chain_id)
            receipt = w3.eth.wait_for_transaction_receipt(tx, timeout=30, poll_latency=0.1)
            elapsed = (perf_counter() - start) * 1000
            if receipt.status != 1:
                raise RuntimeError(f"Anchor failed for decision {decision_id}")
            with b2:
                b2.execute(
                    "UPDATE decisions SET block_number=?, status='CONFIRMED' WHERE decision_id=?",
                    (receipt.blockNumber, decision_id),
                )
            registration = {
                "seed": seed, "test_position": profile["test_position"], "decision_id": decision_id,
                "tx_hash": tx, "block": receipt.blockNumber, "gas": receipt.gasUsed,
                "submit_to_receipt_ms": elapsed, "fee_wei": receipt.gasUsed * receipt.effectiveGasPrice,
            }
            registrations.append(registration)

            changed = dict(original)
            changed["risk_probability"] = "0.00000000" if original["risk_probability"] != "0.00000000" else "1.00000000"
            changed_bytes = canonical_serialize(changed)

            def local_only(arm, db):
                record = get(db, decision_id)
                if record is None:
                    return "NOT_FOUND"
                if arm == "B0":
                    return "ACCEPTED"
                stored = db.execute(
                    "SELECT record_hash, model_hash FROM local_hashes WHERE decision_id=?", (decision_id,)
                ).fetchone()
                actual = commitments(record["record"], record["canonical_bytes"])
                return "ACCEPTED" if stored == actual else "MISMATCH"

            for arm, db in stores.items():
                def verdict():
                    if arm == "B2":
                        return inspect_decision(db, registry, w3, decision_id, expected_chain_id=chain_id).status
                    return local_only(arm, db)

                before = measure(verdict)
                db.execute("SAVEPOINT changed_copy")
                try:
                    db.execute(
                        "UPDATE decisions SET display_json=?, canonical_bytes=? WHERE decision_id=?",
                        (json.dumps(changed), changed_bytes, decision_id),
                    )
                    if arm == "B1":
                        db.execute(
                            "UPDATE local_hashes SET record_hash=?, model_hash=? WHERE decision_id=?",
                            (*commitments(changed, changed_bytes), decision_id),
                        )
                    after = measure(verdict)
                finally:
                    db.execute("ROLLBACK TO changed_copy")
                    db.execute("RELEASE changed_copy")
                for condition, (status, ms) in (("original", before), ("changed", after)):
                    trials.append({
                        "seed": seed, "test_position": profile["test_position"], "decision_id": decision_id,
                        "baseline": arm, "condition": condition, "status": status, "verification_ms": ms,
                    })

    for filename, rows in (("trials.csv", trials), ("registrations.csv", registrations)):
        with (output / filename).open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    arms = summarize(trials)
    changed_rows = {
        arm: {row["decision_id"]: int(row["status"] == "MISMATCH") for row in trials
              if row["baseline"] == arm and row["condition"] == "changed"}
        for arm in BASELINES
    }
    gains = {}
    for control in ("B0", "B1"):
        differences = [flag - changed_rows[control][key] for key, flag in changed_rows["B2"].items()]
        gains[control] = {"rate_gain": sum(differences) / len(differences), "ci95": paired_interval(differences)}
    passed = (
        all(arm["false_alerts"] == 0 and arm["covered"] == arm["verdicts"] for arm in arms.values())
        and all(gain["rate_gain"] >= 0.2 and gain["ci95"][0] > 0 for gain in gains.values())
    )
    result = {
        "seed": seed, "profiles": len(profiles), "chain_id": w3.eth.chain_id, "network": w3.client_version,
        "registry": registry.address, "baselines": arms, "paired_gains": gains,
        "paired_ci_method": "Bonferroni exact binomial bounds for discordant pairs",
        "gas": latency([row["gas"] for row in registrations]),
        "submit_to_receipt_ms": latency([row["submit_to_receipt_ms"] for row in registrations]),
        "passes": passed,
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Seed {seed}: B0/B1/B2 detected {[arms[arm]['detected'] for arm in BASELINES]} of {len(profiles)}, pass={passed}", flush=True)
    if not passed:
        raise RuntimeError(f"Seed {seed} did not pass the paired experiment")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    prepare_mode = modes.add_parser("prepare")
    prepare_mode.add_argument("--bundle", type=Path, default=ROOT / "artifacts/SuperBells_HELOC_XAI")
    prepare_mode.add_argument("--output", type=Path, required=True)
    run_mode = modes.add_parser("run")
    run_mode.add_argument("--input", type=Path, required=True)
    run_mode.add_argument("--output", type=Path, required=True)
    run_mode.add_argument("--rpc", required=True)
    run_mode.add_argument("--seeds", nargs="+", type=int, choices=SEEDS, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.bundle, args.output)
    else:
        payload = json.loads(args.input.read_bytes())
        if payload["model_artifact_sha256"] != MODEL_SHA or len(payload["features"]) != 43:
            parser.error("Use the frozen 43-feature HELOC model.")
        if len(set(args.seeds)) != len(args.seeds):
            parser.error("Each seed must be listed once.")
        for seed in args.seeds:
            run_seed(payload, seed, args.output / str(seed), args.rpc)


if __name__ == "__main__":
    main()
