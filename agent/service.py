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


def _describe_plan(result) -> str:
    """Tell the patient what we actually read, in their terms.

    Reading a document silently is worse than not reading it: the figures change and the
    patient has no way to tell whether we understood their booklet or invented it. Listing
    what was found is also how a misread gets caught, since they know their own plan.
    """
    plan = result.plan
    bits = []
    if plan.plan_name:
        bits.append(f"**{plan.plan_name}**")
    if plan.mbl_annual is not None:
        bits.append(f"limit ₱{plan.mbl_annual:,.0f} per illness per year")
    if plan.room_entitlement:
        bits.append(f"{plan.room_entitlement.lower()} room")
    head = "Read your benefits document: " + ", ".join(bits) + "." if bits else \
        "Read your benefits document."

    detail = []
    if plan.procedure_sublimits:
        n = len(plan.procedure_sublimits)
        detail.append(f"{n} per-procedure limit{'s' if n > 1 else ''}")
    if plan.outpatient_diagnostics_limit is not None:
        detail.append(f"an outpatient ceiling of ₱{plan.outpatient_diagnostics_limit:,.0f}")
    if plan.professional_fees_within_mbl:
        detail.append("doctors' fees drawn from the same limit")
    if detail:
        head += " I also found " + ", ".join(detail) + "."
    if not plan.has_schedule:
        head += (" It does not list per-procedure limits, so I will still treat the HMO "
                 "figure as a ceiling.")
    # Say it out loud. Silently skipping questions looks identical to a flow that forgot
    # to ask them, and the patient has no way to tell which happened.
    head += " I won't ask you about your plan again."
    return head


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
            from agent.format import format_intake_summary
            from agent.intake import next_question
            question = next_question(memory)
            memory.remember_question(question)
            answer = self._reply(estimate, "uploaded request slip", question,
                                 format_intake_summary(estimate))
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

    def handle_benefits(self, file_path, session_id: str = "default") -> ServiceResult:
        """Read an uploaded benefits document and re-price with the member's real limits.

        The second document type this accepts, and a different role from the first. A slip
        says what is being bought; a Summary of Benefits says what the plan pays for it.
        It is optional, it can arrive at any point in the conversation, and it applies to
        every estimate afterwards rather than to one.

        A document that arrives before any slip is still worth reading: the limits are
        held and the next upload is priced with them already in place.
        """
        import time as _time
        from pathlib import Path as _Path

        from agent.intake import next_question
        from pricing.estimate import estimate_from_slip
        from vision.benefits import merge_into, read_benefits

        start = _time.perf_counter()
        memory = self._memory(session_id)

        with track_usage() as usage:
            result = read_benefits(_Path(file_path))
            if not result.ok:
                answer = Answer(
                    status="no_data", path=None, query="uploaded benefits document",
                    answer_text=(
                        "I couldn't read that document. A clearer scan or the PDF itself "
                        "usually works, or just tell me your plan and limit."
                    ),
                )
                answer, report = check_output(answer)
                return ServiceResult(
                    answer=answer, category="cost", output_report=report,
                    latency_ms=int((_time.perf_counter() - start) * 1000),
                    prompt_version=self.prompt_name,
                )

            memory.hmo = merge_into(result.plan, memory.hmo)
            memory.asked.add("hmo")          # the document answered it better than we could

            if memory.slip is None:
                # No path: there is nothing priced yet, so there is no grounded budget for
                # the guard to check these figures against. They came off the patient's own
                # document, and claiming a pricing path we have not walked would invite the
                # guard to rebuild this sentence into an empty report.
                answer = Answer(status="answered", path=None,
                                query="uploaded benefits document", answer_text="")
                answer.answer_text = (_describe_plan(result)
                                      + "\n\nNow send me your doctor's request and I will "
                                        "price it against these limits.")
                answer, report = check_output(answer)
                memory.add_assistant(answer.answer_text)
                return ServiceResult(
                    answer=answer, category="cost", output_report=report,
                    latency_ms=int((_time.perf_counter() - start) * 1000),
                    prompt_version=self.prompt_name, usage=usage,
                )

            estimate = estimate_from_slip(
                memory.slip, hmo=memory.hmo,
                senior_or_pwd=bool(memory.senior_or_pwd),
                procedure_source=memory.procedure_source,
                planned_procedure=memory.planned_procedure,
                philhealth_active=memory.philhealth_active,
                hmo_covers_outpatient=memory.hmo_covers_outpatient,
                room_type=memory.room_type,
                length_of_stay=memory.length_of_stay,
            )
            memory.remember_estimate(estimate)
            question = next_question(memory)
            memory.remember_question(question)
            answer = self._reply(estimate, "uploaded benefits document", question,
                                 _describe_plan(result), hmo=memory.hmo)
            answer, report = check_output(answer)

        memory.add_user("[uploaded a benefits document]")
        memory.add_assistant(answer.answer_text)

        result_out = ServiceResult(
            answer=answer, category="cost", output_report=report,
            latency_ms=int((_time.perf_counter() - start) * 1000),
            prompt_version=self.prompt_name, usage=usage,
        )
        result_out.estimated_cost_usd = estimate_cost(usage)
        if self.enable_mlflow:
            log_service_result("[benefits upload]", result_out)
        return result_out

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

    def answer_choice(self, kind: str, value, extra=None,
                      session_id: str = "default") -> ServiceResult:
        """A widget answer. Deterministic: no model call, so a click costs nothing."""
        from agent.intake import slots_from_choice
        return self._advance(session_id, slots_from_choice(kind, value, extra),
                             asked_kind=kind, echo=str(value))

    def skip_question(self, session_id: str = "default") -> ServiceResult:
        """Move past the current question without answering it."""
        memory = self._memory(session_id)
        return self._advance(session_id, {}, asked_kind=memory.last_asked, echo="Skip")

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

        memory = self._memory(session_id)
        if memory.slip is None:
            return self._no_slip_result()
        with track_usage() as usage:
            slots = parse_answer(text, memory.last_asked)
        return self._advance(session_id, slots, asked_kind=memory.last_asked, echo=text,
                             usage=usage)

    def _advance(self, session_id: str, slots: dict, asked_kind, echo: str,
                 usage=None) -> ServiceResult:
        """Fold an answer in, re-price, and ask the next question (or finish)."""
        import time as _time

        from agent.intake import apply_answer, next_question
        from pricing.estimate import estimate_from_slip

        start = _time.perf_counter()
        memory = self._memory(session_id)
        if memory.slip is None:
            return self._no_slip_result()

        if True:
            refine_kwargs = apply_answer(memory, slots, asked_kind)

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
                philhealth_active=memory.philhealth_active,
                hmo_covers_outpatient=memory.hmo_covers_outpatient,
                room_type=memory.room_type,
                length_of_stay=memory.length_of_stay,
            )
            memory.remember_estimate(estimate)

            question = None if slots.get("wants_report") else next_question(memory)
            memory.remember_question(question)
            # An incomplete answer re-asks rather than advancing, and says what is missing
            # instead of repeating the question verbatim as though nothing happened.
            note = slots.get("_incomplete") or "Got it."
            answer = self._reply(estimate, echo, question, note)
            answer, report = check_output(answer)

        memory.add_user(echo)
        memory.add_assistant(answer.answer_text)

        result = ServiceResult(
            answer=answer, category="cost", output_report=report,
            latency_ms=int((_time.perf_counter() - start) * 1000),
            prompt_version=self.prompt_name, usage=usage or UsageTotals(),
        )
        result.estimated_cost_usd = estimate_cost(result.usage)
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

    @staticmethod
    def _reply(estimate, query: str, question, acknowledgement: str,
               hmo=None) -> Answer:
        """A question while intake is open; the priced report once it closes.

        The estimate is deliberately withheld from the Answer while questions remain, so
        no figure reaches the screen until every question has been answered. It still
        lives in session memory throughout, so the final turn and the PDF are built from
        the same object rather than a recomputed one.
        """
        from agent.format import format_budget_answer

        if question is not None:
            answer = Answer(status="answered", path="budget_report", query=query,
                            answer_text="", budget=None, hmo=hmo)
            answer.answer_text = acknowledgement + "\n\n" + question.text
            return answer

        answer = Answer(status="answered", path="budget_report", query=query,
                        answer_text="", budget=estimate)
        answer.answer_text = ("That is everything I need. Here is what to prepare.\n\n"
                              + format_budget_answer(answer))
        return answer

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
