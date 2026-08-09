"""Curated alias + equivalence maps that complement the embedding matcher.

Two separate jobs:

1. ALIASES (covered + outpatient): map common lay / Taglish phrases to the *canonical*
   catalog entry a person means. Pure embeddings mis-rank the common priced procedures
   (e.g. "normal delivery" -> C-section), so a small hand-curated boost pins the right
   one. This only affects which NAME we match -- never the numbers.

2. SERVICE_EQUIVALENTS: for outpatient Path B, group service strings that are the same
   service under different hospital naming (e.g. Cardinal Santos' "CT Scan (plain, single
   region)" == others' "CT Scan (plain)") so an across-hospitals comparison covers every
   hospital. Real price-relevant distinctions (plain vs contrast, Basic vs Comprehensive,
   OPD tiers) are deliberately NOT merged.
"""

import re

# --- 1a. Covered-procedure aliases (keyed by rvs_code) ----------------------------
# Keyed to the RVS codes that actually have a Makati Medical Center package price. Aliases
# matter MORE than in v1: MMC's own item names are long and clinical ("LAPAROSCOPY,
# SURGICAL; CHOLECYSTECTOMY (ANY METHOD)"), and nobody types that.
#
# Note appendectomy is deliberately absent: MMC publishes no operating-room package for it,
# only professional fees, so there is no covered-procedure row to point an alias at.
COVERED_ALIASES: dict[str, list[str]] = {
    "47562": ["cholecystectomy", "gallbladder removal", "remove gallbladder", "gall bladder",
              "gallstone surgery", "gallstones surgery", "lap chole", "apdo", "tanggal apdo",
              "opera sa apdo"],
    "59409": ["vaginal delivery", "normal delivery", "nsd", "normal spontaneous delivery",
              "spontaneous vaginal delivery", "normal birth", "normal childbirth", "childbirth",
              "give birth", "deliver a baby", "manganak", "panganganak"],
    "59514": ["cesarean", "cesarian", "caesarean", "c-section", "c section", "cs",
              "cesarean section", "cesarean delivery", "cs delivery", "operahan manganak"],
    "58150": ["hysterectomy", "total abdominal hysterectomy", "tah", "tahbso", "remove uterus",
              "uterus removal", "matris", "tanggal matris"],
    "58260": ["vaginal hysterectomy"],
    "58545": ["myomectomy", "fibroid removal", "remove myoma", "myoma surgery", "tanggal myoma"],
    "60240": ["thyroidectomy", "thyroid removal", "remove thyroid", "goiter surgery",
              "goiter removal", "tanggal thyroid"],
    "19240": ["mastectomy", "modified radical mastectomy", "breast removal", "remove breast",
              "tanggal suso"],
    "27447": ["knee replacement", "total knee replacement", "tkr", "knee arthroplasty",
              "knee prosthesis"],
    "29881": ["meniscectomy", "arthroscopic meniscectomy", "knee arthroscopy", "meniscus surgery"],
    "29888": ["acl repair", "acl reconstruction", "anterior cruciate ligament"],
    "49505": ["hernia repair", "inguinal hernia", "herniorrhaphy", "hernioplasty", "luslos",
              "opera sa luslos"],
    "46255": ["hemorrhoidectomy", "hemorrhoid surgery", "piles surgery", "almoranas",
              "opera sa almoranas"],
    "42825": ["tonsillectomy", "tonsil removal", "remove tonsils", "tanggal tonsil"],
    "54152": ["circumcision", "tuli", "pagtutuli"],
    "52000": ["cystoscopy", "cystourethroscopy", "bladder scope"],
    "31622": ["bronchoscopy", "lung scope"],
    "55866": ["prostatectomy", "prostate removal", "radical prostatectomy"],
    "55700": ["prostate biopsy"],
    "55530": ["varicocelectomy", "varicocele surgery"],
    "58120": ["dilatation and curettage", "d&c", "dnc", "raspa"],
    "58555": ["hysteroscopy", "diagnostic hysteroscopy"],
    "58300": ["iud insertion", "iud", "intrauterine device"],
    "57452": ["colposcopy"],
    "57460": ["leep", "loop electrode excision"],
    "50590": ["eswl", "lithotripsy", "shock wave lithotripsy", "kidney stone blasting"],
    "31255": ["fess", "sinus surgery", "endoscopic sinus surgery"],
    "69631": ["tympanoplasty", "eardrum repair"],
    "69641": ["tympanomastoidectomy", "mastoidectomy"],
    "47120": ["hepatectomy", "liver resection"],
    "49000": ["exploratory laparotomy", "ex lap"],
    "63030": ["discectomy", "microdiscectomy", "herniated disc surgery"],
    "22630": ["spinal fusion", "lumbar fusion", "tlif"],
    "33533": ["bypass surgery", "cabg", "coronary artery bypass", "heart bypass"],
    "36821": ["av fistula", "dialysis access", "fistula creation"],
}

# --- 1b. Outpatient-service aliases (keyed by CANONICAL service string) ------------
# The canonical string must be a real `hospital_prices.service` value. These are the terms a
# patient or a doctor's request slip actually uses, mapped onto MMC's catalogue names.
OUTPATIENT_ALIASES: dict[str, list[str]] = {
    "CBC (COMPLETE BLOOD COUNT)": ["cbc", "complete blood count"],
    "URINALYSIS ROUTINE": ["urinalysis", "urine test", "urine exam", "ihi test"],
    "STOOL ROUTINE": ["stool test", "stool exam", "fecalysis", "dumi test"],
    "CREATININE SERUM": ["creatinine", "creatinine test", "kidney function test"],
    "HbA1C": ["hba1c", "a1c", "glycosylated hemoglobin"],
    "TSH CHEMI": ["tsh", "thyroid function test", "thyroid test"],
    "LIPID PROFILE (HDL LDL CHOL TRIG) SERUM": ["lipid profile", "cholesterol test",
                                                "lipid panel", "cholesterol panel"],
    "CHOLESTEROL TOTAL SERUM": ["total cholesterol"],
    "TRIGLYCERIDES SERUM": ["triglycerides", "trigs"],
    "CHEST PA": ["chest xray", "chest x-ray", "chest x ray", "cxr", "xray ng baga",
                 "xray sa dibdib", "chest radiograph"],
    "WHOLE ABDOMEN": ["ultrasound ng tiyan", "ultrasound tiyan", "whole abdomen ultrasound",
                      "abdominal ultrasound", "abdomen ultrasound"],
    "ECG": ["ecg", "ekg", "electrocardiogram"],
    "2D ECHOCARDIOGRAM": ["2d echo", "2decho", "echocardiogram", "heart ultrasound"],
}

# --- 2. Outpatient service equivalence groups (canonical -> member strings) --------
# Members are exact `hospital_prices.service` strings. With a single hospital there are no
# cross-hospital naming variants left to reconcile, so this now does a different job: it
# groups MMC's own near-identical listings (a study and its "& LATERAL" / "W/ OPTIMIZATION"
# sibling) so a price question spans the whole family instead of one arbitrary variant.
# Genuinely price-relevant distinctions (plain vs contrast, panel vs single test) stay apart.
SERVICE_EQUIVALENTS: dict[str, list[str]] = {
    "CHEST PA": ["CHEST PA", "CHEST PA & LATERAL"],
    "2D ECHOCARDIOGRAM": ["2D ECHOCARDIOGRAM", "2D ECHOCARDIOGRAM W/ OPTIMIZATION"],
    "WHOLE ABDOMEN": ["WHOLE ABDOMEN", "WHOLE ABDOMEN WITH UGAP PACKAGE"],
}

# Reverse lookup: any member string -> canonical string. Members not in any group map
# to themselves (built lazily on first use).
_MEMBER_TO_CANONICAL: dict[str, str] = {}
for _canon, _members in SERVICE_EQUIVALENTS.items():
    for _m in _members:
        _MEMBER_TO_CANONICAL[_m] = _canon


def canonical_service(service: str) -> str:
    """Return the group leader for a service string (itself if ungrouped)."""
    return _MEMBER_TO_CANONICAL.get(service, service)


def equivalent_services(service: str) -> list[str]:
    """All service strings equivalent to `service` (including itself)."""
    canon = canonical_service(service)
    return SERVICE_EQUIVALENTS.get(canon, [service])


def _alias_lookup(aliases: dict[str, list[str]], kind: str) -> list[tuple[re.Pattern, str, str]]:
    """Compile (word-boundary pattern, kind, key) triples for phrase matching."""
    out = []
    for key, phrases in aliases.items():
        for phrase in phrases:
            pat = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
            out.append((pat, kind, key))
    return out


# Precompiled patterns, longest phrase first so specific aliases win over generic ones
# (e.g. "cesarean delivery" before "delivery"-like generics).
_ALIAS_PATTERNS = sorted(
    _alias_lookup(COVERED_ALIASES, "covered") + _alias_lookup(OUTPATIENT_ALIASES, "outpatient"),
    key=lambda t: -len(t[0].pattern),
)


def match_aliases(query_text: str) -> list[tuple[str, str]]:
    """Return [(kind, key), ...] for every alias phrase found in query_text, most
    specific (longest) first, de-duplicated."""
    hits: list[tuple[str, str]] = []
    seen = set()
    for pat, kind, key in _ALIAS_PATTERNS:
        if pat.search(query_text) and (kind, key) not in seen:
            hits.append((kind, key))
            seen.add((kind, key))
    return hits
