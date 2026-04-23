"""
SVIES — Repeated Offender Intelligence Module
Layer 5.5: Offender Tracking & Escalation

Delegates all database operations to the unified Supabase layer (api.database).

Usage:
    python -m modules.offender_tracker
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import REPORTS_DIR

# ── Import the unified database layer ──
from api.database import db


def log_violation(plate: str, violations: list[str], risk_score: int,
                  zone_id: str = "", alert_level: str = "LOW",
                  **kwargs) -> str:
    """Log a violation to the database. Returns SHA-256 hash."""
    return db.log_violation(
        plate, violations, risk_score, zone_id, alert_level,
        vehicle_type=kwargs.get("vehicle_type", ""),
        owner_name=kwargs.get("owner_name", ""),
        model_used=kwargs.get("model_used", ""),
        captured_image=kwargs.get("captured_image", ""),
        annotated_image=kwargs.get("annotated_image", ""),
    )


def get_offender_level(plate: str, **_kwargs) -> int:
    """Get offender level: 0=none, 1=1-2, 2=3-5, 3=6+."""
    return db.get_offender_level(plate)


def get_violation_history(plate: str, days: int = 30, **_kwargs) -> list[dict]:
    """Get violation history for a plate within a time window."""
    return db.get_violation_history(plate, days)


def get_all_violations(days: int = 30, **_kwargs) -> list[dict]:
    """Get all violations within a time window."""
    result = db.get_violations(days=days, per_page=9999)
    return result.get("violations", [])


def get_top_offenders(limit: int = 10, days: int = 30, **_kwargs) -> list[dict]:
    """Get top repeat offenders by violation count."""
    return db.get_top_offenders(limit, days)


def generate_court_summons(plate: str, owner_name: str, violations_history: list[dict]) -> str:
    """Generate a court summons PDF using ReportLab."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filepath = REPORTS_DIR / f"court_summons_{plate}_{date_str}.pdf"
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

        doc = SimpleDocTemplate(
            str(filepath), pagesize=A4,
            topMargin=25*mm, bottomMargin=25*mm,
            leftMargin=20*mm, rightMargin=20*mm,
        )
        elements = []
        styles = getSampleStyleSheet()

        # ── Custom cell styles ──
        cell_sm  = ParagraphStyle('CellSm',  parent=styles['Normal'], fontSize=7, leading=9,  wordWrap='CJK', alignment=TA_LEFT)
        cell_ctr = ParagraphStyle('CellCtr', parent=styles['Normal'], fontSize=7, leading=9,  alignment=TA_CENTER)
        th_style = ParagraphStyle('TH',      parent=styles['Normal'], fontSize=8, leading=10,
                                  fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER)

        # ── Page header ──
        elements.append(Paragraph("SVIES — Court Summons Notice", styles['Title']))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1a1a2e')))
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph(f"<b>Vehicle:</b> {plate}", styles['Normal']))
        elements.append(Paragraph(f"<b>Owner:</b> {owner_name or 'Unknown'}", styles['Normal']))
        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        elements.append(Paragraph(f"<b>Total Violations:</b> {len(violations_history)}", styles['Normal']))
        elements.append(Spacer(1, 8*mm))

        # Column widths: #=10, Date=34, Violations=80, Score=18, Level=28 → 170mm (= A4 - 2×20mm margins)
        COL_W = [10*mm, 34*mm, 80*mm, 18*mm, 28*mm]

        # ── Table header ──
        data = [[
            Paragraph("#", th_style),
            Paragraph("Date", th_style),
            Paragraph("Violations", th_style),
            Paragraph("Score", th_style),
            Paragraph("Level", th_style),
        ]]

        # ── Data rows ──
        LEVEL_COLORS = {
            'CRITICAL': '#dc2626', 'HIGH': '#ea580c',
            'MEDIUM': '#d97706',   'LOW':  '#16a34a',
        }
        for i, v in enumerate(violations_history[:20], 1):
            raw   = (v.get("violation_types", "") or "").replace(",", "\n").strip()
            level = v.get("alert_level", "LOW")
            lc    = LEVEL_COLORS.get(level, '#333333')
            data.append([
                Paragraph(str(i), cell_ctr),
                Paragraph(v.get("timestamp", "")[:19].replace("T", " "), cell_ctr),
                Paragraph(raw, cell_sm),
                Paragraph(str(v.get("risk_score", 0)), cell_ctr),
                Paragraph(f'<font color="{lc}"><b>{level}</b></font>', cell_ctr),
            ])

        # ── Table style ──
        ts = [
            ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
            ('LINEBELOW',     (0, 0), (-1, 0),  1.5, colors.HexColor('#1a1a2e')),
        ]
        for r in range(2, len(data), 2):          # alternating row shading
            ts.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#F5F5F5')))

        t = Table(data, colWidths=COL_W, repeatRows=1)
        t.setStyle(TableStyle(ts))
        elements.append(t)
        elements.append(Spacer(1, 10*mm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph(
            "The registered owner is <b>summoned</b> to appear before the designated "
            "Traffic Court within <b>15 days</b> of this notice. "
            "Failure to appear may result in further legal action.",
            styles['Normal'],
        ))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(
            f"<i>Generated by SVIES — Smart Vehicle Intelligence &amp; Enforcement System "
            f"| {datetime.now().strftime('%d-%m-%Y %H:%M')}</i>",
            ParagraphStyle('Note', parent=styles['Normal'], fontSize=7, textColor=colors.grey),
        ))
        doc.build(elements)
        print(f"[PDF] Court summons: {filepath}")
        return str(filepath)
    except ImportError:
        txt = filepath.with_suffix('.txt')
        with open(txt, 'w') as f:
            f.write(f"COURT SUMMONS — {plate}\nOwner: {owner_name}\nViolations: {len(violations_history)}\n")
        return str(txt)
    except Exception as e:
        print(f"[ERROR] PDF generation failed: {e}")
        return ""


if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Offender Tracker Test (Supabase)")
    print("=" * 60)
    print(f"  Backend: {db.backend}")
    print("  [✓] Module loaded successfully!")
