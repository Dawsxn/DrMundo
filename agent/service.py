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

    # ------------------------------------------------------------------ Scope v2: slips
    def handle_slip(
        self,
        image_path,
        session_id: str = "default",
        *,
        synthetic: bool = False,
        reader=None,
    ) -> ServiceResult:
        """Price an uploaded request slip. Pass 1 of the §14 flow: asks NOTHING.

        A patient who just uploaded a slip wants a number, not an intake form. This
        produces a complete report immediately, labelled "before any HMO"; the refine
        questions come afterwards and each one re-prices through `refine` without another
        upload.
        """
        import time as _time
        from pathlib import Path as _Path

        from agent.format import format_budget_answer
        from pricing.estimate import estimate_from_slip
        from vision.extract_request import ReadFailed, read_and_extract

        start = _time.perf_counter()
        memory = self._memory(session_id)

        if reader is None:
            from vision.readers.vlm import VLMReader
            reader = VLMReader()

        with track_usage() as usage:
            try:
                slip = read_and_extract(reader, _Path(image_path), synthetic=synthetic)
            except ReadFailed as exc:
                # Never fall through to an empty estimate: "prepare P0" reads as an
                # answer, and a failed read is not one.
                answer = Answer(
                    status="no_data", path=None, query="uploaded request slip",
                    answer_text=(
                        "I couldn't read that image. Try a clearer, well-lit photo of the "
                        "whole request slip, or type the tests instead."
                    ),
                )
                answer, report = check_output(answer)
                return ServiceResult(
                    answer=answer, category="cost", output_report=report,
                    latency_ms=int((_time.perf_counter() - start) * 1000),
                    prompt_version=self.prompt_name,
                )
            memory.clear_estimate()
            memory.slip = slip
            estimate = estimate_from_slip(slip, hmo=memory.hmo,
                                          senior_or_pwd=bool(memory.senior_or_pwd))
            memory.remember_estimate(estimate)
            from agent.intake import next_question
            answer = self._answer_for(estimate, "uploaded request slip")
            body = format_budget_answer(answer)
            question = next_question(memory)
            memory.last_asked = question.kind if question else None
            answer.answer_text = (
                "\n\n".join([body, question.text]) if question else body
            )
            answer, report = check_output(answer)

        memory.add_user("[uploaded a request slip]")
        memory.add_assistant(answer.answer_text)

        result = ServiceResult(
            answer=answer, pii_found=[], category="cost", output_report=report,
            latency_ms=int((_time.perf_counter() - start) * 1000),
            prompt_version=self.prompt_name, usage=usage,
        )
        result.estimated_cost_usd = estimate_cost(usage)
        if self.enable_mlflow:
            log_service_result("[slip upload]", result)
        return result

    def refine(
        self,
        session_id: str = "default",
        *,
        hmo=None,
        senior_or_pwd: Optional[bool] = None,
        procedure_source=None,
        planned_procedure: Optional[str] = None,
    ) -> ServiceResult:
        """Re-price the slip already in memory. Pass 2 of the §14 flow.

        No re-upload: the slip and every answer given so far live in SessionMemory, so a
        patient answering "yes, Maxicare Gold" does not start over.
        """
        import time as _time

        from agent.format import format_budget_answer
        from pricing.estimate import estimate_from_slip

        start = _time.perf_counter()
        memory = self._memory(session_id)
        if memory.slip is None:
            answer = Answer(status="no_data", path=None, query="refine",
                            answer_text="Upload a request slip first and I'll price it.")
            answer, report = check_output(answer)
            return ServiceResult(answer=answer, output_report=report,
                                 prompt_version=self.prompt_name)

        if hmo is not None:
            memory.hmo = hmo
        if senior_or_pwd is not None:
            memory.senior_or_pwd = senior_or_pwd
        if procedure_source is not None:
            memory.procedure_source = procedure_source
        if planned_procedure is not None:
            memory.planned_procedure = planned_procedure

        estimate = estimate_from_slip(
            memory.slip,
            hmo=memory.hmo,
            senior_or_pwd=bool(memory.senior_or_pwd),
            procedure_source=memory.procedure_source,
            planned_procedure=memory.planned_procedure,
        )
        memory.remember_estimate(estimate)
        answer = self._answer_for(estimate, "refined estimate")
        answer.answer_text = format_budget_answer(answer)
        answer, report = check_output(answer)
        memory.add_assistant(answer.answer_text)

        return ServiceResult(
            answer=answer, category="cost", output_report=report,
            latency_ms=int((_time.perf_counter() - start) * 1000),
            prompt_version=self.prompt_name,
        )

    def converse(self, text: str, session_id: str = "default") -> ServiceResult:
        """One conversational turn of the §14 refine loop.

        The patient answers in their own words; this extracts the slots, re-prices, and
        asks the next question. Never blocks: "just show me the report" is honoured
        immediately, because a figure that arrived before every question was answered is
        still a true figure.
        """
        import time as _time

        from agent.format import format_budget_answer
        from agent.intake import apply_answer, next_question, parse_answer
        from pricing.estimate import estimate_from_slip

        start = _time.perf_counter()
        memory = self._memory(session_id)
        if memory.slip is None:
            return self._no_slip_result()

        with track_usage() as usage:
            slots = parse_answer(text, memory.last_asked)
            refine_kwargs = apply_answer(memory, slots, memory.last_asked)

            if "hmo" in refine_kwargs:
                memory.hmo = refine_kwargs["hmo"]
            if "senior_or_pwd" in refine_kwargs:
                memory.senior_or_pwd = refine_kwargs["senior_or_pwd"]
            if "procedure_source" in refine_kwargs:
                memory.procedure_source = refine_kwargs["procedure_source"]
                memory.planned_procedure = refine_kwargs.get("planned_procedure")

            estimate = estimate_from_slip(
                memory.slip,
                hmo=memory.hmo,
                senior_or_pwd=bool(memory.senior_or_pwd),
                procedure_source=memory.procedure_source,
                planned_procedure=memory.planned_procedure,
            )
            memory.remember_estimate(estimate)

            question = None if slots.get("wants_report") else next_question(memory)
            memory.last_asked = question.kind if question else None

            answer = self._answer_for(estimate, text)
            body = format_budget_answer(answer)
            answer.answer_text = (
                "\n\n".join([body, question.text]) if question else body
            )
            answer, report = check_output(answer)

        memory.add_user(text)
        memory.add_assistant(answer.answer_text)

        result = ServiceResult(
            answer=answer, category="cost", output_report=report,
            latency_ms=int((_time.perf_counter() - start) * 1000),
            prompt_version=self.prompt_name, usage=usage,
        )
        result.estimated_cost_usd = estimate_cost(usage)
        return result

    def _no_slip_result(self) -> ServiceResult:
        answer = Answer(status="no_data", path=None, query="refine",
                        answer_text="Upload a request slip first and I'll price it.")
        answer, report = check_output(answer)
        return ServiceResult(answer=answer, output_report=report,
                             prompt_version=self.prompt_name)

    @staticmethod
    def _answer_for(estimate, query: str) -> Answer:
        return Answer(status="answered", path="budget_report", query=query,
                      answer_text="", budget=estimate)

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
