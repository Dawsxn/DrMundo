"""Regex-based PII detection + redaction.

Runs before anything else so personal data the user pastes never reaches the LLM or the
logs. Patterns are deliberately specific (emails, phone numbers, 12-digit PhilHealth IDs,
long card-like numbers) so we do NOT redact legitimate figures like prices (e.g. 75,000)
or RVS codes (4-5 digits).
"""

import re

# (label, compiled pattern). Order matters: more specific first.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    # PH mobile / intl: +639171234567, 09171234567, 0917-123-4567
    ("PHONE", re.compile(r"(?:\+?63|0)9\d{2}[-\s]?\d{3}[-\s]?\d{4}\b")),
    # PhilHealth Identification Number: 12 digits, often 2-9-1 grouped.
    ("PHILHEALTH_ID", re.compile(r"\b\d{2}[-\s]?\d{9}[-\s]?\d\b")),
    # Card-like: 13-16 digits, optionally space/dash grouped in 4s.
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
]


def redact(text: str) -> tuple[str, list[str]]:
    """Return (redacted_text, sorted list of PII types found)."""
    found: set[str] = set()
    redacted = text
    for label, pattern in _PATTERNS:
        if pattern.search(redacted):
            found.add(label)
            redacted = pattern.sub(f"[{label}_REDACTED]", redacted)
    return redacted, sorted(found)
