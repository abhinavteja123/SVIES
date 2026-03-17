"""
SVIES — Risk Score Engine
Layer 4: Weighted Risk Scoring
Calculates a composite risk score from all violation sources.

Score Weights:
    stolen_vehicle:      40 → CRITICAL
    fake_plate:          35 → CRITICAL
    no_registration:     25 → HIGH
    expired_insurance:   20 → HIGH
    repeat_offender:     20 → HIGH
    blacklist_zone:      15 → HIGH
    overspeeding:        15 → MEDIUM
    no_pucc:             15 → MEDIUM
    helmet_violation:    10 → MEDIUM
    seatbelt_violation:  10 → MEDIUM

Levels: 0-20=LOW, 21-40=MEDIUM, 41-60=HIGH, 61+=CRITICAL

Usage:
    python -m modules.risk_scorer
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── Import sibling modules for type references ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ══════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════

@dataclass
class RiskScore:
    """Calculated risk score with breakdown."""
    total_score: int = 0
    alert_level: str = "LOW"  # LOW / MEDIUM / HIGH / CRITICAL
    breakdown: dict[str, int] = field(default_factory=dict)
    all_violations: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════
# Score Weights (from specification)
# ══════════════════════════════════════════════════════════

RISK_WEIGHTS: dict[str, int] = {
    "STOLEN_VEHICLE": 40,
    "FAKE_PLATE": 35,
    "UNREGISTERED_VEHICLE": 25,
    "NO_REGISTRATION": 25,
    "EXPIRED_INSURANCE": 20,
    "NO_INSURANCE": 20,
    "REPEAT_OFFENDER": 20,
    "BLACKLIST_ZONE": 15,
    "OVERSPEEDING": 15,
    "EXPIRED_PUCC": 15,
    "NO_PUCC": 15,
    "HELMET_VIOLATION": 10,
    "SEATBELT_VIOLATION": 10,
    # Indian-specific violations
    "TRIPLE_RIDING": 10,          # 3+ persons on 2-wheeler (MV Act Sec 128)
    "NO_NUMBER_PLATE": 20,        # Missing/illegible plate (MV Act Sec 39)
    "WRONG_SIDE_DRIVING": 15,     # Driving against traffic
    "RED_LIGHT_VIOLATION": 15,    # Signal jumping
}


def _score_to_level(score: int) -> str:
    """Convert numeric score to alert level.

    Args:
        score: Numeric risk score.

    Returns:
        Alert level string: LOW, MEDIUM, HIGH, or CRITICAL.
    """
    if score >= 61:
        return "CRITICAL"
    elif score >= 41:
        return "HIGH"
    elif score >= 21:
        return "MEDIUM"
    else:
        return "LOW"


# ══════════════════════════════════════════════════════════
# Main Risk Calculation
# ══════════════════════════════════════════════════════════

def calculate_risk(
    db_result: Any = None,
    fake_plate_result: Any = None,
    helmet_violation: bool = False,
    seatbelt_violation: bool = False,
    in_blacklist_zone: bool = False,
    offender_level: int = 0,
    zone_multiplier: float = 1.0,
    overspeeding: bool = False,
) -> RiskScore:
    """Calculate the composite risk score for a detected vehicle.

    Aggregates scores from DB intelligence, fake plate checks,
    safety violations, zone enforcement, and repeat offender status.

    Args:
        db_result: VehicleIntelligence object (from db_intelligence.py).
        fake_plate_result: FakePlateResult object (from fake_plate.py).
        helmet_violation: True if helmet violation detected.
        seatbelt_violation: True if seatbelt violation detected.
        in_blacklist_zone: True if vehicle is in a restricted zone.
        offender_level: Repeat offender level (0=none, 1-3).
        zone_multiplier: Priority multiplier from geofence (default 1.0).

    Returns:
        RiskScore with total score, alert level, and per-violation breakdown.
    """
    score = 0
    breakdown: dict[str, int] = {}
    all_violations: list[str] = []

    # ── DB Intelligence violations ──
    if db_result is not None:
        db_violations = getattr(db_result, 'violations_found', [])
        for violation in db_violations:
            violation_upper = violation.upper()
            weight = RISK_WEIGHTS.get(violation_upper, 0)
            if weight > 0:
                score += weight
                breakdown[violation_upper] = weight
                all_violations.append(violation_upper)

    # ── Fake plate violations ──
    if fake_plate_result is not None:
        is_fake = getattr(fake_plate_result, 'is_fake', False)
        if is_fake:
            weight = RISK_WEIGHTS["FAKE_PLATE"]
            score += weight
            breakdown["FAKE_PLATE"] = weight
            all_violations.append("FAKE_PLATE")

            # ── Add individual fake plate flags for detail ──
            flags = getattr(fake_plate_result, 'flags', [])
            for flag in flags:
                all_violations.append(f"FAKE_{flag}")

    # ── Helmet violation ──
    if helmet_violation:
        weight = RISK_WEIGHTS["HELMET_VIOLATION"]
        score += weight
        breakdown["HELMET_VIOLATION"] = weight
        all_violations.append("HELMET_VIOLATION")

    # ── Seatbelt violation ──
    if seatbelt_violation:
        weight = RISK_WEIGHTS["SEATBELT_VIOLATION"]
        score += weight
        breakdown["SEATBELT_VIOLATION"] = weight
        all_violations.append("SEATBELT_VIOLATION")

    # ── Blacklist zone ──
    if in_blacklist_zone:
        weight = RISK_WEIGHTS["BLACKLIST_ZONE"]
        score += weight
        breakdown["BLACKLIST_ZONE"] = weight
        all_violations.append("BLACKLIST_ZONE")

    # ── Repeat offender ──
    if offender_level >= 2:
        weight = RISK_WEIGHTS["REPEAT_OFFENDER"]
        score += weight
        breakdown["REPEAT_OFFENDER"] = weight
        all_violations.append(f"REPEAT_OFFENDER_LEVEL_{offender_level}")

    # ── Overspeeding ──
    if overspeeding:
        weight = RISK_WEIGHTS["OVERSPEEDING"]
        score += weight
        breakdown["OVERSPEEDING"] = weight
        all_violations.append("OVERSPEEDING")

    # ── Apply zone priority multiplier ──
    if zone_multiplier > 1.0:
        original = score
        score = int(score * zone_multiplier)
        if score != original:
            breakdown["ZONE_MULTIPLIER"] = score - original

    # ── Determine alert level ──
    alert_level = _score_to_level(score)

    return RiskScore(
        total_score=score,
        alert_level=alert_level,
        breakdown=breakdown,
        all_violations=all_violations,
    )


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Risk Score Engine Test")
    print("=" * 60)

    # ── Mock data classes for testing ──
    @dataclass
    class MockDBResult:
        violations_found: list[str] = field(default_factory=list)

    @dataclass
    class MockFakePlate:
        is_fake: bool = False
        flags: list[str] = field(default_factory=list)

    # ── Test 1: LOW risk (no violations) ──
    print("\n" + "-" * 40)
    print("TEST 1: Clean vehicle (no violations)")
    risk = calculate_risk(
        db_result=MockDBResult(violations_found=[]),
        fake_plate_result=MockFakePlate(is_fake=False),
    )
    print(f"  Score: {risk.total_score}  Level: {risk.alert_level}")
    print(f"  Breakdown: {risk.breakdown}")
    assert risk.alert_level == "LOW", f"Expected LOW, got {risk.alert_level}"
    print("  [✓] PASSED")

    # ── Test 2: MEDIUM risk (expired PUCC) ──
    print("\n" + "-" * 40)
    print("TEST 2: Expired PUCC only (score=15)")
    risk = calculate_risk(
        db_result=MockDBResult(violations_found=["NO_PUCC"]),
    )
    print(f"  Score: {risk.total_score}  Level: {risk.alert_level}")
    print(f"  Breakdown: {risk.breakdown}")
    assert risk.total_score == 15, f"Expected 15, got {risk.total_score}"
    assert risk.alert_level == "LOW", f"Expected LOW (15), got {risk.alert_level}"
    print("  [✓] PASSED")

    # ── Test 3: HIGH risk (expired insurance + no PUCC + helmet) ──
    print("\n" + "-" * 40)
    print("TEST 3: Multiple violations (insurance + PUCC + helmet)")
    risk = calculate_risk(
        db_result=MockDBResult(violations_found=["EXPIRED_INSURANCE", "NO_PUCC"]),
        helmet_violation=True,
    )
    expected = 20 + 15 + 10  # 45
    print(f"  Score: {risk.total_score}  Level: {risk.alert_level}")
    print(f"  Breakdown: {risk.breakdown}")
    assert risk.total_score == expected, f"Expected {expected}, got {risk.total_score}"
    assert risk.alert_level == "HIGH", f"Expected HIGH, got {risk.alert_level}"
    print("  [✓] PASSED")

    # ── Test 4: CRITICAL risk (stolen + fake plate) ──
    print("\n" + "-" * 40)
    print("TEST 4: Stolen + fake plate (CRITICAL)")
    risk = calculate_risk(
        db_result=MockDBResult(violations_found=["STOLEN_VEHICLE"]),
        fake_plate_result=MockFakePlate(is_fake=True, flags=["TYPE_MISMATCH"]),
    )
    expected = 40 + 35  # 75
    print(f"  Score: {risk.total_score}  Level: {risk.alert_level}")
    print(f"  Breakdown: {risk.breakdown}")
    print(f"  Violations: {risk.all_violations}")
    assert risk.total_score == expected, f"Expected {expected}, got {risk.total_score}"
    assert risk.alert_level == "CRITICAL", f"Expected CRITICAL, got {risk.alert_level}"
    print("  [✓] PASSED")

    # ── Test 5: Zone multiplier ──
    print("\n" + "-" * 40)
    print("TEST 5: Zone multiplier (1.5x SCHOOL zone)")
    risk = calculate_risk(
        db_result=MockDBResult(violations_found=["EXPIRED_INSURANCE"]),
        helmet_violation=True,
        in_blacklist_zone=True,
        zone_multiplier=1.5,
    )
    base = 20 + 10 + 15  # 45
    expected = int(base * 1.5)  # 67
    print(f"  Base score:    {base}")
    print(f"  With 1.5x:     {risk.total_score} (expected ~{expected})")
    print(f"  Level:         {risk.alert_level}")
    print(f"  Breakdown:     {risk.breakdown}")
    assert risk.alert_level == "CRITICAL", f"Expected CRITICAL, got {risk.alert_level}"
    print("  [✓] PASSED")

    print("\n" + "=" * 60)
    print("[✓] All risk scorer tests completed!")
