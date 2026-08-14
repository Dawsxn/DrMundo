"""Render a Markdown document to PDF with ReportLab.

Written because the usual routes are unavailable on this machine: WeasyPrint needs
libpango and libcairo, pandoc is not installed, and there is no LibreOffice. ReportLab is,
so this is a small purpose-built converter rather than a general Markdown engine. It
handles what our documents actually contain: headings, paragraphs, bold/italic/code spans,
pipe tables, bullet and numbered lists, fenced code, block quotes and horizontal rules.

FONTS MATTER HERE. ReportLab's built-in Helvetica has no peso glyph, so every "P1,234" in
a costing document would render as a black box. We register Arial from the system, which
does carry U+20B1, and fall back to Helvetica with the peso spelled out if it is absent.

    python scripts/md_to_pdf.py TECHNICAL_WRITEUP.md
"""

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, KeepTogether, ListFlowable, ListItem, Paragraph, Preformatted,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

WIN_FONTS = Path(r"C:\Windows\Fonts")
PESO = "\u20b1"


def _register_fonts() -> tuple[str, str, str]:
    """Return (regular, bold, mono) font names, preferring ones with a peso glyph."""
    try:
        pdfmetrics.registerFont(TTFont("DocBody", str(WIN_FONTS / "arial.ttf")))
        pdfmetrics.registerFont(TTFont("DocBold", str(WIN_FONTS / "arialbd.ttf")))
        pdfmetrics.registerFont(TTFont("DocItalic", str(WIN_FONTS / "ariali.ttf")))
        pdfmetrics.registerFont(TTFont("DocMono", str(WIN_FONTS / "consola.ttf")))
        pdfmetrics.registerFontFamily("DocBody", normal="DocBody", bold="DocBold",
                                      italic="DocItalic", boldItalic="DocBold")
        if pdfmetrics.getFont("DocBody").stringWidth(PESO, 12) > 0:
            return "DocBody", "DocBold", "DocMono"
    except Exception:
        pass
    return "Helvetica", "Helvetica-Bold", "Courier"


BODY, BOLD, MONO = _register_fonts()
_HAS_PESO = BODY != "Helvetica"


def _styles() -> dict:
    ss = getSampleStyleSheet()
    base = dict(fontName=BODY, leading=14.5, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName=BOLD, fontSize=21,
                                leading=26, spaceAfter=4, textColor=colors.HexColor("#111111")),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName=BOLD, fontSize=15,
                             leading=19, spaceBefore=16, spaceAfter=6,
                             textColor=colors.HexColor("#111111")),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=BOLD, fontSize=12,
                             leading=16, spaceBefore=12, spaceAfter=4,
                             textColor=colors.HexColor("#222222")),
        "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontName=BOLD, fontSize=10.5,
                             leading=14, spaceBefore=10, spaceAfter=3,
                             textColor=colors.HexColor("#333333")),
        "body": ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.6, spaceAfter=7, **base),
        "meta": ParagraphStyle("m", parent=ss["BodyText"], fontSize=9, spaceAfter=2,
                               textColor=colors.HexColor("#555555"), **base),
        "quote": ParagraphStyle("q", parent=ss["BodyText"], fontSize=9.4, leftIndent=10,
                                borderPadding=0, textColor=colors.HexColor("#444444"),
                                fontName=BODY, leading=14, spaceAfter=7),
        "cell": ParagraphStyle("c", fontName=BODY, fontSize=8.6, leading=11.5),
        "cellhead": ParagraphStyle("ch", fontName=BOLD, fontSize=8.6, leading=11.5),
        "code": ParagraphStyle("code", fontName=MONO, fontSize=7.8, leading=10),
    }


def _inline(text: str) -> str:
    """Markdown inline spans to ReportLab markup. Order matters: escape first."""
    out = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    out = re.sub(r"`([^`]+)`", rf'<font face="{MONO}" size="8.6">\1</font>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#1a4f8a">\1</link>', out)
    if not _HAS_PESO:
        out = out.replace(PESO, "PHP ")
    return out


def _table(rows: list[list[str]], styles: dict, width: float) -> Table:
    header, *body = rows
    data = [[Paragraph(_inline(c), styles["cellhead"]) for c in header]]
    data += [[Paragraph(_inline(c), styles["cell"]) for c in r] for r in body]

    ncols = max(len(r) for r in data)
    data = [r + [Paragraph("", styles["cell"])] * (ncols - len(r)) for r in data]
    # First column carries the labels and needs the room; the rest share what is left.
    first = width * (0.42 if ncols > 2 else 0.55)
    rest = (width - first) / max(1, ncols - 1)

    t = Table(data, colWidths=[first] + [rest] * (ncols - 1), repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.9, colors.HexColor("#333333")),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def convert(md_path: Path, pdf_path: Path) -> None:
    styles = _styles()
    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=md_path.stem.replace("_", " ").title(), author="Dr. Mundo team",
    )
    avail = doc.width
    story: list = []
    lines = md_path.read_text(encoding="utf-8").splitlines()

    i = 0
    seen_title = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # fenced code
        if stripped.startswith("```"):
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            # Keep diagrams whole: an ASCII pipeline split across a page break is
            # unreadable, and these blocks are short enough to always fit on one page.
            story.append(KeepTogether([
                Spacer(1, 3),
                Preformatted("\n".join(block), styles["code"]),
                Spacer(1, 7),
            ]))
            continue

        # pipe table
        if stripped.startswith("|") and i + 1 < len(lines) and set(
                lines[i + 1].strip().replace("|", "").replace(" ", "")) <= set("-:"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not set("".join(cells).replace(" ", "")) <= set("-:"):
                    rows.append(cells)
                i += 1
            story.append(Spacer(1, 3))
            story.append(_table(rows, styles, avail))
            story.append(Spacer(1, 9))
            continue

        # horizontal rule
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            story.append(Spacer(1, 5))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#cccccc")))
            story.append(Spacer(1, 7))
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level, text = len(m.group(1)), m.group(2)
            if level == 1 and not seen_title:
                story.append(Paragraph(_inline(text), styles["title"]))
                seen_title = True
            else:
                story.append(Paragraph(_inline(text), styles[f"h{min(level, 3)}"]))
            i += 1
            continue

        # block quote
        if stripped.startswith(">"):
            block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip(">").strip())
                i += 1
            story.append(Paragraph(_inline(" ".join(block)), styles["quote"]))
            continue

        # lists
        if re.match(r"^[-*+]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
            ordered = bool(re.match(r"^\d+[.)]\s+", stripped))
            items = []
            while i < len(lines):
                s = lines[i].strip()
                m2 = re.match(r"^(?:[-*+]|\d+[.)])\s+(.*)$", s)
                if not m2:
                    break
                items.append(ListItem(Paragraph(_inline(m2.group(1)), styles["body"]),
                                      leftIndent=12))
                i += 1
            story.append(ListFlowable(items, bulletType="1" if ordered else "bullet",
                                      start="1" if ordered else None,
                                      bulletFontName=BODY, leftIndent=14))
            story.append(Spacer(1, 4))
            continue

        # paragraph: gather until a blank line or a structural marker
        block = []
        while i < len(lines):
            s = lines[i].strip()
            if (not s or s.startswith(("#", "|", ">", "```"))
                    or re.fullmatch(r"-{3,}", s)
                    or re.match(r"^(?:[-*+]|\d+[.)])\s+", s)):
                break
            block.append(s)
            i += 1
        # A run of lines that each open with a bold label is a metadata block
        # ("**Course:** ...", "**Team:** ..."). Joining those with spaces produces one
        # run-on line, so keep the authored line breaks.
        label_block = len(block) > 1 and all(b.startswith("**") for b in block)
        if label_block:
            story.append(Paragraph("<br/>".join(_inline(b) for b in block), styles["meta"]))
        else:
            story.append(Paragraph(_inline(" ".join(block)), styles["body"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(BODY, 7.5)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawRightString(A4[0] - 20 * mm, 11 * mm, f"{doc.page}")
    canvas.drawString(20 * mm, 11 * mm, "Dr. Mundo, STAI100 Final Capstone")
    canvas.restoreState()


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "TECHNICAL_WRITEUP.md")
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".pdf")
    convert(src, dst)
    print(f"wrote {dst} ({dst.stat().st_size / 1024:.0f} KB)")
