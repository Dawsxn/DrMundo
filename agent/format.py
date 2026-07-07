"""Deterministic, fully-grounded rendering of an Answer.

Used by the output guardrail as a safe fallback: if the LLM's prose contains a number we
can't tie to a retrieved row, we throw the prose away and render from the structured
fields instead -- which are, by construction, grounded in tool results.
"""

from agent.schemas import Answer

DISCLAIMER = (
    "Estimates only — not medical or financial advice. Price ranges are indicative and "
    "may exclude professional fees, medicines, and room charges."
)


def peso(value) -> str:
    return f"₱{value:,.0f}" if value is not None else "n/a"


def _scope_line(answer: Answer) -> str:
    if answer.hospital:
        return f"at {answer.hospital}"
    n = len(answer.hospitals or [])
    return f"across {n} hospitals" if n else ""


def _oop_text(answer: Answer) -> str:
    if answer.fully_covered:
        return "PhilHealth may fully cover this (case rate meets or exceeds the price range)."
    if answer.oop_low == 0 and (answer.oop_high or 0) > 0:
        return (f"{peso(0)} at the low end up to {peso(answer.oop_high)} at the high end "
                "(may be fully covered at the low end)")
    if answer.oop_low is not None and answer.oop_high is not None:
        return f"{peso(answer.oop_low)} – {peso(answer.oop_high)}"
    return "n/a"


def format_answer(answer: Answer) -> str:
    if answer.status != "answered" or answer.path is None:
        # refusals / clarifications / no-data already carry their own message.
        text = answer.answer_text.strip()
        return text if DISCLAIMER in text else f"{text}\n\n{DISCLAIMER}"

    lines: list[str] = []
    scope = _scope_line(answer)

    if answer.path == "covered":
        lines.append(f"**{answer.procedure_or_service}** {scope}".rstrip())
        if answer.price_low is None:
            lines.append(f"- PhilHealth case rate: {peso(answer.case_rate)}")
            lines.append("- No hospital price is on file for this procedure yet.")
        else:
            lines.append(f"- Hospital price range: {peso(answer.price_low)} – {peso(answer.price_high)}")
            lines.append(f"- PhilHealth case rate: {peso(answer.case_rate)}")
            lines.append(f"- Estimated out-of-pocket: {_oop_text(answer)}")
    else:  # outpatient
        lines.append(f"**{answer.procedure_or_service}** {scope}".rstrip())
        lines.append(f"- Price range: {peso(answer.price_low)} – {peso(answer.price_high)}")
        lines.append("- Not covered by PhilHealth (no case rate or out-of-pocket).")

    if answer.hospitals and not answer.hospital:
        lines.append("")
        lines.append("Per hospital:")
        for h in answer.hospitals:
            label = h.hospital
            rng = f"{peso(h.price_low)} – {peso(h.price_high)}"
            lines.append(f"  • {label}: {rng}")

    if answer.as_of:
        lines.append("")
        lines.append(f"_As of {answer.as_of}._")
    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)
