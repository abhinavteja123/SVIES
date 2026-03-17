"""
SVIES — Configuration Module
Layer: Foundation
Loads all project settings from .env using python-dotenv.
All paths use pathlib.Path for cross-platform compatibility.

Usage:
    from config import *
    # All settings are available as module-level constants
"""

import re
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# ── Resolve project root ──
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# ── Load .env file ──
# We support multiple locations because uvicorn reload spawns a subprocess and
# users often keep `.env` at repo root (or set an explicit path).
_explicit_env = os.getenv("SVIES_ENV_FILE", "").strip()
_env_candidates: list[Path] = []
if _explicit_env:
    _env_candidates.append(Path(_explicit_env).expanduser())
_env_candidates.extend([
    PROJECT_ROOT / ".env",
    PROJECT_ROOT.parent / ".env",
    PROJECT_ROOT.parent.parent / ".env",
])

_loaded_env = False
for _p in _env_candidates:
    try:
        if _p and _p.exists():
            load_dotenv(_p, override=False)
            _loaded_env = True
            break
    except Exception:
        # If dotenv loading fails, continue to other candidates.
        pass

if not _loaded_env:
    # Last-resort: try default dotenv discovery from current working directory.
    try:
        _loaded_env = bool(load_dotenv(override=False))
    except Exception:
        _loaded_env = False

if not _loaded_env:
    print(f"[WARNING] .env file not found (searched: {', '.join(str(p) for p in _env_candidates)}). Using defaults.")

# ── Supabase Configuration (REQUIRED) ──
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# ── Twilio SMS Configuration ──
TWILIO_SID: str = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN: str = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM: str = os.getenv("TWILIO_FROM", "")
TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")

# ── Gmail SMTP Configuration ──
GMAIL_USER: str = os.getenv("GMAIL_USER", "")
GMAIL_PASSWORD: str = os.getenv("GMAIL_PASSWORD", "")

# ── Alert Recipients ──
POLICE_EMAIL: str = os.getenv("POLICE_EMAIL", "police_station@example.com")
POLICE_PHONE: str = os.getenv("POLICE_PHONE", "+919999999999")
RTO_EMAIL: str = os.getenv("RTO_EMAIL", "rto_office@example.com")

# ── Paths (resolved from project root) ──
GEOZONES_PATH: Path = PROJECT_ROOT / os.getenv("GEOZONES_PATH", "data/geozones/zones.json")
SNAPSHOT_DIR: Path = PROJECT_ROOT / os.getenv("SNAPSHOT_DIR", "snapshots")

# ── Create directories if they don't exist ──
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ── Detection Thresholds ──
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
OCR_MIN_CONFIDENCE: float = float(os.getenv("OCR_MIN_CONFIDENCE", "0.3"))

# ── Regex Patterns for Indian License Plates ──
# Standard format: AA00AA0000 or AA00A0000
PLATE_REGEX: re.Pattern = re.compile(r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$')
# BH-series format: 00BH0000AA
BH_REGEX: re.Pattern = re.compile(r'^\d{2}BH\d{4}[A-Z]{1,2}$')

# ── Rate Limiting ──
RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
RATE_LIMIT_UPLOAD: str = os.getenv("RATE_LIMIT_UPLOAD", "10/minute")

# ── Models Directory ──
MODELS_DIR: Path = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ── OpenStreetMap Overpass API (free, no API key required) ──
OSM_OVERPASS_URL: str = os.getenv("OSM_OVERPASS_URL", "https://overpass-api.de/api/interpreter")

# ── Model Versioning ──
MODEL_VERSION: str = os.getenv("MODEL_VERSION", "v1.0")

# ── Groq AI (OCR Verification) ──
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

# ── Roboflow ──
ROBOFLOW_API_KEY: str = os.getenv("ROBOFLOW_API_KEY", "")
PLATE_MODEL_PATH: Path = MODELS_DIR / "svies_plate_detector.pt"
HELMET_MODEL_PATH: Path = MODELS_DIR / "svies_helmet_detector.pt"
INDIAN_VEHICLE_MODEL_PATH: Path = MODELS_DIR / "svies_vehicle_classifier.pt"

# ── Indian Vehicle Types ──
# All vehicle types recognized on Indian roads
INDIAN_VEHICLE_TYPES: list[str] = [
    "CAR", "MOTORCYCLE", "SCOOTER", "AUTO", "BUS", "TRUCK",
    "TEMPO", "TRACTOR", "E_RICKSHAW", "VAN", "SUV",
]

# ── Indian State RTO Codes ──
INDIAN_STATE_CODES: dict[str, str] = {
    "AN": "Andaman & Nicobar", "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh",
    "AS": "Assam", "BR": "Bihar", "CG": "Chhattisgarh", "CH": "Chandigarh",
    "DD": "Daman & Diu", "DL": "Delhi", "GA": "Goa", "GJ": "Gujarat",
    "HP": "Himachal Pradesh", "HR": "Haryana", "JH": "Jharkhand",
    "JK": "Jammu & Kashmir", "KA": "Karnataka", "KL": "Kerala",
    "LA": "Ladakh", "MH": "Maharashtra", "ML": "Meghalaya",
    "MN": "Manipur", "MP": "Madhya Pradesh", "MZ": "Mizoram",
    "NL": "Nagaland", "OD": "Odisha", "PB": "Punjab", "PY": "Puducherry",
    "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu",
    "TR": "Tripura", "TS": "Telangana", "UK": "Uttarakhand",
    "UP": "Uttar Pradesh", "WB": "West Bengal",
}

# ── Reports Directory ──
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SVIES Configuration — Loaded Values")
    print("=" * 60)
    print(f"  PROJECT_ROOT:          {PROJECT_ROOT}")
    print(f"  SUPABASE_URL:          {SUPABASE_URL[:30] + '...' if SUPABASE_URL else '(not set)'}")
    print(f"  SUPABASE_KEY:          {'***' + SUPABASE_KEY[-4:] if len(SUPABASE_KEY) > 4 else '(not set)'}")
    print(f"  TWILIO_SID:            {'***' + TWILIO_SID[-4:] if len(TWILIO_SID) > 4 else '(not set)'}")
    print(f"  TWILIO_TOKEN:          {'***' + TWILIO_TOKEN[-4:] if len(TWILIO_TOKEN) > 4 else '(not set)'}")
    print(f"  TWILIO_FROM:           {TWILIO_FROM or '(not set)'}")
    print(f"  GMAIL_USER:            {GMAIL_USER or '(not set)'}")
    print(f"  GMAIL_PASSWORD:        {'***' if GMAIL_PASSWORD else '(not set)'}")
    print(f"  POLICE_EMAIL:          {POLICE_EMAIL}")
    print(f"  POLICE_PHONE:          {POLICE_PHONE}")
    print(f"  RTO_EMAIL:             {RTO_EMAIL}")
    print(f"  GEOZONES_PATH:         {GEOZONES_PATH}")
    print(f"  SNAPSHOT_DIR:          {SNAPSHOT_DIR}")
    print(f"  CONFIDENCE_THRESHOLD:  {CONFIDENCE_THRESHOLD}")
    print(f"  OCR_MIN_CONFIDENCE:    {OCR_MIN_CONFIDENCE}")
    print(f"  PLATE_REGEX:           {PLATE_REGEX.pattern}")
    print(f"  BH_REGEX:              {BH_REGEX.pattern}")
    print(f"  RATE_LIMIT_DEFAULT:    {RATE_LIMIT_DEFAULT}")
    print(f"  RATE_LIMIT_UPLOAD:     {RATE_LIMIT_UPLOAD}")
    print(f"  MODEL_VERSION:         {MODEL_VERSION}")
    print(f"  MODELS_DIR:            {MODELS_DIR}")
    print(f"  REPORTS_DIR:           {REPORTS_DIR}")
    print("=" * 60)
    print("[✓] Config loaded successfully!")
