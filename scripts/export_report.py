"""
SVIES — Monthly Report Exporter
Generates a PDF report of violations for a given month.

Usage:
    python scripts/export_report.py --month 2026-01
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def query_violations(month: str) -> list[dict]:
    """Query history.db for violations in the given month.

    Args:
        month: Month string in YYYY-MM format (e.g., '2026-01').

    Returns:
        List of violation dicts.
    """
    db_path = PROJECT_ROOT / "data" / "violations" / "history.db"
    if not db_path.exists():
        print(f"[WARNING] Database not found: {db_path}")
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ── Query violations for the month ──
    start_date = f"{month}-01"
    # Calculate end date (first day of next month)
    year, mon = map(int, month.split("-"))
    if mon == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{mon + 1:02d}-01"

    try:
        cursor.execute("""
            SELECT * FROM violations
            WHERE timestamp >= ? AND timestamp < ?
            ORDER BY timestamp DESC
        """, (start_date, end_date))
        rows = cursor.fetchall()
        violations = [dict(row) for row in rows]
    except sqlite3.OperationalError as e:
        print(f"[WARNING] Query error: {e}")
        violations = []
    finally:
        conn.close()

    return violations


def generate_pdf(violations: list[dict], month: str) -> str:
    """Generate a PDF report using ReportLab.

    Args:
        violations: List of violation dicts.
        month: Month string (e.g., '2026-01').

    Returns:
        Path to the generated PDF file.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
        )
    except ImportError:
        print("[ERROR] reportlab not installed. Run: pip install reportlab")
        return ""

    pdf_filename = f"monthly_report_{month}.pdf"
    pdf_path = REPORTS_DIR / pdf_filename

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=20,
        spaceAfter=20,
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=10,
        textColor=colors.grey,
    )

    elements = []

    # ── Title ──
    elements.append(Paragraph("SVIES — Monthly Violation Report", title_style))
    elements.append(Paragraph(
        f"Report Period: {month} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        subtitle_style
    ))
    elements.append(Spacer(1, 20))

    # ── Summary Statistics ──
    total = len(violations)
    critical = sum(1 for v in violations if v.get("alert_level") == "CRITICAL")
    high = sum(1 for v in violations if v.get("alert_level") == "HIGH")
    medium = sum(1 for v in violations if v.get("alert_level") == "MEDIUM")
    low = sum(1 for v in violations if v.get("alert_level") == "LOW")
    unique_plates = len(set(v.get("plate", "") for v in violations))

    summary_data = [
        ["Metric", "Value"],
        ["Total Violations", str(total)],
        ["Critical Alerts", str(critical)],
        ["High Alerts", str(high)],
        ["Medium Alerts", str(medium)],
        ["Low Alerts", str(low)],
        ["Unique Vehicles", str(unique_plates)],
    ]

    summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1f35')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f4f8')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
            colors.HexColor('#f0f4f8'), colors.white
        ]),
    ]))
    elements.append(Paragraph("Summary", styles['Heading2']))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # ── Violation Details Table ──
    if violations:
        elements.append(Paragraph("Violation Details", styles['Heading2']))

        detail_headers = ["#", "Plate", "Time", "Level", "Score", "Violations"]
        detail_data = [detail_headers]

        for i, v in enumerate(violations[:100], 1):  # Cap at 100 rows
            ts = v.get("timestamp", "")[:19]
            detail_data.append([
                str(i),
                v.get("plate", "?"),
                ts,
                v.get("alert_level", "?"),
                str(v.get("risk_score", 0)),
                (v.get("violation_types", "") or "")[:40],
            ])

        col_widths = [0.4 * inch, 1.2 * inch, 1.5 * inch, 0.8 * inch, 0.6 * inch, 2.5 * inch]
        detail_table = Table(detail_data, colWidths=col_widths, repeatRows=1)
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1f35')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
                colors.HexColor('#f0f4f8'), colors.white
            ]),
        ]))
        elements.append(detail_table)
    else:
        elements.append(Paragraph(
            "No violations found for this period.", styles['Normal']
        ))

    # ── Footer ──
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "SVIES — Smart Vehicle Intelligence & Enforcement System | SRM University AP",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8,
                      textColor=colors.grey, alignment=1)
    ))

    doc.build(elements)
    return str(pdf_path)


def main():
    parser = argparse.ArgumentParser(description="SVIES Monthly Report Exporter")
    parser.add_argument("--month", required=True,
                       help="Month in YYYY-MM format (e.g., 2026-01)")
    args = parser.parse_args()

    # ── Validate month format ──
    try:
        datetime.strptime(args.month, "%Y-%m")
    except ValueError:
        print(f"[ERROR] Invalid month format: {args.month}. Use YYYY-MM.")
        sys.exit(1)

    print("=" * 60)
    print(f"SVIES — Monthly Report: {args.month}")
    print("=" * 60)

    # ── Query violations ──
    print(f"\n[1] Querying violations for {args.month}...")
    violations = query_violations(args.month)
    print(f"    Found {len(violations)} violation(s)")

    # ── Summary stats ──
    if violations:
        total = len(violations)
        critical = sum(1 for v in violations if v.get("alert_level") == "CRITICAL")
        high = sum(1 for v in violations if v.get("alert_level") == "HIGH")
        medium = sum(1 for v in violations if v.get("alert_level") == "MEDIUM")
        low = sum(1 for v in violations if v.get("alert_level") == "LOW")
        unique = len(set(v.get("plate", "") for v in violations))

        print(f"\n    Summary:")
        print(f"      Total:    {total}")
        print(f"      Critical: {critical}")
        print(f"      High:     {high}")
        print(f"      Medium:   {medium}")
        print(f"      Low:      {low}")
        print(f"      Unique:   {unique} vehicle(s)")

    # ── Generate PDF ──
    print(f"\n[2] Generating PDF report...")
    pdf_path = generate_pdf(violations, args.month)

    if pdf_path:
        print(f"    [✓] Report saved: {pdf_path}")
    else:
        print("    [✗] PDF generation failed")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("[✓] Report export completed!")


if __name__ == "__main__":
    main()
