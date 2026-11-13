"""SQLite persistence of the exact canonical bytes and audit status."""
import json
import sqlite3
from pathlib import Path

from credit_audit.records import canonical_serialize

DDL = """
CREATE TABLE IF NOT EXISTS decisions (
  decision_id TEXT PRIMARY KEY,
  display_json TEXT NOT NULL,
  canonical_bytes BLOB NOT NULL,
  tx_hash TEXT,
  chain_id INTEGER,
  block_number INTEGER,
  status TEXT NOT NULL DEFAULT 'PENDING',
  error_reason TEXT
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute(DDL)
    db.commit()
    return db


def save(db: sqlite3.Connection, record: dict, canonical_bytes: bytes) -> None:
    if canonical_serialize(record) != canonical_bytes:
        raise ValueError("Canonical bytes disagree with JSON")
    db.execute(
        "INSERT INTO decisions (decision_id, display_json, canonical_bytes) VALUES (?, ?, ?)",
        (record["decision_id"], json.dumps(record, ensure_ascii=False), canonical_bytes),
    )
    db.commit()


def get(db: sqlite3.Connection, decision_id: str):
    row = db.execute("SELECT display_json, canonical_bytes, tx_hash, chain_id, block_number, status FROM decisions WHERE decision_id=?", (decision_id,)).fetchone()
    if row is None:
        return None
    return {"record": json.loads(row[0]), "canonical_bytes": row[1], "tx_hash": row[2], "chain_id": row[3], "block_number": row[4], "status": row[5]}

