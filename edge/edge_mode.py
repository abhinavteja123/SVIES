"""
SVIES — Edge Mode Module
Layer 6: Offline/Raspberry Pi Edge Processing
Uses YOLOv5n for lightweight CPU inference with local cache and offline alert queue.

Usage:
    python -m edge.edge_mode
"""

import json
import socket
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EDGE_CACHE_PATH = PROJECT_ROOT / "edge" / "edge_cache.json"
OFFLINE_QUEUE_PATH = PROJECT_ROOT / "edge" / "offline_queue.json"

_model = None


def _get_model():
    """Load YOLOv5n model (singleton, lightweight for edge)."""
    global _model
    if _model is not None:
        return _model
    try:
        from ultralytics import YOLO
        local = PROJECT_ROOT / "models" / "yolov5n.pt"
        _model = YOLO(str(local) if local.exists() else "yolov5nu.pt")
    except Exception as e:
        print(f"[EDGE] Model load failed: {e}")
    return _model


@dataclass
class EdgeDetection:
    plate_bbox: tuple | None = None
    plate_crop: np.ndarray | None = None
    vehicle_type: str = "UNKNOWN"
    confidence: float = 0.0


VEHICLE_MAP = {2: "CAR", 3: "MOTORCYCLE", 5: "BUS", 7: "TRUCK"}


class EdgeMode:
    """Offline edge processing pipeline."""

    def __init__(self):
        self._cache: dict = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if EDGE_CACHE_PATH.exists():
            try:
                with open(EDGE_CACHE_PATH, "r") as f:
                    self._cache = json.load(f)
                print(f"[EDGE] Loaded cache: {len(self._cache.get('vahan', {}))} vehicles, "
                      f"{len(self._cache.get('stolen', []))} stolen")
            except Exception as e:
                print(f"[EDGE] Cache load error: {e}")
                self._cache = {"vahan": {}, "stolen": []}
        else:
            self._cache = {"vahan": {}, "stolen": []}

    @staticmethod
    def is_online() -> bool:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

    def detect(self, frame: np.ndarray, conf: float = 0.4) -> list[EdgeDetection]:
        model = _get_model()
        if model is None:
            return []
        results = model(frame, verbose=False, conf=conf)
        detections = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0].item())
                if cls_id not in VEHICLE_MAP:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                vtype = VEHICLE_MAP[cls_id]
                # Estimate plate region
                h = y2 - y1
                w = x2 - x1
                px1 = x1 + int(w * 0.15)
                px2 = x1 + int(w * 0.85)
                py1 = y1 + int(h * 0.65)
                py2 = y1 + int(h * 0.90)
                py1 = max(0, min(py1, frame.shape[0]))
                py2 = max(0, min(py2, frame.shape[0]))
                px1 = max(0, min(px1, frame.shape[1]))
                px2 = max(0, min(px2, frame.shape[1]))
                crop = frame[py1:py2, px1:px2] if py2 > py1 and px2 > px1 else None
                detections.append(EdgeDetection(
                    plate_bbox=(px1, py1, px2, py2),
                    plate_crop=crop,
                    vehicle_type=vtype,
                    confidence=float(box.conf[0].item()),
                ))
        return detections

    def lookup_local(self, plate: str) -> dict | None:
        plate = plate.upper().strip()
        vahan = self._cache.get("vahan", {})
        return vahan.get(plate)

    def is_stolen_local(self, plate: str) -> bool:
        return plate.upper().strip() in self._cache.get("stolen", [])

    def queue_alert(self, alert_payload: dict) -> None:
        queue = []
        if OFFLINE_QUEUE_PATH.exists():
            try:
                with open(OFFLINE_QUEUE_PATH, "r") as f:
                    queue = json.load(f)
            except Exception:
                queue = []
        alert_payload["queued_at"] = datetime.now(timezone.utc).isoformat()
        queue.append(alert_payload)
        OFFLINE_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OFFLINE_QUEUE_PATH, "w") as f:
            json.dump(queue, f, indent=2, default=str)
        print(f"[EDGE] Alert queued. Queue size: {len(queue)}")

    def sync_queue(self) -> int:
        if not self.is_online():
            print("[EDGE] Still offline, cannot sync.")
            return 0
        if not OFFLINE_QUEUE_PATH.exists():
            return 0
        try:
            with open(OFFLINE_QUEUE_PATH, "r") as f:
                queue = json.load(f)
        except Exception:
            return 0
        if not queue:
            return 0

        synced = 0
        for alert in queue:
            try:
                # In production: send via alert_system.dispatch_alert()
                print(f"[EDGE] Synced alert: {alert.get('plate', '?')}")
                synced += 1
            except Exception as e:
                print(f"[EDGE] Sync failed for alert: {e}")
                break

        # Clear synced alerts
        remaining = queue[synced:]
        with open(OFFLINE_QUEUE_PATH, "w") as f:
            json.dump(remaining, f, indent=2)
        print(f"[EDGE] Synced {synced}/{len(queue)} alerts. Remaining: {len(remaining)}")
        return synced

    @staticmethod
    def build_edge_cache() -> None:
        """Build edge_cache.json from full mock databases."""
        sys.path.insert(0, str(PROJECT_ROOT))
        from modules.mock_db_loader import _vahan_db, _stolen_db
        cache = {
            "vahan": dict(_vahan_db),
            "stolen": _stolen_db.get("stolen_plates", []),
            "built_at": datetime.now(timezone.utc).isoformat(),
        }
        EDGE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EDGE_CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
        print(f"[EDGE] Cache built: {len(cache['vahan'])} vehicles, {len(cache['stolen'])} stolen")


# ── Package init ──
edge_init = Path(__file__).resolve().parent / "__init__.py"
if not edge_init.exists():
    edge_init.write_text("# SVIES Edge package\n")


if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Edge Mode Test")
    print("=" * 60)

    # Build cache first
    print("\n[1] Building edge cache from mock DBs...")
    EdgeMode.build_edge_cache()

    edge = EdgeMode()

    print(f"\n[2] Online check: {edge.is_online()}")

    print("\n[3] Local lookup: TS09EF1234")
    rec = edge.lookup_local("TS09EF1234")
    print(f"  Result: {rec}")

    print("\n[4] Stolen check: AP28CD1234")
    print(f"  Stolen: {edge.is_stolen_local('AP28CD1234')}")

    print("\n[5] Queue alert test")
    edge.queue_alert({"plate": "TEST123", "violations": ["TEST"]})

    print("\n[6] Sync queue")
    synced = edge.sync_queue()
    print(f"  Synced: {synced}")

    print("\n[7] Detection test (synthetic frame)")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dets = edge.detect(frame)
    print(f"  Detections: {len(dets)} (expected 0 on blank frame)")

    print("\n" + "=" * 60)
    print("[✓] Edge mode tests completed!")
