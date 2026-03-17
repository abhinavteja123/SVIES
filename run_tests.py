"""
SVIES — Integration Test Runner
Runs a sequential test of every module and prints PASS/FAIL.

Usage:
    python run_tests.py
"""

import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

results: list[tuple[str, bool, str]] = []


def run_test(name: str, fn):
    """Run a test function and record result."""
    try:
        fn()
        results.append((name, True, ""))
        print(f"  ✅ {name}")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  ❌ {name}: {e}")
        traceback.print_exc()


def test_config():
    from config import (PROJECT_ROOT, DB_PATH, SNAPSHOT_DIR,
                        PLATE_REGEX, BH_REGEX, CONFIDENCE_THRESHOLD)
    assert PROJECT_ROOT.exists()
    assert CONFIDENCE_THRESHOLD == 0.5
    assert PLATE_REGEX.match("TS09EF1234")
    assert BH_REGEX.match("22BH1234AB")


def test_mock_db():
    from modules.mock_db_loader import lookup_vahan, lookup_pucc, lookup_insurance, is_stolen
    v = lookup_vahan("TS09EF1234")
    assert v is not None and v["owner"] == "Ravi Kumar"
    p = lookup_pucc("TS09EF1234")
    assert p is not None
    i = lookup_insurance("TS09EF1234")
    assert i is not None
    assert is_stolen("AP28CD1234")
    assert not is_stolen("XXXX0000")


def test_fake_plate():
    from modules.fake_plate import check_fake_plate
    r = check_fake_plate("MH12XY9999", "CAR")
    assert r.is_fake and "TYPE_MISMATCH" in r.flags
    r2 = check_fake_plate("TS09EF1234", "CAR")
    assert not r2.is_fake


def test_db_intelligence():
    from modules.db_intelligence import check_vehicle
    intel = check_vehicle("TS09EF1234")
    assert intel.owner_name == "Ravi Kumar"
    assert not intel.is_stolen
    intel2 = check_vehicle("AP28CD1234")
    assert intel2.is_stolen


def test_risk_scorer():
    from dataclasses import dataclass, field
    from modules.risk_scorer import calculate_risk

    @dataclass
    class MockDB:
        violations_found: list = field(default_factory=list)

    @dataclass
    class MockFP:
        is_fake: bool = False
        flags: list = field(default_factory=list)

    r = calculate_risk(db_result=MockDB(["STOLEN_VEHICLE"]),
                       fake_plate_result=MockFP(True, ["TYPE_MISMATCH"]))
    assert r.total_score == 75
    assert r.alert_level == "CRITICAL"


def test_geofence():
    from modules.geofence import check_zone, get_priority_multiplier
    r = check_zone(0.0, 0.0)
    assert r is None
    assert get_priority_multiplier("SCHOOL") == 1.5


def test_offender_tracker():
    import tempfile
    from modules.offender_tracker import init_db, log_violation, get_offender_level
    db = Path(tempfile.mkdtemp()) / "test.db"
    init_db(db)
    for _ in range(3):
        log_violation("TEST_PLATE", ["TEST"], 10, db_path=db)
    assert get_offender_level("TEST_PLATE", db) == 2
    db.unlink(missing_ok=True)


def test_alert_system():
    from modules.alert_system import generate_sha256_hash, build_alert_payload
    h = generate_sha256_hash("TS09", "2025-01-01T00:00:00Z", ["TEST"])
    assert len(h) == 64
    p = build_alert_payload("TS09", violations=["TEST"], risk_score=50, alert_level="HIGH")
    assert p.plate == "TS09"
    assert p.sha256_hash


def test_ocr_module():
    from modules.ocr_parser import _clean_text, _correct_characters, _validate_plate
    assert _clean_text("TS 09 EF 1234") == "TS09EF1234"
    assert _correct_characters("0S09EF1234") == "OS09EF1234"
    plate, fmt = _validate_plate("TS09EF1234")
    assert plate == "TS09EF1234" and fmt == "STANDARD"


def test_edge_mode():
    from edge.edge_mode import EdgeMode
    assert isinstance(EdgeMode.is_online(), bool)
    edge = EdgeMode()
    assert edge.is_stolen_local("NONEXISTENT") is False


if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Integration Test Runner")
    print("=" * 60)
    print()

    tests = [
        ("Config", test_config),
        ("Mock DB Loader", test_mock_db),
        ("Fake Plate Detection", test_fake_plate),
        ("DB Intelligence", test_db_intelligence),
        ("Risk Scorer", test_risk_scorer),
        ("Geofence", test_geofence),
        ("Offender Tracker", test_offender_tracker),
        ("Alert System", test_alert_system),
        ("OCR Module", test_ocr_module),
        ("Edge Mode", test_edge_mode),
    ]

    for name, fn in tests:
        run_test(name, fn)

    print()
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"Results: {passed}/{total} PASSED")

    if passed == total:
        print("[✓] ALL TESTS PASSED!")
    else:
        print("\nFailed tests:")
        for name, ok, err in results:
            if not ok:
                print(f"  ❌ {name}: {err}")

    sys.exit(0 if passed == total else 1)
