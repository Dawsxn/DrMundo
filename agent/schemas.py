"""Pydantic schemas: validated tool arguments + the final Answer structure.

Two roles:
  - Tool-argument models validate what the LLM asks to call (bad args -> we re-prompt).
  - `Answer` is the single structured object the API returns and the UI renders. Every
    numeric field is optional because it only appears on the path that produced it
    (covered vs outpatient), and `status` tells the caller which situation we're in.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ tool arguments
class SearchCatalogArgs(BaseModel):
    query_text: str = Field(..., description="The procedure/service phrase to look up.")
    top_k: int = Field(5, ge=1, le=20)


class GetCoveredCostArgs(BaseModel):
    rvs_code: str = Field(..., description="RVS code of a covered procedure (from search_catalog).")
    hospital: Optional[str] = Field(None, description="Hospital name or id; omit for all hospitals.")


class GetOutpatientCostArgs(BaseModel):
    service: str = Field(..., description="Exact outpatient service name (from search_catalog).")
    hospital: Optional[str] = Field(None, description="Hospital name or id; omit for all hospitals.")


class ListHospitalsArgs(BaseModel):
    name_query: Optional[str] = None
    city: Optional[str] = None


class AskUserArgs(BaseModel):
    question: str = Field(..., description="A single clarifying question for the user.")


# ------------------------------------------------------------------ final answer
class HospitalBreakdown(BaseModel):
    hospital: str
    city: Optional[str] = None
    service: Optional[str] = None          # outpatient: the actual service name used
    price_low: Optional[float] = None
    price_high: Optional[float] = None
    oop_low: Optional[float] = None        # covered only
    oop_high: Optional[float] = None
    fully_covered: Optional[bool] = None


class Answer(BaseModel):
    status: Literal["answered", "needs_clarification", "out_of_scope", "no_data"]
    path: Optional[Literal["covered", "outpatient"]] = None
    query: str
    answer_text: str = Field(..., description="Natural-language reply shown to the user.")

    procedure_or_service: Optional[str] = None
    hospital: Optional[str] = None

    case_rate: Optional[float] = None
    price_low: Optional[float] = None
    price_high: Optional[float] = None
    oop_low: Optional[float] = None
    oop_high: Optional[float] = None
    fully_covered: Optional[bool] = None

    hospitals: Optional[list[HospitalBreakdown]] = None
    as_of: Optional[str] = None

    disclaimer: str = (
        "Estimates only -- not medical or financial advice. Price ranges are indicative "
        "and may exclude professional fees, medicines, and room charges."
    )
