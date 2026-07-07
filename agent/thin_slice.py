"""Phase 5 thin slice: one covered-procedure question -> grounded answer, end to end.

Runs the real ReAct loop against gpt-4o-mini for a single question and prints the
reasoning trace + the structured, grounded Answer.

Usage:
    python -m agent.thin_slice
    python -m agent.thin_slice "How much is a C-section at Makati Med?"
"""

import sys

from agent.loop import run_agent


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "How much is an appendectomy?"
    print(f"USER: {question}\n")

    result = run_agent(question)

    print("--- REASONING TRACE ---")
    for i, step in enumerate(result.trace, 1):
        if step.thought:
            print(f"[{i}] Thought: {step.thought.strip()[:160]}")
        print(f"[{i}] Action: {step.action}({step.action_input})")
        obs = step.observation
        if isinstance(obs, list):  # search_catalog returns a ranked list
            summary = [f"{c['kind']}:{c['key']}({c['score']:.2f})" for c in obs[:3]]
        elif isinstance(obs, dict):
            summary = {k: obs[k] for k in ("status", "procedure", "service", "case_rate",
                                           "price_low", "price_high", "oop_low", "oop_high")
                       if k in obs}
        else:
            summary = obs
        print(f"[{i}] Observation: {summary}\n")

    a = result.answer
    print("--- STRUCTURED ANSWER ---")
    print(f"status={a.status} path={a.path}")
    print(f"procedure/service: {a.procedure_or_service}")
    print(f"case_rate={a.case_rate}  price={a.price_low}-{a.price_high}  "
          f"oop={a.oop_low}-{a.oop_high}  fully_covered={a.fully_covered}  as_of={a.as_of}")
    print()
    print("--- ANSWER TEXT ---")
    print(a.answer_text)


if __name__ == "__main__":
    main()
