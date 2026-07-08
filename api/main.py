"""FastAPI app: POST /ask, GET /health, Swagger at /docs.

The service holds per-session memory in-process, so we instantiate ONE `DrMundoService`
at import time and reuse it across requests (memory is keyed by `session_id`). Request
bodies are validated by Pydantic, so a malformed payload returns 422 automatically.
"""

import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.schemas import Answer
from agent.service import DrMundoService
from config import DB_PATH, EMBEDDINGS_PATH

app = FastAPI(
    title="Dr. Mundo API",
    version="1.0.0",
    description=(
        "Plain-language cost estimates for Philippine medical procedures and outpatient "
        "services. Answers are grounded in local PhilHealth case-rate and hospital-price "
        "data -- no numbers are invented, and no medical advice is given."
    ),
)

# One service instance -> shared per-session memory across requests.
SERVICE = DrMundoService()


# ----------------------------------------------------------------- request / response
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Plain-language or Taglish cost question.")
    session_id: str = Field("default", min_length=1, max_length=128,
                            description="Stable id so follow-up questions keep context.")


class TraceStepOut(BaseModel):
    thought: Optional[str] = None
    action: Optional[str] = None
    # Observations vary by tool: search_catalog returns {candidates, confidence}, cost tools a dict.
    action_input: Optional[Any] = None
    observation: Optional[Any] = None


class OutputReportOut(BaseModel):
    grounded: bool = True
    replaced: bool = False
    violations: list[float] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AskResponse(BaseModel):
    answer: Answer
    trace: list[TraceStepOut] = Field(default_factory=list)
    pii_found: list[str] = Field(default_factory=list)
    category: str = "cost"
    latency_ms: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    prompt_version: str = "system_v2"
    output_report: OutputReportOut = Field(default_factory=OutputReportOut)


class ResetRequest(BaseModel):
    session_id: str = Field("default", min_length=1, max_length=128)


class ResetResponse(BaseModel):
    status: str = "ok"
    session_id: str


# ----------------------------------------------------------------- helpers
def _json_safe(value):
    """Round-trip through JSON (with str fallback) so observation payloads that contain
    e.g. numpy scalars serialise cleanly in the response."""
    if value is None:
        return None
    return json.loads(json.dumps(value, default=str))


# ----------------------------------------------------------------- endpoints
@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness + data-readiness check."""
    return {
        "status": "ok",
        "database": DB_PATH.exists(),
        "embeddings": EMBEDDINGS_PATH.exists(),
    }


@app.post("/ask", response_model=AskResponse, tags=["cost"])
def ask(req: AskRequest) -> AskResponse:
    """Answer one cost question. Follow-ups with the same `session_id` keep context."""
    try:
        result = SERVICE.handle(req.question, session_id=req.session_id)
    except Exception as exc:  # noqa: BLE001 - surface a clean 500 to the client
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    trace = [
        TraceStepOut(
            thought=step.thought,
            action=step.action,
            action_input=_json_safe(step.action_input),
            observation=_json_safe(step.observation),
        )
        for step in result.trace
    ]

    report = result.output_report
    output_report = OutputReportOut(
        grounded=getattr(report, "grounded", True),
        replaced=getattr(report, "replaced", False),
        violations=list(getattr(report, "violations", []) or []),
        notes=list(getattr(report, "notes", []) or []),
    )

    return AskResponse(
        answer=result.answer,
        trace=trace,
        pii_found=result.pii_found,
        category=result.category,
        latency_ms=result.latency_ms,
        total_tokens=result.usage.total_tokens,
        estimated_cost_usd=result.estimated_cost_usd,
        prompt_version=result.prompt_version,
        output_report=output_report,
    )


@app.post("/reset", response_model=ResetResponse, tags=["cost"])
def reset(req: ResetRequest) -> ResetResponse:
    """Clear a session's short-term memory (used by the UI's 'New chat' button)."""
    SERVICE.reset_session(req.session_id)
    return ResetResponse(session_id=req.session_id)
