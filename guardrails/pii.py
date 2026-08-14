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


# Labels the RASTER redactor (vision/redact.py) may report. These live in pixels, not
# text, so nothing above will ever find them -- a patient's name printed on a request
# slip is invisible to a regex. Kept here so both mechanisms share one vocabulary and
# every redaction shows up in the same pii_found list.
RASTER_PII_LABELS = frozenset(
    {"PATIENT_NAME", "PATIENT_ADDRESS", "POLICY_NUMBER", "PHILHEALTH_ID", "SIGNATURE", "BARCODE"}
)


def merge_raster_findings(text_findings: list[str], raster_findings: list[str]) -> list[str]:
    """Combine text-regex and raster-redaction findings into one sorted list."""
    return sorted(set(text_findings) | set(raster_findings))
