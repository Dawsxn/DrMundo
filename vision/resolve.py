"""Resolve a label read off a slip to a taxonomy test code.

The reader (vision LLM or OCR) gives us text. This turns text into a `test_code`, which is
the contract everything downstream keys on. Pricing is a separate step again -- codes carry
no money.

The rules are not ours; they come from `taxonomy/taxonomy.yaml`'s `matching` block, and
each one exists because ignoring it produces a confident wrong answer:

  substring_matching: false   "PT" inside "PTT" is a different test.
  fuzzy: edit distance <= 1   handles OCR noise ("Creatlnine").
  excluded_families           but NEVER across LDL/LDH, SGOT/SGPT, BUN/URIC_ACID,
                              T3/T4/FT3/FT4 -- all one edit apart and all different
                              tests. Fuzzy matching here is how you tell a patient they
                              need a liver enzyme when the doctor ordered a cardiac one.
  blocked_global_aliases      "PT" is prothrombin time OR pregnancy test; "KUB" is an
                              ultrasound OR an x-ray; "CT" is clotting time OR a CT scan.
                              These resolve ONLY with a section heading. Without one the
                              answer is "ask", not a guess.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel

from vision.schemas import ItemKind

# The dataset directory is a drop-in from the generator; keep the glob rather than a fixed
# name so a re-export with a new timestamp does not break every import.
_ROOT = Path(__file__).resolve().parent.parent


def _taxonomy_path() -> Path:
    """Find taxonomy.yaml under either dataset layout.

    `labrequests/` is the committed location; `labrequests-<stamp>/labrequests/` is the
    raw export. Preferring the committed one stops a stale export shadowing it.
    """
    candidates = [_ROOT / "labrequests" / "taxonomy" / "taxonomy.yaml"]
    candidates += sorted(_ROOT.glob("labrequests-*/labrequests/taxonomy/taxonomy.yaml"))
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(
        "taxonomy.yaml not found under labrequests/ or labrequests-<stamp>/labrequests/"
    )


# taxonomy modality -> our ItemKind. Nothing here is ever a `procedure`: this dataset is
# outpatient work-up, so no item resolved through it can attract a PhilHealth case rate.
_MODALITY_TO_KIND: dict[str, ItemKind] = {
    "lab": "lab",
    "ultrasound": "imaging",
    "xray": "imaging",
    "ct": "imaging",
    "nuclear": "imaging",
    "cardiac_dx": "diagnostic",
}

ResolutionMethod = Literal["exact", "alias", "scoped", "fuzzy", "ambiguous", "unresolved"]


class Resolution(BaseModel):
    """What a label resolved to, and how -- `how` matters as much as `what`."""

    test_code: Optional[str] = None
    canonical_name: Optional[str] = None
    kind: ItemKind = "unknown"
    method: ResolutionMethod = "unresolved"
    candidates: list[str] = []

    @property
    def needs_confirmation(self) -> bool:
        """Ambiguous labels must be asked about, never priced on a guess."""
        return self.method == "ambiguous"

    @property
    def resolved(self) -> bool:
        return self.test_code is not None


def _norm(s: str) -> str:
    """taxonomy `matching.normalize`: casefold_strip_punct."""
    return re.sub(r"[^a-z0-9]", "", (s or "").casefold())


def _edit_distance_le_1(a: str, b: str) -> bool:
    """True when a and b differ by at most one insert, delete or substitution."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(x != y for x, y in zip(a, b)) == 1
    shorter, longer = (a, b) if la < lb else (b, a)
    i = j = 0
    skipped = False
    while i < len(shorter) and j < len(longer):
        if shorter[i] != longer[j]:
            if skipped:
                return False
            skipped = True
            j += 1
            continue
        i += 1
        j += 1
    return True


@lru_cache(maxsize=1)
def _taxonomy() -> dict:
    return yaml.safe_load(_taxonomy_path().read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _index() -> dict:
    """Build the lookup tables once."""
    tax = _taxonomy()
    tests = tax["tests"]

    by_code = {t["code"]: t for t in tests}

    # normalised label -> set of codes it could mean (globally valid labels only)
    label_to_codes: dict[str, set[str]] = {}
    # (normalised label, normalised section) -> set of codes. The taxonomy states section
    # scope explicitly for exactly the labels that are ambiguous without one.
    scoped_to_codes: dict[tuple[str, str], set[str]] = {}

    for t in tests:
        for lab in [t["canonical_name"], *t.get("surface_forms", [])]:
            label_to_codes.setdefault(_norm(lab), set()).add(t["code"])
        aliases = t.get("aliases", {}) or {}
        for lab in aliases.get("global", []) or []:
            label_to_codes.setdefault(_norm(lab), set()).add(t["code"])
        for entry in aliases.get("scoped", []) or []:
            for sec in entry.get("sections", []) or []:
                scoped_to_codes.setdefault((_norm(entry["text"]), _norm(sec)), set()).add(t["code"])

    # Section display names as printed on a form ("Cardiac Markers:") -> section id
    # ("cardiac"). A reader sees the heading, not the id.
    section_alias: dict[str, str] = {}
    for sec in tax.get("sections", []) or []:
        section_alias[_norm(sec["id"])] = sec["id"]
        for disp in sec.get("display_names", []) or []:
            section_alias[_norm(disp)] = sec["id"]

    # Labels the taxonomy explicitly refuses to resolve without a section.
    blocked = {
        _norm(k): list(v) for k, v in (tax.get("blocked_global_aliases") or {}).items()
    }

    # Codes that must never fuzzy-match each other.
    families: list[set[str]] = [
        set(fam) for fam in (tax.get("matching", {}).get("fuzzy", {}).get("excluded_families") or [])
    ]

    return {
        "by_code": by_code,
        "label_to_codes": label_to_codes,
        "scoped_to_codes": scoped_to_codes,
        "section_alias": section_alias,
        "blocked": blocked,
        "families": families,
    }


def _same_excluded_family(a: str, b: str) -> bool:
    return any(a in fam and b in fam for fam in _index()["families"])


def _kind(code: str) -> ItemKind:
    entry = _index()["by_code"].get(code)
    if entry is None:
        return "unknown"
    return _MODALITY_TO_KIND.get(entry.get("modality", ""), "unknown")


def _build(code: str, method: ResolutionMethod) -> Resolution:
    entry = _index()["by_code"][code]
    return Resolution(
        test_code=code,
        canonical_name=entry["canonical_name"],
        kind=_kind(code),
        method=method,
    )


def section_id(heading: Optional[str]) -> Optional[str]:
    """Map a section heading as printed on a form to the taxonomy's section id.

    Forms print "Cardiac Markers:" or "Clinical Microscopy"; the taxonomy keys on
    `cardiac` and `hematology`. Returns None for a heading it does not recognise, which
    leaves the label unscoped rather than mis-scoped.
    """
    if not heading:
        return None
    return _index()["section_alias"].get(_norm(heading))


def _scoped_pick(codes: list[str], section: Optional[str], label: str = "") -> Optional[str]:
    """Narrow candidate codes using the section heading the label appeared under.

    Prefers the taxonomy's explicit scoped-alias table, which was written for precisely
    these cases, and falls back to the code's own declared section.
    """
    if not section:
        return None
    idx = _index()
    want = _norm(section_id(section) or section)

    explicit = idx["scoped_to_codes"].get((_norm(label), want), set()) & set(codes)
    if len(explicit) == 1:
        return next(iter(explicit))

    hits = []
    for c in codes:
        entry = idx["by_code"].get(c)
        if entry is None:
            continue
        declared = {_norm(entry.get("default_section", "")), _norm(entry.get("category", ""))}
        if want in declared:
            hits.append(c)
    return hits[0] if len(hits) == 1 else None


def resolve(label: str, section: Optional[str] = None) -> Resolution:
    """Resolve one printed label, optionally scoped by its section heading."""
    idx = _index()
    key = _norm(label)
    if not key:
        return Resolution(method="unresolved")

    # 1. Explicitly ambiguous abbreviations. A section can rescue them; nothing else may.
    if key in idx["blocked"]:
        codes = idx["blocked"][key]
        picked = _scoped_pick(codes, section, label)
        if picked:
            return _build(picked, "scoped")
        return Resolution(method="ambiguous", candidates=sorted(codes))

    # 2. Exact match on a canonical name, surface form or alias.
    codes = sorted(idx["label_to_codes"].get(key, ()))
    if len(codes) == 1:
        return _build(codes[0], "exact")
    if len(codes) > 1:
        picked = _scoped_pick(codes, section, label)
        if picked:
            return _build(picked, "scoped")
        return Resolution(method="ambiguous", candidates=codes)

    # 3. Fuzzy, for reader noise. Never across an excluded family.
    near = {
        c
        for lab, cs in idx["label_to_codes"].items()
        if _edit_distance_le_1(key, lab)
        for c in cs
    }
    if len(near) == 1:
        return _build(next(iter(near)), "fuzzy")
    if len(near) > 1:
        pairs = sorted(near)
        if any(
            _same_excluded_family(a, b)
            for i, a in enumerate(pairs)
            for b in pairs[i + 1:]
        ):
            # LDL vs LDH and friends: one edit apart, entirely different tests. Refusing
            # is the only safe answer.
            return Resolution(method="ambiguous", candidates=pairs)
        picked = _scoped_pick(pairs, section, label)
        if picked:
            return _build(picked, "scoped")
        return Resolution(method="ambiguous", candidates=pairs)

    return Resolution(method="unresolved")
