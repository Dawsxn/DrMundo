"""FastAPI app: POST /ask, GET /health, Swagger at /docs.

The service holds per-session memory in-process, so we instantiate ONE `DrMundoService`
at import time and reuse it across requests (memory is keyed by `session_id`). Request
bodies are validated by Pydantic, so a malformed payload returns 422 automatically.
"""

import json
import os
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
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


class QuestionOut(BaseModel):
    """The pending intake question, described well enough for a UI to render controls."""

    kind: str
    text: str
    options: list[str] = Field(default_factory=list)
    field: Optional[str] = None          # "text" | "number" | None
    subject: Optional[str] = None
    step: int = 0
    total: int = 0


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
    question: Optional[QuestionOut] = None


class RefineRequest(BaseModel):
    """One answer from the §14 refine loop. Every field is optional: the patient answers
    one question at a time, and each answer re-prices the slip already in memory."""

    session_id: str = Field("default", min_length=1, max_length=128)
    hmo_provider: Optional[str] = None
    hmo_plan: Optional[str] = None
    # Always patient-stated: it appears on no card or certificate (plan §0.1).
    hmo_remaining_balance: Optional[str] = Field(
        None, description="Peso amount, as typed by the patient."
    )
    senior_or_pwd: Optional[bool] = None
    planned_procedure: Optional[str] = Field(
        None, description="Operation the work-up is for, if any."
    )
    no_procedure_planned: Optional[bool] = Field(
        None, description="True for routine or precautionary work-up. A real answer, not a refusal."
    )


class ChoiceRequest(BaseModel):
    """A widget answer. Deterministic, so it never reaches the extractor."""

    kind: str = Field(..., min_length=1, max_length=40)
    value: str = Field(..., max_length=200)
    extra: Optional[str] = Field(None, max_length=200,
                                 description="Free text or amount beside the choice.")
    session_id: str = Field("default", min_length=1, max_length=128)


class SkipRequest(BaseModel):
    session_id: str = Field("default", min_length=1, max_length=128)


class ConverseRequest(BaseModel):
    """A free-text reply in the refine loop. The model extracts the slots."""

    text: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field("default", min_length=1, max_length=128)


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


def _pending_question(session_id: str) -> Optional[QuestionOut]:
    """Describe the question the session is waiting on, if any."""
    from agent.intake import next_question

    memory = SERVICE._memory(session_id)
    if memory.estimate is None or memory.last_asked is None:
        return None
    q = next_question(memory)
    if q is None:
        return None
    return QuestionOut(kind=q.kind, text=q.text, options=list(q.options or []),
                       field=q.field, subject=q.subject,
                       step=q.progress[0], total=q.progress[1])


def _to_response(result, session_id: Optional[str] = None) -> "AskResponse":
    """Shared shaping for every endpoint that returns an Answer."""
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
    return AskResponse(
        answer=result.answer,
        trace=trace,
        pii_found=result.pii_found,
        category=result.category,
        latency_ms=result.latency_ms,
        total_tokens=result.usage.total_tokens,
        estimated_cost_usd=result.estimated_cost_usd,
        prompt_version=result.prompt_version,
        output_report=OutputReportOut(
            grounded=getattr(report, "grounded", True),
            replaced=getattr(report, "replaced", False),
            violations=list(getattr(report, "violations", []) or []),
            notes=list(getattr(report, "notes", []) or []),
        ),
        question=_pending_question(session_id) if session_id else None,
    )


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


MAX_UPLOAD_BYTES = 12 * 1024 * 1024
ALLOWED_UPLOAD_TYPES = {"image/png", "image/jpeg", "image/webp"}


@app.post("/ask-slip", response_model=AskResponse, tags=["cost"])
async def ask_slip(
    file: UploadFile = File(..., description="Photo or scan of a doctor's request slip."),
    session_id: str = Form("default"),
) -> AskResponse:
    """Price an uploaded request slip. Pass 1: produces a report without asking anything.

    The upload is written to a temp file OUTSIDE the repository and deleted in a finally
    block. Patient documents never touch the working tree, redacted or otherwise.
    """
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(415, f"Unsupported type {file.content_type!r}. Send a PNG or JPEG.")

    payload = await file.read()
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image too large. Please send something under 12MB.")
    if not payload:
        raise HTTPException(400, "Empty upload.")

    tmp = tempfile.NamedTemporaryFile(suffix=Path(file.filename or "slip.png").suffix,
                                      delete=False)
    try:
        tmp.write(payload)
        tmp.close()
        result = SERVICE.handle_slip(tmp.name, session_id=session_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Extraction error: {exc}") from exc
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    return _to_response(result, session_id)


@app.post("/refine", response_model=AskResponse, tags=["cost"])
def refine(req: RefineRequest) -> AskResponse:
    """Answer one refine question and re-price. No re-upload."""
    from pricing.hmo import resolve_hmo_plan

    hmo = None
    if req.hmo_provider or req.hmo_plan or req.hmo_remaining_balance:
        balance = None
        if req.hmo_remaining_balance:
            try:
                balance = Decimal(req.hmo_remaining_balance.replace(",", "").strip())
            except (InvalidOperation, AttributeError):
                raise HTTPException(422, "Remaining balance must be a number.")
        hmo = resolve_hmo_plan(req.hmo_provider, req.hmo_plan, remaining_balance=balance)

    procedure_source = None
    if req.no_procedure_planned:
        procedure_source = "none_planned"
    elif req.planned_procedure:
        procedure_source = "patient"

    try:
        result = SERVICE.refine(
            session_id=req.session_id,
            hmo=hmo,
            senior_or_pwd=req.senior_or_pwd,
            procedure_source=procedure_source,
            planned_procedure=req.planned_procedure,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Refine error: {exc}") from exc
    return _to_response(result, req.session_id)


@app.post("/converse", response_model=AskResponse, tags=["cost"])
def converse(req: ConverseRequest) -> AskResponse:
    """Answer one refine question in plain language, then ask the next one."""
    try:
        result = SERVICE.converse(req.text, session_id=req.session_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Conversation error: {exc}") from exc
    return _to_response(result, req.session_id)


@app.post("/choice", response_model=AskResponse, tags=["cost"])
def choice(req: ChoiceRequest) -> AskResponse:
    """Answer the current question by picking an option. No model call."""
    try:
        result = SERVICE.answer_choice(req.kind, req.value, req.extra,
                                       session_id=req.session_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Choice error: {exc}") from exc
    return _to_response(result, req.session_id)


@app.post("/skip", response_model=AskResponse, tags=["cost"])
def skip(req: SkipRequest) -> AskResponse:
    """Move past the current question without answering it."""
    try:
        result = SERVICE.skip_question(session_id=req.session_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Skip error: {exc}") from exc
    return _to_response(result, req.session_id)


@app.get("/report.pdf", tags=["cost"])
def report_pdf(session_id: str = "default"):
    """The current estimate as a downloadable one-page PDF.

    Generated from the structured estimate, never from the prose, so the document cannot
    contain a figure the report did not.
    """
    from fastapi.responses import Response

    from report.pdf import build_pdf

    memory = SERVICE._memory(session_id)
    if memory.estimate is None:
        raise HTTPException(404, "No estimate for this session yet. Upload a slip first.")
    try:
        payload = build_pdf(memory.estimate)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Could not render the PDF: {exc}") from exc
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="dr-mundo-estimate.pdf"'},
    )


@app.post("/reset", response_model=ResetResponse, tags=["cost"])
def reset(req: ResetRequest) -> ResetResponse:
    """Clear a session's short-term memory (used by the UI's 'New chat' button)."""
    SERVICE.reset_session(req.session_id)
    return ResetResponse(session_id=req.session_id)
