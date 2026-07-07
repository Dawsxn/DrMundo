"""End-to-end orchestration: input guard -> memory -> ReAct loop -> output guard.

This is the one call the API (and the eval harness) use. It owns per-session memory so
follow-up questions keep context, applies the guardrails on the way in and out, and
returns the grounded Answer plus the reasoning trace and guardrail metadata.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Optional

from agent.loop import DEFAULT_PROMPT, TraceStep, run_agent
from agent.memory import SessionMemory
from agent.schemas import Answer
from guardrails.input_guard import check_input
from guardrails.output_guard import OutputReport, check_output
from monitoring.mlflow_logger import log_service_result
from monitoring.usage import UsageTotals, estimate_cost, track_usage


@dataclass
class ServiceResult:
    answer: Answer
    trace: list[TraceStep] = field(default_factory=list)
    pii_found: list[str] = field(default_factory=list)
    category: str = "cost"
    output_report: Optional[OutputReport] = None
    latency_ms: int = 0
    prompt_version: str = DEFAULT_PROMPT
    usage: UsageTotals = field(default_factory=UsageTotals)
    estimated_cost_usd: float = 0.0


class DrMundoService:
    def __init__(self, prompt_name: str = DEFAULT_PROMPT, enable_mlflow: Optional[bool] = None):
        self.prompt_name = prompt_name
        # MLflow logging is on by default; DR_MUNDO_MLFLOW=0 (or enable_mlflow=False)
        # turns it off for offline/eval runs that don't want per-call runs.
        if enable_mlflow is None:
            enable_mlflow = os.getenv("DR_MUNDO_MLFLOW", "1").lower() not in ("0", "false", "")
        self.enable_mlflow = enable_mlflow
        self._sessions: dict[str, SessionMemory] = {}

    def _memory(self, session_id: str) -> SessionMemory:
        return self._sessions.setdefault(session_id, SessionMemory())

    def reset_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def handle(self, question: str, session_id: str = "default") -> ServiceResult:
        """Answer one question, accounting token usage and (optionally) logging to MLflow.

        The monitoring wrapper is additive: it observes the request but never alters the
        Answer, so the six hard constraints are untouched."""
        with track_usage() as usage:
            result = self._handle(question, session_id)
        result.usage = usage
        result.estimated_cost_usd = estimate_cost(usage)
        if self.enable_mlflow:
            log_service_result(question, result)
        return result

    def _handle(self, question: str, session_id: str = "default") -> ServiceResult:
        start = time.perf_counter()
        memory = self._memory(session_id)

        # 1. Input guardrail: PII redaction + topic restriction.
        verdict = check_input(question)
        if not verdict.allowed:
            answer = Answer(status="out_of_scope", path=None, query=verdict.clean_text,
                            answer_text=verdict.refusal_message or "I can't help with that.")
            answer, report = check_output(answer)
            memory.add_user(verdict.clean_text)
            memory.add_assistant(answer.answer_text)
            return ServiceResult(answer=answer, pii_found=verdict.pii_found,
                                 category=verdict.category, output_report=report,
                                 latency_ms=int((time.perf_counter() - start) * 1000),
                                 prompt_version=self.prompt_name)

        # 2. Model-driven ReAct loop (with session context).
        result = run_agent(verdict.clean_text, history=memory.history(),
                           prompt_name=self.prompt_name)

        # 3. Output guardrail: grounding check + safety notes.
        answer, report = check_output(result.answer)

        # 4. Update short-term memory (redacted text only).
        memory.add_user(verdict.clean_text)
        memory.add_assistant(answer.answer_text)

        return ServiceResult(answer=answer, trace=result.trace, pii_found=verdict.pii_found,
                             category=verdict.category, output_report=report,
                             latency_ms=int((time.perf_counter() - start) * 1000),
                             prompt_version=self.prompt_name)
