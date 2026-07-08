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
# Only the 10 procedures that have hospital prices -- the ones people actually ask about.
COVERED_ALIASES: dict[str, list[str]] = {
    "44950": ["appendectomy", "appendix removal", "remove appendix", "appendix surgery",
              "appendicitis surgery", "appendix", "apendix", "tanggal apendix", "opera sa apendix"],
    "47600": ["cholecystectomy", "gallbladder removal", "remove gallbladder", "gall bladder",
              "gallstone surgery", "gallstones surgery", "apdo", "tanggal apdo", "opera sa apdo"],
    "59409": ["vaginal delivery", "normal delivery", "nsd", "normal spontaneous delivery",
              "spontaneous vaginal delivery", "normal birth", "normal childbirth", "childbirth",
              "give birth", "give birth normally", "deliver a baby", "manganak", "panganganak",
              "manghilot"],
    "59514": ["cesarean", "cesarian", "caesarean", "c-section", "c section", "cs",
              "cesarean section", "cesarean delivery", "cs delivery", "operahan manganak"],
    "58150": ["hysterectomy", "total abdominal hysterectomy", "tah", "remove uterus",
              "uterus removal", "matris", "tanggal matris"],
    "60240": ["thyroidectomy", "thyroid removal", "remove thyroid", "goiter surgery",
              "goiter removal", "tanggal thyroid"],
    "19180": ["mastectomy", "breast removal", "remove breast", "breast surgery", "tanggal suso"],
    "27447": ["knee replacement", "total knee replacement", "tkr", "knee arthroplasty",
              "knee prosthesis"],
    "27130": ["hip replacement", "total hip replacement", "thr", "hip arthroplasty",
              "hip prosthesis"],
    "38220": ["bone marrow biopsy", "bone marrow aspiration", "bone marrow", "bma"],
}

# --- 1b. Outpatient-service aliases (keyed by CANONICAL service string) ------------
# The canonical string must be a real service in the DB (it is also the group leader in
# SERVICE_EQUIVALENTS below). Abbreviations + Taglish that embeddings tend to miss.
OUTPATIENT_ALIASES: dict[str, list[str]] = {
    "CT Scan (plain)": ["ct scan", "ct", "cat scan", "plain ct"],
    "CT Scan (contrast)": ["ct with contrast", "contrast ct", "ct contrast"],
    "MRI (plain)": ["mri", "mri scan", "plain mri"],
    "MRI (contrast)": ["mri with contrast", "contrast mri"],
    "Chest X-ray": ["xray", "x-ray", "chest xray", "chest x ray", "cxr", "xray ng baga",
                    "xray sa dibdib"],
    "Ultrasound (abdomen)": ["ultrasound", "utz", "uts", "sonogram", "ultrasound ng tiyan",
                             "ultrasound tiyan"],
    "2D Echo": ["2d echo", "echo", "echocardiogram", "2decho"],
    "ECG (12-lead)": ["ecg", "ekg", "electrocardiogram"],
    "CBC": ["cbc", "complete blood count"],
    "Urinalysis / Fecalysis": ["urinalysis", "urine test", "fecalysis", "stool test"],
    "Mammogram": ["mammogram", "mammography", "breast xray"],
    "Lipid Profile": ["lipid profile", "cholesterol test"],
    "FBS / RBS": ["fbs", "rbs", "blood sugar", "blood sugar test"],
    "HbA1c": ["hba1c", "a1c"],
    "Prenatal Consult": ["prenatal", "prenatal checkup", "prenatal consult", "buntis checkup"],
}

# --- 2. Outpatient service equivalence groups (canonical -> member strings) --------
# Members are exact strings as they appear in hospital_prices.service. Only true naming
# variants are grouped; price-relevant distinctions are kept separate.
SERVICE_EQUIVALENTS: dict[str, list[str]] = {
    "CT Scan (plain)": ["CT Scan (plain)", "CT Scan (plain, single region)"],
    "CT Scan (contrast)": ["CT Scan (contrast)", "CT Scan (contrast, single region)"],
    "MRI (plain)": ["MRI (plain)", "MRI (plain, single region)"],
    "MRI (contrast)": ["MRI (contrast)", "MRI (contrast, single region)"],
    "Chest X-ray": ["Chest X-ray", "Chest X-ray (PA)"],
    "Ultrasound (abdomen)": ["Ultrasound (abdomen)", "Ultrasound (abdomen / pelvis)"],
    "PET-CT": ["PET-CT", "PET-CT (oncology staging)"],
    "Prenatal Consult": ["Prenatal Consult", "Prenatal Consult (OB)"],
    "ER Consultation": ["ER Consultation", "ER Consultation (triage + MD)"],
    "Executive Check-Up Basic": ["Executive Check-Up Basic", "Executive Check-Up (Basic)"],
    "Executive Check-Up Comprehensive": ["Executive Check-Up Comprehensive",
                                         "Executive Check-Up (Comprehensive)"],
    "Treadmill Stress Test": ["Treadmill Stress Test", "Stress Test (treadmill)"],
    "OPD (general)": ["OPD (general)", "OPD (general practitioner)"],
    "OPD (senior consultant)": ["OPD (senior consultant)", "OPD (senior specialist/consultant)",
                                "OPD (senior consultant / subspecialty)"],
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
