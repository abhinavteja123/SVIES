"""
SVIES — Vehicle & Plate Detector Module
Layer 2: AI Detection Engine
Uses YOLOv8n for vehicle detection and license plate localization.
Optimized for Indian roads: detects cars, motorcycles, auto-rickshaws,
scooters, buses, trucks, tempos, tractors, and e-rickshaws.
Classifies vehicle type and color (via HSV histogram).

Usage:
    python -m modules.detector <image_path>
"""

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("svies.detector")

# ── Lazy-load YOLO to avoid import overhead when not needed ──
_model = None
_plate_model = None
_indian_vehicle_model = None
USING_CUSTOM_MODEL = False
USING_INDIAN_VEHICLE_MODEL = False


def _get_indian_vehicle_model():
    """Load Indian vehicle detector model if available.

    This model is specifically trained on Indian roads to detect:
    auto-rickshaws, tempos, tractors, e-rickshaws, scooters, etc.
    """
    global _indian_vehicle_model, USING_INDIAN_VEHICLE_MODEL
    if _indian_vehicle_model is not None:
        return _indian_vehicle_model

    from ultralytics import YOLO
    models_dir = Path(__file__).resolve().parent.parent / "models"
    indian_model = models_dir / "svies_vehicle_classifier.pt"

    if indian_model.exists():
        logger.info(f"Loading Indian vehicle detector: {indian_model}")
        _indian_vehicle_model = YOLO(str(indian_model))
        USING_INDIAN_VEHICLE_MODEL = True
        return _indian_vehicle_model

    return None


def _get_plate_model():
    """Load dedicated plate detector model if available (singleton)."""
    global _plate_model
    if _plate_model is not None:
        return _plate_model

    from ultralytics import YOLO
    models_dir = Path(__file__).resolve().parent.parent / "models"
    plate_model_path = models_dir / "svies_plate_detector.pt"

    if plate_model_path.exists():
        logger.info(f"Loading dedicated plate detector: {plate_model_path}")
        _plate_model = YOLO(str(plate_model_path))
        return _plate_model

    return None


def _get_model():
    """Load YOLOv8n COCO model as generic fallback (singleton pattern).

    This is only used when neither the Indian vehicle classifier nor
    the dedicated plate detector covers the detection. Loads yolov8n.pt.
    """
    global _model, USING_CUSTOM_MODEL
    if _model is not None:
        return _model

    from ultralytics import YOLO

    models_dir = Path(__file__).resolve().parent.parent / "models"

    # ── Load generic YOLOv8n (plate detector is loaded separately via _get_plate_model) ──
    local_model = models_dir / "yolov8n.pt"
    if local_model.exists():
        logger.info(f"Loading YOLOv8n from: {local_model}")
        _model = YOLO(str(local_model))
    else:
        logger.info("Downloading YOLOv8n (yolov8n.pt)...")
        _model = YOLO("yolov8n.pt")

    USING_CUSTOM_MODEL = False
    return _model


# ══════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════

@dataclass
class DetectionResult:
    """Result from the vehicle/plate detection pipeline."""
    plate_bbox: tuple[int, int, int, int] | None = None
    plate_crop: np.ndarray | None = None
    vehicle_type: str = "UNKNOWN"
    vehicle_color: str = "UNKNOWN"
    vehicle_bbox: tuple[int, int, int, int] | None = None
    confidence: float = 0.0
    raw_detections: list[dict] = field(default_factory=list)
    vehicle_age: str = "UNKNOWN"
    age_confidence: float = 0.0


# ══════════════════════════════════════════════════════════
# COCO Class → Vehicle Type Mapping (Indian roads)
# ══════════════════════════════════════════════════════════

# YOLOv8 COCO class indices for vehicles
VEHICLE_CLASSES: dict[int, str] = {
    2: "CAR",         # car
    3: "MOTORCYCLE",  # motorcycle (+ scooters on Indian roads)
    5: "BUS",         # bus
    7: "TRUCK",       # truck
}

# Additional non-vehicle classes that might help with plate region
RELEVANT_CLASSES: set[int] = {2, 3, 5, 7}

# Indian vehicle types (used by custom Indian vehicle detector)
INDIAN_VEHICLE_TYPES: set[str] = {
    "CAR", "MOTORCYCLE", "SCOOTER", "AUTO", "BUS", "TRUCK",
    "TEMPO", "TRACTOR", "E_RICKSHAW", "VAN", "SUV",
}


# ══════════════════════════════════════════════════════════
# Color Classification via HSV
# ══════════════════════════════════════════════════════════

# HSV ranges for 8-class vehicle color
COLOR_RANGES: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {
    "WHITE": [(np.array([0, 0, 200]), np.array([180, 30, 255]))],
    "BLACK": [(np.array([0, 0, 0]), np.array([180, 30, 50]))],
    "SILVER": [(np.array([0, 0, 100]), np.array([180, 30, 200]))],
    "RED": [
        (np.array([0, 100, 100]), np.array([10, 255, 255])),
        (np.array([160, 100, 100]), np.array([180, 255, 255])),
    ],
    "BLUE": [(np.array([100, 100, 100]), np.array([130, 255, 255]))],
    "GREEN": [(np.array([45, 100, 100]), np.array([85, 255, 255]))],
    "YELLOW": [(np.array([20, 100, 100]), np.array([35, 255, 255]))],
    "GREY": [(np.array([0, 0, 50]), np.array([180, 50, 150]))],
}


def classify_color(crop: np.ndarray) -> str:
    """Classify the dominant color of a vehicle crop using HSV histogram.

    Args:
        crop: BGR image crop of the vehicle.

    Returns:
        Color name string (WHITE, BLACK, RED, BLUE, etc.)
    """
    if crop is None or crop.size == 0:
        return "UNKNOWN"

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    total_pixels = hsv.shape[0] * hsv.shape[1]

    if total_pixels == 0:
        return "UNKNOWN"

    best_color = "UNKNOWN"
    best_ratio = 0.0

    for color_name, ranges in COLOR_RANGES.items():
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lower, upper in ranges:
            mask |= cv2.inRange(hsv, lower, upper)
        ratio = float(np.count_nonzero(mask)) / total_pixels
        if ratio > best_ratio:
            best_ratio = ratio
            best_color = color_name

    return best_color


# ══════════════════════════════════════════════════════════
# Auto-Rickshaw Size Heuristic
# ══════════════════════════════════════════════════════════

def _classify_by_size(bbox: tuple[int, int, int, int], frame_shape: tuple) -> str:
    """Classify a detected vehicle as AUTO/TEMPO/E_RICKSHAW based on size heuristics.

    Indian road-specific: auto-rickshaws, tempos, and e-rickshaws are common
    but not in standard COCO classes. Use size and aspect ratio to differentiate.

    Args:
        bbox: (x1, y1, x2, y2) of the detected vehicle.
        frame_shape: Shape of the original frame (height, width, channels).

    Returns:
        Vehicle type string based on size heuristic.
    """
    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1
    aspect = w / max(h, 1)
    area_ratio = (w * h) / (frame_shape[0] * frame_shape[1])

    # Auto-rickshaws: medium-sized, roughly square-ish aspect ratio
    if 0.01 < area_ratio < 0.10 and 0.6 < aspect < 1.5:
        return "AUTO"
    # Tempos / small commercial: slightly larger than autos
    if 0.10 <= area_ratio < 0.18 and 0.8 < aspect < 2.0:
        return "TEMPO"
    # E-rickshaws: similar size to autos but squarer
    if 0.008 < area_ratio < 0.08 and 0.7 < aspect < 1.3:
        return "E_RICKSHAW"
    return "UNKNOWN"


# ══════════════════════════════════════════════════════════
# Preprocessing
# ══════════════════════════════════════════════════════════

def preprocess_frame(frame: np.ndarray) -> np.ndarray:
    """Apply CLAHE preprocessing for improved detection in low-light conditions.

    Args:
        frame: Input BGR frame.

    Returns:
        Enhanced BGR frame.
    """
    # ── Convert to LAB color space for CLAHE on L channel ──
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # ── Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) ──
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)

    # ── Merge and convert back ──
    lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
    enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

    return enhanced


# ══════════════════════════════════════════════════════════
# Plate Region Estimation
# ══════════════════════════════════════════════════════════

def estimate_plate_region(vehicle_bbox: tuple[int, int, int, int],
                          vehicle_type: str,
                          frame: np.ndarray) -> tuple[int, int, int, int] | None:
    """Estimate the license plate region within a vehicle bounding box.

    Different vehicle types have plates in different locations:
    - Cars/Trucks/Bus: lower center-front area
    - Motorcycles: lower rear area

    Args:
        vehicle_bbox: (x1, y1, x2, y2) of the vehicle.
        vehicle_type: Type string (CAR, MOTORCYCLE, etc.)
        frame: The original frame.

    Returns:
        Estimated plate bbox (x1, y1, x2, y2) or None.
    """
    x1, y1, x2, y2 = vehicle_bbox
    vw = x2 - x1
    vh = y2 - y1

    match vehicle_type:
        case "CAR" | "TRUCK" | "BUS" | "AUTO":
            # Plate is typically in the lower 30%, centered horizontally
            px1 = x1 + int(vw * 0.2)
            py1 = y1 + int(vh * 0.65)
            px2 = x1 + int(vw * 0.8)
            py2 = y2
        case "MOTORCYCLE" | "SCOOTER":
            # Plate is typically in the lower 25%, centered
            px1 = x1 + int(vw * 0.15)
            py1 = y1 + int(vh * 0.7)
            px2 = x1 + int(vw * 0.85)
            py2 = y2
        case "E_RICKSHAW":
            # E-rickshaws: plate at back, lower area
            px1 = x1 + int(vw * 0.25)
            py1 = y1 + int(vh * 0.6)
            px2 = x1 + int(vw * 0.75)
            py2 = y2
        case "TRACTOR":
            # Tractors: plate on front/rear, may be partially obscured
            px1 = x1 + int(vw * 0.15)
            py1 = y1 + int(vh * 0.5)
            px2 = x1 + int(vw * 0.85)
            py2 = y2
        case _:
            # Generic: lower 30% of bbox
            px1 = x1 + int(vw * 0.15)
            py1 = y1 + int(vh * 0.65)
            px2 = x1 + int(vw * 0.85)
            py2 = y2

    # ── Clamp to frame bounds ──
    h, w = frame.shape[:2]
    px1 = max(0, px1)
    py1 = max(0, py1)
    px2 = min(w, px2)
    py2 = min(h, py2)

    if px2 - px1 < 10 or py2 - py1 < 5:
        return None

    return (px1, py1, px2, py2)


# ══════════════════════════════════════════════════════════
# Main Detection Function
# ══════════════════════════════════════════════════════════

def _refine_plate_with_detector(frame: np.ndarray, vehicle_bbox: tuple[int, int, int, int],
                                 conf_threshold: float = 0.25) -> tuple[tuple[int, int, int, int] | None, np.ndarray | None]:
    """Use the dedicated plate detector model to find the actual plate.

    Runs the plate detector on the FULL FRAME (matching the notebook approach)
    and returns the best plate detection that overlaps with the vehicle bbox.
    Adds 10px padding around the detected plate for better OCR.

    Args:
        frame: Full BGR frame.
        vehicle_bbox: (x1, y1, x2, y2) of the vehicle.
        conf_threshold: Min confidence for plate detection.

    Returns:
        (plate_bbox, plate_crop) in frame coordinates, or (None, None).
    """
    plate_model = _get_plate_model()
    if plate_model is None:
        return None, None

    h, w = frame.shape[:2]
    vx1, vy1, vx2, vy2 = vehicle_bbox

    try:
        results = plate_model(frame, imgsz=640, verbose=False, conf=conf_threshold)
        best_plate = None
        best_conf = 0.0

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                conf = float(boxes.conf[i].item())
                bbox = boxes.xyxy[i].cpu().numpy().astype(int)
                px1, py1, px2, py2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

                # Check if this plate overlaps with the vehicle bbox
                # Plate center must be inside (or near) the vehicle bbox
                plate_cx = (px1 + px2) // 2
                plate_cy = (py1 + py2) // 2

                # Allow generous margin around vehicle bbox for plate matching
                margin = 50
                if (vx1 - margin <= plate_cx <= vx2 + margin and
                    vy1 - margin <= plate_cy <= vy2 + margin and
                    conf > best_conf):
                    best_conf = conf
                    best_plate = (px1, py1, px2, py2)

        if best_plate is not None:
            px1, py1, px2, py2 = best_plate

            # Add 10px padding (matching notebook approach)
            pad = 10
            px1 = max(0, px1 - pad)
            py1 = max(0, py1 - pad)
            px2 = min(w, px2 + pad)
            py2 = min(h, py2 + pad)

            if px2 - px1 >= 10 and py2 - py1 >= 5:
                plate_crop = frame[py1:py2, px1:px2].copy()
                return (px1, py1, px2, py2), plate_crop

    except Exception as e:
        logger.warning(f"Plate detector refinement error: {e}")

    return None, None


# Cache full-frame plate detections to avoid running the model multiple times per frame
_cached_plate_detections: list[tuple[tuple[int, int, int, int], float]] = []
_cached_frame_id: int = -1


def _detect_all_plates(frame: np.ndarray, conf_threshold: float = 0.25) -> list[tuple[tuple[int, int, int, int], float]]:
    """Run plate detector on full frame and cache results.

    Returns list of (plate_bbox, confidence) tuples.
    """
    global _cached_plate_detections, _cached_frame_id

    frame_id = id(frame)
    if frame_id == _cached_frame_id:
        return _cached_plate_detections

    plate_model = _get_plate_model()
    if plate_model is None:
        return []

    plates = []
    try:
        results = plate_model(frame, imgsz=640, verbose=False, conf=conf_threshold)
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                conf = float(boxes.conf[i].item())
                bbox = boxes.xyxy[i].cpu().numpy().astype(int)
                plates.append((
                    (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])),
                    conf
                ))
    except Exception as e:
        logger.warning(f"Plate detection error: {e}")

    _cached_plate_detections = plates
    _cached_frame_id = frame_id
    return plates


def _match_plate_to_vehicle(frame: np.ndarray, vehicle_bbox: tuple[int, int, int, int],
                             all_plates: list[tuple[tuple[int, int, int, int], float]],
                             used_plates: set[int] | None = None) -> tuple[tuple[int, int, int, int] | None, np.ndarray | None]:
    """Match the best plate detection to a vehicle bbox (exclusive matching).

    Args:
        frame: Full BGR frame.
        vehicle_bbox: (x1, y1, x2, y2) of the vehicle.
        all_plates: List of (plate_bbox, confidence) from full-frame detection.
        used_plates: Set of plate indices already assigned to other vehicles.
                     Plates in this set will be skipped.

    Returns:
        (plate_bbox_with_padding, plate_crop) or (None, None).
    """
    if used_plates is None:
        used_plates = set()

    h, w = frame.shape[:2]
    vx1, vy1, vx2, vy2 = vehicle_bbox

    best_plate = None
    best_score = -1.0
    best_idx = -1

    for idx, ((px1, py1, px2, py2), conf) in enumerate(all_plates):
        if idx in used_plates:
            continue

        # Plate center must be inside (or near) the vehicle bbox
        plate_cx = (px1 + px2) // 2
        plate_cy = (py1 + py2) // 2

        margin = 30
        if not (vx1 - margin <= plate_cx <= vx2 + margin and
                vy1 - margin <= plate_cy <= vy2 + margin):
            continue

        # Score based on how well the plate center falls within the vehicle bbox
        # (prefer plates that are more centrally located within the vehicle)
        v_cx = (vx1 + vx2) / 2
        v_cy = (vy1 + vy2) / 2
        vw = max(vx2 - vx1, 1)
        vh = max(vy2 - vy1, 1)
        # Normalized distance from vehicle center (0 = center, 1 = edge)
        dx = abs(plate_cx - v_cx) / (vw / 2)
        dy = abs(plate_cy - v_cy) / (vh / 2)
        closeness = max(0, 1.0 - (dx + dy) / 2)  # Higher = closer to center
        score = conf * 0.5 + closeness * 0.5

        if score > best_score:
            best_score = score
            best_plate = (px1, py1, px2, py2)
            best_idx = idx

    if best_plate is not None and best_idx >= 0:
        used_plates.add(best_idx)
        px1, py1, px2, py2 = best_plate

        # Add 10px padding (matching notebook approach)
        pad = 10
        px1 = max(0, px1 - pad)
        py1 = max(0, py1 - pad)
        px2 = min(w, px2 + pad)
        py2 = min(h, py2 + pad)

        if px2 - px1 >= 10 and py2 - py1 >= 5:
            plate_crop = frame[py1:py2, px1:px2].copy()
            return (px1, py1, px2, py2), plate_crop

    return None, None


def _get_coco_vehicle_type(model, frame: np.ndarray, bbox: tuple[int, int, int, int],
                            conf_threshold: float = 0.3) -> str | None:
    """Use COCO YOLOv8n to classify what vehicle type is in a given bbox region.

    Runs COCO model on the vehicle crop and returns the best matching
    vehicle type, or None if no vehicle class is detected.
    """
    x1, y1, x2, y2 = bbox
    # Expand crop slightly for better classification context
    h, w = frame.shape[:2]
    pad = 20
    cx1 = max(0, x1 - pad)
    cy1 = max(0, y1 - pad)
    cx2 = min(w, x2 + pad)
    cy2 = min(h, y2 + pad)
    crop = frame[cy1:cy2, cx1:cx2]

    if crop.size == 0:
        return None

    try:
        results = model(crop, verbose=False, conf=conf_threshold)
        best_type = None
        best_conf = 0.0
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                if cls_id in VEHICLE_CLASSES and conf > best_conf:
                    best_conf = conf
                    best_type = VEHICLE_CLASSES[cls_id]
        return best_type
    except Exception as e:
        logger.warning(f"COCO vehicle classification error: {e}")
        return None


def _has_real_vehicle_classes(model) -> bool:
    """Check if a model has real vehicle class names (not just generic 'object')."""
    if model is None:
        return False
    try:
        names = model.names if hasattr(model, 'names') else {}
        # If model only has generic classes like 'object', it can't classify types
        name_values = {str(v).upper().replace("-", "_").replace(" ", "_") for v in names.values()}
        return bool(name_values & INDIAN_VEHICLE_TYPES)
    except Exception:
        return False


def detect(frame: np.ndarray, confidence_threshold: float = 0.5) -> list[DetectionResult]:
    """Run YOLOv8n detection on a frame and return structured results.

    Optimized for Indian roads: uses the Indian vehicle detector for
    localization if available, then classifies vehicle type via COCO
    YOLOv8n (car, motorcycle, bus, truck). Falls back to COCO-only
    if the Indian model is not available.

    Args:
        frame: Input BGR frame from OpenCV.
        confidence_threshold: Minimum confidence for detections (default 0.5).

    Returns:
        List of DetectionResult objects, one per detected vehicle.
    """
    if frame is None or frame.size == 0:
        logger.warning("detect() called with empty frame")
        return []

    logger.info(f"detect() called: frame={frame.shape}, conf_threshold={confidence_threshold}")

    model = _get_model()

    # ── Preprocess for Indian road conditions (dust, low-light, glare) ──
    enhanced = preprocess_frame(frame)

    # ── Try Indian vehicle detector for localization ──
    indian_model = _get_indian_vehicle_model()
    indian_detections: list[DetectionResult] = []
    can_classify = _has_real_vehicle_classes(indian_model)

    # If Indian model only has generic classes (e.g. 'object'), it can still
    # localize vehicles — we just use COCO for classification via _get_coco_vehicle_type()
    if not can_classify and _indian_vehicle_model is not None:
        logger.info("detect(): Indian model has generic classes — using it for localization, COCO for classification")

    if indian_model is not None:
        try:
            india_results = indian_model(enhanced, verbose=False, conf=confidence_threshold)

            # Run plate detector on full frame ONCE (like notebook does)
            all_plates = _detect_all_plates(frame, conf_threshold=0.25)

            for result in india_results:
                boxes = result.boxes
                if boxes is None:
                    continue
                model_names = result.names if hasattr(result, 'names') else {}
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    conf = float(boxes.conf[i].item())
                    bbox = boxes.xyxy[i].cpu().numpy().astype(int)
                    x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

                    if can_classify:
                        # Model has real vehicle classes — use them directly
                        cls_name = model_names.get(cls_id, "").upper().replace("-", "_").replace(" ", "_")
                        vtype = cls_name if cls_name in INDIAN_VEHICLE_TYPES else "CAR"
                    else:
                        # Model only detects objects — use COCO YOLOv8n to classify
                        vtype = _get_coco_vehicle_type(model, frame, (x1, y1, x2, y2))
                        if vtype is None:
                            # Size-based fallback for Indian vehicle types
                            vtype = _classify_by_size((x1, y1, x2, y2), frame.shape)
                            if vtype == "UNKNOWN":
                                vtype = "CAR"
                        logger.info(f"  COCO classified vehicle at ({x1},{y1},{x2},{y2}) as {vtype}")

                    vehicle_crop = frame[max(0, y1):min(frame.shape[0], y2),
                                         max(0, x1):min(frame.shape[1], x2)]
                    vehicle_color = classify_color(vehicle_crop)

                    # ── Age classification via ResNet50 ──
                    vehicle_age = "UNKNOWN"
                    age_conf = 0.0
                    try:
                        from modules.age_classifier import classify_age
                        age_result = classify_age(vehicle_crop)
                        vehicle_age = age_result.age_category
                        age_conf = age_result.confidence
                    except Exception as e:
                        logger.warning(f"Age classification error: {e}")

                    # Match a plate detection from full-frame results to this vehicle
                    plate_bbox, plate_crop = _match_plate_to_vehicle(frame, (x1, y1, x2, y2), all_plates)

                    # Fallback to heuristic estimation if plate detector didn't find anything
                    if plate_bbox is None:
                        plate_bbox = estimate_plate_region((x1, y1, x2, y2), vtype, frame)
                        plate_crop = None
                        if plate_bbox is not None:
                            px1, py1, px2, py2 = plate_bbox
                            plate_crop = frame[py1:py2, px1:px2].copy()

                    # Fallback: ResNet50 plate detection if still no plate
                    if plate_bbox is None and vehicle_crop.size > 0:
                        try:
                            from modules.plate_detector_resnet import detect_plate_resnet
                            resnet_bbox, resnet_crop = detect_plate_resnet(vehicle_crop)
                            if resnet_bbox is not None:
                                # Convert from vehicle-crop coords to frame coords
                                rx1, ry1, rx2, ry2 = resnet_bbox
                                plate_bbox = (x1 + rx1, y1 + ry1, x1 + rx2, y1 + ry2)
                                plate_crop = resnet_crop
                                logger.info(f"  ResNet50 fallback found plate at {plate_bbox}")
                        except Exception as e:
                            logger.warning(f"ResNet50 plate fallback error: {e}")

                    indian_detections.append(DetectionResult(
                        plate_bbox=plate_bbox,
                        plate_crop=plate_crop,
                        vehicle_type=vtype,
                        vehicle_color=vehicle_color,
                        vehicle_bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        vehicle_age=vehicle_age,
                        age_confidence=age_conf,
                    ))
        except Exception as e:
            logger.warning(f"Indian vehicle model error: {e}")

    if indian_detections:
        logger.info(f"detect(): Indian model found {len(indian_detections)} vehicle(s)")
        return indian_detections

    # ── Fallback: Run primary YOLOv8 inference ──
    logger.info("detect(): Falling back to COCO YOLOv8n model")
    results = model(enhanced, verbose=False, conf=confidence_threshold)

    # Run plate detector on full frame for COCO path too (like notebook does)
    all_plates = _detect_all_plates(frame, conf_threshold=0.25)

    detections: list[DetectionResult] = []
    used_plates: set[int] = set()  # Track plates already assigned to vehicles

    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        # ── Get model class names for custom model handling ──
        model_names = result.names if hasattr(result, 'names') else {}

        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            bbox = boxes.xyxy[i].cpu().numpy().astype(int)
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

            if USING_CUSTOM_MODEL:
                # ── Custom Roboflow model: look for known class names ──
                cls_name = model_names.get(cls_id, "").lower()

                if cls_name == "license_plate" or cls_name == "license-plate":
                    # This is a plate detection — attach to nearest vehicle or create standalone
                    plate_bbox = (x1, y1, x2, y2)
                    plate_crop = frame[max(0, y1):min(frame.shape[0], y2),
                                       max(0, x1):min(frame.shape[1], x2)].copy()
                    detection = DetectionResult(
                        plate_bbox=plate_bbox,
                        plate_crop=plate_crop,
                        vehicle_type="UNKNOWN",
                        vehicle_color="UNKNOWN",
                        vehicle_bbox=None,
                        confidence=conf,
                    )
                    detections.append(detection)
                    continue

                elif cls_name in ("vehicle", "car", "truck", "bus", "motorcycle"):
                    vehicle_type = cls_name.upper()
                    if vehicle_type == "VEHICLE":
                        vehicle_type = _classify_by_size((x1, y1, x2, y2), frame.shape)
                        if vehicle_type == "UNKNOWN":
                            vehicle_type = "CAR"  # Default for custom model

                    vehicle_crop = frame[max(0, y1):min(frame.shape[0], y2),
                                         max(0, x1):min(frame.shape[1], x2)]
                    vehicle_color = classify_color(vehicle_crop)

                    plate_bbox = estimate_plate_region((x1, y1, x2, y2), vehicle_type, frame)
                    plate_crop = None
                    if plate_bbox is not None:
                        px1, py1, px2, py2 = plate_bbox
                        plate_crop = frame[py1:py2, px1:px2].copy()

                    detection = DetectionResult(
                        plate_bbox=plate_bbox,
                        plate_crop=plate_crop,
                        vehicle_type=vehicle_type,
                        vehicle_color=vehicle_color,
                        vehicle_bbox=(x1, y1, x2, y2),
                        confidence=conf,
                    )
                    detections.append(detection)
                    continue
                else:
                    # Skip non-vehicle/non-plate classes in custom model
                    continue

            else:
                # ── Generic COCO model: original behavior ──
                # ── Only process vehicle classes ──
                if cls_id not in RELEVANT_CLASSES:
                    continue

                # ── Map to vehicle type ──
                vehicle_type = VEHICLE_CLASSES.get(cls_id, "UNKNOWN")

                # ── If UNKNOWN, try size-based auto classification ──
                if vehicle_type == "UNKNOWN":
                    vehicle_type = _classify_by_size((x1, y1, x2, y2), frame.shape)

                # ── Crop vehicle region for color analysis ──
                vehicle_crop = frame[max(0, y1):min(frame.shape[0], y2),
                                     max(0, x1):min(frame.shape[1], x2)]
                vehicle_color = classify_color(vehicle_crop)

                # ── Age classification via ResNet50 ──
                vehicle_age = "UNKNOWN"
                age_conf = 0.0
                try:
                    from modules.age_classifier import classify_age
                    age_result = classify_age(vehicle_crop)
                    vehicle_age = age_result.age_category
                    age_conf = age_result.confidence
                except Exception as e:
                    logger.warning(f"Age classification error: {e}")

                # ── Try plate detector first, fall back to heuristic ──
                plate_bbox, plate_crop = _match_plate_to_vehicle(frame, (x1, y1, x2, y2), all_plates, used_plates)
                if plate_bbox is None:
                    plate_bbox = estimate_plate_region((x1, y1, x2, y2), vehicle_type, frame)
                    plate_crop = None
                    if plate_bbox is not None:
                        px1, py1, px2, py2 = plate_bbox
                        plate_crop = frame[py1:py2, px1:px2].copy()

                # ── Fallback: ResNet50 plate detection ──
                if plate_bbox is None and vehicle_crop.size > 0:
                    try:
                        from modules.plate_detector_resnet import detect_plate_resnet
                        resnet_bbox, resnet_crop = detect_plate_resnet(vehicle_crop)
                        if resnet_bbox is not None:
                            rx1, ry1, rx2, ry2 = resnet_bbox
                            plate_bbox = (x1 + rx1, y1 + ry1, x1 + rx2, y1 + ry2)
                            plate_crop = resnet_crop
                            logger.info(f"  ResNet50 fallback found plate at {plate_bbox}")
                    except Exception as e:
                        logger.warning(f"ResNet50 plate fallback error: {e}")

                detection = DetectionResult(
                    plate_bbox=plate_bbox,
                    plate_crop=plate_crop,
                    vehicle_type=vehicle_type,
                    vehicle_color=vehicle_color,
                    vehicle_bbox=(x1, y1, x2, y2),
                    confidence=conf,
                    vehicle_age=vehicle_age,
                    age_confidence=age_conf,
                )
                detections.append(detection)

    logger.info(f"detect(): COCO model found {len(detections)} vehicle(s)")
    return detections


def detect_single(frame: np.ndarray, confidence_threshold: float = 0.5) -> DetectionResult:
    """Run detection and return only the highest-confidence vehicle result.

    Args:
        frame: Input BGR frame.
        confidence_threshold: Minimum detection confidence.

    Returns:
        The highest-confidence DetectionResult, or an empty result.
    """
    results = detect(frame, confidence_threshold)
    if not results:
        return DetectionResult()
    return max(results, key=lambda r: r.confidence)


# ══════════════════════════════════════════════════════════
# Drawing Utilities
# ══════════════════════════════════════════════════════════

def draw_detections(frame: np.ndarray, detections: list[DetectionResult]) -> np.ndarray:
    """Draw bounding boxes and labels on a frame.

    Args:
        frame: Input BGR frame.
        detections: List of DetectionResult objects.

    Returns:
        Annotated frame copy.
    """
    annotated = frame.copy()

    for det in detections:
        # ── Draw vehicle bbox (green) ──
        if det.vehicle_bbox:
            x1, y1, x2, y2 = det.vehicle_bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{det.vehicle_type} ({det.vehicle_color}) {det.confidence:.2f}"
            cv2.putText(annotated, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # ── Draw plate bbox (blue) ──
        if det.plate_bbox:
            px1, py1, px2, py2 = det.plate_bbox
            cv2.rectangle(annotated, (px1, py1), (px2, py2), (255, 0, 0), 2)
            cv2.putText(annotated, "PLATE", (px1, py1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

    return annotated


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m modules.detector <image_path>")
        print("Example: python -m modules.detector test_image.jpg")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)

    print("=" * 60)
    print("SVIES — Detector Module Test")
    print("=" * 60)

    # ── Load test image ──
    print(f"\n[1] Loading image: {image_path}")
    frame = cv2.imread(str(image_path))
    if frame is None:
        print("[ERROR] Failed to load image!")
        sys.exit(1)
    print(f"    Image shape: {frame.shape}")

    # ── Run detection ──
    print("\n[2] Running YOLOv8 detection...")
    results = detect(frame)
    print(f"    Found {len(results)} vehicle(s)")

    # ── Print results ──
    for i, det in enumerate(results):
        print(f"\n  Vehicle {i + 1}:")
        print(f"    Type:       {det.vehicle_type}")
        print(f"    Color:      {det.vehicle_color}")
        print(f"    Confidence: {det.confidence:.3f}")
        print(f"    Vehicle BB: {det.vehicle_bbox}")
        print(f"    Plate BB:   {det.plate_bbox}")
        print(f"    Plate Crop: {'Yes' if det.plate_crop is not None else 'No'}")

    # ── Draw and save annotated image ──
    if results:
        annotated = draw_detections(frame, results)
        output_path = image_path.parent / f"detected_{image_path.name}"
        cv2.imwrite(str(output_path), annotated)
        print(f"\n[3] Annotated image saved: {output_path}")

    print("\n" + "=" * 60)
    print("[✓] Detector module test completed!")
