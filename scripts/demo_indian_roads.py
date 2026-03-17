"""
SVIES — Indian Roads Demo Pipeline
Demonstrates the full SVIES pipeline on sample Indian vehicle data.
No camera or video required — uses mock data to showcase all 7 layers.

Usage:
    python scripts/demo_indian_roads.py
"""

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import config
from modules.mock_db_loader import lookup_vahan, lookup_insurance, lookup_pucc, is_stolen
from modules.fake_plate import check_fake_plate
from modules.db_intelligence import check_vehicle
from modules.risk_scorer import calculate_risk
from modules.geofence import check_zone, get_priority_multiplier
from modules.offender_tracker import log_violation, get_offender_level


def sep(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def demo_vehicle(plate: str, vehicle_type: str,
                 lat: float = 16.4812, lon: float = 80.5025):
    """Run full SVIES pipeline on a single vehicle."""
    print(f"\n{'─' * 50}")
    print(f"  PLATE: {plate}  |  TYPE: {vehicle_type}")
    print(f"{'─' * 50}")

    # Layer 4a: DB Intelligence
    db_result = check_vehicle(plate)
    vahan = lookup_vahan(plate)
    insurance = lookup_insurance(plate)
    pucc = lookup_pucc(plate)
    stolen = is_stolen(plate)

    owner = vahan.get("owner", "UNKNOWN") if vahan else "NOT REGISTERED"
    make = vahan.get("make", "?") if vahan else "?"
    state = vahan.get("state", "?") if vahan else "?"

    print(f"  Owner:     {owner}")
    print(f"  Make:      {make}")
    print(f"  State:     {state}")
    print(f"  Stolen:    {'YES' if stolen else 'No'}")
    print(f"  Insurance: {insurance.get('status', 'NOT FOUND') if insurance else 'NOT FOUND'}")
    print(f"  PUCC:      {pucc.get('status', 'NOT FOUND') if pucc else 'NOT FOUND'}")

    # Layer 2.5: Fake Plate Detection
    fake_result = check_fake_plate(
        plate_number=plate,
        detected_vehicle_type=vehicle_type,
        plate_crop=None,
        camera_id="DEMO_CAM_01",
    )
    if fake_result.is_fake:
        print(f"  Fake Plate: YES — {', '.join(fake_result.flags)}")
    else:
        print(f"  Fake Plate: No")

    # Layer 5a: Geofence Check
    zone_result = check_zone(lat, lon)
    zone_mult = 1.0
    if zone_result:
        print(f"  Zone:      {zone_result.zone_name} ({zone_result.zone_type})")
        zone_mult = get_priority_multiplier(zone_result.zone_type)
    else:
        print(f"  Zone:      None (open road)")

    # Helmet check for 2-wheelers (simulated for demo)
    helmet_violation = vehicle_type in ("MOTORCYCLE", "SCOOTER")

    # Layer 4d: Risk Scoring
    risk = calculate_risk(
        db_result=db_result,
        fake_plate_result=fake_result,
        helmet_violation=helmet_violation,
        zone_multiplier=zone_mult,
        offender_level=get_offender_level(plate),
    )
    print(f"  Violations: {', '.join(risk.all_violations) if risk.all_violations else 'None'}")
    print(f"  Risk Score: {risk.total_score} ({risk.alert_level})")

    # Layer 5b: Log to SQLite
    log_violation(
        plate=plate,
        violations=risk.all_violations,
        risk_score=risk.total_score,
        alert_level=risk.alert_level,
        zone_id=zone_result.zone_id if zone_result else "",
    )

    return risk


def main():
    print("=" * 60)
    print("  SVIES — Indian Roads Demo Pipeline")
    print("  Smart Vehicle Intelligence & Enforcement System")
    print(f"  Demo Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Layer 1: Foundation
    sep("LAYER 1: Loading Foundation")
    # Databases auto-load on import from mock_db_loader
    print(f"  Databases loaded (VAHAN, Insurance, PUCC, Stolen)")
    print(f"  Geofence zones loaded")
    print(f"  ✓ Offender tracker initialized")

    # Demo vehicles — showcasing Indian road diversity
    demo_cases = [
        # (plate, vehicle_type, description)
        ("TS09EF1234", "CAR", "Maruti Swift — Clean record"),
        ("TS06AB5678", "MOTORCYCLE", "Honda Activa — Expired insurance + PUCC"),
        ("AP28CD1234", "CAR", "Hyundai i20 — STOLEN vehicle"),
        ("TS07GH5555", "AUTO", "Bajaj RE Auto — Stolen + Expired PUCC"),
        ("UP14ER7788", "E_RICKSHAW", "Lohia Comfort — Expired insurance + PUCC"),
        ("DL01TM3344", "TEMPO", "Mahindra Bolero Pickup — Clean"),
        ("RJ19TR5566", "TRACTOR", "Mahindra 575 DI — Expired insurance + PUCC"),
        ("KA03SC9911", "SCOOTER", "Ola S1 Pro — Electric scooter"),
        ("MH12XY9999", "CAR", "FAKE: registered as motorcycle, detected as car"),
        ("XX99ZZ0000", "CAR", "Unregistered vehicle — unknown plate"),
    ]

    sep("LAYER 2-5: Processing Indian Vehicles")
    print(f"  Running full pipeline on {len(demo_cases)} vehicles...\n")

    results = []
    for plate, vtype, desc in demo_cases:
        print(f"\n  >> {desc}")
        risk = demo_vehicle(plate, vtype)
        results.append((plate, vtype, desc, risk))

    # Summary
    sep("DEMO SUMMARY")
    print(f"\n  {'Plate':<15} {'Type':<12} {'Score':>6} {'Level':<10}")
    print(f"  {'─' * 50}")
    for plate, vtype, desc, risk in results:
        level_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(risk.alert_level, "⚪")
        print(f"  {plate:<15} {vtype:<12} {risk.total_score:>5}  {level_icon} {risk.alert_level}")

    critical = sum(1 for _, _, _, r in results if r.alert_level == "CRITICAL")
    high = sum(1 for _, _, _, r in results if r.alert_level == "HIGH")
    medium = sum(1 for _, _, _, r in results if r.alert_level == "MEDIUM")
    low = sum(1 for _, _, _, r in results if r.alert_level == "LOW")

    print(f"\n  Total Vehicles Scanned: {len(results)}")
    print(f"  🔴 CRITICAL: {critical}  🟠 HIGH: {high}  🟡 MEDIUM: {medium}  🟢 LOW: {low}")

    # Check offender history
    sep("REPEAT OFFENDER CHECK")
    for plate, _, _, _ in results:
        level = get_offender_level(plate)
        if level and level > 0:
            print(f"  >> {plate}: Level {level}")

    print(f"\n{'═' * 60}")
    print("  Indian vehicle types demonstrated:")
    types_shown = set(vtype for _, vtype, _, _ in results)
    print(f"  {', '.join(sorted(types_shown))}")
    print(f"\n  Demo complete! All data logged to: {config.DB_PATH}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
