"""UCI Taiwan data loading and leakage-safe split manifest."""
from hashlib import sha256
from pathlib import Path
import json

import pandas as pd
from sklearn.model_selection import train_test_split

FEATURES = (
    "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
    "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
    "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6",
)
TARGET = "default payment next month"


def load_taiwan(path: Path) -> pd.DataFrame:
    frame = pd.read_excel(path, sheet_name="Data", header=1)
    expected = {"ID", TARGET, *FEATURES}
    if set(frame.columns) != expected or len(frame) != 30000:
        raise ValueError(f"Unexpected UCI schema/row count: {list(frame.columns)}, {len(frame)}")
    if frame.ID.isna().any() or frame.ID.duplicated().any():
        raise ValueError("Missing or duplicate source IDs")
    if not set(frame[TARGET].unique()) <= {0, 1}:
        raise ValueError("Target must be binary")
    return frame


def split_taiwan(frame: pd.DataFrame, source_path: Path, out: Path, seed: int = 42):
    train_val, test = train_test_split(frame, test_size=0.15, stratify=frame[TARGET], random_state=seed)
    train, val = train_test_split(train_val, test_size=15 / 85, stratify=train_val[TARGET], random_state=seed)
    ids = {name: sorted(int(x) for x in part.ID) for name, part in (("train", train), ("validation", val), ("test", test))}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"dataset_id": "taiwan_uci350", "source_sha256": sha256(source_path.read_bytes()).hexdigest(), "seed": seed, "ids": ids}, separators=(",", ":")), encoding="utf-8")
    return train, val, test

