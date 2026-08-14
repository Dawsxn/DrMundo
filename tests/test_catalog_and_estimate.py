"""Tests for the taxonomy -> MMC price bridge and the end-to-end estimate (Phase 8)."""

from decimal import Decimal
from pathlib import Path

from eval.reader_bench import dataset_dir
from tests.conftest import needs_media
from pricing.catalog import KNOWN_UNPRICED, coverage_report, find_price, price_items
from pricing.estimate import estimate_from_slip
from pricing.hmo import resolve_hmo_plan
from vision.extract_request import read_and_extract
from vision.reader import OracleReader
from vision.schemas import ExtractedItem, RequestSlip


def _item(code: str, kind: str = "lab", cancelled: bool = False) -> ExtractedItem:
    return ExtractedItem(
        raw_text=code, normalized=code, test_code=code, kind=kind,
        state="cancelled" if cancelled else "ordered",
    )


# ------------------------------------------------------------------ coverage
def test_no_unexplained_gaps():
    """Every code MMC cannot price is documented as a genuine absence.

    An unexplained miss means the bridge is broken; a documented one means MMC really
    publishes nothing, which is a fact about the world and gets reported as such.
    """
    r = coverage_report()
    assert r["unexplained"] == []


def test_most_of_the_taxonomy_is_priceable():
    r = coverage_report()
    assert r["priced"] / r["codes"] > 0.85


def test_known_absences_stay_absent():
    # Not engineered around: the handoff's rule is that a missing price is reported.
    for code in ("FECALYSIS", "NM_BONE_SCAN"):
        assert code in KNOWN_UNPRICED
        assert find_price(code) is None


# ------------------------------------------------------------------ variant selection
def test_outpatient_matching_avoids_er_pricing():
    # ER pricing is emergency-room pricing. A request slip is not an emergency, and
    # quoting it would overstate the bill.
    assert not find_price("CBC")["service"].startswith("ER ")
    assert not find_price("TSH")["service"].startswith("ER ")


def test_blood_test_does_not_match_a_urine_assay():
    # CREATININE SERUM and CREATININE URINE 24HRS are different tests at different prices.
    row = find_price("CREATININE")
    assert "URINE" not in row["service"].upper()


def test_extent_is_matched_not_truncated():
    # XR_CHEST_PA_L is PA *and Lateral*, so it must reach CHEST PA & LATERAL -- not the
    # cheaper plain CHEST PA, and not the richer three-view row.
    assert find_price("XR_CHEST_PA_L")["service"] == "CHEST PA & LATERAL"


def test_a_combination_mmc_does_not_sell_is_reported_unpriced():
    # AP *and Lateral*: MMC prices CHEST AP and CHEST LATERAL VIEW ONLY separately and
    # publishes no combined row. Quoting CHEST AP alone would drop the lateral view and
    # understate the bill, so the honest answer is "no published price".
    assert "XR_CHEST_AP_L" in KNOWN_UNPRICED
    assert find_price("XR_CHEST_AP_L") is None


def test_short_surface_form_does_not_match_mid_word():
    """CREATININE's surface form is "Crea", and "crea" sits inside "pan-crea-s".

    Raw substring matching paired it with the PANCREAS row at P3,860-16,800, and the
    shortest-name rule then preferred that 8-character name over CREATININE SERUM. A P740
    blood test was priced as a P16,800 study. A match must begin at a word boundary.
    """
    assert find_price("CREATININE")["service"] == "CREATININE SERUM"


def test_word_boundary_rule_still_spans_punctuation():
    # "Chest PA/L" must still reach "CHEST PA & LATERAL": tokens are joined after the
    # boundary check, because MMC punctuates inconsistently.
    assert find_price("XR_CHEST_PA_L")["service"] == "CHEST PA & LATERAL"


def test_hand_verified_mapping_is_exact_confidence():
    priced, _ = price_items([_item("TROPONIN_I")])
    assert priced[0].catalog_name == "TROPONIN I HIGH SENSITIVITY"
    assert priced[0].match_confidence == 1.0


# ------------------------------------------------------------------ pricing split
def test_nothing_is_dropped_between_priced_and_unpriced():
    items = [_item("CBC"), _item("FECALYSIS"), _item("CREATININE")]
    priced, unpriced = price_items(items)
    assert len(priced) + len(unpriced) == 3


# ------------------------------------------------------------------ end to end
def _slip_for(sample_id: str) -> RequestSlip:
    import json
    base = dataset_dir()
    gt = json.loads((base / "groundtruth" / f"{sample_id}.json").read_text(encoding="utf-8"))
    img = base / "media" / Path(gt["image"]).name
    return read_and_extract(OracleReader(base / "groundtruth"), img, synthetic=True)


@needs_media
def test_real_slip_prices_end_to_end():
    est = estimate_from_slip(_slip_for("0000000"))
    assert est.extracted_count == 7
    assert len(est.priced) == 7
    assert est.gross_low > 0
    assert est.prepare_low <= est.prepare_high


@needs_media
def test_hmo_reduces_what_a_real_slip_costs():
    plan = resolve_hmo_plan("Maxicare", "Gold", remaining_balance=Decimal("40000"))
    with_hmo = estimate_from_slip(_slip_for("0000000"), hmo=plan)
    without = estimate_from_slip(_slip_for("0000000"))
    assert with_hmo.prepare_low < without.prepare_low


@needs_media
def test_non_lab_document_is_not_priced():
    # A results report lists test names and is still not an order.
    est = estimate_from_slip(_slip_for("0000250"))
    assert est.gross_low == Decimal(0)
    assert est.priced == []


@needs_media
def test_blank_form_produces_an_empty_estimate():
    est = estimate_from_slip(_slip_for("0000240"))
    assert est.extracted_count == 0
    assert est.prepare_low == Decimal(0)


@needs_media
def test_item_count_is_conserved_across_the_whole_pipeline():
    for sid in ("0000000", "0000001", "0000002", "0000250"):
        slip = _slip_for(sid)
        est = estimate_from_slip(slip)
        assert (len(est.priced) + len(est.unpriced)
                + len(est.needs_confirmation) + len(est.cancelled)) == len(slip.items)


# ------------------------------------------------------------------ HMO room entitlement
def test_taking_a_room_above_the_entitlement_is_flagged():
    """Silver entitles semi-private. A suite is P19,100 a night more, and the HMO will
    not pay the difference. We hold both figures, so staying silent would be a choice."""
    plan = resolve_hmo_plan("Maxicare", "Silver")        # entitlement: Semi - Private
    est = estimate_from_slip(_slip_for("0000000"), hmo=plan,
                             room_type="PRESIDENTIAL SUITE", length_of_stay=2)
    assert any("will not pay the difference" in c for c in est.caveats)


def test_a_room_within_the_entitlement_is_not_flagged():
    plan = resolve_hmo_plan("Maxicare", "Silver")
    est = estimate_from_slip(_slip_for("0000000"), hmo=plan, room_type="WARD")
    assert not any("will not pay the difference" in c for c in est.caveats)


def test_the_room_line_multiplies_only_when_nights_were_given():
    est = estimate_from_slip(_slip_for("0000000"), room_type="WARD", length_of_stay=3)
    line = next(l for l in est.separate_lines if "Room" in l.label)
    assert line.price_low == Decimal("1810") * 3
    assert "as you told me" in (line.note or "")

    est2 = estimate_from_slip(_slip_for("0000000"), room_type="WARD")
    line2 = next(l for l in est2.separate_lines if "Room" in l.label)
    assert line2.price_low == Decimal("1810")
    assert line2.unit == "per day"
