"""
SVIES -- Supabase Database Layer
=================================

Provides the unified database interface for SVIES using Supabase (PostgreSQL).
All vehicle lookups, violation logging, and feedback operations go through the
Supabase backend.

Module-level singleton
----------------------
    from api.database import db
    db.log_violation(...)
    db.get_violations(...)

Prerequisites
-------------
Set SUPABASE_URL and SUPABASE_KEY in your .env file (REQUIRED).
Run supabase_setup.sql in the Supabase SQL Editor to create all tables.
"""

from __future__ import annotations

import hashlib
import logging
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("svies.database")

# ---------------------------------------------------------------------------
# Resolve project root for config import
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from config import SUPABASE_URL, SUPABASE_KEY  # noqa: E402


# ============================================================================
# SVIESDatabase
# ============================================================================

class SVIESDatabase:
    """Supabase-backed database interface for SVIES.

    Requires ``SUPABASE_URL`` and ``SUPABASE_KEY`` environment variables.
    All public methods are synchronous.
    """

    def __init__(self) -> None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("Supabase credentials missing")

        from supabase import create_client, Client  # type: ignore[import-untyped]

        self._supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase backend connected.")

    # ==================================================================
    # Public API -- Violation logging
    # ==================================================================

    def log_violation(
        self,
        plate: str,
        violations: list[str],
        risk_score: int,
        zone_id: str = "",
        alert_level: str = "LOW",
        vehicle_type: str = "",
        owner_name: str = "",
        model_used: str = "",
        captured_image: str = "",
        annotated_image: str = "",
        vehicle_age: str = "",
    ) -> str:
        """Log a traffic violation and return its SHA-256 evidence hash."""
        plate = plate.upper().strip()
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        vt = ",".join(violations)
        sha = hashlib.sha256(f"{plate}{ts}{vt}".encode()).hexdigest()

        row = {
            "plate": plate,
            "timestamp": ts,
            "violation_types": vt,
            "risk_score": risk_score,
            "zone_id": zone_id,
            "alert_level": alert_level,
            "sha256_hash": sha,
            "vehicle_type": vehicle_type,
            "owner_name": owner_name,
            "model_used": model_used,
            "captured_image": captured_image,
            "annotated_image": annotated_image,
            "vehicle_age": vehicle_age,
        }
        self._supabase.table("violations").insert(row).execute()

        return sha

    # ==================================================================
    # Public API -- Violation queries
    # ==================================================================

    def get_violations(
        self,
        days: int = 30,
        level: str | None = None,
        plate: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """Retrieve a paginated, filterable list of violation records."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")

        query = (
            self._supabase.table("violations")
            .select("*", count="exact")
            .gte("timestamp", cutoff)
            .order("timestamp", desc=True)
        )
        if level:
            levels = [lv.strip().upper() for lv in level.split(",")]
            query = query.in_("alert_level", levels)
        if plate:
            query = query.ilike("plate", f"%{plate.upper().strip()}%")
        query = query.range((page - 1) * per_page, page * per_page - 1)
        response = query.execute()
        total = response.count if response.count is not None else len(response.data)
        violations = response.data

        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            "violations": violations,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    def get_violation_history(self, plate: str, days: int = 30) -> list[dict]:
        """Return the full violation history for a single plate."""
        plate = plate.upper().strip()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")

        response = (
            self._supabase.table("violations")
            .select("*")
            .eq("plate", plate)
            .gte("timestamp", cutoff)
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data

    def get_top_offenders(self, limit: int = 10, days: int = 30) -> list[dict]:
        """Return the top repeat offenders ranked by violation count.

        Note: Supabase client SDK does not support GROUP BY, so we fetch
        raw rows and aggregate in Python. For large-scale deployments,
        use a Postgres RPC / view instead.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")

        response = (
            self._supabase.table("violations")
            .select("plate, timestamp")
            .gte("timestamp", cutoff)
            .order("timestamp", desc=True)
            .execute()
        )
        counts: dict[str, dict[str, Any]] = {}
        for row in response.data:
            p = row["plate"]
            if p not in counts:
                counts[p] = {"plate": p, "count": 0, "latest_timestamp": row["timestamp"]}
            counts[p]["count"] += 1
        ranked = sorted(counts.values(), key=lambda x: x["count"], reverse=True)
        return ranked[:limit]

    def get_offender_level(self, plate: str) -> int:
        """Determine the repeat-offender escalation level for a plate.

        Levels (based on violation count in the last 30 days):
            0 -- No violations.
            1 -- 1-2 violations.
            2 -- 3-5 violations.
            3 -- 6+ violations.
        """
        plate = plate.upper().strip()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace("+00:00", "Z")

        response = (
            self._supabase.table("violations")
            .select("id", count="exact")
            .eq("plate", plate)
            .gte("timestamp", cutoff)
            .execute()
        )
        count = response.count if response.count is not None else len(response.data)

        if count == 0:
            return 0
        elif count <= 2:
            return 1
        elif count <= 5:
            return 2
        else:
            return 3

    def get_all_violations_count(self, days: int = 30) -> dict[str, int]:
        """Return aggregate violation counts by alert level."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")

        response = (
            self._supabase.table("violations")
            .select("plate, alert_level")
            .gte("timestamp", cutoff)
            .execute()
        )
        rows = response.data
        total = len(rows)
        critical = sum(1 for r in rows if r.get("alert_level") == "CRITICAL")
        high = sum(1 for r in rows if r.get("alert_level") == "HIGH")
        medium = sum(1 for r in rows if r.get("alert_level") == "MEDIUM")
        low = sum(1 for r in rows if r.get("alert_level") == "LOW")
        unique_plates = len({r.get("plate", "") for r in rows})

        return {
            "total": total,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "unique_plates": unique_plates,
        }

    # ==================================================================
    # Public API -- Vehicle / document lookups
    # ==================================================================

    def lookup_vehicle(self, plate: str) -> dict | None:
        """Look up vehicle registration data (VAHAN database)."""
        plate = plate.upper().strip()
        # ── Primary lookup: exact match (fast) ──
        response = (
            self._supabase.table("vehicles")
            .select("*")
            .eq("plate", plate)
            .limit(1)
            .execute()
        )
        if response.data:
            logger.debug(f"lookup_vehicle('{plate}'): found via eq match")
            return response.data[0]

        # ── Fallback: case-insensitive match (handles any casing stored in DB) ──
        response2 = (
            self._supabase.table("vehicles")
            .select("*")
            .ilike("plate", plate)
            .limit(1)
            .execute()
        )
        if response2.data:
            logger.warning(f"lookup_vehicle('{plate}'): found via ilike fallback "
                           f"(stored as '{response2.data[0].get('plate')}'). "
                           f"Consider normalising plate casing in DB.")
            return response2.data[0]

        logger.warning(f"lookup_vehicle('{plate}'): NOT FOUND in vehicles table. "
                       f"eq response had {len(response.data)} rows, ilike had {len(response2.data)} rows.")
        return None

    def lookup_pucc(self, plate: str) -> dict | None:
        """Look up a Pollution Under Control Certificate record."""
        plate = plate.upper().strip()
        response = (
            self._supabase.table("pucc")
            .select("*")
            .eq("plate", plate)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def lookup_insurance(self, plate: str) -> dict | None:
        """Look up a motor-insurance record."""
        plate = plate.upper().strip()
        response = (
            self._supabase.table("insurance")
            .select("*")
            .eq("plate", plate)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def is_stolen(self, plate: str) -> bool:
        """Check whether a vehicle is flagged as stolen."""
        plate = plate.upper().strip()
        response = (
            self._supabase.table("stolen_vehicles")
            .select("plate")
            .eq("plate", plate)
            .limit(1)
            .execute()
        )
        return len(response.data) > 0

    # ==================================================================
    # Public API -- Vehicle CRUD
    # ==================================================================

    def list_vehicles(self, page: int = 1, per_page: int = 25, search: str = "") -> dict[str, Any]:
        """List vehicles with optional search and pagination."""
        query = self._supabase.table("vehicles").select("*", count="exact")
        if search:
            search = search.upper().strip()
            query = query.or_(f"plate.ilike.%{search}%,owner.ilike.%{search}%")
        query = query.order("plate").range((page - 1) * per_page, page * per_page - 1)
        response = query.execute()
        total = response.count if response.count is not None else len(response.data)
        total_pages = max(1, (total + per_page - 1) // per_page)

        # Attach PUCC, insurance, stolen status for each vehicle
        vehicles = response.data
        for v in vehicles:
            plate = v["plate"]
            pucc = self.lookup_pucc(plate)
            ins = self.lookup_insurance(plate)
            stolen = self.is_stolen(plate)
            v["pucc"] = pucc
            v["insurance"] = ins
            v["is_stolen"] = stolen

        return {"vehicles": vehicles, "total": total, "page": page, "per_page": per_page, "total_pages": total_pages}

    def add_vehicle(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new vehicle record."""
        data["plate"] = data["plate"].upper().strip()
        self._supabase.table("vehicles").insert(data).execute()
        return {"status": "ok", "plate": data["plate"]}

    def update_vehicle(self, plate: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing vehicle record."""
        plate = plate.upper().strip()
        response = self._supabase.table("vehicles").update(data).eq("plate", plate).execute()
        if not response.data:
            raise ValueError(f"Vehicle {plate} not found")
        return {"status": "ok", "plate": plate, "updated": response.data[0]}

    def delete_vehicle(self, plate: str) -> dict[str, Any]:
        """Delete a vehicle and all related records (PUCC, insurance, stolen)."""
        plate = plate.upper().strip()
        # Delete from related tables first
        self._supabase.table("stolen_vehicles").delete().eq("plate", plate).execute()
        self._supabase.table("pucc").delete().eq("plate", plate).execute()
        self._supabase.table("insurance").delete().eq("plate", plate).execute()
        self._supabase.table("vehicles").delete().eq("plate", plate).execute()
        return {"status": "ok", "plate": plate}

    def upsert_pucc(self, plate: str, data: dict[str, Any]) -> dict[str, Any]:
        """Insert or update a PUCC record."""
        plate = plate.upper().strip()
        row = {"plate": plate, **data}
        self._supabase.table("pucc").upsert(row).execute()
        return {"status": "ok", "plate": plate}

    def upsert_insurance(self, plate: str, data: dict[str, Any]) -> dict[str, Any]:
        """Insert or update an insurance record."""
        plate = plate.upper().strip()
        row = {"plate": plate, **data}
        self._supabase.table("insurance").upsert(row).execute()
        return {"status": "ok", "plate": plate}

    def set_stolen(self, plate: str, stolen: bool) -> dict[str, Any]:
        """Mark or unmark a vehicle as stolen."""
        plate = plate.upper().strip()
        if stolen:
            # Upsert into stolen_vehicles
            self._supabase.table("stolen_vehicles").upsert({"plate": plate}).execute()
        else:
            self._supabase.table("stolen_vehicles").delete().eq("plate", plate).execute()
        return {"status": "ok", "plate": plate, "is_stolen": stolen}

    # ==================================================================
    # Public API -- Feedback / active learning
    # ==================================================================

    def save_feedback(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist a user-submitted correction / feedback entry."""
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        row = {
            "timestamp": ts,
            "original_plate": data.get("original_plate", ""),
            "correct_plate": data.get("correct_plate", ""),
            "correct_vehicle_type": data.get("correct_vehicle_type", ""),
            "notes": data.get("notes", ""),
            "image_file": data.get("image_file", ""),
        }
        self._supabase.table("feedback").insert(row).execute()
        count_resp = (
            self._supabase.table("feedback")
            .select("id", count="exact")
            .execute()
        )
        total = count_resp.count if count_resp.count is not None else 0
        return {"status": "ok", "total_feedback": total}

    def get_feedback_stats(self) -> dict[str, Any]:
        """Retrieve feedback / active-learning statistics."""
        count_resp = (
            self._supabase.table("feedback")
            .select("id", count="exact")
            .execute()
        )
        total = count_resp.count if count_resp.count is not None else 0
        entries_resp = (
            self._supabase.table("feedback")
            .select("*")
            .order("timestamp", desc=True)
            .limit(20)
            .execute()
        )
        return {"total_feedback": total, "entries": entries_resp.data}

    # ==================================================================
    # Public API -- Demo data seeding
    # ==================================================================

    def seed_demo_data(self, count: int = 100) -> dict[str, Any]:
        """Seed the database with realistic demo violation records."""
        plates = [
            "AP09AB1234", "TS08CD5678", "KA01EE9999", "TN22FF4444",
            "MH12GH7777", "DL01AB0001", "AP28HH3333", "TS09KK8888",
            "TS09EF1234", "TS06AB5678", "AP28CD1234", "KA01MN4567",
            "TN07GH8901", "DL04RS2345", "MH02AB3333", "RJ14UV6789",
        ]
        violation_combos: list[tuple[list[str], int, str]] = [
            (["HELMET_VIOLATION"], 10, "LOW"),
            (["SEATBELT_VIOLATION"], 10, "LOW"),
            (["NO_PUCC"], 15, "MEDIUM"),
            (["EXPIRED_INSURANCE"], 20, "MEDIUM"),
            (["NO_PUCC", "EXPIRED_INSURANCE"], 35, "MEDIUM"),
            (["OVERSPEEDING"], 15, "MEDIUM"),
            (["HELMET_VIOLATION", "OVERSPEEDING"], 25, "MEDIUM"),
            (["STOLEN_VEHICLE"], 40, "HIGH"),
            (["FAKE_PLATE"], 35, "HIGH"),
            (["STOLEN_VEHICLE", "FAKE_PLATE"], 75, "CRITICAL"),
            (["NO_REGISTRATION", "HELMET_VIOLATION", "OVERSPEEDING"], 50, "HIGH"),
            (["REPEAT_OFFENDER", "NO_PUCC", "SEATBELT_VIOLATION"], 45, "HIGH"),
        ]
        zones = [
            "SCHOOL_JNTU", "SCHOOL_OU", "HOSPITAL_NIMS", "HOSPITAL_GANDHI",
            "GOVT_SECRETARIAT", "HIGHWAY_ORR_GACHIBOWLI", "HIGHWAY_ORR_SHAMSHABAD",
            "HIGHWAY_HITECH_CITY", "LOW_EMISSION_CHARMINAR", "LOW_EMISSION_TANKBUND",
            "",
        ]

        seeded = 0
        now = datetime.now(timezone.utc)

        for _ in range(count):
            plate = random.choice(plates)
            violations, base_score, level = random.choice(violation_combos)
            zone = random.choice(zones)
            offset = timedelta(
                days=random.randint(0, 29),
                hours=random.randint(6, 22),
                minutes=random.randint(0, 59),
            )
            score = max(0, base_score + random.randint(-5, 10))

            ts = (now - offset).isoformat().replace("+00:00", "Z")
            vt = ",".join(violations)
            sha = hashlib.sha256(f"{plate}{ts}{vt}".encode()).hexdigest()

            self._supabase.table("violations").insert({
                "plate": plate,
                "timestamp": ts,
                "violation_types": vt,
                "risk_score": score,
                "zone_id": zone,
                "alert_level": level,
                "sha256_hash": sha,
            }).execute()

            seeded += 1

        return {
            "status": "ok",
            "seeded": seeded,
            "message": f"Seeded {seeded} demo violations. Dashboard should now show data.",
        }

    # ------------------------------------------------------------------
    # Convenience / introspection
    # ------------------------------------------------------------------

    @property
    def backend(self) -> str:
        """Return the active backend label."""
        return "supabase"

    def __repr__(self) -> str:
        return f"<SVIESDatabase backend={self.backend!r}>"


# ============================================================================
# Local fallback backend (SQLite + mock JSON lookups)
# ============================================================================

class LocalSVIESDatabase:
    """Local development DB.

    - Violations + feedback are stored in SQLite at `data/violations/history.db`
    - Vehicle/PUCC/insurance/stolen lookups come from `data/mock_db/*.json`

    This keeps the backend usable (and logs visible) even when Supabase env
    vars are not configured.
    """

    def __init__(self) -> None:
        self._db_path = _PROJECT_ROOT / "data" / "violations" / "history.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()
        logger.warning(
            "Supabase env not set. Using LOCAL SQLite backend at %s (mock vehicle DB lookups).",
            self._db_path,
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    violation_types TEXT,
                    risk_score INTEGER,
                    zone_id TEXT,
                    alert_level TEXT,
                    sha256_hash TEXT,
                    vehicle_type TEXT DEFAULT '',
                    owner_name TEXT DEFAULT '',
                    model_used TEXT DEFAULT '',
                    captured_image TEXT DEFAULT '',
                    annotated_image TEXT DEFAULT ''
                )
                """
            )
            # Migrate existing tables: add new columns if missing
            existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(violations)").fetchall()}
            for col in ("vehicle_type", "owner_name", "model_used", "captured_image", "annotated_image", "vehicle_age"):
                if col not in existing_cols:
                    cur.execute(f"ALTER TABLE violations ADD COLUMN {col} TEXT DEFAULT ''")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_plate ON violations (plate)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON violations (timestamp)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    original_plate TEXT,
                    correct_plate TEXT,
                    correct_vehicle_type TEXT,
                    notes TEXT,
                    image_file TEXT
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback (timestamp)")
            conn.commit()

    # ==================================================================
    # Public API -- Violation logging
    # ==================================================================

    def log_violation(
        self,
        plate: str,
        violations: list[str],
        risk_score: int,
        zone_id: str = "",
        alert_level: str = "LOW",
        vehicle_type: str = "",
        owner_name: str = "",
        model_used: str = "",
        captured_image: str = "",
        annotated_image: str = "",
        vehicle_age: str = "",
    ) -> str:
        plate = plate.upper().strip()
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        vt = ",".join(violations)
        sha = hashlib.sha256(f"{plate}{ts}{vt}".encode()).hexdigest()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO violations (plate, timestamp, violation_types, risk_score, zone_id, alert_level, sha256_hash,
                                        vehicle_type, owner_name, model_used, captured_image, annotated_image, vehicle_age)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (plate, ts, vt, int(risk_score), zone_id, alert_level, sha,
                 vehicle_type, owner_name, model_used, captured_image, annotated_image, vehicle_age),
            )
            conn.commit()

        return sha

    # ==================================================================
    # Public API -- Violation queries
    # ==================================================================

    def get_violations(
        self,
        days: int = 30,
        level: str | None = None,
        plate: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        where = ["timestamp >= ?"]
        params: list[Any] = [cutoff]

        if level:
            levels = [lv.strip().upper() for lv in level.split(",") if lv.strip()]
            if levels:
                where.append(f"alert_level IN ({','.join(['?'] * len(levels))})")
                params.extend(levels)

        if plate:
            where.append("plate LIKE ?")
            params.append(f"%{plate.upper().strip()}%")

        where_sql = " AND ".join(where) if where else "1=1"
        offset = (page - 1) * per_page

        with self._connect() as conn:
            total_row = conn.execute(f"SELECT COUNT(*) AS c FROM violations WHERE {where_sql}", params).fetchone()
            total = int(total_row["c"]) if total_row else 0

            rows = conn.execute(
                f"""
                SELECT plate, timestamp, violation_types, risk_score, zone_id, alert_level, sha256_hash,
                       vehicle_type, owner_name, model_used, captured_image, annotated_image
                FROM violations
                WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                [*params, int(per_page), int(offset)],
            ).fetchall()

        violations_out = [dict(r) for r in rows]
        total_pages = max(1, (total + per_page - 1) // per_page)
        return {
            "violations": violations_out,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    def get_violation_history(self, plate: str, days: int = 30) -> list[dict]:
        plate = plate.upper().strip()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT plate, timestamp, violation_types, risk_score, zone_id, alert_level, sha256_hash,
                       vehicle_type, owner_name, model_used, captured_image, annotated_image
                FROM violations
                WHERE plate = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                """,
                (plate, cutoff),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_top_offenders(self, limit: int = 10, days: int = 30) -> list[dict]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT plate, COUNT(*) AS count, MAX(timestamp) AS latest_timestamp
                FROM violations
                WHERE timestamp >= ?
                GROUP BY plate
                ORDER BY count DESC
                LIMIT ?
                """,
                (cutoff, int(limit)),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_offender_level(self, plate: str) -> int:
        plate = plate.upper().strip()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace("+00:00", "Z")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM violations WHERE plate = ? AND timestamp >= ?",
                (plate, cutoff),
            ).fetchone()
        count = int(row["c"]) if row else 0
        if count == 0:
            return 0
        if count <= 2:
            return 1
        if count <= 5:
            return 2
        return 3

    def get_all_violations_count(self, days: int = 30) -> dict[str, int]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT plate, alert_level FROM violations WHERE timestamp >= ?",
                (cutoff,),
            ).fetchall()
        rows_d = [dict(r) for r in rows]
        total = len(rows_d)
        critical = sum(1 for r in rows_d if r.get("alert_level") == "CRITICAL")
        high = sum(1 for r in rows_d if r.get("alert_level") == "HIGH")
        medium = sum(1 for r in rows_d if r.get("alert_level") == "MEDIUM")
        low = sum(1 for r in rows_d if r.get("alert_level") == "LOW")
        unique_plates = len({r.get("plate", "") for r in rows_d})
        return {
            "total": total,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "unique_plates": unique_plates,
        }

    # ==================================================================
    # Public API -- Vehicle / document lookups (mock JSON)
    # ==================================================================

    def lookup_vehicle(self, plate: str) -> dict | None:
        from modules.mock_db_loader import lookup_vahan
        return lookup_vahan(plate)

    def lookup_pucc(self, plate: str) -> dict | None:
        from modules.mock_db_loader import lookup_pucc
        return lookup_pucc(plate)

    def lookup_insurance(self, plate: str) -> dict | None:
        from modules.mock_db_loader import lookup_insurance
        return lookup_insurance(plate)

    def is_stolen(self, plate: str) -> bool:
        from modules.mock_db_loader import is_stolen
        return bool(is_stolen(plate))

    # ==================================================================
    # Public API -- Vehicle CRUD (local stubs)
    # ==================================================================

    def list_vehicles(self, page: int = 1, per_page: int = 25, search: str = "") -> dict[str, Any]:
        from modules.mock_db_loader import lookup_vahan, get_all_plates
        all_plates = sorted(get_all_plates())
        if search:
            search = search.upper().strip()
            all_plates = [p for p in all_plates if search in p]
        total = len(all_plates)
        start = (page - 1) * per_page
        page_plates = all_plates[start:start + per_page]
        vehicles = []
        for p in page_plates:
            v = lookup_vahan(p)
            if v:
                v = dict(v)
                v["plate"] = p
                v["pucc"] = self.lookup_pucc(p)
                v["insurance"] = self.lookup_insurance(p)
                v["is_stolen"] = self.is_stolen(p)
                vehicles.append(v)
        total_pages = max(1, (total + per_page - 1) // per_page)
        return {"vehicles": vehicles, "total": total, "page": page, "per_page": per_page, "total_pages": total_pages}

    def add_vehicle(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "plate": data.get("plate", ""), "message": "[LOCAL] Vehicle add simulated."}

    def update_vehicle(self, plate: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "plate": plate, "message": "[LOCAL] Vehicle update simulated."}

    def delete_vehicle(self, plate: str) -> dict[str, Any]:
        return {"status": "ok", "plate": plate, "message": "[LOCAL] Vehicle delete simulated."}

    def upsert_pucc(self, plate: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "plate": plate, "message": "[LOCAL] PUCC upsert simulated."}

    def upsert_insurance(self, plate: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "plate": plate, "message": "[LOCAL] Insurance upsert simulated."}

    def set_stolen(self, plate: str, stolen: bool) -> dict[str, Any]:
        return {"status": "ok", "plate": plate, "is_stolen": stolen, "message": "[LOCAL] Stolen status simulated."}

    # ==================================================================
    # Public API -- Feedback / active learning
    # ==================================================================

    def save_feedback(self, data: dict[str, Any]) -> dict[str, Any]:
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        row = (
            ts,
            data.get("original_plate", ""),
            data.get("correct_plate", ""),
            data.get("correct_vehicle_type", ""),
            data.get("notes", ""),
            data.get("image_file", ""),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback (timestamp, original_plate, correct_plate, correct_vehicle_type, notes, image_file)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            total_row = conn.execute("SELECT COUNT(*) AS c FROM feedback").fetchone()
            conn.commit()
        total = int(total_row["c"]) if total_row else 0
        return {"status": "ok", "total_feedback": total}

    def get_feedback_stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total_row = conn.execute("SELECT COUNT(*) AS c FROM feedback").fetchone()
            entries = conn.execute(
                """
                SELECT timestamp, original_plate, correct_plate, correct_vehicle_type, notes, image_file
                FROM feedback
                ORDER BY timestamp DESC
                LIMIT 20
                """
            ).fetchall()
        total = int(total_row["c"]) if total_row else 0
        return {"total_feedback": total, "entries": [dict(r) for r in entries]}

    # ==================================================================
    # Public API -- Demo data seeding
    # ==================================================================

    def seed_demo_data(self, count: int = 100) -> dict[str, Any]:
        plates = [
            "AP09AB1234", "TS08CD5678", "KA01EE9999", "TN22FF4444",
            "MH12GH7777", "DL01AB0001", "AP28HH3333", "TS09KK8888",
            "TS09EF1234", "TS06AB5678", "AP28CD1234", "KA01MN4567",
            "TN07GH8901", "DL04RS2345", "MH02AB3333", "RJ14UV6789",
        ]
        violation_combos: list[tuple[list[str], int, str]] = [
            (["HELMET_VIOLATION"], 10, "LOW"),
            (["SEATBELT_VIOLATION"], 10, "LOW"),
            (["NO_PUCC"], 15, "MEDIUM"),
            (["EXPIRED_INSURANCE"], 20, "MEDIUM"),
            (["NO_PUCC", "EXPIRED_INSURANCE"], 35, "MEDIUM"),
            (["OVERSPEEDING"], 15, "MEDIUM"),
            (["HELMET_VIOLATION", "OVERSPEEDING"], 25, "MEDIUM"),
            (["STOLEN_VEHICLE"], 40, "HIGH"),
            (["FAKE_PLATE"], 35, "HIGH"),
            (["STOLEN_VEHICLE", "FAKE_PLATE"], 75, "CRITICAL"),
            (["NO_REGISTRATION", "HELMET_VIOLATION", "OVERSPEEDING"], 50, "HIGH"),
            (["REPEAT_OFFENDER", "NO_PUCC", "SEATBELT_VIOLATION"], 45, "HIGH"),
        ]
        zones = [
            "SCHOOL_JNTU", "SCHOOL_OU", "HOSPITAL_NIMS", "HOSPITAL_GANDHI",
            "GOVT_SECRETARIAT", "HIGHWAY_ORR_GACHIBOWLI", "HIGHWAY_ORR_SHAMSHABAD",
            "HIGHWAY_HITECH_CITY", "LOW_EMISSION_CHARMINAR", "LOW_EMISSION_TANKBUND",
            "",
        ]

        seeded = 0
        now = datetime.now(timezone.utc)
        for _ in range(count):
            plate = random.choice(plates)
            violations, base_score, level = random.choice(violation_combos)
            zone = random.choice(zones)
            offset = timedelta(
                days=random.randint(0, 29),
                hours=random.randint(6, 22),
                minutes=random.randint(0, 59),
            )
            score = max(0, base_score + random.randint(-5, 10))
            ts = (now - offset).isoformat().replace("+00:00", "Z")
            vt = ",".join(violations)
            sha = hashlib.sha256(f"{plate}{ts}{vt}".encode()).hexdigest()

            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO violations (plate, timestamp, violation_types, risk_score, zone_id, alert_level, sha256_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (plate, ts, vt, int(score), zone, level, sha),
                )
                conn.commit()
            seeded += 1

        return {
            "status": "ok",
            "seeded": seeded,
            "message": f"Seeded {seeded} demo violations (LOCAL backend). Dashboard should now show data.",
        }

    # ------------------------------------------------------------------
    # Convenience / introspection
    # ------------------------------------------------------------------

    @property
    def backend(self) -> str:
        return "local-sqlite"

    def __repr__(self) -> str:
        return f"<SVIESDatabase backend={self.backend!r}>"


# ============================================================================
# Module-level singleton
# ============================================================================

try:
    db: Any = SVIESDatabase()
except Exception:
    # If Supabase isn't configured, don't crash the server. Use local dev backend.
    db = LocalSVIESDatabase()
