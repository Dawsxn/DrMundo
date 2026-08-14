"""Tests for label -> test_code resolution (Phase 5).

The rules come from the taxonomy's own `matching` block, and each has a failure mode that
is worse than "no answer": resolving LDL to LDH, or bare KUB to the wrong modality, gives
a patient a confident price for a test their doctor did not order.
"""

import pytest

from vision.resolve import resolve, section_id


# ------------------------------------------------------------------ straightforward
def test_exact_surface_form():
    r = resolve("CBC")
    assert r.test_code == "CBC"
    assert r.method == "exact"
    assert r.kind == "lab"


def test_canonical_name():
    assert resolve("Complete Blood Count").test_code == "CBC"


def test_alias_that_looks_nothing_like_the_code():
    # ~12% of printed labels are aliases rather than the canonical form.
    assert resolve("Stool Examination").test_code == "FECALYSIS"
    assert resolve("Fasting Blood Glucose").test_code == "FBS"


def test_unknown_text_is_unresolved_not_guessed():
    r = resolve("something entirely unrelated")
    assert r.test_code is None
    assert r.method == "unresolved"


# ------------------------------------------------------------------ blocked abbreviations
@pytest.mark.parametrize("label", ["PT", "CT", "BT", "KUB", "Chest"])
def test_blocked_abbreviations_never_resolve_bare(label):
    r = resolve(label)
    assert r.method == "ambiguous"
    assert len(r.candidates) > 1
    assert r.needs_confirmation is True


def test_section_heading_rescues_kub():
    # The dataset's headline ambiguity: bare KUB appears under both headings on one sheet.
    assert resolve("KUB", "Ultrasound").test_code == "US_KUB"
    assert resolve("KUB", "X-Ray").test_code == "XR_KUB"


def test_section_heading_rescues_pt():
    assert resolve("PT", "Coagulation").test_code == "PT_PROTHROMBIN"


def test_chest_stays_ambiguous_even_with_a_section():
    # Correct: knowing it is an x-ray does not choose between PA/L and AP/L.
    assert resolve("Chest", "X-Ray").method == "ambiguous"


def test_scoped_alias_table_is_used():
    assert resolve("Upper Abdomen", "ct_advanced").test_code == "CT_UPPER_ABDOMEN"


# ------------------------------------------------------------------ fuzzy, and its limits
def test_fuzzy_absorbs_reader_noise():
    r = resolve("Creatlnine")          # OCR misread of Creatinine
    assert r.test_code == "CREATININE"
    assert r.method == "fuzzy"


def test_ldl_and_ldh_are_never_confused():
    # One edit apart, entirely different tests. Exact matching must win outright.
    assert resolve("LDL").test_code == "LDL"
    assert resolve("LDH").test_code == "LDH"


def test_sgot_and_sgpt_are_never_confused():
    assert resolve("SGOT").test_code != resolve("SGPT").test_code


# ------------------------------------------------------------------ section mapping
def test_printed_headings_map_to_taxonomy_section_ids():
    assert section_id("Cardiac Markers:") == "cardiac"
    assert section_id("Clinical Microscopy") == "hematology"
    assert section_id("not a real heading") is None


# ------------------------------------------------------------------ modality -> kind
def test_modality_maps_to_item_kind():
    assert resolve("CBC").kind == "lab"
    assert resolve("KUB", "Ultrasound").kind == "imaging"
    assert resolve("2D Echo").kind == "diagnostic"


def test_nothing_resolves_to_a_procedure():
    # This dataset is outpatient work-up; no item from it may attract a case rate.
    from eval.resolver_bench import load_samples
    seen = set()
    for s in load_samples()[:40]:
        for m in s.get("marks", []):
            lab = m.get("label_text_on_form")
            if lab:
                seen.add(resolve(lab, m.get("section")).kind)
    assert "procedure" not in seen


# ------------------------------------------------------------------ the whole gold set
def test_perfect_reader_resolves_every_label():
    """Upper bound: with an oracle reader, resolution is lossless.

    Any later model score is bounded by this, so a failure here would cap the whole
    pipeline no matter how good the reader gets.
    """
    from eval.resolver_bench import run
    r = run()
    assert r["labels"] == 1452
    assert r["correct"] == 1452
    assert r["wrong"] == 0


def test_section_headings_are_worth_measuring():
    """Withholding headings costs 46 labels, and costs them as 'ask', not as 'wrong'."""
    from eval.resolver_bench import run
    a = run(use_sections=False)
    assert a["ambiguous"] == 46
    assert a["wrong"] == 0
