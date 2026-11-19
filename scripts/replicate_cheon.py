"""Run the ICLR 2025 authors' experiment scripts from a pinned local checkout.

The paper branch keeps experiment data/path helpers in research/iclr2025/src,
while the importable package resolves them from the repository root. This
launcher maps those helpers without editing the authors' tracked files.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import runpy
import subprocess
import sys


EXPECTED_COMMIT = "4c68c73b34eef7c5e38847274048cb3ab66d702c"


def load_module(name: str, path: Path) -> None:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("setup", "train"))
    parser.add_argument("--dataset", choices=("german", "fico", "givemecredit"), required=True)
    parser.add_argument("--model", choices=("logreg", "xgb", "rf"))
    parser.add_argument("--author-repo", type=Path, default=Path("artifacts/cheon_iclr2025"))
    args = parser.parse_args()
    if args.stage == "train" and args.model is None:
        parser.error("--model is required for the train stage")

    repo = args.author_repo.resolve()
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if commit != EXPECTED_COMMIT:
        raise RuntimeError(f"Author checkout {commit} differs from pinned {EXPECTED_COMMIT}")

    paper = repo / "research" / "iclr2025"
    sys.path.insert(0, str(repo))
    load_module("responsiveness.paths", paper / "src" / "paths.py")
    import responsiveness  # noqa: F401, must load package before its ext.utils module

    load_module("responsiveness.ext.utils", paper / "src" / "utils.py")
    os.chdir(paper)

    if args.stage == "setup":
        script = paper / "experiment" / f"setup_dataset_actionset_{args.dataset}.py"
        sys.argv = [str(script)]
    else:
        script = paper / "experiment" / "train_models.py"
        sys.argv = [
            str(script),
            "--data_name", args.dataset,
            "--action_set_name", "complex_nD",
            "--model_type", args.model,
        ]
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
