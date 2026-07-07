"""Build the Dr. Mundo SQLite database from the source CSVs.

This is a one-time build step. It creates `dr_mundo.db` at the repo root with four
tables and prints the real schema + sample rows so we can confirm everything loaded.

Design notes:
- Prices in the CSVs use thousands separators (e.g. "120,000"). We strip the commas
  and store them as INTEGER so the runtime queries can do arithmetic directly.
- `case_rate` is already a clean decimal, stored as REAL.
- `rvs_code` is the PRIMARY KEY of philhealth_procedure_rates (it is now unique after
  removing the one duplicate, 77401 COBALT).
- Foreign keys tie the two price tables back to hospitals / procedure rates.

Loading uses the stdlib `csv` + `sqlite3` modules only (no ORM). The runtime query
layer in db/ is likewise raw, parameterized sqlite3 -- the LLM never writes SQL.

Usage:
    python data/load_db.py
"""

import csv
import sqlite3
import sys
from pathlib import Path

# The repo path can contain non-Latin characters (e.g. Japanese "ドキュメント"), which
# breaks the default Windows console codec when we print it. Force UTF-8 output.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "dr_mundo.db"

# Explicit, typed schema. Declared here (not inferred) so the constraints are visible
# and teammates can explain them.
SCHEMA = """
CREATE TABLE hospitals (
    id       INTEGER PRIMARY KEY,
    hospital TEXT NOT NULL,
    city     TEXT
);

CREATE TABLE philhealth_procedure_rates (
    rvs_code  TEXT PRIMARY KEY,
    procedure TEXT NOT NULL,
    case_rate REAL NOT NULL
);

CREATE TABLE hospital_procedure_prices (
    rvs_code    TEXT    NOT NULL,
    hospital_id INTEGER NOT NULL,
    price_low   INTEGER NOT NULL,
    price_high  INTEGER NOT NULL,
    as_of       TEXT,
    FOREIGN KEY (rvs_code)    REFERENCES philhealth_procedure_rates(rvs_code),
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
);

CREATE TABLE hospital_prices (
    id          INTEGER PRIMARY KEY,
    hospital_id INTEGER NOT NULL,
    category    TEXT    NOT NULL,
    service     TEXT    NOT NULL,
    price_low   INTEGER NOT NULL,
    price_high  INTEGER NOT NULL,
    as_of       TEXT,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
);

-- rvs_code is looked up constantly on Path A; index the join column.
CREATE INDEX idx_hpp_rvs_code    ON hospital_procedure_prices(rvs_code);
CREATE INDEX idx_hpp_hospital_id ON hospital_procedure_prices(hospital_id);
CREATE INDEX idx_hp_hospital_id  ON hospital_prices(hospital_id);
CREATE INDEX idx_hp_service      ON hospital_prices(service);
"""


def to_int(value: str) -> int:
    """'120,000' -> 120000."""
    return int(value.replace(",", "").strip())


def to_float(value: str) -> float:
    """'7098.00' -> 7098.0."""
    return float(value.replace(",", "").strip())


def read_csv(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()  # rebuild from scratch every run

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA)

    # hospitals
    hospitals = read_csv("hospitals.csv")
    conn.executemany(
        "INSERT INTO hospitals (id, hospital, city) VALUES (?, ?, ?)",
        [(int(r["id"]), r["hospital"], r["city"]) for r in hospitals],
    )

    # philhealth_procedure_rates
    rates = read_csv("procedure_case_rates.csv")
    conn.executemany(
        "INSERT INTO philhealth_procedure_rates (rvs_code, procedure, case_rate) VALUES (?, ?, ?)",
        [(r["rvs_code"], r["procedure"], to_float(r["case_rate"])) for r in rates],
    )

    # hospital_procedure_prices (Path A)
    hpp = read_csv("hospital_procedure_prices.csv")
    conn.executemany(
        "INSERT INTO hospital_procedure_prices (rvs_code, hospital_id, price_low, price_high, as_of) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (r["rvs_code"], int(r["hospital_id"]), to_int(r["price_low"]), to_int(r["price_high"]), r["as_of"])
            for r in hpp
        ],
    )

    # hospital_prices (Path B)
    hp = read_csv("hospital_prices.csv")
    conn.executemany(
        "INSERT INTO hospital_prices (id, hospital_id, category, service, price_low, price_high, as_of) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                int(r["id"]),
                int(r["hospital_id"]),
                r["category"],
                r["service"],
                to_int(r["price_low"]),
                to_int(r["price_high"]),
                r["as_of"],
            )
            for r in hp
        ],
    )

    conn.commit()
    print_report(conn)
    conn.close()
    print(f"\nBuilt database at: {DB_PATH}")


def print_report(conn: sqlite3.Connection) -> None:
    """Print the real schema + counts + sample rows to confirm the load."""
    tables = [
        "hospitals",
        "philhealth_procedure_rates",
        "hospital_procedure_prices",
        "hospital_prices",
    ]
    for table in tables:
        print("=" * 78)
        # actual column definitions as SQLite sees them
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        col_desc = ", ".join(f"{c[1]} {c[2]}" for c in cols)
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}  ({count} rows)")
        print(f"  columns: {col_desc}")
        print("  sample:")
        for row in conn.execute(f"SELECT * FROM {table} LIMIT 3"):
            print(f"    {row}")
        print()


if __name__ == "__main__":
    build()
