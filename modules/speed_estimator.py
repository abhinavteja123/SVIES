"""
SVIES — Speed Estimation Module
Estimates vehicle speed using optical flow between consecutive frames.

Usage:
    python -m modules.speed_estimator
"""

import cv2
import numpy as np
import os
from dataclasses import dataclass


@dataclass
class SpeedResult:
    speed_kmh: float = 0.0
    is_overspeeding: bool = False
    confidence: float = 0.0


# ── Calibration constants (configurable via env or per camera setup) ──
PIXELS_PER_METER = float(os.environ.get("PIXELS_PER_METER", "8.0"))
SPEED_LIMIT_KMH = float(os.environ.get("DEFAULT_SPEED_LIMIT_KMH", "40.0"))

# Indian road speed limits by zone type
INDIAN_SPEED_LIMITS: dict[str, float] = {
    "SCHOOL": 25.0,          # School zones: 25 km/h
    "HOSPITAL": 25.0,        # Hospital zones: 25 km/h
    "RESIDENTIAL": 30.0,     # Residential areas: 30 km/h
    "CITY": 50.0,            # City roads: 50 km/h
    "STATE_HIGHWAY": 80.0,   # State highways: 80 km/h
    "NATIONAL_HIGHWAY": 100.0,  # National highways: 100 km/h
    "EXPRESSWAY": 120.0,     # Expressways: 120 km/h
}


class SpeedEstimator:
    """Optical-flow based speed estimator for tracked vehicles."""

    MAX_TRACKED = 500  # Evict oldest entries when this limit is reached

    def __init__(self, fps: float = 30.0, pixels_per_meter: float = PIXELS_PER_METER,
                 speed_limit: float = SPEED_LIMIT_KMH):
        self.fps = fps
        self.ppm = pixels_per_meter
        self.speed_limit = speed_limit
        self._prev_positions: dict[str, tuple[float, float, float]] = {}
        # {track_id: (cx, cy, timestamp_frame)}
        self._frame_count = 0

    def update(self, track_id: str, bbox: tuple[int, int, int, int]) -> SpeedResult:
        """Update tracker and estimate speed for a vehicle.

        Args:
            track_id: Unique ID for this vehicle (e.g., plate number).
            bbox: Bounding box (x1, y1, x2, y2).

        Returns:
            SpeedResult with estimated speed and overspeeding flag.
        """
        self._frame_count += 1
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0

        # Evict stale entries to prevent memory leak
        if len(self._prev_positions) > self.MAX_TRACKED:
            oldest = sorted(self._prev_positions.items(), key=lambda x: x[1][2])
            for key, _ in oldest[:len(oldest) // 2]:
                del self._prev_positions[key]

        if track_id not in self._prev_positions:
            self._prev_positions[track_id] = (cx, cy, self._frame_count)
            return SpeedResult(speed_kmh=0.0, confidence=0.0)

        prev_cx, prev_cy, prev_frame = self._prev_positions[track_id]
        frame_diff = self._frame_count - prev_frame

        if frame_diff <= 0:
            return SpeedResult(speed_kmh=0.0, confidence=0.0)

        # ── Pixel displacement ──
        dx = cx - prev_cx
        dy = cy - prev_cy
        pixel_dist = np.sqrt(dx ** 2 + dy ** 2)

        # ── Convert to real-world speed ──
        meter_dist = pixel_dist / self.ppm
        time_seconds = frame_diff / self.fps
        speed_ms = meter_dist / time_seconds if time_seconds > 0 else 0
        speed_kmh = speed_ms * 3.6

        # ── Confidence based on displacement magnitude ──
        confidence = min(pixel_dist / 50.0, 1.0)

        # ── Clamp unrealistic speeds ──
        if speed_kmh > 200:
            speed_kmh = 0.0
            confidence = 0.0

        self._prev_positions[track_id] = (cx, cy, self._frame_count)

        return SpeedResult(
            speed_kmh=round(speed_kmh, 1),
            is_overspeeding=speed_kmh > self.speed_limit and confidence > 0.3,
            confidence=round(confidence, 3),
        )

    def reset(self, track_id: str | None = None) -> None:
        if track_id:
            self._prev_positions.pop(track_id, None)
        else:
            self._prev_positions.clear()
            self._frame_count = 0


if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Speed Estimator Test")
    print("=" * 60)

    est = SpeedEstimator(fps=30.0, pixels_per_meter=8.0, speed_limit=40.0)

    # Simulate a car moving at ~50 km/h (13.9 m/s → 111 px/s → 3.7 px/frame)
    bboxes = [(100 + int(i * 3.7), 200, 200 + int(i * 3.7), 300) for i in range(30)]

    for i, bb in enumerate(bboxes):
        r = est.update("CAR_001", bb)
        if i > 0 and i % 5 == 0:
            print(f"  Frame {i:3d}: speed={r.speed_kmh:6.1f} km/h, "
                  f"over={r.is_overspeeding}, conf={r.confidence:.3f}")

    print(f"\n  Final speed: {r.speed_kmh:.1f} km/h")
    print(f"  Overspeeding: {r.is_overspeeding}")
    assert r.speed_kmh > 30, f"Expected > 30 km/h, got {r.speed_kmh}"
    print("  [✓] PASSED")

    print("\n[✓] Speed estimator tests completed!")
