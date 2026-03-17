"""
SVIES — Helmet & Seatbelt Detection Module
Layer 4.5: Safety Violation Detection
Uses YOLOv8n-pose for rider detection and heuristic checks for helmet/seatbelt.

Usage:
    python -m modules.helmet_detector <image_path> <vehicle_type>
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("svies.helmet")

_pose_model = None
_custom_helmet_model = None
_custom_helmet_checked = False
USING_CUSTOM_HELMET = False


def _get_custom_helmet_model():
    """Load custom Roboflow helmet detector if it exists."""
    global _custom_helmet_model, _custom_helmet_checked, USING_CUSTOM_HELMET
    if _custom_helmet_checked:
        return _custom_helmet_model
    _custom_helmet_checked = True
    try:
        from ultralytics import YOLO
        models_dir = Path(__file__).resolve().parent.parent / "models"
        custom = models_dir / "svies_helmet_detector.pt"
        if custom.exists():
            logger.info(f"Loading custom helmet detector: {custom}")
            _custom_helmet_model = YOLO(str(custom))
            USING_CUSTOM_HELMET = True
            return _custom_helmet_model
    except Exception as e:
        logger.warning(f"Custom helmet model load failed: {e}")
    return None


def _get_pose_model():
    """Load YOLOv8n-pose model (singleton)."""
    global _pose_model
    if _pose_model is not None:
        return _pose_model
    try:
        from ultralytics import YOLO
        models_dir = Path(__file__).resolve().parent.parent / "models"
        local = models_dir / "yolov8n-pose.pt"
        if local.exists():
            _pose_model = YOLO(str(local))
        else:
            _pose_model = YOLO("yolov8n-pose.pt")
    except Exception as e:
        logger.warning(f"Pose model load failed: {e}")
        _pose_model = None
    return _pose_model


@dataclass
class HelmetResult:
    """Result from helmet/seatbelt detection."""
    helmet_detected: bool | None = None
    seatbelt_detected: bool | None = None
    confidence: float = 0.0
    violation: bool = False
    model_used: str = "heuristic"  # "custom" | "heuristic"


# ── Skin color HSV range ──
SKIN_LOWER = np.array([0, 50, 100])
SKIN_UPPER = np.array([20, 150, 255])


def _check_helmet_heuristic(head_crop: np.ndarray) -> tuple[bool, float]:
    """Heuristic helmet check using HSV skin detection + edge analysis.

    If top 40% of head crop is non-skin AND has strong edges → helmet present.
    """
    if head_crop is None or head_crop.size == 0 or head_crop.shape[0] < 10:
        return (False, 0.0)

    h, w = head_crop.shape[:2]
    top_region = head_crop[:int(h * 0.4), :]
    if top_region.size == 0:
        return (False, 0.0)

    hsv = cv2.cvtColor(top_region, cv2.COLOR_BGR2HSV)
    skin_mask = cv2.inRange(hsv, SKIN_LOWER, SKIN_UPPER)
    total = skin_mask.shape[0] * skin_mask.shape[1]
    if total == 0:
        return (False, 0.0)

    skin_ratio = float(np.count_nonzero(skin_mask)) / total
    non_skin = 1.0 - skin_ratio

    gray = cv2.cvtColor(top_region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_ratio = float(np.count_nonzero(edges)) / total

    helmet_present = non_skin > 0.6 and edge_ratio > 0.05
    confidence = min(non_skin * 0.7 + edge_ratio * 3.0, 1.0)

    return (helmet_present, confidence)


def _check_seatbelt(driver_crop: np.ndarray) -> tuple[bool, float]:
    """Seatbelt detection using Canny + HoughLinesP for diagonal lines.

    Seatbelts run diagonally (roughly 30-60 degrees from vertical),
    so we look for diagonal lines rather than purely vertical ones.
    Requires multiple consistent lines to reduce false positives.
    """
    if driver_crop is None or driver_crop.size == 0:
        return (False, 0.0)

    gray = cv2.cvtColor(driver_crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30,
                            minLineLength=40, maxLineGap=10)
    if lines is None:
        return (False, 0.0)

    diagonal_count = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length < 30:
            continue
        if abs(x2 - x1) < 1:
            continue  # Skip purely vertical lines (pillars, window frames)
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if 30 <= angle <= 70 or 110 <= angle <= 150:
            diagonal_count += 1

    seatbelt = diagonal_count >= 3
    confidence = min(diagonal_count / 5.0, 1.0)
    return (seatbelt, confidence)


def detect_safety(frame: np.ndarray, vehicle_type: str,
                  vehicle_bbox: tuple[int, int, int, int] | None) -> HelmetResult:
    """Detect helmet/seatbelt violations based on vehicle type.

    For 2W/3W: checks helmet via custom model or pose estimation + heuristic.
    For 4W: checks seatbelt via edge detection.
    """
    if vehicle_bbox is None:
        return HelmetResult(violation=False)

    x1, y1, x2, y2 = vehicle_bbox
    vtype = vehicle_type.upper()

    if vtype in ("MOTORCYCLE", "SCOOTER", "AUTO", "E_RICKSHAW"):
        vehicle_crop = frame[max(0, y1):min(frame.shape[0], y2),
                            max(0, x1):min(frame.shape[1], x2)]
        if vehicle_crop.size == 0:
            return HelmetResult(violation=False)

        # ── Try custom Roboflow helmet model first ──
        custom_model = _get_custom_helmet_model()
        if custom_model is not None:
            try:
                results = custom_model(vehicle_crop, verbose=False)
                helmet_found = False
                no_helmet_found = False
                best_conf = 0.0

                for r in results:
                    if r.boxes is None:
                        continue
                    names = r.names if hasattr(r, 'names') else {}
                    for j in range(len(r.boxes)):
                        cls_id = int(r.boxes.cls[j].item())
                        conf = float(r.boxes.conf[j].item())
                        cls_name = names.get(cls_id, "").lower()

                        if "helmet" in cls_name and "no" not in cls_name:
                            helmet_found = True
                            best_conf = max(best_conf, conf)
                        elif "no_helmet" in cls_name or "no-helmet" in cls_name:
                            no_helmet_found = True
                            best_conf = max(best_conf, conf)

                if helmet_found or no_helmet_found:
                    return HelmetResult(
                        helmet_detected=helmet_found,
                        confidence=best_conf,
                        violation=no_helmet_found and not helmet_found,
                        model_used="custom",
                    )
            except Exception as e:
                logger.warning(f"Custom helmet model error: {e}")

        # ── Fallback to pose + heuristic ──
        model = _get_pose_model()
        head_crop = None
        if model is not None:
            try:
                results = model(vehicle_crop, verbose=False)
                for r in results:
                    if r.keypoints is not None and len(r.keypoints.data) > 0:
                        kp = r.keypoints.data[0]
                        if len(kp) > 0:
                            hx, hy = int(kp[0][0].item()), int(kp[0][1].item())
                            sz = 50
                            cy1 = max(0, hy - sz)
                            cy2 = min(vehicle_crop.shape[0], hy + sz)
                            cx1 = max(0, hx - sz)
                            cx2 = min(vehicle_crop.shape[1], hx + sz)
                            if cy2 > cy1 and cx2 > cx1:
                                head_crop = vehicle_crop[cy1:cy2, cx1:cx2]
                            break
            except Exception as e:
                logger.warning(f"Pose detection error: {e}")

        if head_crop is None:
            h = vehicle_crop.shape[0]
            head_crop = vehicle_crop[:int(h * 0.3), :]

        helmet, conf = _check_helmet_heuristic(head_crop)
        return HelmetResult(helmet_detected=helmet, confidence=conf,
                           violation=not helmet, model_used="heuristic")

    elif vtype in ("CAR", "SUV"):
        vw, vh = x2 - x1, y2 - y1
        dx1 = x1
        dx2 = x1 + int(vw * 0.4)
        dy1 = y1
        dy2 = y1 + int(vh * 0.6)
        driver_crop = frame[max(0, dy1):min(frame.shape[0], dy2),
                           max(0, dx1):min(frame.shape[1], dx2)]
        seatbelt, conf = _check_seatbelt(driver_crop)
        return HelmetResult(seatbelt_detected=seatbelt, confidence=conf,
                           violation=not seatbelt, model_used="heuristic")

    return HelmetResult(violation=False)


if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Helmet/Seatbelt Detector Test")
    print("=" * 60)

    if len(sys.argv) >= 3:
        img = cv2.imread(sys.argv[1])
        vtype = sys.argv[2]
        if img is not None:
            h, w = img.shape[:2]
            result = detect_safety(img, vtype, (0, 0, w, h))
            print(f"  Type: {vtype}")
            print(f"  Helmet:   {result.helmet_detected}")
            print(f"  Seatbelt: {result.seatbelt_detected}")
            print(f"  Violation: {result.violation}")
            print(f"  Confidence: {result.confidence:.3f}")
    else:
        # Synthetic test
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(test_frame, (100, 100), (300, 400), (128, 128, 128), -1)

        r = detect_safety(test_frame, "MOTORCYCLE", (100, 100, 300, 400))
        print(f"  Helmet: {r.helmet_detected}, Violation: {r.violation}")

        r2 = detect_safety(test_frame, "CAR", (100, 100, 300, 400))
        print(f"  Seatbelt: {r2.seatbelt_detected}, Violation: {r2.violation}")

        r3 = detect_safety(test_frame, "BUS", (100, 100, 300, 400))
        print(f"  BUS (N/A): Violation={r3.violation}")
        assert not r3.violation

    print("\n[✓] Helmet/seatbelt detector test completed!")
