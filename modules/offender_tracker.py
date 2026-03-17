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
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(str(filepath), pagesize=A4, topMargin=25*mm, bottomMargin=25*mm)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("SVIES — Court Summons Notice", styles['Title']))
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(f"<b>Vehicle:</b> {plate}", styles['Normal']))
        elements.append(Paragraph(f"<b>Owner:</b> {owner_name}", styles['Normal']))
        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        elements.append(Paragraph(f"<b>Total Violations:</b> {len(violations_history)}", styles['Normal']))
        elements.append(Spacer(1, 8*mm))
        data = [["#", "Date", "Violations", "Score", "Level"]]
        for i, v in enumerate(violations_history[:15], 1):
            data.append([str(i), v.get("timestamp", "")[:19], v.get("violation_types", ""),
                        str(v.get("risk_score", 0)), v.get("alert_level", "")])
        t = Table(data, colWidths=[15*mm, 40*mm, 60*mm, 20*mm, 20*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            "The registered owner is summoned to appear before the designated Traffic Court within 15 days.",
            styles['Normal']))
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
