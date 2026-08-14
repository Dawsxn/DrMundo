"""Model-driven ReAct tool-calling loop.

Thought -> Action (tool call) -> Observation -> repeat (capped) -> Final Answer.

The LLM decides which tool to call from each observation. Crucially, the NUMBERS in the
final structured Answer are filled from the tool observations (the "grounding"), not from
the model's prose -- so figures can never be invented. The model only writes the
natural-language explanation. Every step is recorded in a trace for the UI + MLflow.
"""

import json
from dataclasses import dataclass, field
from typing import Optional

from agent.prompts import load_prompt
from agent.schemas import Answer, HospitalBreakdown
from agent.tools import TOOL_SCHEMAS, execute_tool
from config import CHAT_MODEL, get_openai_client

MAX_ITERS = 5
# system_v2 is the production default: the Phase 9b ablation showed it best-balanced
# (94% pass, 100% coverage/OOP correctness, cheaper than v1). See eval/ and HANDOFF/write-up.
DEFAULT_PROMPT = "system_v2"


@dataclass
class TraceStep:
    thought: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[dict] = None
    observation: Optional[dict] = None


@dataclass
class AgentResult:
    answer: Answer
    trace: list[TraceStep] = field(default_factory=list)
    raw_messages: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------- grounding -> Answer
def _grounding_to_answer(question: str, grounding: dict, answer_text: str) -> Answer:
    """Assemble the structured Answer from a successful pricing observation."""
    hospitals = None
    if grounding.get("hospitals"):
        hospitals = [HospitalBreakdown(**h) for h in grounding["hospitals"]]
    hosp = grounding.get("hospital")
    hosp_name = hosp["hospital"] if isinstance(hosp, dict) else hosp

    if grounding["kind"] == "covered":
        return Answer(
            status="answered",
            path="covered",
            query=question,
            answer_text=answer_text,
            procedure_or_service=grounding.get("procedure"),
            hospital=hosp_name,
            case_rate=grounding.get("case_rate"),
            price_low=grounding.get("price_low"),
            price_high=grounding.get("price_high"),
            oop_low=grounding.get("oop_low"),
            oop_high=grounding.get("oop_high"),
            fully_covered=grounding.get("fully_covered"),
            hospitals=hospitals,
            as_of=grounding.get("as_of"),
        )
    return Answer(
        status="answered",
        path="outpatient",
        query=question,
        answer_text=answer_text,
        procedure_or_service=grounding.get("service"),
        hospital=hosp_name,
        price_low=grounding.get("price_low"),
        price_high=grounding.get("price_high"),
        hospitals=hospitals,
        as_of=grounding.get("as_of"),
    )


def _is_pricing_grounding(name: str, obs: dict) -> bool:
    return name in ("get_covered_cost", "get_outpatient_cost") and obs.get("status") == "ok"


def _grounding_rank(obs: dict) -> tuple[bool, int]:
    """Richness of a pricing observation: prefer ones that actually have hospital prices,
    then more hospitals. Lets us keep the best grounding when the model makes several
    pricing calls (e.g. exploring procedure variants), instead of just the last one."""
    has_prices = obs.get("price_low") is not None
    return has_prices, len(obs.get("hospitals") or [])


# ---------------------------------------------------------------- the loop
def run_agent(question: str, history: Optional[list[dict]] = None,
              prompt_name: str = DEFAULT_PROMPT, max_iters: int = MAX_ITERS) -> AgentResult:
    client = get_openai_client()
    messages: list[dict] = [{"role": "system", "content": load_prompt(prompt_name)}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    trace: list[TraceStep] = []
    grounding: Optional[dict] = None

    for _ in range(max_iters):
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0,
        )
        msg = resp.choices[0].message

        # No tool call -> the model produced its final natural-language answer.
        if not msg.tool_calls:
            answer_text = msg.content or ""
            if grounding is not None:
                answer = _grounding_to_answer(question, grounding, answer_text)
            else:
                # No pricing data was retrieved (refusal / out-of-scope / no data).
                answer = Answer(status="answered", path=None, query=question,
                                answer_text=answer_text)
            messages.append({"role": "assistant", "content": answer_text})
            return AgentResult(answer=answer, trace=trace, raw_messages=messages)

        # Record the assistant turn (with its tool calls) verbatim for the next round.
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            observation = execute_tool(name, args)
            trace.append(TraceStep(thought=msg.content, action=name,
                                   action_input=args, observation=observation))

            # ask_user -> stop and surface the clarifying question.
            if name == "ask_user":
                answer = Answer(status="needs_clarification", path=None, query=question,
                                answer_text=observation.get("question", "Could you clarify?"))
                return AgentResult(answer=answer, trace=trace, raw_messages=messages)

            if _is_pricing_grounding(name, observation):
                if grounding is None or _grounding_rank(observation) > _grounding_rank(grounding):
                    grounding = observation

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(observation, default=str),
            })

    # Hit the iteration cap without a final answer.
    fallback = Answer(status="no_data", path=None, query=question,
                      answer_text="I couldn't complete that request. Please try rephrasing.")
    return AgentResult(answer=fallback, trace=trace, raw_messages=messages)
