"""Slip -> BudgetEstimate. The join between extraction and the waterfall.

One function, because the ordering matters and scattering it across callers is how a
cancelled row eventually gets billed:

    triage      cancelled / needs-confirmation / priceable   (vision/extract_request.py)
    price       priceable -> priced + unpriced               (pricing/catalog.py)
    waterfall   priced -> what to prepare                    (pricing/waterfall.py)

The item count is conserved end to end. Whatever the reader saw lands in exactly one of
the four buckets, and `BudgetEstimate` raises if it does not.
"""

import re
from decimal import Decimal
from typing import Optional

from pricing.catalog import price_items
from pricing.schemas import BudgetEstimate, HMOPlan, SeparateLine
from pricing.waterfall import compute_budget
from vision.extract_request import triage
from vision.schemas import ProcedureSource, RequestSlip


def estimate_from_slip(
    slip: RequestSlip,
    *,
    hmo: Optional[HMOPlan] = None,
    senior_or_pwd: bool = False,
    separate_lines: Optional[list[SeparateLine]] = None,
    procedure_source: Optional[ProcedureSource] = None,
    planned_procedure: Optional[str] = None,
    philhealth_active: Optional[bool] = None,
    hmo_covers_outpatient: Optional[bool] = None,
    room_type: Optional[str] = None,
    length_of_stay: Optional[int] = None,
) -> BudgetEstimate:
    """Price a whole request slip.

    A document that is not a laboratory request returns an EMPTY estimate rather than a
    priced one. A results report lists test names and reference ranges and is not an
    order; pricing it would bill someone for tests they have already had.
    """
    if not slip.is_laboratory_request:
        return compute_budget(
            extracted_count=len(slip.items),
            needs_confirmation=list(slip.items),
            procedure_source="none_planned",
        )

    buckets = triage(slip)
    priced, unpriced = price_items(buckets["priceable"])

    lines = list(separate_lines or [])
    room = _room_line(room_type, length_of_stay)
    if room is not None:
        lines.append(room)
    upgrade = _room_upgrade_note(hmo, room_type)

    return compute_budget(
        priced=priced,
        unpriced=unpriced,
        needs_confirmation=buckets["needs_confirmation"],
        cancelled=buckets["cancelled"],
        extracted_count=len(slip.items),
        hmo=hmo,
        senior_or_pwd=senior_or_pwd,
        separate_lines=lines,
        procedure_source=procedure_source or slip.procedure_source,
        planned_procedure=planned_procedure or slip.planned_procedure,
        philhealth_active=philhealth_active,
        hmo_covers_outpatient=hmo_covers_outpatient,
        extra_caveats=[upgrade] if upgrade else [],
    )


# MMC room names, cheapest first. Used to tell whether a chosen room sits above what the
# patient's plan entitles them to.
_ROOM_LADDER = ["ward", "semi private", "small private", "regular private", "large private",
                "premium large private", "regular suite", "presidential suite"]


def _rank_room(name: Optional[str]) -> Optional[int]:
    """Where a room name sits on the ladder, or None if we do not recognise it.

    Maxicare writes "Semi - Private" and MMC writes "SEMI PRIVATE", so whitespace and
    hyphens are flattened before matching. Scanning the ladder from the dearest end
    matters too: "large private" contains "private", and checking cheapest-first would
    rank a large private room as a plain one.
    """
    if not name:
        return None
    key = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    for i in range(len(_ROOM_LADDER) - 1, -1, -1):
        if _ROOM_LADDER[i] in key:
            return i
    return None


def _room_upgrade_note(hmo: Optional[HMOPlan], room_type: Optional[str]) -> Optional[str]:
    """Warn when the chosen room sits above the plan's entitlement.

    HMO plans cover room and board only up to the tier you bought. Take a suite on a
    semi-private entitlement and the difference is yours every night, which on MMC's
    ladder is P19,100 a night between those two. We hold both figures, so saying nothing
    would be a choice rather than a limitation.
    """
    if hmo is None or not room_type or not hmo.room_entitlement:
        return None
    chosen, allowed = _rank_room(room_type), _rank_room(hmo.room_entitlement)
    if chosen is None or allowed is None or chosen <= allowed:
        return None
    return (f"Your plan covers a {hmo.room_entitlement.lower()} room. You chose "
            f"{room_type.title()}, so your HMO will not pay the difference in room rate "
            f"and you will settle it yourself.")


def _room_line(room_type: Optional[str], nights: Optional[int]) -> Optional[SeparateLine]:
    """Room and board as a separate line, never folded into the total.

    Length of stay is ASKED, never assumed (handoff §8). When the patient gives one we
    multiply and say so on the line; when they do not, the per-day rate stands on its own.
    """
    if not room_type:
        return None
    from db.queries import get_facility_rates

    match = next((r for r in get_facility_rates()["rates"]
                  if r["room_type"].lower() == room_type.lower()), None)
    if match is None:
        return None

    low, high = Decimal(str(match["rate_low"])), Decimal(str(match["rate_high"]))
    if nights and nights > 0:
        return SeparateLine(
            label=f"Room & board, {match['room_type'].title()}",
            price_low=low * nights, price_high=high * nights,
            note=f"{nights} night(s) at {low:,.0f}/night, as you told me",
        )
    return SeparateLine(label=f"Room & board, {match['room_type'].title()}",
                        price_low=low, price_high=high, unit="per day")
