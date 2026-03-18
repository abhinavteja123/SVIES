"""
SVIES — Main Processing Pipeline
Orchestrates all layers: Detection → OCR → Fake Plate → DB Intel →
Risk Score → Geofence → Alerts → Offender Tracking

Usage:
    python main.py                            # webcam
    python main.py --source video.mp4         # video file
    python main.py --source image.jpg --image # single image
"""

import argparse
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

# ── Import all modules ──
from modules.detector import detect, draw_detections
from modules.ocr_parser import extract_plate
from modules.fake_plate import check_fake_plate
from modules.db_intelligence import check_vehicle
from modules.risk_scorer import calculate_risk
from modules.helmet_detector import detect_safety
from modules.alert_system import build_alert_payload, dispatch_alert
from modules.offender_tracker import log_violation, get_offender_level
from modules.geofence import check_zone, get_priority_multiplier
from modules.speed_estimator import SpeedEstimator
from config import CONFIDENCE_THRESHOLD

# ── Speed Estimator (module-level singleton) ──
_speed_estimator = SpeedEstimator()

# ── Violation snapshots directory ──
_VIOLATION_SNAPSHOTS_DIR = Path(__file__).resolve().parent / "snapshots" / "violations"
_VIOLATION_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
UNABLE_TO_DETECT_LABEL = "UNABLE_TO_DETECT"


def process_frame(frame: np.ndarray, camera_id: str = "CAM_01",
                  gps_lat: float = 0.0, gps_lon: float = 0.0) -> tuple[list[dict], list]:
    """Process a single frame through the full SVIES pipeline.

    Returns:
        (records, detections) — records are violation dicts,
        detections are raw Detection objects for drawing/reuse.
    """
    records = []
    detections = detect(frame, confidence_threshold=CONFIDENCE_THRESHOLD)

    for det in detections:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "camera_id": camera_id,
            "vehicle_type": det.vehicle_type,
            "vehicle_color": det.vehicle_color,
            "confidence": det.confidence,
        }

        # ── Layer 3: OCR ──
        plate_number = None
        ocr_bboxes = []
        if det.plate_crop is not None:
            ocr_result = extract_plate(det.plate_crop, min_confidence=0.3)
            plate_number = ocr_result.plate_number
            ocr_bboxes = ocr_result.char_bboxes
            record["plate"] = plate_number
            record["ocr_confidence"] = ocr_result.confidence
            record["ocr_raw"] = ocr_result.raw_text

        if plate_number is None:
            record["plate"] = UNABLE_TO_DETECT_LABEL
            record["status"] = "PLATE_NOT_RECOGNIZED"
            records.append(record)
            continue

        # ── Layer 2.5: Fake Plate Detection ──
        fake_result = check_fake_plate(
            plate_number=plate_number,
            detected_vehicle_type=det.vehicle_type,
            plate_crop=det.plate_crop,
            ocr_char_bboxes=ocr_bboxes,
            camera_id=camera_id,
        )
        record["fake_plate"] = fake_result.is_fake
        record["fake_flags"] = fake_result.flags

        # ── Layer 4: DB Intelligence ──
        db_intel = check_vehicle(plate_number)
        record["owner"] = db_intel.owner_name
        record["stolen"] = db_intel.is_stolen
        record["pucc_status"] = db_intel.pucc_status
        record["insurance_status"] = db_intel.insurance_status
        record["db_violations"] = db_intel.violations_found

        # ── Layer 4.5: Helmet/Seatbelt ──
        safety = detect_safety(frame, det.vehicle_type, det.vehicle_bbox)
        record["helmet"] = safety.helmet_detected
        record["seatbelt"] = safety.seatbelt_detected
        record["safety_violation"] = safety.violation

        # ── Layer 4: Speed Estimation ──
        speed_result = None
        if det.vehicle_bbox is not None:
            speed_result = _speed_estimator.update(
                track_id=plate_number,
                bbox=det.vehicle_bbox,
            )
        if speed_result:
            record["speed_kmh"] = speed_result.speed_kmh
            record["overspeeding"] = speed_result.is_overspeeding
        else:
            record["speed_kmh"] = 0.0
            record["overspeeding"] = False

        # ── Layer 5: Geofence ──
        zone_result = check_zone(gps_lat, gps_lon) if (gps_lat is not None and gps_lon is not None and (gps_lat != 0.0 or gps_lon != 0.0)) else None
        zone_multiplier = 1.0
        zone_id = ""
        if zone_result:
            zone_id = zone_result.zone_id
            zone_multiplier = get_priority_multiplier(zone_result.zone_type)
            record["zone"] = zone_result.zone_name

        # ── Layer 4: Offender Level ──
        offender_level = get_offender_level(plate_number)

        # ── Layer 4: Risk Score ──
        risk = calculate_risk(
            db_result=db_intel,
            fake_plate_result=fake_result,
            helmet_violation=(safety.violation and not safety.helmet_detected),
            seatbelt_violation=(safety.violation and not safety.seatbelt_detected),
            in_blacklist_zone=(zone_result is not None),
            offender_level=offender_level,
            zone_multiplier=zone_multiplier,
            overspeeding=speed_result.is_overspeeding if speed_result else False,
        )
        record["risk_score"] = risk.total_score
        record["alert_level"] = risk.alert_level
        record["risk_breakdown"] = risk.breakdown
        record["all_violations"] = risk.all_violations

        # ── Layer 5: Log violation ──
        if risk.all_violations:
            # Save violation images
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            safe_plate = plate_number.replace("/", "_").replace("\\", "_")
            sha_prefix = hashlib.sha256(f"{plate_number}{ts_str}".encode()).hexdigest()[:8]
            base_name = f"{ts_str}_{safe_plate}_{sha_prefix}"

            cap_path = _VIOLATION_SNAPSHOTS_DIR / f"{base_name}_captured.jpg"
            ann_frame = draw_detections(frame, detections)
            ann_path = _VIOLATION_SNAPSHOTS_DIR / f"{base_name}_annotated.jpg"
            cv2.imwrite(str(cap_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            cv2.imwrite(str(ann_path), ann_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

            captured_url = f"/snapshots/violations/{cap_path.name}"
            annotated_url = f"/snapshots/violations/{ann_path.name}"

            sha = log_violation(
                plate=plate_number,
                violations=risk.all_violations,
                risk_score=risk.total_score,
                zone_id=zone_id,
                alert_level=risk.alert_level,
                vehicle_type=det.vehicle_type,
                owner_name=db_intel.owner_name or "",
                model_used=safety.model_used if safety.violation else "yolo",
                captured_image=captured_url,
                annotated_image=annotated_url,
            )
            record["sha256"] = sha
            record["captured_image"] = captured_url
            record["annotated_image"] = annotated_url

        # ── Layer 5: Alert dispatch ──
        if risk.alert_level in ("HIGH", "CRITICAL"):
            payload = build_alert_payload(
                plate=plate_number,
                owner_name=db_intel.owner_name or "",
                owner_phone=db_intel.owner_phone or "",
                owner_email=getattr(db_intel, 'owner_email', "") or "",
                violations=risk.all_violations,
                fake_plate_flags=fake_result.flags,
                risk_score=risk.total_score,
                alert_level=risk.alert_level,
                zone=zone_id,
                gps_location=f"{gps_lat},{gps_lon}" if (gps_lat != 0.0 or gps_lon != 0.0) else "",
                frame=frame,
            )
            dispatch_result = dispatch_alert(payload, risk.alert_level)
            record["alert_dispatched"] = dispatch_result

        records.append(record)

    return records, detections


def run_video(source, camera_id: str = "CAM_01"):
    """Run SVIES pipeline on a video source (file or webcam)."""
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video source: {source}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_skip = max(1, int(fps / 5))  # Process ~5 FPS
    frame_count = 0

    print(f"[INFO] Video source opened. FPS={fps:.1f}, processing every {frame_skip} frames")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        start = time.time()
        records, detections = process_frame(frame, camera_id=camera_id)
        elapsed = time.time() - start

        # ── Draw detections (reuse from process_frame, no double-inference) ──
        annotated = draw_detections(frame, detections)

        # ── Overlay info ──
        for i, rec in enumerate(records):
            y = 30 + i * 25
            plate = rec.get("plate", "?")
            level = rec.get("alert_level", "?")
            score = rec.get("risk_score", 0)
            color = {"LOW": (0, 255, 0), "MEDIUM": (0, 255, 255),
                     "HIGH": (0, 128, 255), "CRITICAL": (0, 0, 255)}.get(level, (255, 255, 255))
            cv2.putText(annotated, f"{plate} | {level} | Score:{score}",
                       (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.putText(annotated, f"FPS: {1/elapsed:.1f}" if elapsed > 0 else "FPS: --",
                   (10, annotated.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow("SVIES - Smart Vehicle Intelligence", annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def run_image(source: str, camera_id: str = "CAM_01"):
    """Run SVIES pipeline on a single image."""
    frame = cv2.imread(source)
    if frame is None:
        print(f"[ERROR] Cannot load image: {source}")
        return

    print(f"\n[INFO] Processing image: {source}")
    records, detections = process_frame(frame, camera_id=camera_id)

    print(f"\n{'=' * 60}")
    print(f"SVIES Results — {len(records)} detection(s)")
    print(f"{'=' * 60}")

    for i, rec in enumerate(records, 1):
        print(f"\n--- Detection {i} ---")
        for k, v in rec.items():
            print(f"  {k:20s}: {v}")

    # Save annotated (reuse detections, no double-inference)
    annotated = draw_detections(frame, detections)
    out_path = Path(source).stem + "_svies_result.jpg"
    cv2.imwrite(out_path, annotated)
    print(f"\n[INFO] Annotated image saved: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SVIES Main Pipeline")
    parser.add_argument("--source", default="0", help="Video/image path or 0 for webcam")
    parser.add_argument("--image", action="store_true", help="Process as single image")
    parser.add_argument("--camera-id", default="CAM_01", help="Camera identifier")
    args = parser.parse_args()

    print("=" * 60)
    print("SVIES — Smart Vehicle Intelligence & Enforcement System")
    print("=" * 60)

    if args.image:
        run_image(args.source, args.camera_id)
    else:
        source = int(args.source) if args.source.isdigit() else args.source
        run_video(source, args.camera_id)
