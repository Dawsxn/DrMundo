"""Panel vs. individual-component comparison.

A lab panel is often cheaper than buying its member tests separately -- at MMC all three
lipid panels are, by P60 to P1,400 depending on the panel and which end of the range you
land on. Telling a patient that is real, checkable money.

This is ADVISORY. It never rewrites what the waterfall charges: the slip says what the
doctor ordered, and the estimate prices that. The comparison sits alongside it so the
patient can go back and ask.
"""

from decimal import Decimal
from typing import Iterable, Optional

from db.queries import get_panel_comparison
from pricing.schemas import PricedItem


def _member_names(panel: str) -> set[str]:
    res = get_panel_comparison(panel)
    if res["status"] == "ok":
        return {m["service"] for m in res["members"]}
    if res["status"] == "incomplete":
        return {m["service"] for m in res["members_priced"]}
    return set()


def compare_panels_on_slip(priced: Iterable[PricedItem]) -> list[dict]:
    """For every panel among the priced items, compare it against its components.

    Returns one advisory dict per panel found. `already_has_members` flags the awkward
    case where the slip lists BOTH a panel and some of its member tests -- see
    `panel_and_members_note` for why that is reported rather than silently resolved.
    """
    priced = list(priced)
    on_slip = {p.catalog_name for p in priced}
    out: list[dict] = []

    for p in priced:
        res = get_panel_comparison(p.catalog_name)
        if res["status"] == "no_data":
            continue  # not a panel, or the panel itself is unpriced

        overlap = sorted(_member_names(p.catalog_name) & on_slip)

        if res["status"] == "incomplete":
            out.append({
                "panel": p.catalog_name,
                "status": "incomplete",
                "message": res["message"],
                "members_missing": res["members_missing"],
                "already_has_members": overlap,
            })
            continue

        out.append({
            "panel": p.catalog_name,
            "status": "ok",
            "cheaper": res["cheaper"],
            "panel_price_low": Decimal(str(res["panel_price_low"])),
            "panel_price_high": Decimal(str(res["panel_price_high"])),
            "components_price_low": Decimal(str(res["components_price_low"])),
            "components_price_high": Decimal(str(res["components_price_high"])),
            "saving_low": Decimal(str(res["saving_low"])),
            "saving_high": Decimal(str(res["saving_high"])),
            "members": [m["service"] for m in res["members"]],
            "already_has_members": overlap,
        })

    return out


def panel_advisory_text(comparison: dict) -> Optional[str]:
    """One patient-facing line for a comparison, or None when there is nothing to say."""
    if comparison["status"] == "incomplete":
        return (
            f"{comparison['panel']}: some member tests have no published price, so we "
            f"cannot say whether buying them separately would be cheaper."
        )

    # Both the panel and some of its members are on the same slip. We do NOT quietly drop
    # the duplicates: the doctor may have wanted a repeat, and removing an ordered test
    # from an estimate is a clinical decision, not a pricing one.
    if comparison["already_has_members"]:
        dupes = ", ".join(comparison["already_has_members"])
        return (
            f"Your slip lists {comparison['panel']} and also {dupes}, which the panel "
            f"already includes. Both are priced above -- worth asking whether you need both."
        )

    if comparison["cheaper"] == "panel":
        return (
            f"{comparison['panel']} costs less as a panel than buying its "
            f"{len(comparison['members'])} tests separately -- you save between "
            f"P{comparison['saving_low']:,.0f} and P{comparison['saving_high']:,.0f}."
        )
    if comparison["cheaper"] == "components":
        return (
            f"Buying the {len(comparison['members'])} tests in {comparison['panel']} "
            f"separately costs less than the panel."
        )
    # Crosses over: cheaper at one end of the range, dearer at the other.
    return (
        f"{comparison['panel']} and its individual tests overlap in price -- neither is "
        f"reliably cheaper."
    )
