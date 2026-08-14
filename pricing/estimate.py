"""Slip -> BudgetEstimate. The join between extraction and the waterfall.

One function, because the ordering matters and scattering it across callers is how a
cancelled row eventually gets billed:

    triage      cancelled / needs-confirmation / priceable   (vision/extract_request.py)
    price       priceable -> priced + unpriced               (pricing/catalog.py)
    waterfall   priced -> what to prepare                    (pricing/waterfall.py)

The item count is conserved end to end. Whatever the reader saw lands in exactly one of
the four buckets, and `BudgetEstimate` raises if it does not.
"""

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

    return compute_budget(
        priced=priced,
        unpriced=unpriced,
        needs_confirmation=buckets["needs_confirmation"],
        cancelled=buckets["cancelled"],
        extracted_count=len(slip.items),
        hmo=hmo,
        senior_or_pwd=senior_or_pwd,
        separate_lines=separate_lines or [],
        procedure_source=procedure_source or slip.procedure_source,
        planned_procedure=planned_procedure or slip.planned_procedure,
    )
