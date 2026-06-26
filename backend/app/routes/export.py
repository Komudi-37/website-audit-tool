import io
import os
from xml.sax.saxutils import escape
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
    Image,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

router = APIRouter()
def _severity_colour(severity: str) -> colors.Color:
    return {
        "critical": colors.HexColor("#E53E3E"),
        "warning":  colors.HexColor("#D69E2E"),
        "info":     colors.HexColor("#3182CE"),
        "pass":     colors.HexColor("#38A169"),
    }.get(severity.lower(), colors.HexColor("#718096"))

def _build_pdf(data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=24, textColor=colors.HexColor("#1A202C"), spaceAfter=6)
    h1_style = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#2D3748"), spaceBefore=12, spaceAfter=6)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#4A5568"), spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#4A5568"), spaceAfter=4)
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#718096"))

    story = []

    # ── Cover ────────────────────────────────────────────────────────
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("Website Audit Report", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0")))
    story.append(Spacer(1, 0.4*cm))

    url = data.get("url", "N/A")
    timestamp = data.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        formatted_date = dt.strftime("%d %B %Y, %H:%M UTC")
    except Exception:
        formatted_date = timestamp

    overall_score = round(data.get("overall_score", 0), 1)

    cover_data = [
        ["Website", escape(url)],
        ["Audit Date", formatted_date],
        ["Overall Score", f"{overall_score} / 100"],
    ]
    cover_table = Table(cover_data, colWidths=[4*cm, 13*cm])
    cover_table.setStyle(TableStyle([
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",   (0, 0), (0, -1), colors.HexColor("#718096")),
        ("TEXTCOLOR",   (1, 0), (1, -1), colors.HexColor("#1A202C")),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 0.8*cm))

    # ── Scores summary ───────────────────────────────────────────────
    story.append(Paragraph("Audit Scores", h1_style))
    results = data.get("results", [])
    score_data = [["Audit Type", "Score", "Status"]]
    for r in results:
        score = round(r.get("score", 0), 1)
        status = "Good" if score >= 90 else "Needs Work" if score >= 50 else "Poor"
        score_data.append([r.get("audit_type", "").capitalize(), f"{score} / 100", status])

    score_table = Table(score_data, colWidths=[6*cm, 4*cm, 7*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#2D3748")),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.8*cm))

    # ── Screenshot ───────────────────────────────────────────────────
    for r in results:
        screenshot_path = r.get("metrics", {}).get("screenshot_path")
        if screenshot_path and os.path.exists(screenshot_path):
            story.append(Paragraph("Website Preview", h1_style))
            try:
                img = Image(screenshot_path, width=17*cm, height=9*cm)
                img.hAlign = "LEFT"
                story.append(img)
                story.append(Spacer(1, 0.8*cm))
            except Exception:
                pass
            break

    # ── Findings & Recommendations per audit ────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Detailed Findings", h1_style))

    for r in results:
        audit_type = r.get("audit_type", "").capitalize()
        score = round(r.get("score", 0), 1)
        story.append(Paragraph(f"{escape(audit_type)} — {score}/100", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0")))

        findings = r.get("findings", [])
        if findings:
            findings_data = [["Severity", "Title", "Description"]]
            for f in findings:
                sev = f.get("severity", "info")
                findings_data.append([
                    sev.capitalize(),
                    escape(f.get("title", "")),
                    Paragraph(escape(f.get("description", "")[:200]), small_style),
                ])
            f_table = Table(findings_data, colWidths=[2.5*cm, 5*cm, 9.5*cm])
            f_table.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#2D3748")),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",    (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white]),
                ("TOPPADDING",  (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(f_table)
            story.append(Spacer(1, 0.4*cm))

        recommendations = r.get("recommendations", [])
        if recommendations:
            story.append(Paragraph("Recommendations", ParagraphStyle("RecHead", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold", textColor=colors.HexColor("#2D3748"), spaceBefore=6, spaceAfter=4)))
            for i, rec in enumerate(recommendations, 1):
                story.append(Paragraph(f"{i}. {escape(rec)}", body_style))
            story.append(Spacer(1, 0.6*cm))

    # ── Footer via canvas callback ───────────────────────────────────
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(2*cm, 1.2*cm, f"Generated by WebAudit Pro — {formatted_date}")
        canvas.drawRightString(A4[0] - 2*cm, 1.2*cm, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)
    return buffer.read()
@router.post("/export/pdf")
async def export_pdf(data: dict):
    pdf_bytes = _build_pdf(data)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=audit-report.pdf"
        },
    )