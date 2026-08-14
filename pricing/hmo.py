"""HMO plan resolution: a named plan -> an `HMOPlan` pre-filled from published tiers.

Conversational, never extracted from an image (plan §2.3). The agent asks which provider
and plan the patient has, this fills in what Maxicare publishes for that tier, and the
patient's own figures override anything found here.

Two things this module will not do:

  - It will not invent a plan. A plan name matching nothing is the EXPECTED case, not an
    error: these are individual/family tiers, most PH coverage is employer-provided and
    negotiated, so a corporate member matches nothing. The agent then asks for the MBL.
  - It will not supply a remaining balance. That changes with every claim, lives in the
    member portal, and is always typed by the patient.
"""

import csv
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pricing.schemas import HMOPlan

TIERS_PATH = Path(__file__).resolve().parent.parent / "data" / "hmo_published_tiers.csv"


class MissingTierTable(FileNotFoundError):
    """Raised when the published-tier table is absent.

    Deliberately fatal rather than falling back to defaults. Inventing HMO numbers is
    precisely what handoff §7 rejected, and a silent default here would put a fabricated
    benefit limit in front of a patient.
    """


@lru_cache(maxsize=1)
def load_tiers() -> list[dict]:
    if not TIERS_PATH.exists():
        raise MissingTierTable(
            f"{TIERS_PATH} is missing. It carries published figures with source URLs; "
            f"see data/HMO_TIERS_PROVENANCE.md. Do not substitute your own numbers."
        )
    with TIERS_PATH.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("is_published", "").lower() == "true"]


def _norm(s: str) -> str:
    """Fold case, spacing and punctuation so 'Platinum-Plus' matches 'platinum plus'."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def list_plans(provider: Optional[str] = None) -> list[dict]:
    """Published plans, optionally filtered by provider. For offering the user a choice."""
    rows = load_tiers()
    if provider:
        p = _norm(provider)
        rows = [r for r in rows if _norm(r["provider"]) == p]
    return rows


def resolve_hmo_plan(
    provider: Optional[str] = None,
    plan_name: Optional[str] = None,
    remaining_balance: Optional[Decimal] = None,
    mbl_annual: Optional[Decimal] = None,
) -> HMOPlan:
    """Build an HMOPlan from a named tier, with patient-stated figures taking precedence.

    `mbl_annual` passed in wins over the table -- if the patient read their own certificate,
    that is better evidence than a published tier for a plan they may not actually hold.
    """
    row = _match(provider, plan_name)

    if mbl_annual is not None:
        resolved_mbl, source = mbl_annual, "patient_stated"
    elif row is not None:
        resolved_mbl, source = Decimal(row["mbl_annual"]), "published_tier"
    else:
        resolved_mbl, source = None, None

    return HMOPlan(
        provider=(row["provider"] if row else provider) or None,
        plan_name=(row["plan_name"] if row else plan_name) or None,
        mbl_annual=resolved_mbl,
        remaining_balance=remaining_balance,   # always patient-stated
        room_entitlement=row["room_entitlement"] if row else None,
        mbl_source=source,
    )


def _match(provider: Optional[str], plan_name: Optional[str]) -> Optional[dict]:
    """Find a published tier. Forgiving about casing and spacing, strict about identity."""
    if not plan_name:
        return None
    rows = list_plans(provider)
    target = _norm(plan_name)
    if not target:
        return None

    for r in rows:                                   # exact
        if _norm(r["plan_name"]) == target:
            return r

    # Substring, longest first. "platinum" must not win over "platinumplus" when the user
    # typed the longer name, and a bare "platinum" should not silently resolve to the
    # dearer tier.
    candidates = [r for r in rows if _norm(r["plan_name"]) in target or target in _norm(r["plan_name"])]
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        exact_len = sorted(candidates, key=lambda r: abs(len(_norm(r["plan_name"])) - len(target)))
        best, runner_up = exact_len[0], exact_len[1]
        if len(_norm(best["plan_name"])) != len(_norm(runner_up["plan_name"])):
            return best
    return None                                       # ambiguous -> ask, do not guess


def mmc_room_type(plan: HMOPlan) -> Optional[str]:
    """The MMC `facility_rates` room type this plan entitles the member to, if unambiguous.

    Returns None where the two vocabularies do not line up. Maxicare's "Regular Private"
    has no MMC equivalent -- MMC publishes SMALL / LARGE / PREMIUM LARGE PRIVATE -- and
    guessing would silently change what a patient is told they are entitled to.
    """
    if not plan.plan_name:
        return None
    for r in load_tiers():
        if _norm(r["plan_name"]) == _norm(plan.plan_name):
            return r.get("mmc_room_type") or None
    return None
