"""SQLite connection helper shared by every query function.

Connections are read-only at the app level (we only ever SELECT at runtime; the DB is
built once by data/load_db.py). Rows come back as sqlite3.Row so query functions can
return plain dicts keyed by column name.
"""

import sqlite3

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Database not found at {DB_PATH}. Build it first: python -m data.load_db"
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]
