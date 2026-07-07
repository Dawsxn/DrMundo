"""Shared test fixtures. Ensures the SQLite DB exists before the DB tests run."""

import subprocess
import sys

import pytest

from config import DB_PATH, ROOT


@pytest.fixture(scope="session", autouse=True)
def ensure_database():
    if not DB_PATH.exists():
        subprocess.run([sys.executable, "-m", "data.load_db"], cwd=ROOT, check=True)
    return DB_PATH
