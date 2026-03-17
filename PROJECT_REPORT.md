# SVIES — Smart Vehicle Intelligence & Enforcement System

> **B.Tech CSE-AIML Final Year Project | SRM University AP — Amaravati**
> **Group 3 | Digital Image Processing (DIP) Course Project**

--- 
## 1. Project Idea & Vision

**SVIES** is a real-time AI-powered surveillance and enforcement system designed for Indian roads. It combines deep learning, computer vision, and multi-database intelligence to automatically detect traffic violations, identify vehicles, assess risk, and dispatch alerts to law enforcement — all from a single camera feed.

### The Problem

India loses approximately 1.5 lakh lives annually in road accidents. Manual enforcement is inconsistent, slow, and prone to human error. Existing ANPR (Automatic Number Plate Recognition) systems only read plates — they don't cross-check registration databases, detect fake plates, or assess cumulative risk.

### The Solution

SVIES goes beyond basic ANPR by implementing a **7-layer intelligence pipeline** that processes each video frame through:

1. **Vehicle Detection** — YOLOv8-based detection of cars, bikes, trucks, auto-rickshaws
2. **License Plate Localization & OCR** — EasyOCR + Tesseract ensemble with Indian plate regex validation
3. **Fake Plate Detection** (Novel) — 5 checks including type mismatch, color code violation, font anomaly, clone detection, state mismatch
4. **Database Intelligence** — Parallel cross-check against VAHAN (registration), PUCC (pollution), Insurance, and Stolen Vehicle databases
5. **Safety Compliance** — Helmet detection for two-wheelers and seatbelt detection for cars
6. **Speed Estimation** — Optical flow-based speed calculation with zone-specific Indian speed limits
7. **Risk Scoring & Alerts** — Weighted composite risk engine with automated SMS/email dispatch

### Novel Contributions

- **Fake Plate Detection Module** — First implementation of 5-check counterfeit plate detection using CMVR (Central Motor Vehicles Rules) and IS 10731 standards
- **Multi-Database Cross-Intelligence** — Parallel lookup across 4 government databases with SHA-256 integrity hashing
- **Zone-Aware Risk Scoring** — Multiplied penalties for violations in school zones, hospital zones, and government areas
- **Repeated Offender Escalation** — 3-tier escalation system (Yellow Flag → Orange Flag → Red Flag with automatic court summons)

---

## 2. System Architecture

```
                         ┌─────────────────────────────────────┐
                         │         SVIES Architecture          │
                         └─────────────────────────────────────┘

   ┌──────────┐    ┌──────────────────────────────────────────────────────┐
   │  Camera   │───>│                  SVIES Backend (Python)              │
   │  Feed     │    │                                                      │
   └──────────┘    │  ┌─────────┐  ┌──────┐  ┌───────────┐  ┌─────────┐  │
                   │  │ YOLOv8  │─>│ OCR  │─>│ Fake Plate│─>│ DB Intel│  │
                   │  │Detector │  │Engine│  │ Detection │  │ Lookup  │  │
                   │  └─────────┘  └──────┘  └───────────┘  └─────────┘  │
                   │                                                      │
                   │  ┌─────────┐  ┌──────┐  ┌───────────┐  ┌─────────┐  │
                   │  │ Helmet/ │─>│Speed │─>│ Geofence  │─>│  Risk   │  │
                   │  │Seatbelt │  │Estim.│  │  Check    │  │ Scorer  │  │
                   │  └─────────┘  └──────┘  └───────────┘  └─────────┘  │
                   │                                                      │
                   │  ┌──────────────────┐  ┌────────────────────────┐    │
                   │  │ Offender Tracker  │  │ Alert System (SMS/Email)│   │
                   │  └──────────────────┘  └────────────────────────┘    │
                   └──────────────────────────────────────────────────────┘
                           │                          │
                           ▼                          ▼
                   ┌──────────────┐          ┌──────────────────┐
                   │  FastAPI +   │          │  React Dashboard │
                   │  WebSocket   │◄────────>│  (Dark Glassmorphism)  │
                   │  REST API    │          │  11 Pages + Auth │
                   └──────────────┘          └──────────────────┘
                           │
                   ┌───────┴────────┐
                   ▼                ▼
            ┌────────────┐   ┌───────────┐
            │  Supabase  │   │  Firebase  │
            │ PostgreSQL │   │   Auth     │
            │ (Primary)  │   │ (Roles)   │
            └────────────┘   └───────────┘
```

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Object Detection | YOLOv8s (Ultralytics) | Vehicle, plate, helmet detection |
| OCR Engine | EasyOCR + Tesseract | Dual-engine license plate text extraction |
| Speed Estimation | OpenCV Optical Flow | Frame-to-frame displacement-based speed |
| Geofencing | Shapely (Python) | Point-in-polygon zone checks |
| Backend API | FastAPI + Uvicorn | REST + WebSocket endpoints |
| Frontend | React 19 + Vite 7 | Dark glassmorphism dashboard |
| Charts | Recharts | Analytics visualizations |
| Maps | Leaflet + React-Leaflet | Geofence zone visualization |
| Authentication | Firebase Auth | Email/password + Google sign-in with role-based access |
| Database | Supabase (PostgreSQL) | Primary data storage with SQLite fallback |
| Alerts | Twilio (SMS) + Gmail SMTP | Automated violation notifications |
| PDF Reports | ReportLab | Court summons and monthly reports |
| Training | Roboflow + Kaggle | Dataset management and model training |
| Deployment | Docker + Docker Compose | Containerized backend + frontend |

---

## 4. The 7-Layer Pipeline (Detailed)

### Layer 1: Vehicle Detection (`modules/detector.py` — 589 lines)
- Uses YOLOv8 model for detecting vehicles and license plates
- Supports car, motorcycle, bus, truck, auto-rickshaw
- Extracts vehicle bounding box, type, color, and plate crop
- Optimized for Indian road conditions

### Layer 2: OCR Engine (`modules/ocr_parser.py` — 451 lines)
- Dual-engine approach: EasyOCR (primary) + Tesseract (fallback)
- Indian plate regex validation: `^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$`
- Supports BH-series (Bharat) plates: `^BH\d{2}[A-Z]{1,3}\d{4}$`
- Character-level bounding box extraction for font analysis
- Confidence scoring with minimum threshold filtering

### Layer 2.5: Fake Plate Detection (`modules/fake_plate.py` — 540 lines) [NOVEL]
Five independent checks:
1. **TYPE_MISMATCH** — Compares detected vehicle type with VAHAN registration (e.g., motorcycle plate on a car)
2. **COLOR_CODE_VIOLATION** — Validates plate color against CMVR rules (white = private, yellow = commercial, green = EV)
3. **FONT_ANOMALY** — Checks character spacing and height against IS 10731:1983 standards
4. **DUPLICATE_PLATE_CLONE** — Detects the same plate at multiple camera locations simultaneously
5. **STATE_MISMATCH** — Validates plate prefix (e.g., "TS" for Telangana) against registration state

### Layer 3: Database Intelligence (`modules/db_intelligence.py` — 237 lines)
Parallel cross-check against 4 databases:
- **VAHAN** — Vehicle registration (owner, type, make, year, status)
- **PUCC** — Pollution Under Control Certificate (valid/expired/not found)
- **Insurance** — Third-party/comprehensive coverage (valid/expired)
- **Stolen** — National stolen vehicle registry

### Layer 4: Safety Compliance (`modules/helmet_detector.py` — 273 lines)
- YOLOv8-pose based rider detection on two-wheelers
- Helmet presence check using head region analysis
- Seatbelt detection for car occupants using diagonal line detection (30-70 degree angle)
- Violation flagging with confidence scoring

### Layer 5: Speed Estimation (`modules/speed_estimator.py` — 130 lines)
- Optical flow between consecutive frames
- Pixel displacement → real-world speed conversion
- Configurable pixels-per-meter calibration
- Zone-specific Indian speed limits:
  - School Zone: 25 km/h
  - Hospital Zone: 25 km/h
  - Residential: 30 km/h
  - City Road: 50 km/h
  - State Highway: 80 km/h
  - National Highway: 100 km/h
  - Expressway: 120 km/h

### Layer 6: Geofencing (`modules/geofence.py` — 221 lines)
- Shapely-based point-in-polygon zone detection
- 4 predefined zones: School, Hospital, Government, Low Emission
- Priority multipliers: School (1.8x), Hospital (1.5x), Government (1.3x), Low Emission (1.2x)

### Layer 7: Risk Scoring & Alerts

**Risk Scorer** (`modules/risk_scorer.py` — 294 lines):

| Violation | Weight | Severity |
|-----------|--------|----------|
| Stolen Vehicle | 40 | CRITICAL |
| Fake Plate | 35 | CRITICAL |
| No Registration | 25 | HIGH |
| Expired Insurance | 20 | HIGH |
| Repeat Offender | 20 | HIGH |
| Blacklist Zone | 15 | HIGH |
| Overspeeding | 15 | MEDIUM |
| No PUCC | 15 | MEDIUM |
| Helmet Violation | 10 | MEDIUM |
| Seatbelt Violation | 10 | MEDIUM |

Alert Levels: 0-20 = LOW, 21-40 = MEDIUM, 41-60 = HIGH, 61+ = CRITICAL

**Alert System** (`modules/alert_system.py` — 428 lines):
- CRITICAL/HIGH → SMS + Email to police and owner
- MEDIUM → Email to RTO and owner
- LOW → Log only
- SHA-256 integrity hash on every violation record
- Snapshot attachment with email alerts

**Offender Tracker** (`modules/offender_tracker.py` — 191 lines):
- Level 1 (Yellow Flag): 1-2 violations → Warning
- Level 2 (Orange Flag): 3-5 violations → Heavy fine
- Level 3 (Red Flag): 6+ violations → Court summons generated automatically

---

## 5. Frontend Dashboard

### Design System
- **Theme**: Dark government intelligence dashboard with glassmorphism
- **Background**: Deep navy (#0a0e1a) base with frosted glass cards (`backdrop-filter: blur(12px)`)
- **Accents**: Indigo primary (#6366f1), cyan secondary (#06b6d4)
- **Icons**: Lucide React (all SVG, professional, no emojis)
- **Font**: Inter (Google Fonts)
- **Responsive**: Mobile-friendly with sidebar collapse at 768px

### Pages (11 total)

| Page | Route | Description |
|------|-------|-------------|
| **Login** | `/login` | Firebase email/password + Google sign-in |
| **Overview** | `/` | Dashboard with 6 KPI cards, charts, recent violations |
| **Live Detection** | `/detect` | Real-time video processing via WebSocket |
| **Image Verify** | `/verify` | Single image 7-layer pipeline visualization |
| **Vehicle Lookup** | `/lookup` | Plate search with full VAHAN + compliance details |
| **Violations** | `/violations` | Paginated, filterable violation log |
| **Analytics** | `/analytics` | 4 charts: top violations, risk distribution, hourly patterns, alert breakdown |
| **Offenders** | `/offenders` | Top repeat offenders leaderboard with history |
| **Zone Map** | `/zones` | Leaflet map with colored zone polygons |
| **Active Learning** | `/learning` | Feedback submission + model retraining trigger |
| **User Management** | `/users` | Admin-only: create users, assign roles |

### Role-Based Access Control
| Role | Access Level |
|------|-------------|
| ADMIN | Full access — user management, retraining, all pages |
| POLICE | Detection, verification, violations, offenders, reports |
| RTO | Vehicle lookup, violations, analytics, zones |
| VIEWER | Read-only: dashboard, zones, basic stats |

---

## 6. API Endpoints (21 total)

### REST Endpoints (19)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health` | None | Health check |
| GET | `/api/stats` | VIEWER | Dashboard KPI stats |
| GET | `/api/violations` | RTO | Paginated violation log |
| GET | `/api/offenders` | POLICE | Top repeat offenders |
| GET | `/api/zones` | VIEWER | Geofence zone data |
| GET | `/api/vehicle/{plate}` | RTO | Full vehicle intelligence |
| GET | `/api/analytics` | RTO | Charts and trend data |
| POST | `/api/process-image` | POLICE | Process image through pipeline |
| POST | `/api/process-video` | POLICE | Upload video for processing |
| GET | `/api/process-status` | VIEWER | Video processing status |
| POST | `/api/seed-demo` | ADMIN | Seed 30 demo violations |
| GET | `/api/generate-report` | POLICE | Generate court summons PDF |
| POST | `/api/feedback` | POLICE | Submit OCR/detection corrections |
| GET | `/api/feedback/stats` | ADMIN | Active learning statistics |
| POST | `/api/retrain` | ADMIN | Trigger model retraining |
| GET | `/api/auth/verify` | Any | Verify token, return user info |
| GET | `/api/auth/users` | ADMIN | List all Firebase users |
| POST | `/api/auth/set-role` | ADMIN | Assign role to user |
| POST | `/api/auth/create-user` | ADMIN | Create new user account |

### WebSocket Endpoints (2)

| Endpoint | Description |
|----------|-------------|
| `/ws/live` | Real-time violation event stream |
| `/ws/live-feed` | Live video frame stream with detections |

---

## 7. Database Design

### Mock Database (JSON — 602 records)
| Database | Records | Purpose |
|----------|---------|---------|
| `vahan.json` | 200 | Vehicle registration — all 36 Indian states/UTs |
| `pucc.json` | 200 | Pollution certificates (~20% expired) |
| `insurance.json` | 200 | Insurance policies (~15% expired) |
| `stolen.json` | 2 | Stolen vehicle reports |
| `zones.json` | 4 | Geofence zones (school, hospital, govt, low emission) |

### Supabase PostgreSQL Tables
- `violations` — All logged violations with SHA-256 hash
- `vehicles` — Vehicle registration data
- `pucc_records` — PUCC certificates
- `insurance_records` — Insurance policies
- `stolen_vehicles` — Stolen vehicle registry
- `feedback` — OCR/detection corrections for active learning

### SQLite Fallback
- `data/violations/history.db` — Offline mode violation storage
- Automatic fallback when Supabase credentials are not configured

---

## 8. Model Training

### 3 Custom YOLOv8s Models

| Model | Dataset Source | Classes | Base | Epochs |
|-------|--------------|---------|------|--------|
| Plate Detector | Roboflow: vehicle-registration-plates | License plate | yolov8s.pt | 80 |
| Helmet Detector | Roboflow: hard-hat-workers | Helmet, No-Helmet | yolov8s.pt | 80 |
| Vehicle Detector | Roboflow: indian-vehicles-detection | Car, Bike, Bus, Truck, Auto | yolov8s.pt | 100 |

**Training Infrastructure**: NVIDIA V100 32GB GPU
**Training Notebooks**: `scripts/SVIES_V100_Training.ipynb`, `scripts/SVIES_Model_Training.ipynb`

### Hyperparameters (V100 Optimized)
- Image Size: 640x640
- Batch Size: 64
- Patience: 15 (early stopping)
- Workers: 4
- Augmentation: Mosaic, MixUp, HSV adjustments

---

## 9. Project Statistics

| Metric | Count |
|--------|-------|
| Total Python files | 34 |
| Total Python lines of code | ~8,862 |
| Total JSX/JS/CSS files | 28 |
| Total Frontend lines of code | ~5,191 |
| **Total lines of code** | **~14,053** |
| REST API endpoints | 19 |
| WebSocket endpoints | 2 |
| Frontend pages | 11 |
| Reusable React components | 9 |
| Python backend modules | 13 |
| Utility scripts | 7 |
| Jupyter notebooks | 2 |
| YOLO model files | 3 |
| Mock database records | 602 |
| Geofence zones | 4 |
| Python dependencies | 19 |
| NPM dependencies | 9 |

---

## 10. What Has Been Built (Completed Work)

### Backend — Python Pipeline (Fully Implemented)
- [x] 7-layer processing pipeline (`main.py` — orchestrates all modules)
- [x] YOLOv8 vehicle + plate detector (`modules/detector.py`)
- [x] EasyOCR + Tesseract dual-engine OCR with Indian plate regex (`modules/ocr_parser.py`)
- [x] 5-check fake plate detection system (`modules/fake_plate.py`) [NOVEL]
- [x] 4-database parallel cross-intelligence (`modules/db_intelligence.py`)
- [x] Helmet + seatbelt safety compliance detection (`modules/helmet_detector.py`)
- [x] Optical flow speed estimation with zone-specific limits (`modules/speed_estimator.py`)
- [x] Shapely-based geofencing with priority multipliers (`modules/geofence.py`)
- [x] Weighted composite risk scoring engine (`modules/risk_scorer.py`)
- [x] SMS (Twilio) + Email (Gmail SMTP) alert dispatch (`modules/alert_system.py`)
- [x] 3-tier repeat offender tracking with court summons (`modules/offender_tracker.py`)
- [x] Mock database loader for all 4 databases (`modules/mock_db_loader.py`)
- [x] Roboflow + Kaggle model training pipelines (`modules/roboflow_trainer.py`, `modules/kaggle_trainer.py`)

### Backend — API Server (Fully Implemented)
- [x] FastAPI REST API with 19 endpoints (`api/server.py` — 1,043 lines)
- [x] WebSocket live feed with token-based authentication
- [x] Firebase Admin SDK middleware with role-based access (`api/auth.py`)
- [x] Supabase PostgreSQL database layer with SQLite fallback (`api/database.py`)
- [x] CORS configuration (configurable via environment variable)
- [x] Image + video processing endpoints
- [x] User management endpoints (create, list, set role)
- [x] Demo data seeding endpoint
- [x] PDF court summons report generation
- [x] Active learning feedback + retrain endpoints

### Frontend — React Dashboard (Fully Implemented)
- [x] Dark glassmorphism design system (`styles/index.css` — 1,441 lines)
- [x] Firebase Authentication context (email + Google sign-in)
- [x] Role-based route protection (ADMIN > POLICE > RTO > VIEWER)
- [x] 11 pages covering all system features
- [x] 9 reusable components (Sidebar, Header, KPICard, StatusBadge, DataTable, etc.)
- [x] Recharts analytics (bar, area, pie charts)
- [x] Leaflet zone map with colored polygons
- [x] WebSocket real-time updates
- [x] Toast notifications for all actions
- [x] Responsive design (mobile-friendly)

### Data (Fully Implemented)
- [x] 200 vehicle records covering all 36 Indian states/UTs
- [x] 200 PUCC records (~20% expired for realistic testing)
- [x] 200 insurance records (~15% expired)
- [x] 2 stolen vehicle records
- [x] 4 geofence zones with GPS coordinates
- [x] Mock data generator script (`data/mock_db/generate_mock_data.py`)

### Training & Scripts
- [x] V100-optimized training notebook for 3 models (`scripts/SVIES_V100_Training.ipynb`)
- [x] General training notebook (`scripts/SVIES_Model_Training.ipynb`)
- [x] Demo pipeline script (no camera needed)
- [x] Setup verification script
- [x] PDF report export script
- [x] Roboflow dataset browser

### DevOps
- [x] Docker + Docker Compose configuration
- [x] Environment variable configuration (`.env.example`)
- [x] Git repository with proper `.gitignore`

### Bug Fixes Applied
- [x] Fixed double-detection bug (process_frame now returns detections for reuse)
- [x] Fixed alert system — owner email was never sent (missing field in AlertPayload)
- [x] Fixed WebSocket authentication (token verification added)
- [x] Fixed CORS — now configurable via `CORS_ORIGINS` env var
- [x] Fixed report generation — auth token now sent with blob download
- [x] Fixed seatbelt false positives — changed from vertical to diagonal line detection (30-70 degrees)
- [x] Fixed speed estimator — now reads from environment variables
- [x] Fixed component barrel file — rewrote with proper `export { default }` pattern
- [x] Fixed alert dispatch — owner email now sent for MEDIUM alerts too
- [x] Cleaned up project — removed duplicate files, untracked large binaries from git

---

## 11. Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- Firebase project with Authentication enabled
- (Optional) Supabase project for PostgreSQL

### Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your Firebase, Supabase, Twilio, Gmail credentials

# Start the API server
uvicorn api.server:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
# Opens at http://localhost:5173
```

### Model Training (V100 GPU)
1. Upload `scripts/SVIES_V100_Training.ipynb` to a Jupyter server with V100 GPU
2. Set your Roboflow API key in the notebook
3. Run all cells — trains 3 models in sequence
4. Download the `.pt` files to `models/` directory

---

## 12. Directory Structure

```
svies/
├── api/                        # FastAPI backend
│   ├── auth.py                 # Firebase auth middleware
│   ├── database.py             # Supabase + SQLite database layer
│   └── server.py               # REST + WebSocket endpoints
├── config.py                   # Environment configuration loader
├── main.py                     # 7-layer pipeline orchestrator
├── modules/                    # Core processing modules
│   ├── alert_system.py         # SMS/Email alerts
│   ├── db_intelligence.py      # 4-database cross-check
│   ├── detector.py             # YOLOv8 vehicle detection
│   ├── fake_plate.py           # 5-check fake plate detection [NOVEL]
│   ├── geofence.py             # Zone-based priority checks
│   ├── helmet_detector.py      # Helmet/seatbelt detection
│   ├── mock_db_loader.py       # JSON database loader
│   ├── ocr_parser.py           # Dual-engine OCR
│   ├── offender_tracker.py     # Repeat offender escalation
│   ├── risk_scorer.py          # Weighted risk scoring
│   ├── roboflow_trainer.py     # Model training via Roboflow
│   └── speed_estimator.py      # Optical flow speed estimation
├── frontend/                   # React dashboard
│   └── src/
│       ├── components/         # 9 reusable components
│       ├── config/firebase.js  # Firebase initialization
│       ├── context/            # Auth state management
│       ├── pages/              # 11 page components
│       └── styles/             # Glassmorphism CSS
├── data/                       # Databases and configs
│   ├── mock_db/                # 4 JSON databases (602 records)
│   └── geozones/               # Zone polygon definitions
├── models/                     # Trained YOLO .pt model files
├── scripts/                    # Training notebooks + utilities
├── requirements.txt            # Python dependencies
└── docker-compose.yml          # Container orchestration
```

---

## 13. Team

**SRM University AP — Amaravati**
B.Tech CSE-AIML, Final Year
Digital Image Processing (DIP) — Group 3

---

*This document was auto-generated based on the current state of the SVIES codebase.*
*Total codebase: ~14,053 lines across 62 source files.*
