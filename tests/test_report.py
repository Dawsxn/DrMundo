"""Tests for the one-page budget report renderer (no DB, no API)."""

import re
from decimal import Decimal

from pricing.schemas import BudgetEstimate, HMOPlan, PricedItem, SeparateLine
from report.render import displayed_pesos, oldest_as_of, peso, render_html
from vision.schemas import ExtractedItem

_MONEY_IN_HTML = re.compile(r"₱([\d,]+)")


def _item(name: str, kind: str = "lab") -> ExtractedItem:
    return ExtractedItem(raw_text=name, normalized=name, kind=kind, ocr_confidence=0.9)


def _priced(name: str, low: str, high: str, as_of: str | None = None,
            case_rate: str | None = None) -> PricedItem:
    return PricedItem(
        item=_item(name),
        mmc_code="X",
        catalog_name=name,
        price_low=Decimal(low),
        price_high=Decimal(high),
        case_rate=Decimal(case_rate) if case_rate else None,
        match_confidence=0.9,
        as_of=as_of,
    )


def _full() -> BudgetEstimate:
    return BudgetEstimate(
        priced=[
            _priced("CBC (COMPLETE BLOOD COUNT)", "630", "1200", "August 31, 2023"),
            _priced("CHEST PA", "1105", "3400", "July 21, 2021"),
        ],
        unpriced=[_item("FECALYSIS"), _item("SODIUM")],
        needs_confirmation=[_item("CREA")],
        extracted_count=5,
        gross_low=Decimal("1735"),
        gross_high=Decimal("4600"),
        prepare_low=Decimal("1735"),
        prepare_high=Decimal("4600"),
        separate_lines=[
            SeparateLine(label="Room & board, if admitted", price_low=Decimal("1810"),
                         price_high=Decimal("37200"), unit="per day"),
        ],
        caveats=["This figure is before any HMO benefit."],
    )


# ------------------------------------------------------------------ traceability
def test_every_peso_on_the_page_traces_to_the_estimate():
    # The same contract the output guardrail enforces on prose.
    e = _full()
    html = render_html(e)
    printed = {int(m.replace(",", "")) for m in _MONEY_IN_HTML.findall(html)}
    assert printed <= displayed_pesos(e)
    assert printed  # and it actually printed something


def test_headline_range_is_rendered():
    html = render_html(_full())
    assert "₱1,735" in html and "₱4,600" in html
    assert "What you'll pay" in html


# ------------------------------------------------------------------ buckets never collapse
def test_unpriced_bucket_is_rendered_and_marked_excluded():
    html = render_html(_full())
    assert "Not priced (2)" in html
    assert "FECALYSIS" in html and "SODIUM" in html
    assert "not</strong> in the total" in html


def test_needs_confirmation_bucket_is_rendered():
    html = render_html(_full())
    assert "Please confirm (1)" in html
    assert "CREA" in html


def test_buckets_are_absent_only_when_empty():
    e = BudgetEstimate(priced=[_priced("CBC", "630", "1200")], extracted_count=1,
                       prepare_low=Decimal("630"), prepare_high=Decimal("1200"))
    html = render_html(e)
    assert "Not priced" not in html
    assert "Please confirm" not in html


# ------------------------------------------------------------------ excluded costs
def test_room_and_board_sits_outside_the_total():
    html = render_html(_full())
    assert "Not included" in html
    assert "per day" in html
    # It must not have been folded into the headline.
    assert "₱37,200" in html
    assert render_html(_full()).index("Not included") > html.index("What you'll pay")


def test_room_and_board_is_never_multiplied():
    # No length of stay is assumed anywhere, so the per-day figure appears verbatim.
    e = _full()
    html = render_html(e)
    printed = {int(m.replace(",", "")) for m in _MONEY_IN_HTML.findall(html)}
    assert 1810 in printed and 37200 in printed
    assert 1810 * 3 not in printed


# ------------------------------------------------------------------ staleness
def test_oldest_as_of_is_shown_not_the_freshest():
    e = _full()
    assert oldest_as_of(e) == "July 21, 2021"
    assert "July 21, 2021" in render_html(e)


def test_unparseable_as_of_still_reported():
    e = BudgetEstimate(priced=[_priced("X", "1", "2", as_of="sometime")], extracted_count=1,
                       prepare_low=Decimal("1"), prepare_high=Decimal("2"))
    assert oldest_as_of(e) == "sometime"


def test_no_as_of_is_not_fabricated():
    e = BudgetEstimate(priced=[_priced("X", "1", "2")], extracted_count=1,
                       prepare_low=Decimal("1"), prepare_high=Decimal("2"))
    assert oldest_as_of(e) is None


# ------------------------------------------------------------------ HMO labelling
def test_published_tier_hmo_is_flagged_on_the_page():
    e = _full()
    e.hmo = HMOPlan(mbl_annual=Decimal("100000"), mbl_source="published_tier")
    e.hmo_low = Decimal("500")
    e.hmo_high = Decimal("500")
    html = render_html(e)
    assert "check your own certificate" in html
    assert "‡" in html


def test_patient_stated_hmo_is_not_flagged():
    e = _full()
    e.hmo = HMOPlan(remaining_balance=Decimal("40000"), mbl_source="patient_stated")
    e.hmo_low = Decimal("500")
    e.hmo_high = Decimal("500")
    assert "check your own certificate" not in render_html(e)


# ------------------------------------------------------------------ deduction rows
def test_deduction_rows_appear_only_when_non_zero():
    e = _full()
    html = render_html(e)
    assert "PhilHealth case rate" not in html   # nothing deducted in this fixture
    e.philhealth_low = Decimal("60450")
    e.philhealth_high = Decimal("60450")
    assert "PhilHealth case rate" in render_html(e)


def test_caveats_are_rendered():
    assert "before any HMO" in render_html(_full())


def test_bucket_echo_caveats_are_not_repeated_on_the_page():
    # The page already has "Not priced (2)" and "Please confirm (1)" headings; repeating
    # them as caveats buries the ones carrying real information. They stay in the
    # estimate for the guardrail's plain-text fallback, which has no buckets.
    e = _full()
    e.caveats = e.caveats + [
        "2 item(s) have no published MMC price and are NOT included in the total above.",
        "1 item(s) need confirmation before they can be priced.",
    ]
    html = render_html(e)
    assert "have no published MMC price and are NOT" not in html
    assert "need confirmation before they can be priced" not in html
    assert "before any HMO" in html          # informative caveat survives
    assert "Not priced (2)" in html          # the bucket still says it structurally


def test_patient_facing_caveats_use_real_dashes():
    from decimal import Decimal as D

    from pricing.waterfall import compute_budget
    e = compute_budget(
        priced=[_priced("VATS PACKAGE", "50000", "60000")],
    )
    e.priced[0].item.kind = "procedure"
    e2 = compute_budget(priced=[_priced("X", "1", "2")])
    for c in e.caveats + e2.caveats:
        assert " -- " not in c, c


# ------------------------------------------------------------------ formatting
def test_peso_formatting_and_none():
    assert peso(Decimal("60450")) == "₱60,450"
    assert peso(Decimal("12400.5")) == "₱12,401"   # ROUND_HALF_UP, matches the guard
    assert peso(None) == "n/a"


def test_empty_estimate_still_renders():
    html = render_html(BudgetEstimate(extracted_count=0))
    assert "What you'll pay" in html
