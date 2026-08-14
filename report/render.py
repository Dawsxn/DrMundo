"""One-page budget report.

Renders a `BudgetEstimate` to HTML -- the inline view in chat, and the source a PDF
adapter can print. Nothing here computes money: every figure comes from the estimate and
is rounded through `to_display_pesos`, the same function the grounding guard uses.

Layout rules, in priority order (plan §11):
  1. The headline "prepare" range is the largest thing on the page. It is what the
     patient came for.
  2. Excluded lines -- professional fees, room & board -- sit visually OUTSIDE the total.
     A reader skimming must not be able to mistake them for included.
  3. NOT PRICED and PLEASE CONFIRM are always rendered when non-empty. They never
     collapse; a dropped bucket is how an understated bill becomes invisible.
  4. Room & board is per-day and never multiplied. Length of stay is unknowable from a
     request slip (handoff §8).
  5. Figures from the published HMO tier table carry a visible marker.
  6. The OLDEST as_of across items is shown, so staleness is visible rather than hidden
     behind the freshest row.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pricing.schemas import BudgetEstimate, to_display_pesos

_TEMPLATES = Path(__file__).resolve().parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

# MMC's as_of strings look like "August 31, 2023".
_AS_OF_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d")


def peso(amount: Optional[Decimal]) -> str:
    """Format for display. Rounds through the one function the guard also uses."""
    if amount is None:
        return "n/a"
    return f"₱{to_display_pesos(amount):,}"


def _parse_as_of(value: str) -> Optional[datetime]:
    for fmt in _AS_OF_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def oldest_as_of(estimate: BudgetEstimate) -> Optional[str]:
    """The stalest price in the report. Showing the freshest would flatter the data."""
    dated = []
    for item in estimate.priced:
        if item.as_of:
            parsed = _parse_as_of(item.as_of)
            if parsed is not None:
                dated.append((parsed, item.as_of))
    if not dated:
        # Fall back to any unparseable string rather than claiming no date exists.
        raw = [i.as_of for i in estimate.priced if i.as_of]
        return raw[0] if raw else None
    return min(dated)[1]


def displayed_pesos(estimate: BudgetEstimate) -> set[int]:
    """Every peso figure the template will print.

    Exists so a test can assert the page introduces no number that is absent from the
    estimate -- the same contract the output guardrail enforces on prose.
    """
    vals: set[int] = set()

    def add(*amounts):
        for a in amounts:
            if a is not None:
                vals.add(to_display_pesos(a))

    add(estimate.prepare_low, estimate.prepare_high,
        estimate.gross_low, estimate.gross_high,
        estimate.discount_low, estimate.discount_high,
        estimate.philhealth_low, estimate.philhealth_high,
        estimate.hmo_low, estimate.hmo_high)
    for item in estimate.priced:
        add(item.price_low, item.price_high)
    for line in estimate.separate_lines:
        add(line.price_low, line.price_high)
    return vals


# Caveats whose content the rendered page already states structurally. They must STAY in
# BudgetEstimate.caveats -- the guardrail's plain-text fallback has no buckets and needs
# them -- but repeating them under a "Not priced (2)" heading that says the same thing
# reads as padding and buries the caveats that carry real information.
_BUCKET_ECHO_PREFIXES = ("no published MMC price", "need confirmation")


def visible_caveats(estimate: BudgetEstimate) -> list[str]:
    """Caveats worth printing next to a page that already shows the buckets."""
    return [
        c for c in estimate.caveats
        if not any(frag in c for frag in _BUCKET_ECHO_PREFIXES)
    ]


def render_html(estimate: BudgetEstimate, hospital: str = "Makati Medical Center") -> str:
    """Render the one-page report as a self-contained HTML fragment."""
    has_discount = bool(estimate.discount_low or estimate.discount_high)
    has_philhealth = bool(estimate.philhealth_low or estimate.philhealth_high)
    has_hmo = bool(estimate.hmo_low or estimate.hmo_high)

    return _env.get_template("report.html").render(
        e=estimate,
        peso=peso,
        hospital=hospital,
        caveats=visible_caveats(estimate),
        as_of=oldest_as_of(estimate),
        has_discount=has_discount,
        has_philhealth=has_philhealth,
        has_hmo=has_hmo,
        # Any figure sourced from the published tier table is the patient's plan TIER,
        # not their policy. Labelling is the agreed answer to handoff §7's objection.
        hmo_needs_verification=bool(estimate.hmo and estimate.hmo.needs_verification_note),
    )
