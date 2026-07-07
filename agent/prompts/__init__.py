"""Versioned system-prompt files. `load_prompt("system_v1")` reads the .md by name."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt '{name}' not found at {path}")
    return path.read_text(encoding="utf-8")
