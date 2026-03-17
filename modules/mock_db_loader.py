"""
SVIES — Mock Database Loader
Layer: Foundation
Loads all 4 JSON mock databases into memory at startup and provides
lookup functions for each database.

Usage:
    from modules.mock_db_loader import lookup_vahan, lookup_pucc, lookup_insurance, is_stolen
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("svies.mock_db_loader")


# ── Resolve paths ──
_MODULE_DIR: Path = Path(__file__).resolve().parent
_PROJECT_ROOT: Path = _MODULE_DIR.parent
_MOCK_DB_DIR: Path = _PROJECT_ROOT / "data" / "mock_db"

# ── Load databases into memory at import time ──
_vahan_db: dict[str, dict[str, Any]] = {}
_pucc_db: dict[str, dict[str, Any]] = {}
_insurance_db: dict[str, dict[str, Any]] = {}
_stolen_db: dict[str, Any] = {}


def _load_json(file_path: Path) -> dict:
    """Load a JSON file and return its contents as a dictionary.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed JSON data as a dict.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Mock DB file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in {file_path}: {e}")
        return {}


def _initialize_databases() -> None:
    """Load all mock databases into module-level variables."""
    global _vahan_db, _pucc_db, _insurance_db, _stolen_db

    _vahan_db = _load_json(_MOCK_DB_DIR / "vahan.json")
    _pucc_db = _load_json(_MOCK_DB_DIR / "pucc.json")
    _insurance_db = _load_json(_MOCK_DB_DIR / "insurance.json")
    _stolen_db = _load_json(_MOCK_DB_DIR / "stolen.json")


# ── Auto-load on import ──
_initialize_databases()


# ══════════════════════════════════════════════════════════
# Public Lookup Functions
# ══════════════════════════════════════════════════════════

def lookup_vahan(plate: str) -> dict | None:
    """Look up a vehicle registration record from the VAHAN database.

    Args:
        plate: License plate number (e.g., 'TS09EF1234').

    Returns:
        A dict with vehicle details (owner, phone, email, vehicle_type,
        color, make, year, state, registration_state_code, status),
        or None if not found.
    """
    plate = plate.upper().strip()
    return _vahan_db.get(plate, None)


def lookup_pucc(plate: str) -> dict | None:
    """Look up a Pollution Under Control Certificate record.

    Args:
        plate: License plate number.

    Returns:
        A dict with fields (valid_until, status), or None if not found.
    """
    plate = plate.upper().strip()
    return _pucc_db.get(plate, None)


def lookup_insurance(plate: str) -> dict | None:
    """Look up an insurance record.

    Args:
        plate: License plate number.

    Returns:
        A dict with fields (valid_until, type, status), or None if not found.
    """
    plate = plate.upper().strip()
    return _insurance_db.get(plate, None)


def is_stolen(plate: str) -> bool:
    """Check if a vehicle is in the stolen vehicle list.

    Args:
        plate: License plate number.

    Returns:
        True if the plate is in the stolen list, False otherwise.
    """
    plate = plate.upper().strip()
    stolen_plates: list[str] = _stolen_db.get("stolen_plates", [])
    return plate in stolen_plates


def get_all_plates() -> list[str]:
    """Get a list of all plate numbers in the VAHAN database.

    Returns:
        List of plate number strings.
    """
    return list(_vahan_db.keys())


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Mock Database Loader Test")
    print("=" * 60)

    # ── Database load status ──
    print(f"\n  VAHAN records loaded:     {len(_vahan_db)}")
    print(f"  PUCC records loaded:      {len(_pucc_db)}")
    print(f"  Insurance records loaded: {len(_insurance_db)}")
    stolen_count = len(_stolen_db.get('stolen_plates', []))
    print(f"  Stolen plates loaded:     {stolen_count}")

    # ── Test 1: VAHAN lookup (valid plate) ──
    print("\n" + "-" * 40)
    print("TEST 1: VAHAN lookup — TS09EF1234")
    result = lookup_vahan("TS09EF1234")
    if result:
        print(f"  Owner:        {result['owner']}")
        print(f"  Vehicle Type: {result['vehicle_type']}")
        print(f"  Color:        {result['color']}")
        print(f"  Make:         {result['make']}")
        print(f"  State:        {result['state']}")
        print("  [✓] PASSED")
    else:
        print("  [✗] FAILED — record not found!")

    # ── Test 2: VAHAN lookup (unknown plate) ──
    print("\n" + "-" * 40)
    print("TEST 2: VAHAN lookup — XX00ZZ9999 (unknown)")
    result = lookup_vahan("XX00ZZ9999")
    if result is None:
        print("  Result: None (as expected)")
        print("  [✓] PASSED")
    else:
        print("  [✗] FAILED — should have returned None!")

    # ── Test 3: PUCC lookup ──
    print("\n" + "-" * 40)
    print("TEST 3: PUCC lookup — TS06AB5678")
    result = lookup_pucc("TS06AB5678")
    if result:
        print(f"  Valid Until: {result['valid_until']}")
        print(f"  Status:      {result['status']}")
        print("  [✓] PASSED" if result['status'] == "EXPIRED" else "  [✗] FAILED")
    else:
        print("  [✗] FAILED — record not found!")

    # ── Test 4: Insurance lookup ──
    print("\n" + "-" * 40)
    print("TEST 4: Insurance lookup — TS09EF1234")
    result = lookup_insurance("TS09EF1234")
    if result:
        print(f"  Valid Until: {result['valid_until']}")
        print(f"  Type:        {result['type']}")
        print(f"  Status:      {result['status']}")
        print("  [✓] PASSED" if result['status'] == "VALID" else "  [✗] FAILED")
    else:
        print("  [✗] FAILED — record not found!")

    # ── Test 5: Stolen vehicle check ──
    print("\n" + "-" * 40)
    print("TEST 5: Stolen check — AP28CD1234 (should be stolen)")
    stolen = is_stolen("AP28CD1234")
    print(f"  Is Stolen: {stolen}")
    print("  [✓] PASSED" if stolen else "  [✗] FAILED")

    # ── Test 6: Stolen vehicle check (not stolen) ──
    print("\n" + "-" * 40)
    print("TEST 6: Stolen check — TS09EF1234 (should NOT be stolen)")
    stolen = is_stolen("TS09EF1234")
    print(f"  Is Stolen: {stolen}")
    print("  [✓] PASSED" if not stolen else "  [✗] FAILED")

    print("\n" + "=" * 60)
    print("[✓] All mock DB loader tests completed!")
