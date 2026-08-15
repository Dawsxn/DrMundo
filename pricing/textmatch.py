"""Matching a medical name written one way against the same name written another way.

Two places need this and they must agree. `pricing/catalog.py` matches a taxonomy code's
name against MMC's service list; `pricing/waterfall.py` matches an HMO schedule's
procedure name against a priced item. Both are joining vocabularies that nobody
publishes a crosswalk between, and both are one careless substring away from a wrong
peso figure in front of a patient.

The rule that earns this its own module: A KEY MUST BEGIN AT A WORD BOUNDARY.

Raw substring matching on normalised text is how CREATININE, whose surface form is "Crea",
matched PANCREAS -- "crea" sits inside "pan-crea-s". The shortest-name rule then preferred
the 8-character PANCREAS over CREATININE SERUM, and a P740 blood test was priced as a
P16,800 study. The taxonomy says `substring_matching: false` for exactly this reason.

No database, no I/O, no imports from the rest of the package. That is what lets the
waterfall use it without giving up being pure.
"""

import re


def norm(s: str) -> str:
    """Fold to bare alphanumerics, so punctuation and spacing stop mattering."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def aligns(key: str, text: str) -> bool:
    """Does `key` (already normalised) match `text` starting at a word boundary?

    Tokens are joined after the boundary check, because the sources punctuate
    inconsistently and "Chest PA/L" still has to reach "CHEST PA & LATERAL".
    """
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return any("".join(tokens[i:]).startswith(key) for i in range(len(tokens)))
