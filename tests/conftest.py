"""Shared test fixtures and collection guards.

Ensures the SQLite DB exists before the DB tests run, and marks the tests that need
dataset images so they skip instead of failing in a media-free clone.

The evaluation dataset ships in two halves. The LABELS (groundtruth, taxonomy, answer
key) are about 1.3MB and are what most of the suite needs. The MEDIA is 381MB of PNGs and
is only needed to benchmark a reader against real images.

A clone that skips the media is a legitimate and encouraged setup, so tests that open an
image skip with a clear reason rather than failing. `pytest -q` should be green either way,
and a wall of red would otherwise be the first thing a new contributor sees.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from config import DB_PATH, ROOT

_ROOT = Path(__file__).resolve().parent.parent


def _dataset_dir() -> Path | None:
    for candidate in [_ROOT / "labrequests", *sorted(_ROOT.glob("labrequests-*/labrequests"))]:
        if (candidate / "groundtruth").is_dir():
            return candidate
    return None


DATASET = _dataset_dir()
HAS_LABELS = DATASET is not None
HAS_MEDIA = bool(DATASET and (DATASET / "media").is_dir()
                 and any((DATASET / "media").glob("*.png")))

needs_media = pytest.mark.skipif(
    not HAS_MEDIA,
    reason=(
        "dataset images not present. This is expected in a media-free clone; the labels "
        "are enough for everything except reader benchmarking. See README."
    ),
)

needs_labels = pytest.mark.skipif(
    not HAS_LABELS,
    reason="labrequests labels not found (expected at labrequests/groundtruth).",
)


@pytest.fixture(scope="session", autouse=True)
def ensure_database():
    """Build dr_mundo.db on demand. It is a gitignored build artifact."""
    if not DB_PATH.exists():
        subprocess.run([sys.executable, "-m", "data.load_db"], cwd=ROOT, check=True)
    return DB_PATH
