"""Central configuration for Dr. Mundo.

Loads environment variables from `.env` and exposes shared settings + an OpenAI
client factory. Every module (data build, db search, agent, api) imports from here so
there is one place that knows about paths, model names, and the API key.
"""

import os
import sys
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# The repo path can contain non-Latin characters (e.g. Japanese "ドキュメント"), which
# breaks the default Windows console codec on print. Force UTF-8 stdout everywhere.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "dr_mundo.db"
DATA_DIR = ROOT / "data"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npz"

load_dotenv(ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


@lru_cache(maxsize=1)
def get_openai_client():
    """Return a cached OpenAI client. Imported lazily so modules that don't touch the
    API (e.g. the pure-SQL queries) don't require the SDK or a key to import.

    The client is wrapped so token usage is recorded inside a `monitoring.track_usage()`
    block (Phase 9a). The wrapper is transparent -- it never alters responses -- so this
    does not change any answer."""
    from openai import OpenAI

    from monitoring.usage import wrap_client

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return wrap_client(OpenAI(api_key=OPENAI_API_KEY))
