"""Create paginated submission PDFs from the canonical root Markdown documents.

Requires reportlab and pypdf, independently of the agent's runtime dependencies.
"""
import html
import re
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf"
OUTPUT.mkdir(parents=True, exist_ok=True)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=13, spaceAfter=7)
TITLE = ParagraphStyle("title", parent=BODY, fontSize=18, leading=22, spaceAfter=12, textColor=colors.HexColor("#183d54"))
HEADING = ParagraphStyle("heading", parent=BODY, fontSize=12, leading=15, spaceBefore=6, spaceAfter=7, fontName="Helvetica-Bold")
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8, leading=10, spaceAfter=0)
CODE = ParagraphStyle("code", fontName="Courier", fontSize=7.1, leading=10, spaceAfter=9)


def inline(text):
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r"\1", text)
    text = html.escape(text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"`(.*?)`", r'<font name="Courier">\1</font>', text)


def footer(canvas, doc):
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#657481"))
    canvas.drawString(38, 24, "NUBARA / AI AGENTIC ENGINEERING / FINAL EXAM")
    canvas.drawRightString(A4[0]-38, 24, str(doc.page))


def render(source, output, limit, split=False):
    lines = (ROOT / source).read_text(encoding="utf-8-sig").splitlines()
    flow, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            flow.append(Preformatted("\n".join(code), CODE))
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[-| :]+\|$", lines[i]):
                    rows.append([Paragraph(inline(c.strip()), CELL) for c in lines[i].strip("|").split("|")])
                i += 1
            widths = [76, 65, 99, 100, A4[0]-76-65-99-100-76]
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6eef3")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fa")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#aebfcc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            flow.extend([table, Spacer(1, 10)])
            continue
        elif line.startswith("# "):
            flow.append(Paragraph(inline(line[2:]), TITLE))
        elif line.startswith("## "):
            if split and line.startswith("## 2."):
                flow.append(PageBreak())
            flow.append(Paragraph(inline(line[3:]), HEADING))
        else:
            flow.append(Paragraph(inline(line), BODY))
        i += 1
    path = OUTPUT / output
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=38, rightMargin=38, topMargin=34, bottomMargin=38,
                      title=source, author="Nubara exam project").build(flow, onFirstPage=footer, onLaterPages=footer)
    count = len(PdfReader(path).pages)
    if count > limit:
        raise ValueError(f"{output}: {count} pages exceeds {limit}")
    print(f"{output}: {count} pages")


render("README.md", "Engineering-README.pdf", 2, split=True)
render("AI_USAGE_NOTE.md", "AI-Usage-Decision-Note.pdf", 1)
