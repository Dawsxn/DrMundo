"""Tool registry for the ReAct agent.

Exposes the db/ query functions + `ask_user` as OpenAI function-calling tools. The LLM
chooses a tool and supplies JSON arguments; `execute_tool` validates those arguments
with the Pydantic models (re-prompting on bad input) and dispatches to the real Python
function. The tool *descriptions* below are what steer the model's routing, so they
encode the two-path logic.
"""

from typing import Any

from pydantic import ValidationError

from agent.schemas import (
    AskUserArgs,
    GetCoveredCostArgs,
    GetOutpatientCostArgs,
    ListHospitalsArgs,
    SearchCatalogArgs,
)
from db.queries import get_covered_cost, get_outpatient_cost, list_hospitals
from db.search import search_catalog


def _ask_user(question: str) -> dict:
    """Sentinel tool: signals the loop to stop and ask the user. Handled by the loop."""
    return {"status": "needs_clarification", "question": question}


# name -> (callable, Pydantic arg model)
_REGISTRY: dict[str, tuple[Any, Any]] = {
    "search_catalog": (search_catalog, SearchCatalogArgs),
    "get_covered_cost": (get_covered_cost, GetCoveredCostArgs),
    "get_outpatient_cost": (get_outpatient_cost, GetOutpatientCostArgs),
    "list_hospitals": (list_hospitals, ListHospitalsArgs),
    "ask_user": (_ask_user, AskUserArgs),
}


# OpenAI tool schemas. Descriptions carry the routing logic the model relies on.
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": (
                "STEP 1 for any cost question. Match the user's phrase to a covered "
                "procedure OR an outpatient service. Returns {candidates, confidence}. Each "
                "candidate has a 'kind' field: 'covered' (PhilHealth procedure, use "
                "get_covered_cost) or 'outpatient' (not covered, use get_outpatient_cost). "
                "The 'confidence.level' is high/medium/low/ambiguous: if it is 'ambiguous' "
                "or 'low' (or there are no candidates), call ask_user to clarify instead of "
                "guessing. Otherwise price the single best (top) candidate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_text": {"type": "string", "description": "Procedure/service phrase."},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_covered_cost",
            "description": (
                "PATH A. For a COVERED procedure (kind='covered'), get the PhilHealth case "
                "rate, hospital price range, and estimated out-of-pocket. Pass the rvs_code "
                "from search_catalog. Omit 'hospital' for an across-hospitals comparison; "
                "pass a hospital name/id for one hospital."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "rvs_code": {"type": "string"},
                    "hospital": {"type": "string", "description": "Optional hospital name or id."},
                },
                "required": ["rvs_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_outpatient_cost",
            "description": (
                "PATH B. For an OUTPATIENT service (kind='outpatient'), get the price range "
                "across hospitals. These are NOT PhilHealth-covered: never compute a case "
                "rate or out-of-pocket here. Pass the exact service name from search_catalog."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "hospital": {"type": "string", "description": "Optional hospital name or id."},
                },
                "required": ["service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_hospitals",
            "description": (
                "List hospitals or resolve a hospital mention. Filter by name_query or city "
                "(case-insensitive substring). Use to disambiguate when a hospital name is "
                "unclear or matches several."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name_query": {"type": "string"},
                    "city": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": (
                "Ask the user ONE clarifying question and stop. Use when the procedure/"
                "service is ambiguous, when a hospital name matches several, or when you "
                "cannot confidently route the question. Do NOT guess."
            ),
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
]


def execute_tool(name: str, arguments: dict) -> dict:
    """Validate arguments against the tool's Pydantic model, then call it.

    Returns the tool's result dict, or an {"error": ...} observation the agent can read
    and recover from (e.g. re-prompt with corrected arguments)."""
    if name not in _REGISTRY:
        return {"error": f"Unknown tool '{name}'."}
    func, arg_model = _REGISTRY[name]
    try:
        validated = arg_model(**(arguments or {}))
    except ValidationError as e:
        return {"error": "invalid_arguments", "detail": e.errors()}
    return func(**validated.model_dump(exclude_none=True))
