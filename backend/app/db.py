"""SQLite access layer.

Thin helpers over the stdlib sqlite3 module. Table and column names are
interpolated only from ALLOWED_TABLES / model code, never from user input;
all values go through ? placeholders.
"""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "ci.db"

ALLOWED_TABLES = {
    "products",
    "runs",
    "competitors",
    "sources",
    "findings",
    "claims",
    "eval_results",
}


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # SQLite does not enforce foreign keys unless asked, per-connection.
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL lets the API serve reads while a pipeline thread is writing.
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def insert_row(conn: sqlite3.Connection, table: str, fields: dict) -> int:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"unknown table: {table}")
    cols = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    cur = conn.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
        tuple(fields.values()),
    )
    conn.commit()
    return cur.lastrowid


def fetch_row(conn: sqlite3.Connection, table: str, row_id: int) -> sqlite3.Row | None:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"unknown table: {table}")
    return conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
