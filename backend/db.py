from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "history.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  text TEXT NOT NULL,
  label TEXT NOT NULL CHECK(label IN ('CG', 'OR')),
  probability REAL NOT NULL CHECK(probability >= 0 AND probability <= 1),
  confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
  source TEXT,
  model_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_label ON analyses(label);
"""

@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def initialize() -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)

def insert_analysis(text: str, label: str, probability: float, confidence: float, source: str | None, model_version: str) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        cursor = conn.execute(
            "INSERT INTO analyses(text,label,probability,confidence,source,model_version,created_at) VALUES (?,?,?,?,?,?,?)",
            (text, label, probability, confidence, source, model_version, created_at),
        )
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

def insert_many(analyses: list[tuple]) -> list[dict]:
    """Store an entire batch in one transaction, or none on failure."""
    rows = []
    with connection() as conn:
        for text, label, probability, confidence, source, model_version in analyses:
            created_at = datetime.now(timezone.utc).isoformat()
            cursor = conn.execute(
                "INSERT INTO analyses(text,label,probability,confidence,source,model_version,created_at) VALUES (?,?,?,?,?,?,?)",
                (text, label, probability, confidence, source, model_version, created_at),
            )
            rows.append(dict(conn.execute("SELECT * FROM analyses WHERE id = ?", (cursor.lastrowid,)).fetchone()))
    return rows

def list_analyses(limit: int, offset: int, label: str | None = None) -> tuple[list[dict], int]:
    where = "WHERE label = ?" if label in {"CG", "OR"} else ""
    params = (label,) if where else ()
    with connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM analyses {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM analyses {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows], total

def analytics() -> dict:
    with connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        generated = conn.execute("SELECT COUNT(*) FROM analyses WHERE label='CG'").fetchone()[0]
        daily = conn.execute("SELECT substr(created_at,1,10) day, COUNT(*) count FROM analyses GROUP BY day ORDER BY day DESC LIMIT 14").fetchall()
        return {"total": total, "generated_count": generated, "original_count": total - generated, "daily": [dict(row) for row in daily]}
