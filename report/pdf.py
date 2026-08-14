"""Render a BudgetEstimate to a one-page PDF.

Built on ReportLab rather than an HTML-to-PDF engine: WeasyPrint needs libpango and
libcairo, which python:3.11-slim does not ship and Windows fights about. ReportLab has no
system dependencies, so this works in the container and on a laptop without a build step.

FONT NOTE: ReportLab's built-in Helvetica has no peso glyph, so every figure would render
as a black box. We register a system TTF that carries U+20B1 and fall back to spelling out
"PHP" only if none is available.

The layout follows the same rules as the HTML report (plan §11): the headline range is the
largest thing on the page, excluded costs sit outside the total, and the unpriced,
needs-confirmation and cancelled buckets are always rendered when non-empty. A bucket
quietly missing from a report is how an understated bill becomes invisible.
"""

import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from pricing.schemas import BudgetEstimate, to_display_pesos
from report.render import oldest_as_of, visible_caveats

PESO = "\u20b1"
_FONT_DIRS = [Path(r"C:\Windows\Fonts"), Path("/usr/share/fonts/truetype/dejavu"),
              Path("/usr/share/fonts/truetype/liberation")]
_CANDIDATES = [("arial.ttf", "arialbd.ttf"), ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
               ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf")]


def _register_fonts() -> tuple[str, str, bool]:
    for directory in _FONT_DIRS:
        for regular, bold in _CANDIDATES:
            if (directory / regular).exists() and (directory / bold).exists():
                try:
                    pdfmetrics.registerFont(TTFont("RptBody", str(directory / regular)))
                    pdfmetrics.registerFont(TTFont("RptBold", str(directory / bold)))
                    if pdfmetrics.getFont("RptBody").stringWidth(PESO, 12) > 0:
                        return "RptBody", "RptBold", True
                except Exception:
                    continue
    return "Helvetica", "Helvetica-Bold", False


BODY, BOLD, HAS_PESO = _register_fonts()


def peso(amount: Optional[Decimal]) -> str:
    if amount is None:
        return "n/a"
    value = f"{to_display_pesos(amount):,}"
    return f"{PESO}{value}" if HAS_PESO else f"PHP {value}"


def _styles() -> dict:
    ink = colors.HexColor("#1a1a1a")
    mute = colors.HexColor("#666666")
    return {
        "label": ParagraphStyle("label", fontName=BODY, fontSize=8, leading=11,
                                textColor=mute, spaceAfter=1),
        "headline": ParagraphStyle("headline", fontName=BOLD, fontSize=25, leading=29,
                                   textColor=ink, spaceAfter=12),
        "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=8.5, leading=12,
                             textColor=mute, spaceBefore=12, spaceAfter=4),
        "body": ParagraphStyle("body", fontName=BODY, fontSize=9, leading=12.5,
                               textColor=ink),
        "sub": ParagraphStyle("sub", fontName=BODY, fontSize=8, leading=11,
                              textColor=mute),
        "caveat": ParagraphStyle("caveat", fontName=BODY, fontSize=8, leading=11.5,
                                 textColor=colors.HexColor("#444444"), spaceAfter=3),
        "foot": ParagraphStyle("foot", fontName=BODY, fontSize=7.2, leading=10,
                               textColor=mute),
    }


def _rows_table(rows: list[tuple[str, str]], st: dict, width: float,
                bold_last: bool = False) -> Table:
    data = [[Paragraph(a, st["body"]), Paragraph(b, st["body"])] for a, b in rows]
    t = Table(data, colWidths=[width * 0.62, width * 0.38], hAlign="LEFT")
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#e3e3e3")),
    ]
    if bold_last:
        style += [("LINEABOVE", (0, -1), (-1, -1), 0.7, colors.HexColor("#333333")),
                  ("FONTNAME", (0, -1), (-1, -1), BOLD)]
    t.setStyle(TableStyle(style))
    return t


def build_pdf(estimate: BudgetEstimate, hospital: str = "Makati Medical Center") -> bytes:
    """Return the report as PDF bytes. Nothing is computed here; it all comes from the
    estimate, and every figure rounds through the same to_display_pesos the grounding
    guard uses."""
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Dr. Mundo budget estimate", author="Dr. Mundo",
    )
    w = doc.width
    story: list = []

    # Header
    header = Table(
        [[Paragraph("<b>DR. MUNDO BUDGET ESTIMATE</b>", st["body"]),
          Paragraph(hospital, st["sub"])]],
        colWidths=[w * 0.6, w * 0.4], hAlign="LEFT",
    )
    header.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header)
    story.append(HRFlowable(width="100%", thickness=1.1, color=colors.HexColor("#1a1a1a"),
                            spaceAfter=6))

    as_of = oldest_as_of(estimate)
    meta = f"Read from your request: {estimate.extracted_count} item(s)"
    if as_of:
        meta += f"  \u00b7  prices as of {as_of}"
    story.append(Paragraph(meta, st["sub"]))
    story.append(Spacer(1, 14))

    # Headline
    story.append(Paragraph("WHAT YOU'LL PAY", st["label"]))
    story.append(Paragraph(
        f"{peso(estimate.prepare_low)} &ndash; {peso(estimate.prepare_high)}", st["headline"]))

    # Priced items and deductions
    if estimate.priced:
        story.append(Paragraph(f"PRICED ({len(estimate.priced)})", st["h2"]))
        rows = [(i.catalog_name, f"{peso(i.price_low)} &ndash; {peso(i.price_high)}")
                for i in estimate.priced]
        rows.append(("<b>Subtotal</b>",
                     f"<b>{peso(estimate.gross_low)} &ndash; {peso(estimate.gross_high)}</b>"))
        story.append(_rows_table(rows, st, w, bold_last=True))

        deductions = []
        if estimate.discount_low or estimate.discount_high:
            deductions.append(("Senior citizen / PWD reduction",
                               f"&minus;{peso(estimate.discount_low)} &ndash; "
                               f"&minus;{peso(estimate.discount_high)}"))
        if estimate.philhealth_low or estimate.philhealth_high:
            deductions.append(("PhilHealth case rate",
                               f"&minus;{peso(estimate.philhealth_low)} &ndash; "
                               f"&minus;{peso(estimate.philhealth_high)}"))
        if estimate.hmo_low or estimate.hmo_high:
            marker = " \u2021" if (estimate.hmo and estimate.hmo.needs_verification_note) else ""
            deductions.append((f"HMO benefit{marker}",
                               f"&minus;{peso(estimate.hmo_low)} &ndash; "
                               f"&minus;{peso(estimate.hmo_high)}"))
        if deductions:
            story.append(Spacer(1, 4))
            story.append(_rows_table(deductions, st, w))

    # Excluded costs, visually outside the total
    if estimate.separate_lines:
        block = [Paragraph("NOT INCLUDED, ASK ABOUT THESE SEPARATELY", st["h2"])]
        rows = []
        for line in estimate.separate_lines:
            label = line.label + (f" ({line.note})" if line.note else "")
            amount = f"{peso(line.price_low)} &ndash; {peso(line.price_high)}"
            if line.unit:
                amount += f" {line.unit}"
            rows.append((label, amount))
        block.append(_rows_table(rows, st, w))
        story.append(Spacer(1, 8))
        story.append(KeepTogether(block))

    # Buckets that must never collapse
    for key, title, note in (
        ("unpriced", "NOT PRICED",
         "MMC publishes no price for these, so they are NOT in the total above."),
        ("needs_confirmation", "PLEASE CONFIRM",
         "These need a little more detail before they can be priced."),
        ("cancelled", "CROSSED OUT BY YOUR DOCTOR",
         "Not ordered, so not charged. Tell us if any of these should have been included."),
    ):
        items = getattr(estimate, key)
        if not items:
            continue
        block = [Paragraph(f"{title} ({len(items)})", st["h2"]),
                 Paragraph(note, st["sub"]), Spacer(1, 3)]
        for item in items:
            block.append(Paragraph(f"\u2022 {item.normalized or item.raw_text}", st["body"]))
        story.append(KeepTogether(block))

    caveats = visible_caveats(estimate)
    if caveats:
        story.append(Spacer(1, 12))
        for c in caveats:
            story.append(Paragraph(c, st["caveat"]))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#dddddd"),
                            spaceAfter=5))
    foot = []
    if estimate.hmo and estimate.hmo.needs_verification_note:
        foot.append("\u2021 Published figures for this plan tier, not your actual policy. "
                    "Check your own certificate.")
    foot.append("Estimates only, not a quotation. Every price traces to a Makati Medical "
                "Center catalogue item code.")
    foot.append(f"Generated {datetime.now():%d %B %Y, %H:%M}.")
    for line in foot:
        story.append(Paragraph(line, st["foot"]))

    doc.build(story)
    return buf.getvalue()
