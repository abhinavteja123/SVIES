"""
SVIES — Risk Scorer Unit Tests
Tests the weighted risk scoring engine in modules/risk_scorer.py.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.risk_scorer import calculate_risk, RISK_WEIGHTS, _score_to_level, RiskScore
from tests.conftest import MockDBResult, MockFakePlateResult


# ══════════════════════════════════════════════════════════
# _score_to_level thresholds
# ══════════════════════════════════════════════════════════

class TestScoreToLevel:
    """Boundary tests for numeric-score → alert-level mapping."""

    def test_zero_is_low(self):
        assert _score_to_level(0) == "LOW"

    def test_twenty_is_low(self):
        assert _score_to_level(20) == "LOW"

    def test_twenty_one_is_medium(self):
        assert _score_to_level(21) == "MEDIUM"

    def test_forty_is_medium(self):
        assert _score_to_level(40) == "MEDIUM"

    def test_forty_one_is_high(self):
        assert _score_to_level(41) == "HIGH"

    def test_sixty_is_high(self):
        assert _score_to_level(60) == "HIGH"

    def test_sixty_one_is_critical(self):
        assert _score_to_level(61) == "CRITICAL"

    def test_large_value_is_critical(self):
        assert _score_to_level(500) == "CRITICAL"


# ══════════════════════════════════════════════════════════
# calculate_risk — basic scenarios
# ══════════════════════════════════════════════════════════

class TestCalculateRiskBasic:
    """Tests for individual and combined violation scenarios."""

    def test_clean_vehicle_scores_zero(self, clean_db_result, clean_plate):
        risk = calculate_risk(db_result=clean_db_result, fake_plate_result=clean_plate)
        assert risk.total_score == 0
        assert risk.alert_level == "LOW"
        assert risk.breakdown == {}
        assert risk.all_violations == []

    def test_no_arguments_scores_zero(self):
        risk = calculate_risk()
        assert risk.total_score == 0
        assert risk.alert_level == "LOW"

    def test_single_db_violation_no_pucc(self):
        db = MockDBResult(violations_found=["NO_PUCC"])
        risk = calculate_risk(db_result=db)
        assert risk.total_score == 15
        assert risk.alert_level == "LOW"
        assert risk.breakdown == {"NO_PUCC": 15}
        assert "NO_PUCC" in risk.all_violations

    def test_single_db_violation_expired_insurance(self):
        db = MockDBResult(violations_found=["EXPIRED_INSURANCE"])
        risk = calculate_risk(db_result=db)
        assert risk.total_score == 20
        assert risk.alert_level == "LOW"

    def test_multiple_db_violations_sum_correctly(self, expired_docs_db_result):
        risk = calculate_risk(db_result=expired_docs_db_result)
        expected = RISK_WEIGHTS["EXPIRED_PUCC"] + RISK_WEIGHTS["EXPIRED_INSURANCE"]  # 15+20=35
        assert risk.total_score == expected
        assert risk.alert_level == "MEDIUM"

    def test_stolen_vehicle_is_high_score(self, stolen_db_result):
        risk = calculate_risk(db_result=stolen_db_result)
        assert risk.total_score == 40
        assert risk.alert_level == "MEDIUM"  # 40 -> MEDIUM (21-40)
        assert "STOLEN_VEHICLE" in risk.all_violations

    def test_unregistered_vehicle_all_flags(self, unregistered_db_result):
        risk = calculate_risk(db_result=unregistered_db_result)
        expected = 25 + 15 + 20  # UNREGISTERED + NO_PUCC + NO_INSURANCE
        assert risk.total_score == expected
        assert risk.alert_level == "HIGH"  # 60 -> HIGH

    def test_unknown_violation_ignored(self):
        db = MockDBResult(violations_found=["SOME_UNKNOWN_VIOLATION"])
        risk = calculate_risk(db_result=db)
        assert risk.total_score == 0
        assert risk.alert_level == "LOW"


# ══════════════════════════════════════════════════════════
# calculate_risk — fake plate
# ══════════════════════════════════════════════════════════

class TestFakePlate:

    def test_fake_plate_adds_weight(self, fake_plate):
        risk = calculate_risk(fake_plate_result=fake_plate)
        assert risk.total_score == 35
        assert "FAKE_PLATE" in risk.all_violations

    def test_fake_plate_flags_in_all_violations(self, fake_plate):
        risk = calculate_risk(fake_plate_result=fake_plate)
        assert "FAKE_TYPE_MISMATCH" in risk.all_violations
        assert "FAKE_FORMAT_INVALID" in risk.all_violations

    def test_clean_plate_no_penalty(self, clean_plate):
        risk = calculate_risk(fake_plate_result=clean_plate)
        assert risk.total_score == 0

    def test_stolen_plus_fake_is_critical(self, stolen_db_result, fake_plate):
        risk = calculate_risk(db_result=stolen_db_result, fake_plate_result=fake_plate)
        expected = 40 + 35  # 75
        assert risk.total_score == expected
        assert risk.alert_level == "CRITICAL"


# ══════════════════════════════════════════════════════════
# calculate_risk — boolean violations
# ══════════════════════════════════════════════════════════

class TestBooleanViolations:

    def test_helmet_violation(self):
        risk = calculate_risk(helmet_violation=True)
        assert risk.total_score == 10
        assert "HELMET_VIOLATION" in risk.all_violations

    def test_seatbelt_violation(self):
        risk = calculate_risk(seatbelt_violation=True)
        assert risk.total_score == 10
        assert "SEATBELT_VIOLATION" in risk.all_violations

    def test_blacklist_zone(self):
        risk = calculate_risk(in_blacklist_zone=True)
        assert risk.total_score == 15
        assert "BLACKLIST_ZONE" in risk.all_violations

    def test_overspeeding(self):
        risk = calculate_risk(overspeeding=True)
        assert risk.total_score == 15
        assert "OVERSPEEDING" in risk.all_violations

    def test_all_boolean_violations_combined(self):
        risk = calculate_risk(
            helmet_violation=True,
            seatbelt_violation=True,
            in_blacklist_zone=True,
            overspeeding=True,
        )
        expected = 10 + 10 + 15 + 15  # 50
        assert risk.total_score == expected
        assert risk.alert_level == "HIGH"


# ══════════════════════════════════════════════════════════
# calculate_risk — repeat offender
# ══════════════════════════════════════════════════════════

class TestRepeatOffender:

    def test_offender_level_0_no_penalty(self):
        risk = calculate_risk(offender_level=0)
        assert risk.total_score == 0

    def test_offender_level_1_no_penalty(self):
        risk = calculate_risk(offender_level=1)
        assert risk.total_score == 0

    def test_offender_level_2_adds_weight(self):
        risk = calculate_risk(offender_level=2)
        assert risk.total_score == 20
        assert "REPEAT_OFFENDER" in risk.breakdown
        violations_strs = " ".join(risk.all_violations)
        assert "REPEAT_OFFENDER_LEVEL_2" in violations_strs

    def test_offender_level_3_adds_weight(self):
        risk = calculate_risk(offender_level=3)
        assert risk.total_score == 20
        violations_strs = " ".join(risk.all_violations)
        assert "REPEAT_OFFENDER_LEVEL_3" in violations_strs


# ══════════════════════════════════════════════════════════
# calculate_risk — zone multiplier
# ══════════════════════════════════════════════════════════

class TestZoneMultiplier:

    def test_default_multiplier_no_change(self):
        db = MockDBResult(violations_found=["NO_PUCC"])
        risk = calculate_risk(db_result=db, zone_multiplier=1.0)
        assert risk.total_score == 15

    def test_multiplier_below_1_no_change(self):
        db = MockDBResult(violations_found=["NO_PUCC"])
        risk = calculate_risk(db_result=db, zone_multiplier=0.5)
        assert risk.total_score == 15  # multiplier only applies if > 1.0

    def test_school_zone_1_5x(self):
        db = MockDBResult(violations_found=["EXPIRED_INSURANCE"])
        risk = calculate_risk(
            db_result=db, helmet_violation=True, in_blacklist_zone=True,
            zone_multiplier=1.5,
        )
        base = 20 + 10 + 15  # 45
        expected = int(base * 1.5)  # 67
        assert risk.total_score == expected
        assert risk.alert_level == "CRITICAL"
        assert "ZONE_MULTIPLIER" in risk.breakdown

    def test_govt_zone_1_3x(self):
        risk = calculate_risk(overspeeding=True, zone_multiplier=1.3)
        base = 15
        expected = int(base * 1.3)  # 19
        assert risk.total_score == expected

    def test_multiplier_recorded_in_breakdown(self):
        risk = calculate_risk(helmet_violation=True, zone_multiplier=1.5)
        base = 10
        after = int(base * 1.5)  # 15
        assert risk.breakdown.get("ZONE_MULTIPLIER") == after - base


# ══════════════════════════════════════════════════════════
# calculate_risk — complex combined scenarios
# ══════════════════════════════════════════════════════════

class TestCombinedScenarios:

    def test_max_severity_scenario(self, stolen_db_result, fake_plate):
        """Stolen + fake plate + all booleans + level 3 offender + 1.5x zone."""
        risk = calculate_risk(
            db_result=stolen_db_result,
            fake_plate_result=fake_plate,
            helmet_violation=True,
            seatbelt_violation=True,
            in_blacklist_zone=True,
            overspeeding=True,
            offender_level=3,
            zone_multiplier=1.5,
        )
        base = 40 + 35 + 10 + 10 + 15 + 15 + 20  # 145
        expected = int(base * 1.5)  # 217
        assert risk.total_score == expected
        assert risk.alert_level == "CRITICAL"

    def test_return_type(self):
        risk = calculate_risk()
        assert isinstance(risk, RiskScore)
        assert isinstance(risk.total_score, int)
        assert isinstance(risk.alert_level, str)
        assert isinstance(risk.breakdown, dict)
        assert isinstance(risk.all_violations, list)


# ══════════════════════════════════════════════════════════
# RISK_WEIGHTS constant validation
# ══════════════════════════════════════════════════════════

class TestRiskWeightsConstant:

    def test_stolen_is_highest(self):
        assert RISK_WEIGHTS["STOLEN_VEHICLE"] == 40

    def test_fake_plate_second_highest(self):
        assert RISK_WEIGHTS["FAKE_PLATE"] == 35

    def test_all_weights_positive(self):
        for key, val in RISK_WEIGHTS.items():
            assert val > 0, f"{key} should have a positive weight"
