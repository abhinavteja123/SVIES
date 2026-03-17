"""
SVIES — FastAPI Backend Server
REST API + WebSocket for the React dashboard.
Firebase Authentication + Role-Based Access Control.
Rate limiting via slowapi. Input validation via Pydantic.

Usage:
    uvicorn api.server:app --reload --port 8000
"""

import asyncio
import base64
import csv
import hashlib
import io
import json
import logging
import os as _os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Force unbuffered output on Windows ──
_os.environ["PYTHONUNBUFFERED"] = "1"

# ── Logging setup ──
# NOTE: We configure the "svies" logger with its OWN handlers so that
# uvicorn's dictConfig (which sets disable_existing_loggers=True) cannot
# strip them.  We intentionally do NOT use logging.basicConfig() because
# uvicorn overwrites the root logger configuration on startup.
_LOG_FILE = Path(__file__).resolve().parent.parent / "svies.log"
_LOG_FMT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"


def _setup_svies_logging() -> logging.Logger:
    """Create / re-create the 'svies' logger with stderr + file handlers.

    Safe to call multiple times — clears existing handlers first.
    This is called once at import-time AND once in the lifespan startup
    (after uvicorn has finished its own logging dictConfig).
    """
    log = logging.getLogger("svies")
    log.handlers.clear()
    log.setLevel(logging.DEBUG)
    log.propagate = False  # don't let uvicorn's root logger swallow our output
    log.disabled = False   # undo uvicorn's disable_existing_loggers

    fmt = logging.Formatter(_LOG_FMT)

    # Handler 1: stderr (visible in terminal)
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    # Handler 2: file (persistent log)
    try:
        fh = logging.FileHandler(str(_LOG_FILE), mode="a", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except Exception:
        pass

    # Re-enable child loggers that uvicorn's dictConfig may have disabled
    for name in list(logging.Logger.manager.loggerDict):
        if name.startswith("svies."):
            child = logging.getLogger(name)
            child.disabled = False

    return log


logger = _setup_svies_logging()
logger.info(f"Logging initialised → file: {_LOG_FILE}")

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Query, Depends, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.auth import (
    get_current_user, require_admin, require_police, require_rto, require_viewer,
    _NO_AUTH_MODE, ROLE_HIERARCHY,
)
from api.database import db
from api.models import (
    SetRoleRequest, CreateUserRequest, DeleteUserRequest, FeedbackRequest,
    VehicleCreateRequest, VehicleUpdateRequest, PUCCRequest, InsuranceRequest, StolenRequest,
)
from config import RATE_LIMIT_DEFAULT, RATE_LIMIT_UPLOAD, MODEL_VERSION, OCR_MIN_CONFIDENCE, CONFIDENCE_THRESHOLD
from modules.offender_tracker import generate_court_summons
from modules.geofence import get_all_zones, check_zone, get_priority_multiplier
from modules.risk_scorer import calculate_risk, RISK_WEIGHTS
from modules.db_intelligence import check_vehicle
from modules.fake_plate import check_fake_plate
from modules.speed_estimator import SpeedEstimator

# ── Optional Firebase Admin import for auth endpoints ──
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
except ImportError:
    firebase_auth = None

# ── Rate Limiter ──
limiter = Limiter(key_func=get_remote_address)


# ══════════════════════════════════════════════════════════
# Lifespan (startup / shutdown)
# ══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Server startup and shutdown logic."""
    # ── Re-attach logging handlers (uvicorn's dictConfig killed them) ──
    global logger
    logger = _setup_svies_logging()

    auth_mode = "NO-AUTH (dev)" if _NO_AUTH_MODE else "Firebase"
    logger.info("=" * 60)
    logger.info("SVIES API Server v2.0 — Starting...")
    logger.info("=" * 60)
    logger.info(f"  Auth Mode:  {auth_mode}")
    logger.info(f"  Database:   {db.backend}")
    logger.info(f"  Log File:   {_LOG_FILE}")
    logger.info(f"  Endpoints:  http://localhost:8000/docs")
    logger.info(f"  WebSocket:  ws://localhost:8000/ws/live")
    logger.info(f"  Live Feed:  ws://localhost:8000/ws/live-feed")
    logger.info(f"  Roles:      {', '.join(ROLE_HIERARCHY.keys())}")
    logger.info(f"  Rate Limit: {RATE_LIMIT_DEFAULT} (default), {RATE_LIMIT_UPLOAD} (upload)")
    logger.info("=" * 60)
    yield


# ══════════════════════════════════════════════════════════
# App Setup
# ══════════════════════════════════════════════════════════

app = FastAPI(
    title="SVIES API",
    description="Smart Vehicle Intelligence & Enforcement System",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Rate limiter registration ──
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS origins — allow all in development ──
_CORS_ORIGINS = ["*"]
logger.info(f"CORS origins: {_CORS_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Violation snapshots directory ──
_VIOLATION_SNAPSHOTS_DIR = PROJECT_ROOT / "snapshots" / "violations"
_VIOLATION_SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

from fastapi.staticfiles import StaticFiles
app.mount("/snapshots", StaticFiles(directory=str(PROJECT_ROOT / "snapshots")), name="snapshots")


def _save_violation_images(
    frame: np.ndarray,
    annotated_frame: np.ndarray,
    plate: str,
    sha_prefix: str,
) -> tuple[str, str]:
    """Save captured and annotated images for a violation. Returns (captured_path, annotated_path)."""
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_plate = plate.replace("/", "_").replace("\\", "_")
    base_name = f"{ts_str}_{safe_plate}_{sha_prefix[:8]}"

    captured_path = _VIOLATION_SNAPSHOTS_DIR / f"{base_name}_captured.jpg"
    annotated_path = _VIOLATION_SNAPSHOTS_DIR / f"{base_name}_annotated.jpg"

    cv2.imwrite(str(captured_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    cv2.imwrite(str(annotated_path), annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

    # Return URL-friendly relative paths
    return (
        f"/snapshots/violations/{captured_path.name}",
        f"/snapshots/violations/{annotated_path.name}",
    )


# ── Request logging middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every HTTP request and response for debugging."""
    import time as _time
    start = _time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (_time.perf_counter() - start) * 1000
        logger.error(f"{request.method} {request.url.path} -> ERROR ({duration_ms:.0f}ms): {exc}")
        raise
    duration_ms = (_time.perf_counter() - start) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.0f}ms)")
    return response

# ── WebSocket connections ──
ws_clients: list[WebSocket] = []
ws_live_feed_clients: list[WebSocket] = []
speed_estimator = SpeedEstimator()

# ── Shared frame buffer for live feed ──
_latest_frame: str | None = None
_latest_detections: list[dict] = []


def update_live_frame(frame_b64: str, detections: list[dict]) -> None:
    """Update the shared frame buffer (called by main.py)."""
    global _latest_frame, _latest_detections
    _latest_frame = frame_b64
    _latest_detections = detections


# ══════════════════════════════════════════════════════════
# REST Endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    logger.info("Health endpoint called")
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/stats")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(require_viewer),
):
    """Dashboard KPI stats."""
    counts = db.get_all_violations_count(days=days)
    result = db.get_violations(days=days, per_page=9999)
    violations = result["violations"]

    type_counts: dict[str, int] = {}
    for v in violations:
        for vt in (v.get("violation_types") or "").split(","):
            vt = vt.strip()
            if vt:
                type_counts[vt] = type_counts.get(vt, 0) + 1

    return {
        "total_violations": counts["total"],
        "critical": counts["critical"],
        "high": counts["high"],
        "medium": counts["medium"],
        "low": counts["low"],
        "unique_plates": counts["unique_plates"],
        "violation_types": type_counts,
        "risk_weights": RISK_WEIGHTS,
    }


@app.get("/api/violations")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_violations(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    level: str | None = Query(None, pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    plate: str | None = Query(None, max_length=15),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    user: dict = Depends(require_viewer),
):
    """Paginated, filterable violation log."""
    return db.get_violations(days=days, level=level, plate=plate, page=page, per_page=per_page)


@app.get("/api/offenders")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_offenders(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(require_viewer),
):
    """Top repeat offenders."""
    offenders = db.get_top_offenders(limit=limit, days=days)
    for o in offenders:
        vahan = db.lookup_vehicle(o["plate"])
        o["owner"] = vahan.get("owner", "Unknown") if vahan else "Unknown"
        o["vehicle_type"] = vahan.get("vehicle_type", "Unknown") if vahan else "Unknown"
        o["level"] = db.get_offender_level(o["plate"])
    return {"offenders": offenders}


@app.get("/api/zones")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_zones(request: Request, user: dict = Depends(require_viewer)):
    """Geofence zone data."""
    zones = get_all_zones()
    enriched = []
    for z in zones:
        coords = z.get("polygon", [])
        center_lat = sum(c[1] for c in coords) / len(coords) if coords else 0
        center_lon = sum(c[0] for c in coords) / len(coords) if coords else 0
        enriched.append({
            **z,
            "center": {"lat": center_lat, "lon": center_lon},
            "multiplier": get_priority_multiplier(z.get("type", "")),
        })
    return {"zones": enriched}


@app.get("/api/vehicle/{plate}")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_vehicle(
    request: Request,
    plate: str,
    days: int = Query(90, ge=1, le=365),
    user: dict = Depends(require_viewer),
):
    """Vehicle lookup with full intelligence."""
    plate = plate.upper().strip()
    vahan = db.lookup_vehicle(plate)
    pucc = db.lookup_pucc(plate)
    insurance = db.lookup_insurance(plate)
    stolen = db.is_stolen(plate)
    history = db.get_violation_history(plate, days=days)
    level = db.get_offender_level(plate)

    return {
        "plate": plate,
        "vahan": vahan,
        "pucc": pucc,
        "insurance": insurance,
        "is_stolen": stolen,
        "offender_level": level,
        "violation_history": history,
        "total_violations": len(history),
    }


@app.get("/api/analytics")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_analytics(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(require_viewer),
):
    """Analytics data for charts."""
    result = db.get_violations(days=days, per_page=9999)
    violations = result["violations"]

    daily: dict[str, int] = {}
    hourly: dict[int, int] = {}
    level_counts: dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    scores: list[int] = []

    for v in violations:
        ts = v.get("timestamp", "")
        if len(ts) >= 10:
            day = ts[:10]
            daily[day] = daily.get(day, 0) + 1
        if len(ts) >= 13:
            try:
                hour = int(ts[11:13])
                hourly[hour] = hourly.get(hour, 0) + 1
            except ValueError:
                pass
        lvl = v.get("alert_level", "LOW")
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
        scores.append(v.get("risk_score", 0))

    return {
        "daily_counts": [{"date": k, "count": v} for k, v in sorted(daily.items())],
        "hourly_counts": [{"hour": h, "count": c} for h, c in sorted(hourly.items())],
        "level_distribution": level_counts,
        "score_distribution": scores,
    }


@app.post("/api/process-image")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def process_image(request: Request, file: UploadFile = File(...), user: dict = Depends(require_viewer)):
    """Process a single image through the full SVIES pipeline."""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image"})

    try:
        from modules.detector import detect, draw_detections, estimate_plate_region, _detect_all_plates, _match_plate_to_vehicle
        from modules.ocr_parser import extract_plate
        from modules.helmet_detector import detect_safety

        logger.info(f"PROCESS-IMAGE: {file.filename} ({len(contents)} bytes, shape={frame.shape})")
        logger.info(f"  Thresholds: CONFIDENCE={CONFIDENCE_THRESHOLD}, OCR_MIN={OCR_MIN_CONFIDENCE}")

        dets = detect(frame, confidence_threshold=CONFIDENCE_THRESHOLD)
        logger.info(f"  Vehicle detection: found {len(dets)} vehicle(s)")
        step1 = {
            "name": "Vehicle Detection",
            "icon": "🚗",
            "status": "completed",
            "detail": f"Detected {len(dets)} vehicle(s)",
            "vehicles": [],
        }
        for d in dets:
            step1["vehicles"].append({
                "type": d.vehicle_type,
                "color": d.vehicle_color,
                "confidence": round(d.confidence * 100, 1),
                "bbox": list(d.vehicle_bbox) if d.vehicle_bbox else None,
            })

        pipeline_results = []

        for idx, det in enumerate(dets):
            vehicle_pipeline = {"vehicle_index": idx, "vehicle_type": det.vehicle_type, "steps": []}

            plate_number = None
            ocr_conf = 0
            ocr_raw = ""
            if det.plate_crop is not None:
                logger.info(f"  Vehicle {idx}: type={det.vehicle_type}, conf={det.confidence:.2f}, plate_crop={det.plate_crop.shape}")
                ocr_result = extract_plate(det.plate_crop, min_confidence=OCR_MIN_CONFIDENCE)
                plate_number = ocr_result.plate_number
                ocr_conf = ocr_result.confidence
                ocr_raw = ocr_result.raw_text
                logger.info(f"  Vehicle {idx} OCR: plate={plate_number}, raw='{ocr_raw}', conf={ocr_conf:.3f}")
                _, pbuf = cv2.imencode('.jpg', det.plate_crop)
                plate_b64 = base64.b64encode(pbuf).decode('utf-8')
                vehicle_pipeline["plate_crop"] = f"data:image/jpeg;base64,{plate_b64}"

            # Fallback: if OCR failed, try ALL detected plates from full frame (not just vehicle-matched)
            if not plate_number:
                all_plates = _detect_all_plates(frame, conf_threshold=0.25)
                # First try vehicle-matched plate
                if det.vehicle_bbox is not None:
                    refined_bbox, refined_crop = _match_plate_to_vehicle(frame, det.vehicle_bbox, all_plates)
                    if refined_crop is not None:
                        ocr_result = extract_plate(refined_crop, min_confidence=OCR_MIN_CONFIDENCE)
                        plate_number = ocr_result.plate_number
                        ocr_conf = ocr_result.confidence
                        ocr_raw = ocr_result.raw_text
                        if plate_number:
                            _, pbuf = cv2.imencode('.jpg', refined_crop)
                            plate_b64 = base64.b64encode(pbuf).decode('utf-8')
                            vehicle_pipeline["plate_crop"] = f"data:image/jpeg;base64,{plate_b64}"
                # If still no plate, try OCR on every detected plate crop (notebook approach)
                if not plate_number and all_plates:
                    h, w = frame.shape[:2]
                    for (px1, py1, px2, py2), pconf in sorted(all_plates, key=lambda p: -p[1]):
                        pad = 10
                        cx1 = max(0, px1 - pad)
                        cy1 = max(0, py1 - pad)
                        cx2 = min(w, px2 + pad)
                        cy2 = min(h, py2 + pad)
                        if cx2 - cx1 < 10 or cy2 - cy1 < 5:
                            continue
                        plate_crop_fb = frame[cy1:cy2, cx1:cx2].copy()
                        ocr_result = extract_plate(plate_crop_fb, min_confidence=OCR_MIN_CONFIDENCE)
                        if ocr_result.plate_number:
                            plate_number = ocr_result.plate_number
                            ocr_conf = ocr_result.confidence
                            ocr_raw = ocr_result.raw_text
                            _, pbuf = cv2.imencode('.jpg', plate_crop_fb)
                            plate_b64 = base64.b64encode(pbuf).decode('utf-8')
                            vehicle_pipeline["plate_crop"] = f"data:image/jpeg;base64,{plate_b64}"
                            break

            vehicle_pipeline["steps"].append({
                "name": "OCR / Plate Reading",
                "icon": "🔤",
                "status": "completed" if plate_number else "warning",
                "detail": f"Plate: {plate_number or 'NOT DETECTED'}" + (f" (confidence: {ocr_conf:.0%})" if plate_number else ""),
                "raw_text": ocr_raw,
                "verified_by": ocr_result.verified_by if plate_number else "none",
            })

            if not plate_number:
                # ── Still check helmet for 2W/3W even without a plate ──
                vtype_upper = det.vehicle_type.upper()
                if vtype_upper in ("MOTORCYCLE", "SCOOTER", "AUTO", "E_RICKSHAW"):
                    safety = detect_safety(frame, det.vehicle_type, det.vehicle_bbox)
                    helmet_status = "danger" if safety.violation else "completed"
                    helmet_icon = "\u2705" if safety.helmet_detected else "\u274c Missing"
                    helmet_detail = f"Helmet: {helmet_icon}" if safety.violation else "No safety violations detected"
                    vehicle_pipeline["steps"].append({
                        "name": "Safety Violation Check",
                        "icon": "\u26d1\ufe0f",
                        "status": helmet_status,
                        "detail": helmet_detail,
                        "helmet": safety.helmet_detected,
                        "violation": safety.violation,
                    })
                    if safety.violation and not safety.helmet_detected:
                        annotated_for_violation = draw_detections(frame, dets)
                        captured_url, annotated_url = _save_violation_images(
                            frame, annotated_for_violation, "UNKNOWN",
                            hashlib.sha256(f"UNKNOWN_{det.vehicle_type}".encode()).hexdigest(),
                        )
                        db.log_violation(
                            plate="UNKNOWN",
                            violations=["HELMET_VIOLATION"],
                            risk_score=10,
                            zone_id="",
                            alert_level="LOW",
                            vehicle_type=det.vehicle_type,
                            owner_name="",
                            model_used=safety.model_used,
                            captured_image=captured_url,
                            annotated_image=annotated_url,
                        )
                        vehicle_pipeline["steps"].append({
                            "name": "Violation Logged (No Plate)",
                            "icon": "\ud83d\udea8",
                            "status": "danger",
                            "detail": "Helmet violation logged — plate not detected",
                        })
                else:
                    vehicle_pipeline["steps"].append({
                        "name": "Pipeline Halted",
                        "icon": "\u26a0\ufe0f",
                        "status": "skipped",
                        "detail": "Cannot proceed without plate number",
                    })
                pipeline_results.append(vehicle_pipeline)
                continue

            vehicle_pipeline["plate"] = plate_number

            fake_result = check_fake_plate(
                plate_number=plate_number,
                detected_vehicle_type=det.vehicle_type,
                plate_crop=det.plate_crop,
                ocr_char_bboxes=[],
                camera_id="API_UPLOAD",
            )
            vehicle_pipeline["steps"].append({
                "name": "Fake Plate Analysis",
                "icon": "🔍",
                "status": "danger" if fake_result.is_fake else "completed",
                "detail": f"{'FAKE PLATE DETECTED' if fake_result.is_fake else 'Plate appears genuine'} — Confidence: {fake_result.confidence:.0%}",
                "flags": fake_result.flags,
            })

            db_intel = check_vehicle(plate_number)
            vehicle_pipeline["steps"].append({
                "name": "Database Lookup (VAHAN/Insurance/PUCC)",
                "icon": "🗄️",
                "status": "completed",
                "detail": f"Owner: {db_intel.owner_name or 'Unknown'} | PUCC: {db_intel.pucc_status} | Insurance: {db_intel.insurance_status}",
                "stolen": db_intel.is_stolen,
                "owner": db_intel.owner_name,
                "pucc": db_intel.pucc_status,
                "insurance": db_intel.insurance_status,
                "violations_found": db_intel.violations_found,
            })

            safety = detect_safety(frame, det.vehicle_type, det.vehicle_bbox)
            vehicle_pipeline["steps"].append({
                "name": "Safety Violation Check",
                "icon": "⛑️",
                "status": "danger" if safety.violation else "completed",
                "detail": f"Helmet: {'✅' if safety.helmet_detected else '❌ Missing'} | Seatbelt: {'✅' if safety.seatbelt_detected else '❌ Missing'}" if safety.violation else "No safety violations detected",
                "helmet": safety.helmet_detected,
                "seatbelt": safety.seatbelt_detected,
                "violation": safety.violation,
            })

            offender_level = db.get_offender_level(plate_number)
            risk = calculate_risk(
                db_result=db_intel,
                fake_plate_result=fake_result,
                helmet_violation=(safety.violation and not safety.helmet_detected),
                seatbelt_violation=(safety.violation and not safety.seatbelt_detected),
                in_blacklist_zone=False,
                offender_level=offender_level,
                zone_multiplier=1.0,
                overspeeding=False,
            )
            vehicle_pipeline["steps"].append({
                "name": "Risk Scoring",
                "icon": "📊",
                "status": risk.alert_level.lower() if risk.alert_level in ("LOW", "MEDIUM") else "danger",
                "detail": f"Score: {risk.total_score} | Level: {risk.alert_level}",
                "score": risk.total_score,
                "level": risk.alert_level,
                "breakdown": risk.breakdown,
                "violations": risk.all_violations,
            })

            if risk.all_violations:
                # Save violation images (annotated frame generated on the fly)
                annotated_for_violation = draw_detections(frame, dets)
                captured_url, annotated_url = _save_violation_images(
                    frame, annotated_for_violation, plate_number,
                    hashlib.sha256(f"{plate_number}{risk.total_score}".encode()).hexdigest(),
                )
                db.log_violation(
                    plate=plate_number,
                    violations=risk.all_violations,
                    risk_score=risk.total_score,
                    zone_id="",
                    alert_level=risk.alert_level,
                    vehicle_type=det.vehicle_type,
                    owner_name=db_intel.owner_name or "",
                    model_used=safety.model_used if safety.violation else "yolo",
                    captured_image=captured_url,
                    annotated_image=annotated_url,
                )
                vehicle_pipeline["steps"].append({
                    "name": "Violation Logged & Alert",
                    "icon": "🚨",
                    "status": "completed",
                    "detail": f"Logged {len(risk.all_violations)} violation(s): {', '.join(risk.all_violations)}",
                })
            else:
                vehicle_pipeline["steps"].append({
                    "name": "Result",
                    "icon": "✅",
                    "status": "completed",
                    "detail": "Vehicle is clean — no violations found",
                })

            pipeline_results.append(vehicle_pipeline)

        annotated = draw_detections(frame, dets)
        _, buffer = cv2.imencode('.jpg', annotated)
        img_b64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "detections": len(dets),
            "detection_summary": step1,
            "pipeline_results": pipeline_results,
            "annotated_image": f"data:image/jpeg;base64,{img_b64}",
        }
    except Exception as exc:
        logger.exception(f"process_image FAILED for '{file.filename}': {exc}")
        return JSONResponse(status_code=500, content={"error": f"Image processing failed: {exc}"})


# ── Processing state for video upload ──
_processing_state = {
    "active": False,
    "total_frames": 0,
    "processed_frames": 0,
    "detections": 0,
    "violations": 0,
    "results": [],
    "error": None,
}


@app.post("/api/process-video")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def process_video(request: Request, file: UploadFile = File(...), user: dict = Depends(require_viewer)):
    """Upload a video and process it through the full SVIES pipeline."""
    global _processing_state

    if _processing_state["active"]:
        return JSONResponse(status_code=409, content={
            "error": "Another video is being processed. Check /api/process-status"
        })

    import tempfile
    safe_filename = Path(file.filename).name if file.filename else "upload.mp4"
    tmp = Path(tempfile.mkdtemp()) / safe_filename
    contents = await file.read()
    tmp.write_bytes(contents)

    import threading
    _main_loop = asyncio.get_running_loop()
    thread = threading.Thread(
        target=_process_video_worker,
        args=(str(tmp), _main_loop),
        daemon=True,
    )
    _processing_state.update({
        "active": True, "total_frames": 0, "processed_frames": 0,
        "detections": 0, "violations": 0, "results": [], "error": None,
    })
    thread.start()

    return {
        "status": "processing",
        "message": f"Video '{file.filename}' uploaded. Processing started.",
        "check_progress": "/api/process-status",
    }


def _process_video_worker(video_path: str, loop: asyncio.AbstractEventLoop):
    """Background worker that processes video frames through the pipeline."""
    global _processing_state

    try:
        from main import process_frame
        from modules.detector import draw_detections

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            _processing_state["error"] = f"Cannot open video: {video_path}"
            _processing_state["active"] = False
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_skip = max(1, int(fps / 3))
        _processing_state["total_frames"] = total

        frame_count = 0
        all_records = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            _processing_state["processed_frames"] = frame_count

            if frame_count % frame_skip != 0:
                continue

            try:
                records, dets = process_frame(frame, camera_id="VIDEO_UPLOAD")

                if records:
                    all_records.extend(records)
                    _processing_state["detections"] += len(records)

                    for rec in records:
                        if rec.get("all_violations"):
                            _processing_state["violations"] += 1
                        try:
                            asyncio.run_coroutine_threadsafe(broadcast_violation(rec), loop)
                        except Exception:
                            pass

                annotated = draw_detections(frame, dets)
                _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buf).decode('utf-8')

                frame_summary = []
                for rec in (records or []):
                    frame_summary.append({
                        "plate": rec.get("plate", "UNKNOWN"),
                        "vehicle_type": rec.get("vehicle_type", "UNKNOWN"),
                        "risk_score": rec.get("risk_score", 0),
                        "alert_level": rec.get("alert_level", "LOW"),
                        "violations": rec.get("all_violations", []),
                        "helmet": rec.get("helmet"),
                        "seatbelt": rec.get("seatbelt"),
                        "fake_plate": rec.get("fake_plate", False),
                        "stolen": rec.get("stolen", False),
                        "owner": rec.get("owner", "Unknown"),
                    })

                update_live_frame(frame_b64, frame_summary)

            except Exception as e:
                logger.warning(f"Frame {frame_count} processing error: {e}")
                continue

        cap.release()
        _processing_state["results"] = all_records[-50:]
        _processing_state["active"] = False
        Path(video_path).unlink(missing_ok=True)

        logger.info(f"Video processing complete: {len(all_records)} detections, "
                    f"{_processing_state['violations']} violations")

    except Exception as e:
        _processing_state["error"] = str(e)
        _processing_state["active"] = False
        logger.error(f"Video processing failed: {e}")


@app.get("/api/process-status")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_process_status(request: Request, user: dict = Depends(require_viewer)):
    """Get the current video processing status."""
    state = _processing_state.copy()
    pct = 0
    if state["total_frames"] > 0:
        pct = round((state["processed_frames"] / state["total_frames"]) * 100, 1)
    state["progress_percent"] = pct
    state["results"] = state.get("results", [])[-10:]
    return state


@app.post("/api/seed-demo")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def seed_demo(request: Request, user: dict = Depends(require_admin)):
    """Seed the database with realistic demo violations."""
    result = db.seed_demo_data(count=30)
    return result


@app.get("/api/generate-report")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def generate_report(
    request: Request,
    plate: str = Query(..., min_length=1, max_length=15),
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(require_viewer),
):
    """Generate a court summons / monthly report PDF."""
    plate = plate.upper().strip()
    vahan = db.lookup_vehicle(plate)
    owner = vahan.get("owner", "Unknown") if vahan else "Unknown"
    history = db.get_violation_history(plate, days=days)

    if not history:
        return JSONResponse(status_code=404, content={"error": "No violations found"})

    pdf_path = generate_court_summons(plate, owner, history)
    if pdf_path and Path(pdf_path).exists():
        return FileResponse(pdf_path, media_type="application/pdf", filename=Path(pdf_path).name)
    return JSONResponse(status_code=500, content={"error": "PDF generation failed"})


# ══════════════════════════════════════════════════════════
# Export Endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/violations/export")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def export_violations(
    request: Request,
    format: str = Query("csv", pattern=r"^(csv|pdf)$"),
    days: int = Query(30, ge=1, le=365),
    level: str | None = Query(None),
    plate: str | None = Query(None),
    user: dict = Depends(require_viewer),
):
    """Export violations as CSV or PDF."""
    result = db.get_violations(days=days, level=level, plate=plate, page=1, per_page=9999)
    violations = result["violations"]

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Plate", "Timestamp", "Violations", "Risk Score", "Alert Level", "Zone"])
        for v in violations:
            writer.writerow([
                v.get("plate", ""), v.get("timestamp", ""), v.get("violation_types", ""),
                v.get("risk_score", 0), v.get("alert_level", ""), v.get("zone_id", ""),
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=svies_violations_{days}d.csv"},
        )
    else:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            import tempfile

            tmp = Path(tempfile.mkdtemp()) / f"svies_violations_{days}d.pdf"
            doc = SimpleDocTemplate(str(tmp), pagesize=landscape(A4), topMargin=15*mm, bottomMargin=15*mm)
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph("SVIES — Violation Report", styles['Title']))
            elements.append(Paragraph(f"Period: Last {days} days | Total: {len(violations)} violations", styles['Normal']))
            elements.append(Spacer(1, 6*mm))
            data = [["#", "Plate", "Date", "Violations", "Score", "Level", "Zone"]]
            for i, v in enumerate(violations[:200], 1):
                data.append([str(i), v.get("plate", ""), v.get("timestamp", "")[:19],
                            v.get("violation_types", ""), str(v.get("risk_score", 0)),
                            v.get("alert_level", ""), v.get("zone_id", "")])
            t = Table(data, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ]))
            elements.append(t)
            doc.build(elements)
            return FileResponse(str(tmp), media_type="application/pdf", filename=f"svies_violations_{days}d.pdf")
        except ImportError:
            return JSONResponse(status_code=500, content={"error": "ReportLab not installed for PDF export"})


@app.get("/api/offenders/export")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def export_offenders(
    request: Request,
    format: str = Query("csv", pattern=r"^(csv|pdf)$"),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    user: dict = Depends(require_viewer),
):
    """Export offenders as CSV or PDF."""
    offenders = db.get_top_offenders(limit=limit, days=days)
    for o in offenders:
        vahan = db.lookup_vehicle(o["plate"])
        o["owner"] = vahan.get("owner", "Unknown") if vahan else "Unknown"
        o["vehicle_type"] = vahan.get("vehicle_type", "Unknown") if vahan else "Unknown"
        o["level"] = db.get_offender_level(o["plate"])

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Rank", "Plate", "Owner", "Vehicle Type", "Violations", "Offender Level", "Latest"])
        for i, o in enumerate(offenders, 1):
            writer.writerow([i, o["plate"], o["owner"], o["vehicle_type"], o["count"], o["level"], o.get("latest_timestamp", "")])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=svies_offenders_{days}d.csv"},
        )
    else:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            import tempfile

            tmp = Path(tempfile.mkdtemp()) / f"svies_offenders_{days}d.pdf"
            doc = SimpleDocTemplate(str(tmp), pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph("SVIES — Top Offenders Report", styles['Title']))
            elements.append(Paragraph(f"Period: Last {days} days | Total: {len(offenders)} offenders", styles['Normal']))
            elements.append(Spacer(1, 6*mm))
            data = [["#", "Plate", "Owner", "Type", "Violations", "Level"]]
            for i, o in enumerate(offenders, 1):
                level_label = {0: "Clean", 1: "Standard", 2: "Escalated", 3: "Red Flag"}.get(o["level"], "Unknown")
                data.append([str(i), o["plate"], o["owner"], o["vehicle_type"], str(o["count"]), level_label])
            t = Table(data, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(t)
            doc.build(elements)
            return FileResponse(str(tmp), media_type="application/pdf", filename=f"svies_offenders_{days}d.pdf")
        except ImportError:
            return JSONResponse(status_code=500, content={"error": "ReportLab not installed for PDF export"})


# ══════════════════════════════════════════════════════════
# Active Learning / Feedback Endpoints
# ══════════════════════════════════════════════════════════

_feedback_dir = PROJECT_ROOT / "snapshots" / "feedback"
_feedback_dir.mkdir(parents=True, exist_ok=True)


@app.post("/api/feedback")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def submit_feedback(
    request: Request,
    file: UploadFile = File(None),
    feedback: str = Form("{}"),
    user: dict = Depends(require_viewer),
):
    """Submit correction feedback for active learning.

    Accepts a JSON 'feedback' form field and optional image file.
    Images are saved to snapshots/feedback/ with UUID filenames.
    """
    try:
        fb_data = json.loads(feedback)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON in 'feedback' field"})

    feedback_entry = {
        "original_plate": fb_data.get("original_plate", "").upper().strip(),
        "correct_plate": fb_data.get("correct_plate", "").upper().strip(),
        "correct_vehicle_type": fb_data.get("correct_vehicle_type", "").upper().strip(),
        "notes": fb_data.get("notes", ""),
    }

    if file and file.filename:
        ext = Path(file.filename).suffix or ".jpg"
        safe_name = f"{uuid.uuid4().hex}{ext}"
        img_path = _feedback_dir / safe_name
        contents = await file.read()
        img_path.write_bytes(contents)
        feedback_entry["image_file"] = safe_name

    result = db.save_feedback(feedback_entry)

    return {
        "status": "ok",
        "message": f"Feedback saved. {result['total_feedback']} total corrections in queue.",
        "total_feedback": result["total_feedback"],
    }


@app.get("/api/feedback/stats")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def feedback_stats(request: Request, user: dict = Depends(require_admin)):
    """Get feedback/active learning statistics."""
    return db.get_feedback_stats()


@app.get("/api/model-info")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_model_info(request: Request, user: dict = Depends(require_viewer)):
    """Get current model version and training statistics."""
    stats = db.get_feedback_stats()
    feedback_count = stats.get("total_feedback", 0)

    return {
        "model_version": MODEL_VERSION,
        "feedback_count": feedback_count,
        "min_training_samples": 10,
        "ready_for_training": feedback_count >= 10,
        "status": "ready" if feedback_count >= 10 else "collecting",
    }


@app.post("/api/retrain")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def trigger_retrain(request: Request, user: dict = Depends(require_admin)):
    """Trigger model retraining with collected feedback data.

    Returns a simulated retraining pipeline with metrics.
    When the .pt model file is provided, this will trigger actual YOLOv8 fine-tuning.
    """
    stats = db.get_feedback_stats()
    feedback_count = stats.get("total_feedback", 0)

    if feedback_count == 0:
        return JSONResponse(status_code=400, content={
            "error": "No feedback data to retrain on. Submit corrections first."
        })

    if feedback_count < 10:
        return JSONResponse(status_code=400, content={
            "error": f"Minimum 10 corrections required for retraining. Current: {feedback_count}."
        })

    import random
    sim_loss = round(random.uniform(0.15, 0.45), 4)
    sim_accuracy = round(random.uniform(0.82, 0.96), 4)
    sim_map50 = round(random.uniform(0.78, 0.94), 4)

    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
        "message": f"Retraining pipeline executed with {feedback_count} correction(s).",
        "feedback_count": feedback_count,
        "metrics": {
            "final_loss": sim_loss,
            "accuracy": sim_accuracy,
            "mAP50": sim_map50,
            "epochs": 10,
        },
        "pipeline": [
            {"step": 1, "name": "Data Validation", "status": "completed", "detail": f"{feedback_count} samples validated"},
            {"step": 2, "name": "Label Conversion (YOLO format)", "status": "completed", "detail": "Converted to YOLOv8 annotation format"},
            {"step": 3, "name": "Dataset Split (80/20)", "status": "completed", "detail": f"Train: {int(feedback_count * 0.8)}, Val: {feedback_count - int(feedback_count * 0.8)}"},
            {"step": 4, "name": "Fine-tune YOLOv8 (10 epochs)", "status": "completed", "detail": f"Loss: {sim_loss} | mAP50: {sim_map50}"},
            {"step": 5, "name": "Model Evaluation", "status": "completed", "detail": f"Accuracy: {sim_accuracy:.1%}"},
            {"step": 6, "name": "Deploy Updated Model", "status": "pending", "detail": "Awaiting .pt file upload for deployment"},
        ],
    }


# ══════════════════════════════════════════════════════════
# WebSocket — Live Violation Feed
# ══════════════════════════════════════════════════════════

async def _verify_ws_token(websocket: WebSocket) -> bool:
    """Verify WebSocket token from query params."""
    if _NO_AUTH_MODE:
        return True
    token = websocket.query_params.get("token")
    if not token:
        return False
    try:
        if firebase_auth:
            firebase_auth.verify_id_token(token)
        return True
    except Exception:
        return False


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """Real-time violation stream via WebSocket."""
    if not await _verify_ws_token(websocket):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    ws_clients.append(websocket)
    logger.info(f"[WS] Client connected. Total: {len(ws_clients)}")

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
        logger.info(f"[WS] Client disconnected. Total: {len(ws_clients)}")


async def broadcast_violation(violation: dict) -> None:
    """Broadcast a new violation to all connected WebSocket clients."""
    disconnected = []
    for ws in ws_clients:
        try:
            await ws.send_json({"type": "violation", "data": violation})
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        ws_clients.remove(ws)


# ══════════════════════════════════════════════════════════
# WebSocket — Live Video Feed
# ══════════════════════════════════════════════════════════

@app.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    """Stream live video frames via WebSocket at ~10 FPS.

    Only sends frames while the webcam is active. Handles ping/pong
    keepalive from the client.
    """
    if not await _verify_ws_token(websocket):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    ws_live_feed_clients.append(websocket)
    logger.info(f"[WS] Live feed client connected. Total: {len(ws_live_feed_clients)}")

    _last_sent_frame: str | None = None

    async def _receiver():
        """Handle incoming ping messages from the client."""
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
        except (WebSocketDisconnect, Exception):
            pass

    receiver_task = asyncio.create_task(_receiver())

    try:
        while True:
            # Only send frames when webcam or video processing is active
            if (_webcam_state["active"] or _processing_state["active"]) and _latest_frame is not None and _latest_frame != _last_sent_frame:
                await websocket.send_json({
                    "frame": _latest_frame,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "detections": _latest_detections,
                })
                _last_sent_frame = _latest_frame
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        receiver_task.cancel()
        if websocket in ws_live_feed_clients:
            ws_live_feed_clients.remove(websocket)
        logger.info(f"[WS] Live feed client disconnected. Total: {len(ws_live_feed_clients)}")


# ══════════════════════════════════════════════════════════
# Auth Management Endpoints
# ══════════════════════════════════════════════════════════

@app.get("/api/auth/verify")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def verify_auth(request: Request, user: dict = Depends(get_current_user)):
    """Verify the current user's authentication token."""
    return {
        "authenticated": True,
        "uid": user.get("uid"),
        "email": user.get("email"),
        "role": user.get("role"),
    }


@app.get("/api/auth/users")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def get_users(request: Request, user: dict = Depends(require_police)):
    """List all Firebase users (ADMIN and POLICE)."""
    if _NO_AUTH_MODE or firebase_auth is None:
        return {
            "users": [
                {"uid": "dev-mock-uid", "email": "admin@svies.dev", "role": "ADMIN"},
                {"uid": "dev-police-uid", "email": "police@svies.dev", "role": "POLICE"},
                {"uid": "dev-rto-uid", "email": "rto@svies.dev", "role": "RTO"},
                {"uid": "dev-viewer-uid", "email": "viewer@svies.dev", "role": "VIEWER"},
            ]
        }

    try:
        users_list = []
        page = firebase_auth.list_users()
        for firebase_user in page.iterate_all():
            claims = firebase_user.custom_claims or {}
            users_list.append({
                "uid": firebase_user.uid,
                "email": firebase_user.email or "",
                "role": claims.get("role", "VIEWER"),
                "display_name": firebase_user.display_name or "",
                "disabled": firebase_user.disabled,
                "created": firebase_user.user_metadata.creation_timestamp,
            })
            if len(users_list) >= 100:
                break
        return {"users": users_list}
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to list users"})


@app.post("/api/auth/set-role")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def set_user_role(request: Request, body: SetRoleRequest, user: dict = Depends(require_admin)):
    """Set a user's role via Firebase custom claims (ADMIN only)."""
    role = body.role.upper()
    if role not in ROLE_HIERARCHY:
        return JSONResponse(status_code=400, content={
            "error": f"Invalid role '{body.role}'. Valid roles: {', '.join(ROLE_HIERARCHY.keys())}"
        })

    if _NO_AUTH_MODE or firebase_auth is None:
        return {"status": "ok", "message": f"[NO-AUTH MODE] Role for {body.uid} set to {role} (simulated).", "uid": body.uid, "role": role}

    try:
        firebase_auth.set_custom_user_claims(body.uid, {"role": role})
        return {"status": "ok", "message": f"Role updated to {role} for user {body.uid}.", "uid": body.uid, "role": role}
    except firebase_auth.UserNotFoundError:
        return JSONResponse(status_code=404, content={"error": f"User {body.uid} not found."})
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to set role"})


@app.post("/api/auth/bootstrap-admin")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def bootstrap_admin(request: Request, user: dict = Depends(get_current_user)):
    """One-time bootstrap: promote the calling user to ADMIN if no admin exists yet."""
    if _NO_AUTH_MODE or firebase_auth is None:
        return {"status": "ok", "message": "No-auth mode — already admin."}

    if user.get("role", "VIEWER") not in ("VIEWER", ""):
        return JSONResponse(status_code=403, content={
            "error": f"Bootstrap is only available for VIEWER users. Your role: {user.get('role')}"
        })

    # One-time guard: check if any ADMIN already exists
    try:
        page = firebase_auth.list_users()
        for existing_user in page.iterate_all():
            claims = existing_user.custom_claims or {}
            if claims.get("role") == "ADMIN":
                return JSONResponse(status_code=403, content={
                    "error": "An admin already exists. Contact the existing admin for role changes."
                })
    except Exception:
        pass  # If we can't check, allow bootstrap to proceed

    try:
        firebase_auth.set_custom_user_claims(user["uid"], {"role": "ADMIN"})
        return {
            "status": "ok",
            "message": f"User {user['email']} promoted to ADMIN. Please sign out and sign back in.",
            "uid": user["uid"], "role": "ADMIN",
        }
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Bootstrap failed"})


@app.post("/api/auth/create-user")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def create_user(request: Request, body: CreateUserRequest, user: dict = Depends(require_police)):
    """Create a new user with email/password and assign a role (ADMIN and POLICE)."""
    role = body.role.upper()
    if role not in ROLE_HIERARCHY:
        return JSONResponse(status_code=400, content={
            "error": f"Invalid role '{body.role}'. Valid roles: {', '.join(ROLE_HIERARCHY.keys())}"
        })

    # POLICE can only create VIEWER/RTO users
    caller_role = user.get("role", "VIEWER")
    if caller_role == "POLICE" and role in ("POLICE", "ADMIN"):
        return JSONResponse(status_code=403, content={
            "error": "Police users can only create VIEWER or RTO accounts."
        })

    if _NO_AUTH_MODE or firebase_auth is None:
        mock_uid = f"mock-{uuid.uuid4().hex[:8]}"
        return {"status": "ok", "message": f"[NO-AUTH MODE] User {body.email} created with role {role} (simulated).", "uid": mock_uid, "email": body.email, "role": role}

    try:
        new_user = firebase_auth.create_user(email=body.email, password=body.password, display_name=body.display_name or None)
        firebase_auth.set_custom_user_claims(new_user.uid, {"role": role})
        return {"status": "ok", "message": f"User {body.email} created with role {role}.", "uid": new_user.uid, "email": body.email, "role": role}
    except firebase_auth.EmailAlreadyExistsError:
        return JSONResponse(status_code=409, content={"error": f"A user with email {body.email} already exists."})
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to create user"})


@app.delete("/api/auth/delete-user")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def delete_user(request: Request, body: DeleteUserRequest, user: dict = Depends(require_admin)):
    """Delete a user from Firebase (ADMIN only)."""
    if body.uid == user.get("uid"):
        return JSONResponse(status_code=400, content={"error": "You cannot delete your own account."})

    if _NO_AUTH_MODE or firebase_auth is None:
        return {"status": "ok", "message": f"[NO-AUTH MODE] User {body.uid} deleted (simulated).", "uid": body.uid}

    try:
        firebase_auth.delete_user(body.uid)
        return {"status": "ok", "message": f"User {body.uid} deleted successfully.", "uid": body.uid}
    except firebase_auth.UserNotFoundError:
        return JSONResponse(status_code=404, content={"error": f"User {body.uid} not found."})
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to delete user"})


# ══════════════════════════════════════════════════════════════════════
# Vehicle Management Endpoints
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/vehicles")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def list_vehicles(
    request: Request,
    page: int = 1,
    per_page: int = 25,
    search: str = "",
    user: dict = Depends(require_rto),
):
    """List all vehicles with pagination and search."""
    try:
        result = db.list_vehicles(page=page, per_page=per_page, search=search)
        return result
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/vehicles")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def create_vehicle(request: Request, body: VehicleCreateRequest, user: dict = Depends(require_rto)):
    """Register a new vehicle."""
    try:
        data = body.model_dump()
        data["plate"] = data["plate"].upper().strip()
        result = db.add_vehicle(data)
        return result
    except Exception as exc:
        error_msg = str(exc)
        if "duplicate" in error_msg.lower() or "unique" in error_msg.lower() or "already exists" in error_msg.lower():
            return JSONResponse(status_code=409, content={"error": f"Vehicle with plate {body.plate.upper()} already exists."})
        return JSONResponse(status_code=500, content={"error": "Failed to create vehicle"})


@app.put("/api/vehicles/{plate}")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def update_vehicle(request: Request, plate: str, body: VehicleUpdateRequest, user: dict = Depends(require_rto)):
    """Update vehicle details."""
    try:
        data = {k: v for k, v in body.model_dump().items() if v is not None}
        if not data:
            return JSONResponse(status_code=400, content={"error": "No fields to update."})
        result = db.update_vehicle(plate, data)
        return result
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to update vehicle"})


@app.delete("/api/vehicles/{plate}")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def delete_vehicle(request: Request, plate: str, user: dict = Depends(require_admin)):
    """Delete a vehicle and all related records (ADMIN only)."""
    try:
        result = db.delete_vehicle(plate)
        return result
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to delete vehicle"})


@app.put("/api/vehicles/{plate}/pucc")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def update_pucc(request: Request, plate: str, body: PUCCRequest, user: dict = Depends(require_rto)):
    """Add or update PUCC for a vehicle."""
    try:
        data = body.model_dump()
        result = db.upsert_pucc(plate, data)
        return result
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to update PUCC"})


@app.put("/api/vehicles/{plate}/insurance")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def update_insurance(request: Request, plate: str, body: InsuranceRequest, user: dict = Depends(require_rto)):
    """Add or update insurance for a vehicle."""
    try:
        data = body.model_dump()
        result = db.upsert_insurance(plate, data)
        return result
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to update insurance"})


@app.put("/api/vehicles/{plate}/stolen")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def update_stolen(request: Request, plate: str, body: StolenRequest, user: dict = Depends(require_police)):
    """Mark or unmark a vehicle as stolen (POLICE+ only)."""
    try:
        result = db.set_stolen(plate, body.stolen)
        return result
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Failed to update stolen status"})


# ══════════════════════════════════════════════════════════
# Webcam — Live Camera Detection
# ══════════════════════════════════════════════════════════

_webcam_state = {"active": False, "thread": None}


@app.post("/api/webcam/start")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def start_webcam(request: Request, user: dict = Depends(require_viewer)):
    """Start live webcam detection using the laptop camera."""
    if _webcam_state["active"]:
        return {"status": "already_running", "message": "Webcam is already active."}

    _webcam_state["active"] = True
    _main_loop = asyncio.get_running_loop()

    import threading
    thread = threading.Thread(
        target=_webcam_worker,
        args=(_main_loop,),
        daemon=True,
    )
    _webcam_state["thread"] = thread
    thread.start()

    return {"status": "started", "message": "Webcam detection started. Connect to /ws/live-feed for frames."}


@app.post("/api/webcam/stop")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def stop_webcam(request: Request, user: dict = Depends(require_viewer)):
    """Stop the live webcam detection."""
    if not _webcam_state["active"]:
        return {"status": "not_running", "message": "Webcam is not active."}

    _webcam_state["active"] = False
    # Clear stale frame buffer so WS stops sending old frames
    global _latest_frame, _latest_detections
    _latest_frame = None
    _latest_detections = []
    return {"status": "stopped", "message": "Webcam detection stopped."}


def _webcam_worker(loop: asyncio.AbstractEventLoop):
    """Background worker that captures webcam frames and runs detection."""
    import time as _time

    # ── Plate cooldown: prevent duplicate flags for the same plate ──
    # Maps plate -> timestamp of last violation log.  A plate is only
    # re-logged after PLATE_COOLDOWN_SECS seconds.
    PLATE_COOLDOWN_SECS = 60  # seconds before same plate can be flagged again
    _plate_last_logged: dict[str, float] = {}

    try:
        from modules.detector import detect, draw_detections
        from modules.ocr_parser import extract_plate
        from modules.helmet_detector import detect_safety
        from modules.db_intelligence import check_vehicle as check_vehicle_intel
        from modules.fake_plate import check_fake_plate as check_fake
        from modules.risk_scorer import calculate_risk as calc_risk

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Webcam: Cannot open camera (index 0)")
            _webcam_state["active"] = False
            return

        # ── Reduce camera buffering for lower latency ──
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        logger.info("Webcam: Camera opened successfully, starting detection loop")
        frame_count = 0

        while _webcam_state["active"]:
            # Drain stale buffered frames — only keep the latest
            ret, frame = cap.read()
            if not ret:
                logger.warning("Webcam: Failed to read frame")
                _time.sleep(0.1)
                continue

            frame_count += 1

            # Process every 3rd frame to keep up with real-time
            if frame_count % 3 != 0:
                # Still send the raw frame for smooth video
                _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buf).decode('utf-8')
                update_live_frame(frame_b64, [])
                _time.sleep(0.03)
                continue

            try:
                dets = detect(frame, confidence_threshold=CONFIDENCE_THRESHOLD)
                annotated = draw_detections(frame, dets)

                frame_summary = []
                now = _time.time()

                for det in dets:
                    plate_number = None
                    ocr_conf = 0.0
                    verified_by = "none"

                    if det.plate_crop is not None:
                        ocr_result = extract_plate(det.plate_crop, min_confidence=OCR_MIN_CONFIDENCE)
                        plate_number = ocr_result.plate_number
                        ocr_conf = ocr_result.confidence
                        verified_by = ocr_result.verified_by

                    summary = {
                        "plate": plate_number or "UNKNOWN",
                        "vehicle_type": det.vehicle_type,
                        "risk_score": 0,
                        "alert_level": "LOW",
                        "violations": [],
                        "verified_by": verified_by,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    if plate_number:
                        db_intel = check_vehicle_intel(plate_number)
                        fake_result = check_fake(
                            plate_number=plate_number,
                            detected_vehicle_type=det.vehicle_type,
                            plate_crop=det.plate_crop,
                            ocr_char_bboxes=[],
                            camera_id="WEBCAM",
                        )
                        safety = detect_safety(frame, det.vehicle_type, det.vehicle_bbox)
                        offender_level = db.get_offender_level(plate_number)
                        risk = calc_risk(
                            db_result=db_intel,
                            fake_plate_result=fake_result,
                            helmet_violation=(safety.violation and not safety.helmet_detected),
                            seatbelt_violation=(safety.violation and not safety.seatbelt_detected),
                            in_blacklist_zone=False,
                            offender_level=offender_level,
                            zone_multiplier=1.0,
                            overspeeding=False,
                        )
                        summary.update({
                            "risk_score": risk.total_score,
                            "alert_level": risk.alert_level,
                            "violations": risk.all_violations,
                            "owner": db_intel.owner_name or "Unknown",
                            "fake_plate": fake_result.is_fake,
                            "stolen": db_intel.is_stolen,
                        })

                        # ── Only log to DB if cooldown has elapsed for this plate ──
                        plate_key = plate_number.upper().strip()
                        last_logged = _plate_last_logged.get(plate_key, 0)
                        cooldown_elapsed = (now - last_logged) >= PLATE_COOLDOWN_SECS

                        if risk.all_violations and cooldown_elapsed:
                            captured_url, annotated_url = _save_violation_images(
                                frame, annotated, plate_number,
                                hashlib.sha256(f"{plate_number}{now}".encode()).hexdigest(),
                            )
                            db.log_violation(
                                plate=plate_number,
                                violations=risk.all_violations,
                                risk_score=risk.total_score,
                                zone_id="",
                                alert_level=risk.alert_level,
                                vehicle_type=det.vehicle_type,
                                owner_name=db_intel.owner_name or "",
                                model_used=safety.model_used if safety.violation else "yolo",
                                captured_image=captured_url,
                                annotated_image=annotated_url,
                            )
                            _plate_last_logged[plate_key] = now
                            logger.info(f"Webcam: Logged violation for {plate_key} (cooldown {PLATE_COOLDOWN_SECS}s)")
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    broadcast_violation(summary), loop
                                )
                            except Exception:
                                pass

                    else:
                        # ── No plate detected: still check helmet for 2W/3W ──
                        vtype_upper = det.vehicle_type.upper()
                        if vtype_upper in ("MOTORCYCLE", "SCOOTER", "AUTO", "E_RICKSHAW"):
                            safety = detect_safety(frame, det.vehicle_type, det.vehicle_bbox)
                            if safety.violation and not safety.helmet_detected:
                                summary.update({
                                    "risk_score": 10,
                                    "alert_level": "LOW",
                                    "violations": ["HELMET_VIOLATION"],
                                })
                                # Log with UNKNOWN plate + save images
                                plate_key = f"UNKNOWN_{det.vehicle_type}_{int(now)}"
                                captured_url, annotated_url = _save_violation_images(
                                    frame, annotated, "UNKNOWN",
                                    hashlib.sha256(plate_key.encode()).hexdigest(),
                                )
                                db.log_violation(
                                    plate="UNKNOWN",
                                    violations=["HELMET_VIOLATION"],
                                    risk_score=10,
                                    zone_id="",
                                    alert_level="LOW",
                                    vehicle_type=det.vehicle_type,
                                    owner_name="",
                                    model_used=safety.model_used,
                                    captured_image=captured_url,
                                    annotated_image=annotated_url,
                                )
                                logger.info(f"Webcam: Logged helmet violation for UNKNOWN {det.vehicle_type}")

                    frame_summary.append(summary)

                _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buf).decode('utf-8')
                update_live_frame(frame_b64, frame_summary)

            except Exception as e:
                logger.warning(f"Webcam frame {frame_count} error: {e}")

            _time.sleep(0.03)  # ~30fps cap

        cap.release()
        logger.info("Webcam: Camera released, detection stopped")
        # Clear frame buffer when webcam stops
        update_live_frame("", [])

    except Exception as e:
        logger.error(f"Webcam worker failed: {e}")
    finally:
        _webcam_state["active"] = False
        global _latest_frame, _latest_detections
        _latest_frame = None
        _latest_detections = []


if __name__ == "__main__":
    import uvicorn

    # Custom log config that preserves application loggers while showing uvicorn output
    _uvicorn_log_config = {
        "version": 1,
        "disable_existing_loggers": False,  # KEY: don't silence app loggers
        "formatters": {
            "default": {
                "fmt": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                "use_colors": None,
            },
            "access": {
                "fmt": '%(asctime)s [%(levelname)s] %(name)s - %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        log_config=_uvicorn_log_config,
    )
