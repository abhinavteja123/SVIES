"""
SVIES — Database Intelligence Module
Layer 4: Multi-Database Cross-Check
Performs parallel lookups across VAHAN, PUCC, Insurance, and Police (stolen)
databases using threading.

Usage:
    python -m modules.db_intelligence
"""

import logging
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("svies.db_intelligence")

# ── Import unified Supabase database layer ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.database import db as _db


def lookup_vahan(plate: str):
    return _db.lookup_vehicle(plate)

def lookup_pucc(plate: str):
    return _db.lookup_pucc(plate)

def lookup_insurance(plate: str):
    return _db.lookup_insurance(plate)

def is_stolen(plate: str) -> bool:
    return _db.is_stolen(plate)


# ══════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════

@dataclass
class VehicleIntelligence:
    """Aggregated vehicle intelligence from all database sources."""
    plate: str = ""
    vahan_record: dict | None = None
    pucc_status: str = "NOT_FOUND"         # VALID / EXPIRED / NOT_FOUND
    insurance_status: str = "NOT_FOUND"    # VALID / EXPIRED / NOT_FOUND
    is_stolen: bool = False
    owner_name: str | None = None
    owner_phone: str | None = None
    owner_email: str | None = None
    violations_found: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════
# Threaded Lookup Functions
# ══════════════════════════════════════════════════════════

def _lookup_vahan_thread(plate: str, results: dict) -> None:
    """Thread target for VAHAN lookup.

    Args:
        plate: License plate number.
        results: Shared dict to store results.
    """
    try:
        record = lookup_vahan(plate)
        results["vahan"] = record
    except Exception as e:
        logger.warning(f"VAHAN lookup error: {e}")
        results["vahan"] = None


def _lookup_pucc_thread(plate: str, results: dict) -> None:
    """Thread target for PUCC lookup.

    Args:
        plate: License plate number.
        results: Shared dict to store results.
    """
    try:
        record = lookup_pucc(plate)
        results["pucc"] = record
    except Exception as e:
        logger.warning(f"PUCC lookup error: {e}")
        results["pucc"] = None


def _lookup_insurance_thread(plate: str, results: dict) -> None:
    """Thread target for Insurance lookup.

    Args:
        plate: License plate number.
        results: Shared dict to store results.
    """
    try:
        record = lookup_insurance(plate)
        results["insurance"] = record
    except Exception as e:
        logger.warning(f"Insurance lookup error: {e}")
        results["insurance"] = None


def _check_stolen_thread(plate: str, results: dict) -> None:
    """Thread target for stolen vehicle check.

    Args:
        plate: License plate number.
        results: Shared dict to store results.
    """
    try:
        stolen = is_stolen(plate)
        results["stolen"] = stolen
    except Exception as e:
        logger.warning(f"Stolen check error: {e}")
        results["stolen"] = False


# ══════════════════════════════════════════════════════════
# Main Intelligence Function
# ══════════════════════════════════════════════════════════

def check_vehicle(plate_number: str) -> VehicleIntelligence:
    """Perform parallel multi-database lookup for a vehicle.

    Queries VAHAN, PUCC, Insurance, and Police (stolen) databases
    concurrently using threading, then aggregates all results into
    a VehicleIntelligence object.

    Args:
        plate_number: The license plate number to check.

    Returns:
        VehicleIntelligence with all database results and violation codes.
    """
    plate = plate_number.upper().strip()
    logger.info(f"check_vehicle() called for plate='{plate}'")
    result = VehicleIntelligence(plate=plate)

    # ── Launch parallel lookups ──
    shared_results: dict[str, Any] = {}

    threads = [
        threading.Thread(target=_lookup_vahan_thread, args=(plate, shared_results)),
        threading.Thread(target=_lookup_pucc_thread, args=(plate, shared_results)),
        threading.Thread(target=_lookup_insurance_thread, args=(plate, shared_results)),
        threading.Thread(target=_check_stolen_thread, args=(plate, shared_results)),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)  # 5-second timeout per thread

    # ── Process VAHAN result ──
    vahan = shared_results.get("vahan")
    if vahan is not None:
        result.vahan_record = vahan
        result.owner_name = vahan.get("owner")
        result.owner_phone = vahan.get("phone")
        result.owner_email = vahan.get("email")
    else:
        result.violations_found.append("UNREGISTERED_VEHICLE")

    # ── Process PUCC result ──
    pucc = shared_results.get("pucc")
    if pucc is not None:
        result.pucc_status = pucc.get("status", "NOT_FOUND")
        if result.pucc_status == "EXPIRED":
            result.violations_found.append("EXPIRED_PUCC")
    else:
        result.pucc_status = "NOT_FOUND"
        result.violations_found.append("NO_PUCC")

    # ── Process Insurance result ──
    insurance = shared_results.get("insurance")
    if insurance is not None:
        result.insurance_status = insurance.get("status", "NOT_FOUND")
        if result.insurance_status == "EXPIRED":
            result.violations_found.append("EXPIRED_INSURANCE")
    else:
        result.insurance_status = "NOT_FOUND"
        result.violations_found.append("NO_INSURANCE")

    # ── Process Stolen check ──
    result.is_stolen = shared_results.get("stolen", False)
    if result.is_stolen:
        result.violations_found.append("STOLEN_VEHICLE")

    logger.info(f"check_vehicle('{plate}'): owner={result.owner_name}, stolen={result.is_stolen}, "
                f"pucc={result.pucc_status}, insurance={result.insurance_status}, violations={result.violations_found}")
    return result


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Database Intelligence Module Test")
    print("=" * 60)

    # ── Test 1: Registered vehicle with valid docs ──
    print("\n" + "-" * 40)
    print("TEST 1: TS09EF1234 (registered, valid docs)")
    intel = check_vehicle("TS09EF1234")
    print(f"  Owner:       {intel.owner_name}")
    print(f"  Phone:       {intel.owner_phone}")
    print(f"  PUCC:        {intel.pucc_status}")
    print(f"  Insurance:   {intel.insurance_status}")
    print(f"  Stolen:      {intel.is_stolen}")
    print(f"  Violations:  {intel.violations_found}")
    assert intel.owner_name == "Ravi Kumar", f"Expected 'Ravi Kumar', got '{intel.owner_name}'"
    assert len(intel.violations_found) == 0, f"Expected no violations, got {intel.violations_found}"
    print("  [✓] PASSED")

    # ── Test 2: Vehicle with expired docs ──
    print("\n" + "-" * 40)
    print("TEST 2: TS06AB5678 (expired PUCC + insurance)")
    intel = check_vehicle("TS06AB5678")
    print(f"  Owner:       {intel.owner_name}")
    print(f"  PUCC:        {intel.pucc_status}")
    print(f"  Insurance:   {intel.insurance_status}")
    print(f"  Violations:  {intel.violations_found}")
    assert "EXPIRED_PUCC" in intel.violations_found, "Should have EXPIRED_PUCC!"
    assert "EXPIRED_INSURANCE" in intel.violations_found, "Should have EXPIRED_INSURANCE!"
    print("  [✓] PASSED")

    # ── Test 3: Stolen vehicle ──
    print("\n" + "-" * 40)
    print("TEST 3: AP28CD1234 (stolen vehicle)")
    intel = check_vehicle("AP28CD1234")
    print(f"  Owner:       {intel.owner_name}")
    print(f"  Stolen:      {intel.is_stolen}")
    print(f"  Violations:  {intel.violations_found}")
    assert intel.is_stolen, "Should be flagged as stolen!"
    assert "STOLEN_VEHICLE" in intel.violations_found, "Should have STOLEN_VEHICLE!"
    print("  [✓] PASSED")

    # ── Test 4: Unknown vehicle ──
    print("\n" + "-" * 40)
    print("TEST 4: XX99ZZ0000 (unregistered)")
    intel = check_vehicle("XX99ZZ0000")
    print(f"  Owner:       {intel.owner_name}")
    print(f"  PUCC:        {intel.pucc_status}")
    print(f"  Insurance:   {intel.insurance_status}")
    print(f"  Violations:  {intel.violations_found}")
    assert "UNREGISTERED_VEHICLE" in intel.violations_found, "Should have UNREGISTERED_VEHICLE!"
    assert "NO_PUCC" in intel.violations_found, "Should have NO_PUCC!"
    assert "NO_INSURANCE" in intel.violations_found, "Should have NO_INSURANCE!"
    print("  [✓] PASSED")

    print("\n" + "=" * 60)
    print("[✓] All DB intelligence tests completed!")
