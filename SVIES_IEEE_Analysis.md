# SVIES Codebase Analysis — IEEE Conference Paper Reference

**Document Generated:** 2026-03-23
**Project:** Smart Vehicle Intelligence & Enforcement System (SVIES)
**Purpose:** Technical extraction for IEEE conference research paper

---

## SECTION 1 — PROJECT STRUCTURE

```
svies/
├── api/
│   ├── __init__.py
│   ├── auth.py                # Firebase authentication & RBAC
│   ├── database.py            # Supabase/SQLite unified DB layer
│   ├── models.py              # Pydantic request/response models
│   └── server.py              # FastAPI REST + WebSocket server
├── data/
│   ├── geozones/zones.json    # 14 predefined geofence zones (Hyderabad)
│   ├── mock_db/
│   │   ├── generate_mock_data.py
│   │   ├── insurance.json, pucc.json, stolen.json, vahan.json
│   └── violations/init_db.py
├── edge/
│   ├── __init__.py
│   └── edge_mode.py           # YOLOv5n offline edge processing
├── frontend/                  # React + Vite dashboard
│   ├── package.json
│   └── src/                   # React components
├── models/                    # Pre-trained .pt model files
│   ├── svies_plate_detector.pt
│   ├── svies_helmet_detector.pt
│   ├── svies_vehicle_classifier.pt
│   ├── svies_age_classifier.pt
│   └── yolov8n.pt
├── modules/
│   ├── detector.py            # YOLOv8 vehicle/plate detection
│   ├── ocr_parser.py          # EasyOCR + Groq AI OCR pipeline
│   ├── fake_plate.py          # 8 forensic fake plate checks
│   ├── helmet_detector.py     # YOLOv8n-pose + heuristic safety
│   ├── age_classifier.py      # ResNet50 vehicle age classifier
│   ├── geofence.py            # Shapely point-in-polygon + OSM
│   ├── risk_scorer.py         # Weighted violation scoring
│   ├── alert_system.py        # Twilio SMS/WhatsApp + Gmail alerts
│   ├── db_intelligence.py     # Threaded 4-database cross-check
│   ├── offender_tracker.py    # Repeat offender escalation
│   ├── speed_estimator.py     # Optical flow speed estimation
│   └── mock_db_loader.py      # JSON mock database loader
├── scripts/                   # Training & utility scripts
├── tests/                     # pytest test suite
├── config.py                  # Environment configuration
├── main.py                    # Main processing pipeline orchestrator
├── requirements.txt           # Python dependencies
├── supabase_setup.sql         # PostgreSQL schema + seed data
├── Dockerfile, docker-compose.yml
└── SVIES_V100_Training_fixed.ipynb  # Model training notebook
```

### Entry Points

| File | Purpose | Command |
|------|---------|---------|
| `main.py` | Video/image processing pipeline with OpenCV viewer | `python main.py --source video.mp4` |
| `api/server.py` | FastAPI backend server | `uvicorn api.server:app --port 8000` |
| `edge/edge_mode.py` | Offline Raspberry Pi mode | `python -m edge.edge_mode` |

---

## SECTION 2 — TECH STACK & DEPENDENCIES

### Python Backend (`requirements.txt`)

| Category | Package | Version |
|----------|---------|---------|
| **Core AI/Vision** | ultralytics (YOLOv8) | ≥8.0.0 |
| | opencv-python | ≥4.8.0 |
| | torch | ≥2.0.0 |
| | torchvision | ≥0.15.0 |
| | numpy | ≥1.24.0 |
| **OCR** | easyocr | ≥1.7.0 |
| | pytesseract | ≥0.3.10 |
| **AI OCR Verification** | groq | ≥0.28.0 |
| **Geofencing** | shapely | ≥2.0.0 |
| **Backend API** | fastapi | ≥0.100.0 |
| | uvicorn[standard] | ≥0.23.0 |
| | python-multipart | ≥0.0.6 |
| | slowapi | ≥0.1.9 |
| **Database** | supabase | ≥2.0.0 |
| | pandas | ≥2.0.0 |
| **Auth** | firebase-admin | ≥6.0.0 |
| **Alerts** | twilio | ≥8.0.0 |
| **PDF Reports** | reportlab | ≥4.0.0 |
| **ML Training** | roboflow | ≥0.2.0 |

### Frontend (`frontend/package.json`)

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^19.2.0 | UI framework |
| react-dom | ^19.2.0 | DOM rendering |
| react-router-dom | ^7.13.0 | Client-side routing |
| firebase | ^11.0.0 | Authentication |
| leaflet | ^1.9.4 | Map rendering |
| react-leaflet | ^5.0.0 | React map components |
| recharts | ^3.7.0 | Data visualization charts |
| lucide-react | ^0.460.0 | Icon library |
| vite | ^7.3.1 | Build tool |

---

## SECTION 3 — AI/ML MODELS IMPLEMENTED

### 3.1 YOLOv8 Detection

#### Model Files Present in Repository

| File | Purpose | Size |
|------|---------|------|
| `svies_plate_detector.pt` | Indian license plate detection | Custom trained |
| `svies_helmet_detector.pt` | Helmet violation detection | Custom trained |
| `svies_vehicle_classifier.pt` | Vehicle type classification | Custom trained |
| `svies_age_classifier.pt` | Vehicle age estimation | ResNet50-based |
| `yolov8n.pt` | COCO-pretrained fallback | Standard YOLOv8n |

#### Architecture Details

- **Model Variant:** YOLOv8s (Small variant)
- **Parameters:** 11.2M
- **Input Image Size:** 640×640 (hardcoded at `detector.py:354`, `detector.py:422`)
- **Confidence Threshold:** 0.5 default (`config.py:82`), 0.25 for plate refinement (`detector.py:331`)

#### Detection Classes (COCO fallback)

From `detector.py:123-128`:
```python
VEHICLE_CLASSES: dict[int, str] = {
    2: "CAR",         # car
    3: "MOTORCYCLE",  # motorcycle
    5: "BUS",         # bus
    7: "TRUCK",       # truck
}
```

#### Indian Vehicle Types

From `detector.py:134-137`:
```python
INDIAN_VEHICLE_TYPES: set[str] = {
    "CAR", "MOTORCYCLE", "SCOOTER", "AUTO", "BUS", "TRUCK",
    "TEMPO", "TRACTOR", "E_RICKSHAW", "VAN", "SUV",
}
```

#### Preprocessing Pipeline

From `detector.py:232-253`:
- CLAHE enhancement on LAB L-channel
- Parameters: `clipLimit=2.0`, `tileGridSize=(8,8)`

---

### 3.2 OCR Pipeline

**File:** `modules/ocr_parser.py`

#### Primary OCR Engine: EasyOCR

From `ocr_parser.py:38-52`:
- Language: English
- GPU-enabled
- Character whitelist: `ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`

#### Secondary Engine: Tesseract OCR (Fallback)

From lines 305-339:
- Config: `--oem 3 --psm 8`
- Used when EasyOCR confidence is low

#### 6 Preprocessing Variants

From `ocr_parser.py:95-154`:

| Variant | Technique | Parameters |
|---------|-----------|------------|
| 1 | Standard Otsu | Binary threshold |
| 2 | CLAHE + Otsu | clipLimit=4.0, tileGridSize=(4,4) |
| 3 | Denoised + Otsu | fastNlMeansDenoising h=10 |
| 4 | Inverted | Bitwise NOT |
| 5 | Raw upscaled | Grayscale, no threshold |
| 6 | Adaptive Gaussian | blockSize=31, C=10 |

#### Image Upscaling

- Target height: 250px
- Maximum scale: 5×
- Interpolation: INTER_LANCZOS4

#### AI OCR Verification (Groq LLM)

From `ocr_parser.py:446-537`:
- **Model:** `meta-llama/llama-4-scout-17b-16e-instruct`
- **Input:** Base64 JPEG image + OCR text
- **Output:** Verified/corrected plate number

#### Indian Plate Regex Patterns

From `config.py:87-89`:
```python
PLATE_REGEX = re.compile(r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$')
BH_REGEX = re.compile(r'^\d{2}BH\d{4}[A-Z]{1,2}$')
```

#### Character Correction Logic

From `ocr_parser.py:346-403`:

| Position | Type | Corrections |
|----------|------|-------------|
| 0-1 | State code (letters) | `0→O`, `1→I`, `8→B` |
| 2-3 | District (numbers) | `O→0`, `I→1`, `B→8`, `S→5`, `Z→2` |
| Tail | Registration number | Context-aware substitution |

---

### 3.3 Fake Plate Detection Module

**File:** `modules/fake_plate.py`

#### 8 Forensic Checks Implemented

| # | Flag Name | Function | Line | Status |
|---|-----------|----------|------|--------|
| 0 | STOLEN_VEHICLE | `check_stolen_vehicle()` | 227-246 | ✅ Full |
| 0.5 | VAHAN_NOT_EXISTS | `check_vahan_exists()` | 129-155 | ✅ Full |
| 1 | TYPE_MISMATCH | `check_type_mismatch()` | 250-278 | ✅ Full |
| 2 | COLOR_CODE_VIOLATION | `check_color_code_violation()` | 333-369 | ✅ Full |
| 3 | FONT_ANOMALY | `check_font_anomaly()` | 376-449 | ✅ Full |
| 4 | DUPLICATE_PLATE_CLONE | `check_duplicate_plate()` | 456-490 | ✅ Full |
| 5 | STATE_MISMATCH | `check_state_mismatch()` | 506-541 | ✅ Full |
| 6 | PUCC_INVALID | `check_pucc_valid()` | 157-189 | ✅ Full |
| 7 | INSURANCE_INVALID | `check_insurance_valid()` | 192-224 | ✅ Full |

#### CMVR Color Classification

From `fake_plate.py:285-330`:

| Plate Type | HSV Range |
|------------|-----------|
| PRIVATE (white) | H[0-180], S[0-30], V[200-255] |
| COMMERCIAL (yellow) | H[20-35], S[100-255], V[100-255] |
| EV (green) | H[45-85], S[100-255], V[100-255] |
| RENTAL (black) | H[0-180], S[0-30], V[0-50] |

#### IS 10731 Font Anomaly Detection

From `fake_plate.py:376-449`:
- Expected height ratio: 0.5-0.7
- Expected spacing ratio: 0.1-0.3
- Flags if >30% characters fail metrics

#### Clone Detection Algorithm

From `fake_plate.py:456-490`:
- Data structure: In-memory dict `{plate: (last_seen_utc, camera_id)}`
- Time window: 10 minutes
- Flags plates seen at multiple cameras within window

---

### 3.4 Helmet & Seatbelt Detection

**File:** `modules/helmet_detector.py`

#### Models Used

| Priority | Model | Purpose |
|----------|-------|---------|
| 1 | `svies_helmet_detector.pt` | Custom helmet detector |
| 2 | `yolov8n-pose.pt` | Pose estimation fallback |
| 3 | Heuristic | Skin/edge analysis |

#### Skin Color Detection Parameters

From `helmet_detector.py:88-95`:
```python
# HSV ranges for Indian skin tones
SKIN_LOWER_1 = np.array([0, 30, 80])    # Lighter skin
SKIN_UPPER_1 = np.array([25, 180, 255])
SKIN_LOWER_2 = np.array([0, 20, 50])    # Darker skin
SKIN_UPPER_2 = np.array([20, 200, 180])
```

Also uses YCrCb space for dark skin tones (line 122-124).

#### Helmet Detection Logic

From `helmet_detector.py:140-142`:
```python
helmet_present = non_skin > 0.75 and edge_ratio > 0.08
confidence = min(non_skin * 0.5 + edge_ratio * 2.5, 1.0)
```

#### Seatbelt Detection Algorithm

From `helmet_detector.py:149-180`:
1. Canny edge detection (thresholds: 50, 150)
2. HoughLinesP parameters:
   - threshold=30
   - minLineLength=40
   - maxLineGap=10
3. Count diagonal lines (30-70° or 110-150°)
4. Seatbelt detected if `diagonal_count ≥ 3`

---

### 3.5 Vehicle Age Classifier

**File:** `modules/age_classifier.py`

#### Model Architecture

- **Base:** ResNet50
- **Model file:** `svies_age_classifier.pt`
- **FC Head Structure:**
  ```
  Dropout(0.3) → Linear(2048, 512) → ReLU → Dropout(0.3) → Linear(512, 5)
  ```

#### Age Categories

From `age_classifier.py:33`:
```python
AGE_CATEGORIES = ["NEW", "1-3 YEARS", "3-5 YEARS", "5-10 YEARS", "OLD"]
```

| Category | Age Range |
|----------|-----------|
| NEW | 0-1 years (showroom condition) |
| 1-3 YEARS | Slight wear, recent model |
| 3-5 YEARS | Moderate wear |
| 5-10 YEARS | Visible aging, older model |
| OLD | 10+ years, significant wear |

#### Preprocessing

From `age_classifier.py:152-183`:
- Resize: 224×224 (ResNet50 standard)
- Color conversion: BGR → RGB
- ImageNet normalization:
  - mean = [0.485, 0.456, 0.406]
  - std = [0.229, 0.224, 0.225]

---

## SECTION 4 — RISK SCORING ENGINE

**File:** `modules/risk_scorer.py`

### Violation Weights

From `risk_scorer.py:50-69`:

| Violation | Weight |
|-----------|--------|
| STOLEN_VEHICLE | 40 |
| FAKE_PLATE | 35 |
| UNREGISTERED_VEHICLE | 25 |
| NO_REGISTRATION | 25 |
| EXPIRED_INSURANCE | 20 |
| NO_INSURANCE | 20 |
| REPEAT_OFFENDER | 20 |
| NO_NUMBER_PLATE | 20 |
| BLACKLIST_ZONE | 15 |
| OVERSPEEDING | 15 |
| EXPIRED_PUCC | 15 |
| NO_PUCC | 15 |
| WRONG_SIDE_DRIVING | 15 |
| RED_LIGHT_VIOLATION | 15 |
| HELMET_VIOLATION | 10 |
| SEATBELT_VIOLATION | 10 |
| TRIPLE_RIDING | 10 |

### Alert Level Thresholds

From `risk_scorer.py:72-88`:

| Score Range | Alert Level |
|-------------|-------------|
| 61+ | CRITICAL |
| 41-60 | HIGH |
| 21-40 | MEDIUM |
| 0-20 | LOW |

### Risk Calculation Formula

```python
total_score = sum(RISK_WEIGHTS[violation] for violation in detected_violations)
if zone_multiplier > 1.0:
    total_score = int(total_score * zone_multiplier)
alert_level = _score_to_level(total_score)
```

---

## SECTION 5 — DATABASE SCHEMA

**File:** `supabase_setup.sql`

### Tables

#### violations
```sql
CREATE TABLE violations (
    id          BIGSERIAL PRIMARY KEY,
    plate       TEXT NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
    violation_types TEXT,
    risk_score  INTEGER DEFAULT 0,
    zone_id     TEXT DEFAULT '',
    alert_level TEXT DEFAULT 'LOW',
    sha256_hash TEXT UNIQUE,
    vehicle_type    TEXT DEFAULT '',
    owner_name      TEXT DEFAULT '',
    model_used      TEXT DEFAULT '',
    captured_image  TEXT DEFAULT '',
    annotated_image TEXT DEFAULT '',
    vehicle_age     TEXT DEFAULT ''
);
```

#### vehicles (VAHAN mirror)
```sql
CREATE TABLE vehicles (
    plate                   TEXT PRIMARY KEY,
    owner                   TEXT,
    phone                   TEXT,
    email                   TEXT,
    vehicle_type            TEXT,
    color                   TEXT,
    make                    TEXT,
    year                    INTEGER,
    state                   TEXT,
    registration_state_code TEXT,
    status                  TEXT DEFAULT 'ACTIVE'
);
```

#### pucc
```sql
CREATE TABLE pucc (
    plate       TEXT PRIMARY KEY,
    valid_until DATE,
    status      TEXT DEFAULT 'VALID'
);
```

#### insurance
```sql
CREATE TABLE insurance (
    plate       TEXT PRIMARY KEY,
    valid_until DATE,
    type        TEXT,
    status      TEXT DEFAULT 'VALID'
);
```

#### stolen_vehicles
```sql
CREATE TABLE stolen_vehicles (
    plate       TEXT PRIMARY KEY,
    reported_on DATE DEFAULT CURRENT_DATE
);
```

#### feedback
```sql
CREATE TABLE feedback (
    id                  BIGSERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT now(),
    original_plate      TEXT,
    correct_plate       TEXT,
    correct_vehicle_type TEXT,
    notes               TEXT,
    image_file          TEXT
);
```

### Indexes

```sql
CREATE INDEX idx_violations_plate ON violations (plate);
CREATE INDEX idx_violations_timestamp ON violations (timestamp DESC);
CREATE INDEX idx_violations_level ON violations (alert_level);
CREATE INDEX idx_feedback_timestamp ON feedback (timestamp DESC);
```

### Repeat Offender Logic

From `database.py:186-214`:
```python
def get_offender_level(self, plate: str) -> int:
    # Count violations in last 30 days
    if count == 0:
        return 0      # No violations
    elif count <= 2:
        return 1      # 1-2 violations
    elif count <= 5:
        return 2      # 3-5 violations
    else:
        return 3      # 6+ violations
```

---

## SECTION 6 — GEOFENCING & ZONE LOGIC

**File:** `modules/geofence.py`

### Zone Definition Format

**File:** `data/geozones/zones.json`

```json
{
    "zones": [
        {
            "id": "SCHOOL_JNTU",
            "name": "JNTU Hyderabad Campus",
            "type": "SCHOOL",
            "priority": "HIGH",
            "polygon": [
                [78.4900, 17.4935],
                [78.4958, 17.4935],
                [78.4958, 17.4880],
                [78.4900, 17.4880]
            ]
        }
    ]
}
```

### Predefined Zones (14 total)

| Type | Zones |
|------|-------|
| SCHOOL | JNTU, OU, UoH |
| HOSPITAL | NIMS, Gandhi, KIMS |
| GOVT | Secretariat, Collectorate |
| HIGHWAY | ORR Gachibowli, Shamshabad, Hitech City |
| LOW_EMISSION | Charminar, Tank Bund, Jubilee Hills |

### Priority Multipliers

From `geofence.py:39-45`:
```python
PRIORITY_MULTIPLIERS: dict[str, float] = {
    "SCHOOL": 1.5,
    "HOSPITAL": 1.5,
    "GOVT": 1.3,
    "LOW_EMISSION": 1.2,
    "HIGHWAY": 1.4,
}
```

### Point-in-Polygon Implementation

- **Library:** Shapely
- **Function:** `Point.contains()` for polygon containment checks

### OSM Dynamic Zone Loading

From `geofence.py:180-313`:
- **API:** Overpass API (free, no API key required)
- **Query radius:** Configurable
- **Fetches:** Schools, hospitals, government buildings
- **OSM amenity → SVIES type mapping** at lines 170-178

---

## SECTION 7 — ALERT & NOTIFICATION SYSTEM

**File:** `modules/alert_system.py`

### SMS via Twilio

From `alert_system.py:118-157`:

**Template:**
```
SVIES ALERT [{alert_level}]
Vehicle: {plate}
Owner: {owner_name}
Violations: {violations}
Risk Score: {risk_score}/100
Location: {gps_location}
Time: {timestamp_utc}
```

### Email via Gmail SMTP

From `alert_system.py:214-278`:
- **Port:** 587 with STARTTLS
- **Attachments:** Snapshot image (if available)
- **Includes:** SHA-256 evidence hash

### WhatsApp via Twilio

From `alert_system.py:164-207`:
- Uses emoji formatting
- Same content structure as SMS

### SHA-256 Evidence Hashing

From `alert_system.py:64-79`:
```python
def generate_sha256_hash(plate: str, timestamp_utc: str, violations: list[str]) -> str:
    violations_str = ",".join(sorted(violations))
    data = f"{plate}{timestamp_utc}{violations_str}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
```

**Fields hashed:** plate + ISO timestamp + comma-joined sorted violations

### Alert Routing Matrix

From `alert_system.py:284-354`:

| Alert Level | SMS | Email | WhatsApp | Recipients |
|-------------|-----|-------|----------|------------|
| CRITICAL | ✅ | ✅ | ✅ | Police + Owner |
| HIGH | ✅ | ✅ | ✅ | Police + Owner |
| MEDIUM | ❌ | ✅ | ❌ | RTO only |
| LOW | ❌ | ❌ | ❌ | Log only |

---

## SECTION 8 — OFFLINE EDGE MODE

**File:** `edge/edge_mode.py`

### Edge Model

- **Model:** YOLOv5n (lightweight)
- **Fallback:** `yolov5nu.pt` from Ultralytics hub
- **Location:** Lines 28-39

### Edge Cache Structure

**File:** `edge/edge_cache.json`

```json
{
    "vahan": {
        "PLATE_NUMBER": {
            "owner": "...",
            "vehicle_type": "...",
            ...
        }
    },
    "stolen": ["PLATE1", "PLATE2", ...],
    "built_at": "ISO_TIMESTAMP"
}
```

### Offline Alert Queue

**File:** `edge/offline_queue.json`

- Queue limit: Unlimited
- Each alert includes `queued_at` timestamp
- Sync-on-connect implementation at `sync_queue()` (lines 137-166)

### Edge Detection Classes

From `edge_mode.py:50`:
```python
VEHICLE_MAP = {2: "CAR", 3: "MOTORCYCLE", 5: "BUS", 7: "TRUCK"}
```

### Plate Region Estimation

From `edge_mode.py:94-105`:
- Horizontal: 15%-85% of vehicle width
- Vertical: 65%-90% of vehicle height

---

## SECTION 9 — DASHBOARD & API

### Dashboard Technology Stack

| Layer | Technology |
|-------|------------|
| Framework | React 19 |
| Build Tool | Vite 7.3 |
| Routing | React Router 7 |
| Charts | Recharts |
| Maps | Leaflet + React-Leaflet |
| Icons | Lucide React |
| Authentication | Firebase |

### REST API Endpoints

**File:** `api/server.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Health check |
| POST | `/detect` | Image upload detection |
| GET | `/violations` | Paginated violation list |
| GET | `/violations/{sha256}` | Single violation by hash |
| GET | `/stats` | Dashboard statistics |
| GET | `/offenders` | Top repeat offenders |
| GET | `/vehicles` | Vehicle registry list |
| POST | `/vehicles` | Add vehicle |
| PUT | `/vehicles/{plate}` | Update vehicle |
| DELETE | `/vehicles/{plate}` | Delete vehicle |
| POST | `/feedback` | Submit OCR correction |
| POST | `/seed-demo` | Seed demo data |
| WebSocket | `/ws/detections` | Real-time detection stream |

### Export Formats

- CSV export for violations
- CSV export for offenders
- PDF court summons generation

---

## SECTION 10 — PERFORMANCE RESULTS

### Training Results (From Notebook)

**Hardware:** NVIDIA Tesla V100-SXM2 (32GB VRAM)

| Model | Expected mAP@50 | Inference Time |
|-------|-----------------|----------------|
| Indian Plate Detector | 88-95% | ~8ms/image |
| Helmet Violation Detector | 82-90% | ~8ms/image |
| Vehicle Classifier | 70-82% | ~8ms/image |

### Notes

- No end-to-end latency benchmarks found in codebase
- No confusion matrices saved in repository
- No ROC curves present
- Training time on V100: ~3-5 hours for all 3 models

---

## SECTION 11 — DATASET DETAILS

**Source:** `SVIES_V100_Training_fixed.ipynb`

### Model 1 — Indian License Plate Detector

| Dataset | Source | Images | Class |
|---------|--------|--------|-------|
| indian-number-plate | Roboflow v3 | 1,683 | IndianNumberPlate |
| indian-cars-number-plate | Roboflow v1 | 418 | License-Plate |
| **Total** | Merged | ~2,100 | plate |

### Model 2 — Helmet Violation Detector

| Dataset | Source | Images | Original Classes |
|---------|--------|--------|------------------|
| motorcycle-helmet-detection | Roboflow v2 | 2,215 | no helmet, full-faced, half-faced, invalid |
| two-wheeler-helmet | Roboflow v1 | 305 | with_helmet, without_helmet |
| **Total** | Merged | ~2,520 | with_helmet, without_helmet |

**Remapping:** `full-faced`, `half-faced` → `with_helmet`; `no helmet` → `without_helmet`; `invalid` → dropped

### Model 3 — Vehicle Type Detector

| Dataset | Source | Images | Classes |
|---------|--------|--------|---------|
| vehicles-openimages | Roboflow v1 | 627 | Car, Bus, Motorcycle, Truck, Ambulance |

### Training Hyperparameters

| Parameter | Plates/Helmets | Vehicles |
|-----------|----------------|----------|
| Epochs | 100 | 150 |
| Batch Size | 32 | 16 |
| Image Size | 640×640 | 640×640 |
| Optimizer | AdamW | AdamW |
| Learning Rate | 0.001 → 0.01 | 0.001 → 0.01 |
| LR Schedule | Cosine | Cosine |
| Patience | 15 | 20 |
| Warmup Epochs | 5 | 5 |

### Data Augmentation

Default YOLOv8 augmentations:
- Mosaic
- HSV color jitter
- Horizontal flip
- Scale

---

## SECTION 12 — NOVEL CONTRIBUTIONS

### 1. Multi-Attempt OCR Pipeline

**File:** `ocr_parser.py:95-256`

- 6 preprocessing variants with best-score selection
- Position-based character correction for Indian plates
- **Novel:** AI verification via Groq LLM vision API

### 2. 8-Check Fake Plate Detection System

**File:** `fake_plate.py`

Combines:
- Database existence verification
- Vehicle type mismatch detection
- CMVR color compliance checking
- IS 10731 font metrics analysis
- **Novel:** Clone detection using in-memory plate tracking across cameras
- State code mismatch
- PUCC/Insurance validity

### 3. Hybrid Helmet Detection

**File:** `helmet_detector.py`

Cascade:
1. Custom YOLO model
2. YOLOv8n-pose keypoints
3. **Novel:** Skin/edge heuristic with multi-range HSV + YCrCb detection tuned for Indian skin tones

### 4. Indian-Specific Vehicle Classification

**File:** `detector.py:197-225`

Types not in standard COCO:
- AUTO (auto-rickshaw)
- E_RICKSHAW
- TEMPO
- TRACTOR

Size-based classification heuristic for Indian vehicle types.

### 5. Zone-Weighted Risk Scoring

**File:** `risk_scorer.py`, `geofence.py`

- Priority multipliers (1.2×-1.5×) for sensitive zones
- **Novel:** OSM dynamic zone loading via Overpass API

### 6. Cryptographic Evidence Integrity

**File:** `alert_system.py:64-79`

SHA-256 hashing of plate + timestamp + violations for tamper-proof violation records.

---

## Summary — Algorithms Written From Scratch

| Algorithm | File | Lines |
|-----------|------|-------|
| Plate color classification (CMVR) | `fake_plate.py` | 285-330 |
| Font anomaly detection (IS 10731) | `fake_plate.py` | 376-449 |
| Clone detection | `fake_plate.py` | 456-490 |
| Helmet skin-detection heuristic | `helmet_detector.py` | 98-146 |
| Optical flow speed estimator | `speed_estimator.py` | 52-107 |
| Indian plate character correction | `ocr_parser.py` | 346-403 |

## Dependencies on Existing Libraries

| Library | Purpose |
|---------|---------|
| Ultralytics YOLOv8 | Object detection backbone |
| EasyOCR | Primary OCR engine |
| Shapely | Geofence polygon operations |
| Groq SDK | LLM-based OCR verification |
| Firebase Admin | Authentication |
| Twilio | SMS/WhatsApp alerts |
| Supabase | Cloud database |

---

*This document was auto-generated from SVIES codebase analysis for IEEE conference paper preparation.*
