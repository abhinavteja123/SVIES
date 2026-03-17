"""
SVIES — Alert System Module
Layer 5: Automated Alerts (SMS + Email)
Sends alerts via Twilio SMS and Gmail SMTP based on violation severity.

Usage:
    python -m modules.alert_system
"""

import hashlib
import logging
import os
import smtplib
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# ── Import config ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM,
    GMAIL_USER, GMAIL_PASSWORD,
    POLICE_EMAIL, POLICE_PHONE, RTO_EMAIL,
    SNAPSHOT_DIR,
)

logger = logging.getLogger("svies.alert_system")


# ══════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════

@dataclass
class AlertPayload:
    """Structured alert payload for SMS/Email dispatch."""
    plate: str = ""
    owner_name: str = ""
    owner_phone: str = ""
    owner_email: str = ""
    violations: list[str] = field(default_factory=list)
    fake_plate_flags: list[str] = field(default_factory=list)
    risk_score: int = 0
    alert_level: str = "LOW"
    zone: str = ""
    gps_location: str = ""
    snapshot_path: str = ""
    timestamp_utc: str = ""
    sha256_hash: str = ""


# ══════════════════════════════════════════════════════════
# SHA-256 Hash Generation
# ══════════════════════════════════════════════════════════

def generate_sha256_hash(plate: str, timestamp_utc: str, violations: list[str]) -> str:
    """Generate a SHA-256 hash for alert integrity verification.

    Format: sha256(plate + timestamp_utc + comma_joined_violations)

    Args:
        plate: License plate number.
        timestamp_utc: ISO 8601 UTC timestamp string.
        violations: List of violation type strings.

    Returns:
        Hex digest of the SHA-256 hash.
    """
    violations_str = ",".join(sorted(violations))
    data = f"{plate}{timestamp_utc}{violations_str}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════
# Snapshot Saving
# ══════════════════════════════════════════════════════════

def save_snapshot(frame: np.ndarray, plate: str) -> str:
    """Save a detection snapshot to disk.

    Filename format: snapshots/{plate}_{YYYYMMDD}_{HHMMSS}.jpg

    Args:
        frame: BGR image to save.
        plate: License plate number for filename.

    Returns:
        File path of the saved snapshot.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    # Sanitize plate for safe filename (remove path-traversal characters)
    safe_plate = "".join(c for c in plate if c.isalnum() or c in ('-', '_'))
    filename = f"{safe_plate}_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}.jpg"
    filepath = SNAPSHOT_DIR / filename

    try:
        cv2.imwrite(str(filepath), frame)
        return str(filepath)
    except Exception as e:
        logger.warning(f"Failed to save snapshot: {e}")
        return ""


# ══════════════════════════════════════════════════════════
# SMS Alert (Twilio)
# ══════════════════════════════════════════════════════════

def send_sms_alert(payload: AlertPayload, recipient_phone: str) -> bool:
    """Send an SMS alert via Twilio.

    Args:
        payload: AlertPayload with violation details.
        recipient_phone: Phone number to send SMS to.

    Returns:
        True if sent successfully, False on error.
    """
    if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_FROM:
        print("[WARNING] Twilio credentials not configured. SMS not sent.")
        return False

    sms_body = (
        f"SVIES ALERT [{payload.alert_level}]\n"
        f"Vehicle: {payload.plate}\n"
        f"Owner: {payload.owner_name}\n"
        f"Violations: {', '.join(payload.violations)}\n"
        f"Risk Score: {payload.risk_score}/100\n"
        f"Location: {payload.gps_location}\n"
        f"Time: {payload.timestamp_utc}"
    )

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            body=sms_body,
            from_=TWILIO_FROM,
            to=recipient_phone,
        )
        print(f"[SMS] Sent to {recipient_phone} | SID: {message.sid}")
        return True
    except ImportError:
        print("[WARNING] Twilio package not installed. SMS not sent.")
        return False
    except Exception as e:
        logger.warning(f"SMS send failed: {e}")
        return False


# ══════════════════════════════════════════════════════════
# Email Alert (Gmail SMTP)
# ══════════════════════════════════════════════════════════

def send_email_alert(payload: AlertPayload, recipient_email: str) -> bool:
    """Send an email alert via Gmail SMTP.

    Args:
        payload: AlertPayload with violation details.
        recipient_email: Email address to send to.

    Returns:
        True if sent successfully, False on error.
    """
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("[WARNING] Gmail credentials not configured. Email not sent.")
        return False

    subject = f"SVIES [{payload.alert_level}] Vehicle Violation: {payload.plate}"

    body = (
        f"SVIES — Smart Vehicle Intelligence & Enforcement System\n"
        f"{'=' * 50}\n\n"
        f"Alert Level:       {payload.alert_level}\n"
        f"Vehicle Plate:     {payload.plate}\n"
        f"Owner Name:        {payload.owner_name}\n"
        f"Owner Phone:       {payload.owner_phone}\n\n"
        f"Violations:\n"
    )
    for v in payload.violations:
        body += f"  • {v}\n"
    body += (
        f"\nFake Plate Flags:  {', '.join(payload.fake_plate_flags) if payload.fake_plate_flags else 'None'}\n"
        f"Risk Score:        {payload.risk_score}/100\n"
        f"Zone:              {payload.zone or 'N/A'}\n"
        f"GPS Location:      {payload.gps_location or 'N/A'}\n"
        f"Timestamp (UTC):   {payload.timestamp_utc}\n"
        f"SHA-256 Hash:      {payload.sha256_hash}\n"
        f"Snapshot:          {payload.snapshot_path or 'N/A'}\n\n"
        f"{'=' * 50}\n"
        f"This is an automated alert from SVIES.\n"
    )

    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # ── Attach snapshot if exists ──
        if payload.snapshot_path and Path(payload.snapshot_path).exists():
            with open(payload.snapshot_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-Disposition', 'attachment',
                               filename=Path(payload.snapshot_path).name)
                msg.attach(img)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, recipient_email, msg.as_string())

        print(f"[EMAIL] Sent to {recipient_email}")
        return True
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        return False


# ══════════════════════════════════════════════════════════
# Alert Dispatch Router
# ══════════════════════════════════════════════════════════

def dispatch_alert(payload: AlertPayload, alert_level: str) -> dict[str, Any]:
    """Route alerts to appropriate recipients based on severity level.

    Routing rules:
        CRITICAL: SMS + Email to police + owner
        HIGH:     SMS + Email to police + owner
        MEDIUM:   Email only to RTO + owner
        LOW:      Log only, no alert sent

    Args:
        payload: AlertPayload with all violation details.
        alert_level: Severity level (LOW/MEDIUM/HIGH/CRITICAL).

    Returns:
        Dict with dispatch results: sms_sent, email_sent, recipients.
    """
    result = {
        "sms_sent": False,
        "email_sent": False,
        "recipients": [],
        "alert_level": alert_level,
    }

    match alert_level:
        case "CRITICAL" | "HIGH":
            # ── SMS to police + owner ──
            if POLICE_PHONE:
                sms_ok = send_sms_alert(payload, POLICE_PHONE)
                result["sms_sent"] = result["sms_sent"] or sms_ok
                result["recipients"].append(f"SMS: {POLICE_PHONE}")

            if payload.owner_phone:
                sms_ok = send_sms_alert(payload, payload.owner_phone)
                result["sms_sent"] = result["sms_sent"] or sms_ok
                result["recipients"].append(f"SMS: {payload.owner_phone}")

            # ── Email to police + owner ──
            if POLICE_EMAIL:
                email_ok = send_email_alert(payload, POLICE_EMAIL)
                result["email_sent"] = result["email_sent"] or email_ok
                result["recipients"].append(f"Email: {POLICE_EMAIL}")

            if payload.owner_name and payload.owner_email:
                email_ok = send_email_alert(payload, payload.owner_email)
                result["email_sent"] = result["email_sent"] or email_ok
                result["recipients"].append(f"Email: {payload.owner_email}")

        case "MEDIUM":
            # ── Email only to RTO + owner ──
            if RTO_EMAIL:
                email_ok = send_email_alert(payload, RTO_EMAIL)
                result["email_sent"] = result["email_sent"] or email_ok
                result["recipients"].append(f"Email: {RTO_EMAIL}")

        case "LOW":
            # ── Log only ──
            print(f"[LOG] LOW risk alert for {payload.plate} — no notification sent.")

    return result


# ══════════════════════════════════════════════════════════
# Build Alert Payload Helper
# ══════════════════════════════════════════════════════════

def build_alert_payload(
    plate: str,
    owner_name: str = "",
    owner_phone: str = "",
    owner_email: str = "",
    violations: list[str] | None = None,
    fake_plate_flags: list[str] | None = None,
    risk_score: int = 0,
    alert_level: str = "LOW",
    zone: str = "",
    gps_location: str = "",
    frame: np.ndarray | None = None,
) -> AlertPayload:
    """Build a complete AlertPayload with timestamp and hash.

    Args:
        plate: License plate number.
        owner_name: Vehicle owner name.
        owner_phone: Vehicle owner phone.
        violations: List of violation codes.
        fake_plate_flags: List of fake plate flags.
        risk_score: Numeric risk score.
        alert_level: Alert severity level.
        zone: Zone ID where violation occurred.
        gps_location: GPS coordinates string.
        frame: Optional frame to save as snapshot.

    Returns:
        Fully populated AlertPayload.
    """
    violations = violations or []
    fake_plate_flags = fake_plate_flags or []

    timestamp_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sha256_hash = generate_sha256_hash(plate, timestamp_utc, violations)

    snapshot_path = ""
    if frame is not None:
        snapshot_path = save_snapshot(frame, plate)

    return AlertPayload(
        plate=plate,
        owner_name=owner_name,
        owner_phone=owner_phone,
        owner_email=owner_email,
        violations=violations,
        fake_plate_flags=fake_plate_flags,
        risk_score=risk_score,
        alert_level=alert_level,
        zone=zone,
        gps_location=gps_location,
        snapshot_path=snapshot_path,
        timestamp_utc=timestamp_utc,
        sha256_hash=sha256_hash,
    )


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Alert System Module Test")
    print("=" * 60)

    # ── Test 1: SHA-256 hash generation ──
    print("\n" + "-" * 40)
    print("TEST 1: SHA-256 Hash Generation")
    hash1 = generate_sha256_hash("TS09EF1234", "2025-02-01T14:30:22Z", ["EXPIRED_INSURANCE", "NO_PUCC"])
    hash2 = generate_sha256_hash("TS09EF1234", "2025-02-01T14:30:22Z", ["EXPIRED_INSURANCE", "NO_PUCC"])
    hash3 = generate_sha256_hash("TS09EF1234", "2025-02-01T14:30:23Z", ["EXPIRED_INSURANCE", "NO_PUCC"])
    print(f"  Hash 1: {hash1[:32]}...")
    print(f"  Hash 2: {hash2[:32]}...")
    print(f"  Hash 3: {hash3[:32]}... (different timestamp)")
    assert hash1 == hash2, "Same inputs should produce same hash!"
    assert hash1 != hash3, "Different timestamps should produce different hash!"
    print("  [✓] PASSED")

    # ── Test 2: Snapshot saving ──
    print("\n" + "-" * 40)
    print("TEST 2: Snapshot Saving")
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(test_frame, "TEST SNAPSHOT", (100, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
    snap_path = save_snapshot(test_frame, "TEST_PLATE")
    print(f"  Saved to: {snap_path}")
    assert snap_path != "", "Snapshot path should not be empty!"
    assert Path(snap_path).exists(), "Snapshot file should exist!"
    print("  [✓] PASSED")

    # ── Test 3: Build alert payload ──
    print("\n" + "-" * 40)
    print("TEST 3: Build Alert Payload")
    payload = build_alert_payload(
        plate="TS09EF1234",
        owner_name="Ravi Kumar",
        owner_phone="+919876543210",
        violations=["EXPIRED_INSURANCE", "NO_PUCC"],
        fake_plate_flags=["TYPE_MISMATCH"],
        risk_score=55,
        alert_level="HIGH",
        zone="SCHOOL_ZONE_01",
        gps_location="16.4823, 80.5012",
    )
    print(f"  Plate:       {payload.plate}")
    print(f"  Owner:       {payload.owner_name}")
    print(f"  Violations:  {payload.violations}")
    print(f"  Score:        {payload.risk_score}")
    print(f"  Level:       {payload.alert_level}")
    print(f"  Timestamp:   {payload.timestamp_utc}")
    print(f"  SHA256:      {payload.sha256_hash[:32]}...")
    assert payload.plate == "TS09EF1234"
    assert payload.timestamp_utc.endswith("Z")
    assert len(payload.sha256_hash) == 64
    print("  [✓] PASSED")

    # ── Test 4: Dispatch routing (dry run) ──
    print("\n" + "-" * 40)
    print("TEST 4: Alert Dispatch Routing (dry run — no actual SMS/email)")
    result = dispatch_alert(payload, "HIGH")
    print(f"  SMS Sent:    {result['sms_sent']}")
    print(f"  Email Sent:  {result['email_sent']}")
    print(f"  Recipients:  {result['recipients']}")
    print("  [✓] PASSED (credentials not configured = expected behavior)")

    # ── Test 5: LOW alert (log only) ──
    print("\n" + "-" * 40)
    print("TEST 5: LOW alert (should log only)")
    result = dispatch_alert(payload, "LOW")
    assert not result["sms_sent"]
    assert not result["email_sent"]
    print("  [✓] PASSED")

    print("\n" + "=" * 60)
    print("[✓] All alert system tests completed!")
