"""Deterministic, fully-grounded rendering of an Answer.

Used by the output guardrail as a safe fallback: if the LLM's prose contains a number we
can't tie to a retrieved row, we throw the prose away and render from the structured
fields instead -- which are, by construction, grounded in tool results.
"""

from agent.schemas import Answer
from pricing.schemas import to_display_pesos

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


def format_budget_answer(answer: Answer) -> str:
    """Deterministic rendering of a Scope v2 budget report.

    This is the guardrail's SAFETY FALLBACK, not the patient-facing report -- it is
    deliberately plain and dependency-free so it cannot itself introduce an ungrounded
    number. The designed one-pager lives in report/.

    Every bucket is rendered even when empty-ish, because a dropped bucket is how an
    understated bill becomes invisible.
    """
    b = answer.budget
    if b is None:
        return format_answer(answer)

    p = lambda d: peso(to_display_pesos(d))  # noqa: E731 -- local shorthand, one file
    lines: list[str] = ["**Budget estimate — Makati Medical Center**", ""]
    lines.append(f"Read from your request: {b.extracted_count} item(s)")
    lines.append("")
    lines.append(f"**Prepare: {p(b.prepare_low)} – {p(b.prepare_high)}**")
    lines.append("")

    if b.priced:
        lines.append(f"Priced ({len(b.priced)}) — {p(b.gross_low)} – {p(b.gross_high)}")
        for it in b.priced:
            lines.append(f"  • {it.catalog_name}: {p(it.price_low)} – {p(it.price_high)}")
    if b.discount_low or b.discount_high:
        lines.append(f"Senior/PWD reduction: −{p(b.discount_low)} – −{p(b.discount_high)}")
    if b.philhealth_low or b.philhealth_high:
        lines.append(f"PhilHealth: −{p(b.philhealth_low)} – −{p(b.philhealth_high)}")
    if b.hmo_low or b.hmo_high:
        lines.append(f"HMO: −{p(b.hmo_low)} – −{p(b.hmo_high)}")

    if b.separate_lines:
        lines.append("")
        lines.append("Not included in the total above:")
        for s in b.separate_lines:
            unit = f" {s.unit}" if s.unit else ""
            lines.append(f"  • {s.label}: {p(s.price_low)} – {p(s.price_high)}{unit}")

    if b.unpriced:
        lines.append("")
        lines.append(f"Not priced ({len(b.unpriced)}) — MMC publishes no price; NOT in the total:")
        for it in b.unpriced:
            lines.append(f"  • {it.normalized or it.raw_text}")

    if b.needs_confirmation:
        lines.append("")
        lines.append(f"Please confirm ({len(b.needs_confirmation)}):")
        for it in b.needs_confirmation:
            lines.append(f"  • {it.raw_text}")

    if b.caveats:
        lines.append("")
        for c in b.caveats:
            lines.append(f"_{c}_")

    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def format_answer(answer: Answer) -> str:
    if answer.path == "budget_report" and answer.budget is not None:
        return format_budget_answer(answer)
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
