"""
SVIES — Database Initializer
Layer: Foundation
Creates the SQLite violations database with the required schema.

Usage:
    python data/violations/init_db.py
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone


def get_db_path() -> Path:
    """Get the path to history.db relative to this script's location."""
    return Path(__file__).resolve().parent / "history.db"


def init_database(db_path: Path | None = None) -> None:
    """Create the violations table in the SQLite database.

    Args:
        db_path: Path to the SQLite database file. Defaults to history.db
                 in the same directory as this script.
    """
    if db_path is None:
        db_path = get_db_path()

    # ── Ensure parent directory exists ──
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # ── Create violations table ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            violation_types TEXT,
            risk_score INTEGER,
            zone_id TEXT,
            alert_level TEXT,
            sha256_hash TEXT
        )
    """)

    # ── Create index on plate for fast lookups ──
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_violations_plate
        ON violations (plate)
    """)

    # ── Create index on timestamp for date-range queries ──
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_violations_timestamp
        ON violations (timestamp)
    """)

    conn.commit()
    conn.close()
    print(f"[✓] Database initialized at: {db_path}")


def insert_dummy_record(db_path: Path | None = None) -> int:
    """Insert a dummy violation record for testing.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        The row ID of the inserted record.
    """
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    timestamp_utc: str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    cursor.execute("""
        INSERT INTO violations (plate, timestamp, violation_types, risk_score,
                                zone_id, alert_level, sha256_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "TS09EF1234",
        timestamp_utc,
        "EXPIRED_INSURANCE,NO_PUCC",
        35,
        "SCHOOL_ZONE_01",
        "MEDIUM",
        "dummy_hash_for_testing_12345"
    ))

    row_id: int = cursor.lastrowid  # type: ignore
    conn.commit()
    conn.close()
    return row_id


def read_record(row_id: int, db_path: Path | None = None) -> dict | None:
    """Read a violation record by ID.

    Args:
        row_id: The row ID to look up.
        db_path: Path to the SQLite database.

    Returns:
        A dict with the record data, or None if not found.
    """
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM violations WHERE id = ?", (row_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return dict(row)


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Database Initializer Test")
    print("=" * 60)

    db_path = get_db_path()

    # ── Step 1: Initialize database ──
    print("\n[1] Initializing database...")
    init_database(db_path)

    # ── Step 2: Insert dummy record ──
    print("\n[2] Inserting dummy violation record...")
    row_id = insert_dummy_record(db_path)
    print(f"    Inserted record with ID: {row_id}")

    # ── Step 3: Read it back ──
    print("\n[3] Reading record back...")
    record = read_record(row_id, db_path)
    if record:
        print(f"    Plate:           {record['plate']}")
        print(f"    Timestamp:       {record['timestamp']}")
        print(f"    Violations:      {record['violation_types']}")
        print(f"    Risk Score:      {record['risk_score']}")
        print(f"    Zone:            {record['zone_id']}")
        print(f"    Alert Level:     {record['alert_level']}")
        print(f"    SHA256 Hash:     {record['sha256_hash']}")
        print("\n[✓] Database test PASSED!")
    else:
        print("\n[✗] Database test FAILED — record not found!")
        sys.exit(1)
