"""
SVIES — Fake Plate Detection Module
Layer 2.5: Fake Plate Detection [NOVEL]
Implements 5 checks to detect counterfeit or mismatched license plates.

Checks:
    1. TYPE_MISMATCH — detected vehicle vs VAHAN registration mismatch
    2. COLOR_CODE_VIOLATION — plate color vs CMVR rules mismatch
    3. FONT_ANOMALY — IS 10731 character spacing/height anomaly
    4. DUPLICATE_PLATE_CLONE — same plate at multiple locations
    5. STATE_MISMATCH — plate prefix vs registration state mismatch

Usage:
    python -m modules.fake_plate
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# ── Import mock DB for VAHAN lookups ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.mock_db_loader import lookup_vahan, lookup_pucc, lookup_insurance, is_stolen


# ══════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════

@dataclass
class FakePlateResult:
    """Result from the fake plate detection pipeline."""
    is_fake: bool = False
    flags: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


# ══════════════════════════════════════════════════════════
# Module-Level State for Clone Detection
# ══════════════════════════════════════════════════════════

# {plate_number: (last_seen_utc, camera_id)}
_seen_plates: dict[str, tuple[datetime, str]] = {}


# ══════════════════════════════════════════════════════════
# Vehicle Category Mapping
# ══════════════════════════════════════════════════════════

def _detected_to_category(vehicle_type: str) -> str:
    """Map detected vehicle type to a broad category.

    Supports India-specific vehicle types: auto-rickshaws, tempos,
    e-rickshaws, scooters, tractors.

    Args:
        vehicle_type: Vehicle type from detector (CAR, MOTORCYCLE, etc.)

    Returns:
        Category string: '2W', '3W', '4W', 'FARM', or 'UNKNOWN'.
    """
    match vehicle_type.upper():
        case "CAR" | "SUV" | "VAN" | "TRUCK" | "BUS" | "TEMPO":
            return "4W"
        case "MOTORCYCLE" | "SCOOTER":
            return "2W"
        case "AUTO" | "E_RICKSHAW":
            return "3W"
        case "TRACTOR":
            return "FARM"
        case _:
            return "UNKNOWN"


def _vahan_to_category(vehicle_type: str) -> str:
    """Map VAHAN registered vehicle type to a broad category.

    Args:
        vehicle_type: Vehicle type from VAHAN DB (e.g. 'MOTORCYCLE', 'CAR').

    Returns:
        Category string: '2W', '3W', '4W', 'FARM', or 'UNKNOWN'.
    """
    match vehicle_type.upper():
        case "MOTORCYCLE" | "SCOOTER":
            return "2W"
        case "CAR" | "SUV" | "VAN":
            return "4W"
        case "TRUCK" | "BUS" | "TEMPO":
            return "4W"
        case "AUTO" | "E_RICKSHAW":
            return "3W"
        case "TRACTOR":
            return "FARM"
        case _:
            return "UNKNOWN"


# ══════════════════════════════════════════════════════════
# Database Existence Checks
# ══════════════════════════════════════════════════════════

def check_vahan_exists(plate_number: str) -> dict:
    """Check if plate exists in VAHAN database (vehicle registration).

    A plate NOT found in VAHAN is highly suspicious — could be fake,
    not yet registered, or cloned.

    Args:
        plate_number: The license plate number.

    Returns:
        Dict with 'flagged' bool and 'evidence' details.
    """
    vahan = lookup_vahan(plate_number)

    if vahan is None:
        return {
            "flagged": True,
            "severity": "HIGH",
            "reason": "Plate NOT found in VAHAN database — unregistered, fake, or cloned",
        }

    return {
        "flagged": False,
        "reason": "Plate found in VAHAN database",
        "registered_owner": vahan.get("owner", "Unknown"),
    }


def check_pucc_valid(plate_number: str) -> dict:
    """Check if plate has valid Pollution Under Control Certificate (PUCC).

    Missing or expired PUCC indicates vehicle may not be roadworthy.

    Args:
        plate_number: The license plate number.

    Returns:
        Dict with 'flagged' bool and 'evidence' details.
    """
    pucc = lookup_pucc(plate_number)

    if pucc is None:
        return {
            "flagged": True,
            "severity": "MEDIUM",
            "reason": "No PUCC (Pollution Certificate) found in database",
        }

    status = pucc.get("status", "UNKNOWN").upper()
    if status == "EXPIRED":
        return {
            "flagged": True,
            "severity": "MEDIUM",
            "reason": f"PUCC expired on {pucc.get('valid_until', 'unknown date')}",
        }

    return {
        "flagged": False,
        "reason": "Valid PUCC found",
        "valid_until": pucc.get("valid_until", "Unknown"),
    }


def check_insurance_valid(plate_number: str) -> dict:
    """Check if plate has valid insurance coverage.

    Missing or expired insurance is a legal violation.

    Args:
        plate_number: The license plate number.

    Returns:
        Dict with 'flagged' bool and 'evidence' details.
    """
    insurance = lookup_insurance(plate_number)

    if insurance is None:
        return {
            "flagged": True,
            "severity": "MEDIUM",
            "reason": "No insurance record found in database",
        }

    status = insurance.get("status", "UNKNOWN").upper()
    if status == "EXPIRED":
        return {
            "flagged": True,
            "severity": "MEDIUM",
            "reason": f"Insurance expired on {insurance.get('valid_until', 'unknown date')}",
        }

    return {
        "flagged": False,
        "reason": "Valid insurance found",
        "valid_until": insurance.get("valid_until", "Unknown"),
    }


def check_stolen_vehicle(plate_number: str) -> dict:
    """Check if vehicle is reported as stolen.

    Args:
        plate_number: The license plate number.

    Returns:
        Dict with 'flagged' bool and evidence.
    """
    if is_stolen(plate_number):
        return {
            "flagged": True,
            "severity": "CRITICAL",
            "reason": "Vehicle is reported STOLEN in national database — Alert authorities immediately!",
        }

    return {
        "flagged": False,
        "reason": "Vehicle not in stolen database",
    }

# ══════════════════════════════════════════════════════════

def check_type_mismatch(plate_number: str, detected_vehicle_type: str) -> dict:
    """Check if detected vehicle type matches VAHAN registration.

    Args:
        plate_number: The license plate number.
        detected_vehicle_type: Vehicle type from the detector.

    Returns:
        Dict with 'flagged' bool and 'evidence' details.
    """
    vahan = lookup_vahan(plate_number)
    if vahan is None:
        return {"flagged": False, "reason": "VAHAN record not found — cannot compare"}

    detected_cat = _detected_to_category(detected_vehicle_type)
    vahan_cat = _vahan_to_category(vahan["vehicle_type"])

    if detected_cat == "UNKNOWN" or vahan_cat == "UNKNOWN":
        return {"flagged": False, "reason": "Could not classify one or both types"}

    flagged = detected_cat != vahan_cat
    return {
        "flagged": flagged,
        "detected_type": detected_vehicle_type,
        "detected_category": detected_cat,
        "vahan_type": vahan["vehicle_type"],
        "vahan_category": vahan_cat,
        "reason": f"Detected {detected_cat} but registered as {vahan_cat}" if flagged else "Match",
    }


# ══════════════════════════════════════════════════════════
# CHECK 2: Color Code Violation (CMVR Rules)
# ══════════════════════════════════════════════════════════

def _classify_plate_color(plate_crop: np.ndarray) -> str:
    """Classify plate background color using HSV analysis.

    Analyzes the top 10px strip of the plate crop.

    Args:
        plate_crop: BGR image of the cropped plate region.

    Returns:
        Plate class: 'PRIVATE', 'COMMERCIAL', 'EV', 'RENTAL', or 'UNKNOWN'.
    """
    if plate_crop is None or plate_crop.size == 0:
        return "UNKNOWN"

    # ── Use top 10px strip for background color ──
    h = plate_crop.shape[0]
    strip_h = min(10, h // 3)
    top_strip = plate_crop[:strip_h, :]

    if top_strip.size == 0:
        return "UNKNOWN"

    hsv = cv2.cvtColor(top_strip, cv2.COLOR_BGR2HSV)

    # ── Color ranges per CMVR rules ──
    masks = {
        "PRIVATE": cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255])),     # White
        "COMMERCIAL": cv2.inRange(hsv, np.array([20, 100, 100]), np.array([35, 255, 255])),  # Yellow
        "EV": cv2.inRange(hsv, np.array([45, 100, 100]), np.array([85, 255, 255])),        # Green
        "RENTAL": cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 30, 50])),          # Black
    }

    total = hsv.shape[0] * hsv.shape[1]
    if total == 0:
        return "UNKNOWN"

    best_class = "UNKNOWN"
    best_ratio = 0.0

    for cls, mask in masks.items():
        ratio = float(np.count_nonzero(mask)) / total
        if ratio > best_ratio and ratio > 0.3:  # At least 30% coverage
            best_ratio = ratio
            best_class = cls

    return best_class


def check_color_code_violation(plate_crop: np.ndarray, plate_number: str) -> dict:
    """Check if plate color class conflicts with registered vehicle type.

    Args:
        plate_crop: BGR image of the cropped plate.
        plate_number: The license plate number.

    Returns:
        Dict with 'flagged' bool and evidence.
    """
    if plate_crop is None or plate_crop.size == 0:
        return {"flagged": False, "reason": "No plate crop available"}

    plate_class = _classify_plate_color(plate_crop)
    vahan = lookup_vahan(plate_number)

    if vahan is None:
        return {"flagged": False, "reason": "VAHAN record not found", "plate_color_class": plate_class}

    vtype = vahan["vehicle_type"].upper()
    flagged = False
    reason = "Match"

    # ── CMVR rules check ──
    if plate_class == "COMMERCIAL" and vtype not in ("TRUCK", "BUS", "AUTO"):
        flagged = True
        reason = f"Commercial (yellow) plate on {vtype} — expected on TRUCK/BUS/AUTO only"
    elif plate_class == "PRIVATE" and vtype in ("TRUCK", "BUS", "AUTO"):
        flagged = True
        reason = f"Private (white) plate on {vtype} — should be commercial (yellow)"

    return {
        "flagged": flagged,
        "plate_color_class": plate_class,
        "vehicle_type": vtype,
        "reason": reason,
    }


# ══════════════════════════════════════════════════════════
# CHECK 3: Font Anomaly (IS 10731)
# ══════════════════════════════════════════════════════════

def check_font_anomaly(ocr_char_bboxes: list, plate_crop: np.ndarray | None = None) -> dict:
    """Check if character dimensions follow IS 10731 standard.

    Expected ratios:
    - char_height / plate_height: 0.5 - 0.7
    - char_spacing / char_width: 0.1 - 0.3

    Args:
        ocr_char_bboxes: List of character bounding boxes from OCR.
        plate_crop: Optional plate crop for height reference.

    Returns:
        Dict with 'flagged' bool and evidence.
    """
    if not ocr_char_bboxes or len(ocr_char_bboxes) < 3:
        return {"flagged": False, "reason": "Insufficient char bboxes for analysis"}

    plate_height = 0
    if plate_crop is not None and plate_crop.size > 0:
        plate_height = plate_crop.shape[0]
    else:
        # ── Estimate from char bboxes ──
        all_tops = [bb[1] for bb in ocr_char_bboxes if len(bb) >= 4]
        all_bottoms = [bb[3] for bb in ocr_char_bboxes if len(bb) >= 4]
        if all_tops and all_bottoms:
            plate_height = max(all_bottoms) - min(all_tops)

    if plate_height <= 0:
        return {"flagged": False, "reason": "Could not determine plate height"}

    anomaly_count = 0
    total_chars = 0

    for i, bbox in enumerate(ocr_char_bboxes):
        if len(bbox) < 4:
            continue

        x1, y1, x2, y2 = bbox[:4]
        char_h = y2 - y1
        char_w = x2 - x1

        if char_w <= 0 or char_h <= 0:
            continue

        total_chars += 1

        # ── Height ratio check ──
        height_ratio = char_h / plate_height
        if not (0.5 <= height_ratio <= 0.7):
            anomaly_count += 1
            continue

        # ── Spacing check (with next character) ──
        if i + 1 < len(ocr_char_bboxes) and len(ocr_char_bboxes[i + 1]) >= 4:
            next_x1 = ocr_char_bboxes[i + 1][0]
            spacing = next_x1 - x2
            spacing_ratio = spacing / char_w if char_w > 0 else 0
            if not (0.1 <= spacing_ratio <= 0.3):
                anomaly_count += 1

    if total_chars == 0:
        return {"flagged": False, "reason": "No valid character boxes"}

    anomaly_pct = anomaly_count / total_chars
    flagged = anomaly_pct > 0.30  # Flag if >30% chars fail

    return {
        "flagged": flagged,
        "anomaly_count": anomaly_count,
        "total_chars": total_chars,
        "anomaly_percentage": round(anomaly_pct * 100, 1),
        "reason": f"{anomaly_pct * 100:.1f}% chars fail IS 10731 check" if flagged
                  else f"Within tolerance ({anomaly_pct * 100:.1f}% anomaly)",
    }


# ══════════════════════════════════════════════════════════
# CHECK 4: Duplicate Plate / Clone Detection
# ══════════════════════════════════════════════════════════

def check_duplicate_plate(plate_number: str, camera_id: str) -> dict:
    """Check if this plate was recently seen at a different camera.

    If same plate seen on different camera within 10 minutes → CLONE_ALERT.

    Args:
        plate_number: The license plate number.
        camera_id: ID of the current camera.

    Returns:
        Dict with 'flagged' bool and evidence.
    """
    global _seen_plates

    now = datetime.now(timezone.utc)
    plate_key = plate_number.upper().strip()

    if plate_key in _seen_plates:
        last_seen, last_camera = _seen_plates[plate_key]
        time_diff = (now - last_seen).total_seconds()

        if last_camera != camera_id and time_diff < 600:  # 10 minutes
            _seen_plates[plate_key] = (now, camera_id)
            return {
                "flagged": True,
                "reason": f"Same plate seen on camera '{last_camera}' "
                          f"{time_diff:.0f}s ago (< 10 min) — potential clone!",
                "last_camera": last_camera,
                "current_camera": camera_id,
                "time_diff_seconds": time_diff,
            }

    # ── Update seen record ──
    _seen_plates[plate_key] = (now, camera_id)
    return {"flagged": False, "reason": "No duplicate detected"}


# ══════════════════════════════════════════════════════════
# CHECK 5: State Code Mismatch
# ══════════════════════════════════════════════════════════

# Valid Indian state codes
INDIAN_STATE_CODES: set[str] = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "GA",
    "GJ", "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH",
    "ML", "MN", "MP", "MZ", "NL", "OD", "PB", "PY", "RJ", "SK",
    "TN", "TR", "TS", "UK", "UP", "WB",
}


def check_state_mismatch(plate_number: str) -> dict:
    """Check if plate's state prefix matches VAHAN registration state.

    Args:
        plate_number: The license plate number.

    Returns:
        Dict with 'flagged' bool and evidence.
    """
    if len(plate_number) < 2:
        return {"flagged": False, "reason": "Plate too short for state code extraction"}

    plate_state = plate_number[:2].upper()

    # ── Skip BH-series plates ──
    if plate_number[2:4].upper() == "BH":
        return {"flagged": False, "reason": "BH-series plate — no state mismatch check needed"}

    vahan = lookup_vahan(plate_number)
    if vahan is None:
        return {"flagged": False, "reason": "VAHAN record not found", "plate_state": plate_state}

    reg_state = vahan.get("registration_state_code", "").upper()

    if not reg_state:
        return {"flagged": False, "reason": "No registration_state_code in VAHAN"}

    flagged = plate_state != reg_state

    return {
        "flagged": flagged,
        "plate_state_code": plate_state,
        "registration_state_code": reg_state,
        "reason": f"Plate prefix '{plate_state}' ≠ registered state '{reg_state}'" if flagged
                  else "State codes match",
    }


# ══════════════════════════════════════════════════════════
# Master Function
# ══════════════════════════════════════════════════════════

def check_fake_plate(
    plate_number: str,
    detected_vehicle_type: str,
    plate_crop: np.ndarray | None = None,
    ocr_char_bboxes: list | None = None,
    camera_id: str = "default_cam",
) -> FakePlateResult:
    """Run all 8 fake plate detection checks.

    Args:
        plate_number: The extracted license plate number.
        detected_vehicle_type: Vehicle type from detector module.
        plate_crop: BGR image of the cropped plate (for color analysis).
        ocr_char_bboxes: List of OCR character bounding boxes.
        camera_id: Camera identifier for clone detection.

    Returns:
        FakePlateResult with aggregated flags, details, and confidence.
    """
    flags: list[str] = []
    details: dict[str, Any] = {}
    severity_weights: dict[str, int] = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}

    # ── CHECK 0: Stolen Vehicle (highest priority) ──
    result_stolen = check_stolen_vehicle(plate_number)
    details["STOLEN_VEHICLE"] = result_stolen
    if result_stolen["flagged"]:
        flags.append("STOLEN_VEHICLE")

    # ── CHECK 0.5: VAHAN Registration Exists ──
    result_vahan = check_vahan_exists(plate_number)
    details["VAHAN_EXISTS"] = result_vahan
    if result_vahan["flagged"]:
        flags.append("VAHAN_NOT_EXISTS")

    # ── CHECK 1: Type Mismatch (only if VAHAN record found) ──
    result1 = check_type_mismatch(plate_number, detected_vehicle_type)
    details["TYPE_MISMATCH"] = result1
    if result1["flagged"]:
        flags.append("TYPE_MISMATCH")

    # ── CHECK 2: Color Code Violation ──
    result2 = check_color_code_violation(plate_crop, plate_number)
    details["COLOR_CODE_VIOLATION"] = result2
    if result2["flagged"]:
        flags.append("COLOR_CODE_VIOLATION")

    # ── CHECK 3: Font Anomaly ──
    result3 = check_font_anomaly(ocr_char_bboxes or [], plate_crop)
    details["FONT_ANOMALY"] = result3
    if result3["flagged"]:
        flags.append("FONT_ANOMALY")

    # ── CHECK 4: Duplicate Plate / Clone ──
    result4 = check_duplicate_plate(plate_number, camera_id)
    details["DUPLICATE_PLATE_CLONE"] = result4
    if result4["flagged"]:
        flags.append("DUPLICATE_PLATE_CLONE")

    # ── CHECK 5: State Mismatch ──
    result5 = check_state_mismatch(plate_number)
    details["STATE_MISMATCH"] = result5
    if result5["flagged"]:
        flags.append("STATE_MISMATCH")

    # ── CHECK 6: PUCC (Pollution Certificate) Valid ──
    result_pucc = check_pucc_valid(plate_number)
    details["PUCC_INVALID"] = result_pucc
    if result_pucc["flagged"]:
        flags.append("PUCC_INVALID")

    # ── CHECK 7: Insurance Valid ──
    result_insurance = check_insurance_valid(plate_number)
    details["INSURANCE_INVALID"] = result_insurance
    if result_insurance["flagged"]:
        flags.append("INSURANCE_INVALID")

    # ── Aggregate result with improved confidence ──
    # NEW LOGIC: Higher confidence if multiple checks fail, especially critical ones
    is_fake = len(flags) > 0

    # Calculate confidence based on flags and severity
    confidence = 0.0
    if is_fake:
        # Each flag contributes to confidence, with critical flags weighted heavily
        confidence_numerator = sum(
            severity_weights.get(details.get(flag.replace("_NOT_EXISTS", ""), {}).get("severity", "LOW"), 1)
            for flag in flags
        )
        # Max confidence: 8 checks total, but critical ones can push it higher
        # STOLEN = 3, VAHAN_NOT_EXISTS = 2, others = 1 each
        confidence = min(1.0, confidence_numerator / 5.0)  # Normalize to 0-1 range

    return FakePlateResult(
        is_fake=is_fake,
        flags=flags,
        details=details,
        confidence=confidence,
    )


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Fake Plate Detection Module Test")
    print("=" * 60)

    # ── Test 1: Type Mismatch Scenario ──
    # MH12XY9999 is registered as MOTORCYCLE in VAHAN,
    # but we detect it as a CAR → TYPE_MISMATCH
    print("\n" + "-" * 40)
    print("TEST 1: Type Mismatch (CAR detected, MOTORCYCLE registered)")
    result = check_fake_plate(
        plate_number="MH12XY9999",
        detected_vehicle_type="CAR",
        plate_crop=None,
        ocr_char_bboxes=None,
        camera_id="CAM_01",
    )
    print(f"  Is Fake:    {result.is_fake}")
    print(f"  Flags:      {result.flags}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Details:    {result.details['TYPE_MISMATCH']['reason']}")
    assert result.is_fake, "Should be flagged as fake!"
    assert "TYPE_MISMATCH" in result.flags, "Should have TYPE_MISMATCH flag!"
    print("  [✓] PASSED")

    # ── Test 2: Clean Plate (no mismatch) ──
    print("\n" + "-" * 40)
    print("TEST 2: Clean Plate (CAR detected, CAR registered)")
    result = check_fake_plate(
        plate_number="TS09EF1234",
        detected_vehicle_type="CAR",
        plate_crop=None,
        ocr_char_bboxes=None,
        camera_id="CAM_01",
    )
    print(f"  Is Fake:    {result.is_fake}")
    print(f"  Flags:      {result.flags}")
    print(f"  Confidence: {result.confidence:.2f}")
    assert not result.is_fake, "Should NOT be flagged as fake!"
    print("  [✓] PASSED")

    # ── Test 3: State Mismatch ──
    # Simulating a plate that says MH but the code expects TS
    # We'll use TS09EF1234 which is registered in TS — no mismatch
    print("\n" + "-" * 40)
    print("TEST 3: State Code Check (TS plate, TS registration)")
    r5 = check_state_mismatch("TS09EF1234")
    print(f"  Flagged: {r5['flagged']}")
    print(f"  Reason:  {r5['reason']}")
    assert not r5["flagged"], "Should NOT be flagged!"
    print("  [✓] PASSED")

    # ── Test 4: Clone Detection ──
    print("\n" + "-" * 40)
    print("TEST 4: Clone Detection (same plate, different cameras)")
    # First sighting
    r4a = check_duplicate_plate("TS09EF1234", "CAM_NORTH")
    print(f"  First sighting (CAM_NORTH): Flagged={r4a['flagged']}")
    # Second sighting at different camera within 10 min
    r4b = check_duplicate_plate("TS09EF1234", "CAM_SOUTH")
    print(f"  Second sighting (CAM_SOUTH): Flagged={r4b['flagged']}")
    print(f"  Reason: {r4b['reason']}")
    assert r4b["flagged"], "Should be flagged as clone!"
    print("  [✓] PASSED")

    print("\n" + "=" * 60)
    print("[✓] All fake plate detection tests completed!")
