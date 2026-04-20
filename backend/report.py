"""
report.py

Fixes vs original:
  • Creates reports/ directory if it doesn't exist (crashed silently before)
  • Adds timestamp to avoid overwriting the previous report
  • Adds all recent accident images, not just the first
  • Adds a proper title page with date/time
  • FIXED: generate_accident_report now accepts (ids, all_alerts) as called
    by main.py — the old signature (frames, accidents, risk) was completely
    wrong and would crash every time /download-accident-report was hit.
"""

import os
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

REPORTS_DIR   = "backend/reports"
ACCIDENTS_DIR = "backend/accidents"
MAX_IMAGES    = 5   # how many recent snapshots to embed

os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_report(frames: int, accidents: int, risk: str) -> str:
    """
    Build a summary PDF report and return its file path.
    """
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"traffic_report_{ts}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, filename)

    doc    = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        "SubHeading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1a56db"),
        spaceBefore=12,
        spaceAfter=4,
    )
    body_style = styles["Normal"]
    body_style.fontSize = 11
    body_style.leading  = 18

    risk_color = "#dc2626" if risk == "HIGH" else "#16a34a"
    risk_style = ParagraphStyle(
        "Risk",
        parent=styles["Normal"],
        fontSize=13,
        textColor=colors.HexColor(risk_color),
        fontName="Helvetica-Bold",
    )

    elements = []

    elements.append(Paragraph("Smart City Traffic AI Report", title_style))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}",
        styles["Normal"],
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Summary", sub_style))
    elements.append(Paragraph(f"Frames processed:   {frames:,}", body_style))
    elements.append(Paragraph(f"Accidents detected: {accidents}", body_style))
    elements.append(Paragraph(f"Risk level: {risk}", risk_style))
    elements.append(Spacer(1, 12))

    if os.path.exists(ACCIDENTS_DIR):
        images = sorted(
            [f for f in os.listdir(ACCIDENTS_DIR) if f.endswith(".jpg")],
            reverse=True,
        )[:MAX_IMAGES]

        if images:
            elements.append(Paragraph("Accident Snapshots", sub_style))
            elements.append(HRFlowable(width="100%", thickness=0.5,
                                       color=colors.lightgrey))
            elements.append(Spacer(1, 8))

            for img_name in images:
                img_path = os.path.join(ACCIDENTS_DIR, img_name)
                try:
                    elements.append(Image(img_path, width=440, height=270))
                    elements.append(Paragraph(img_name, styles["Caption"]))
                    elements.append(Spacer(1, 10))
                except Exception as e:
                    print(f"[report] ⚠ Could not embed {img_name}: {e}")

    doc.build(elements)
    print(f"[report] 📄 Report saved: {pdf_path}")
    return pdf_path


# ── FIX: generate_accident_report now accepts (ids, all_alerts) ───────────────
# Old broken signature was (frames, accidents, risk) — completely mismatched
# with how main.py calls it: generate_accident_report(ids, all_alerts)
def generate_accident_report(ids: list, all_alerts: list) -> str:
    """
    Build a per-accident PDF report for the given alert IDs.
    Filters all_alerts to only the requested ids, then renders a PDF
    with details + snapshots for each matched accident.
    """
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    ids_str  = "_".join(str(i) for i in ids[:4]) if ids else "all"
    filename = f"accident_report_{ids_str}_{ts}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, filename)

    doc    = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        "SubHeading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#dc2626"),
        spaceBefore=14,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=18,
    )

    # Filter alerts — if ids list is empty, include all
    if ids:
        matched = [a for a in all_alerts if a.get("id") in ids]
    else:
        matched = list(all_alerts)

    elements = []
    elements.append(Paragraph("Smart City Traffic AI — Accident Report", title_style))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}",
        styles["Normal"],
    ))
    elements.append(Paragraph(
        f"Total accidents in this report: {len(matched)}",
        styles["Normal"],
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    elements.append(Spacer(1, 12))

    if not matched:
        elements.append(Paragraph("No matching accident records found.", body_style))
    else:
        for a in matched:
            elements.append(Paragraph(
                f"Accident #{a.get('id')} — {a.get('camera_name', 'Unknown')}",
                sub_style,
            ))
            elements.append(HRFlowable(width="100%", thickness=0.5,
                                       color=colors.lightgrey))
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(f"Camera ID : CAM-{a.get('camera_id', '?')}", body_style))
            elements.append(Paragraph(f"Date      : {a.get('date', 'N/A')}", body_style))
            elements.append(Paragraph(f"Time      : {a.get('time', 'N/A')}", body_style))
            lat = a.get("lat", 0.0)
            lon = a.get("lon", 0.0)
            elements.append(Paragraph(f"Location  : {lat:.5f}°, {lon:.5f}°", body_style))
            map_link = f"https://maps.google.com/?q={lat},{lon}"
            elements.append(Paragraph(
                f'<link href="{map_link}">View on Google Maps</link>',
                body_style,
            ))
            elements.append(Spacer(1, 8))

            # Embed snapshot if it exists
            snap = a.get("snapshot")
            if snap:
                # snapshot may be stored as filename only or full path
                img_path = snap if os.path.isabs(snap) else os.path.join(ACCIDENTS_DIR, snap)
                if os.path.exists(img_path):
                    try:
                        elements.append(Image(img_path, width=440, height=270))
                        elements.append(Paragraph(os.path.basename(img_path), styles["Caption"]))
                    except Exception as e:
                        print(f"[report] ⚠ Could not embed snapshot {img_path}: {e}")
                else:
                    elements.append(Paragraph(f"[Snapshot not found: {snap}]", body_style))

            elements.append(Spacer(1, 16))

    doc.build(elements)
    print(f"[report] 📄 Accident report saved: {pdf_path}")
    return pdf_path