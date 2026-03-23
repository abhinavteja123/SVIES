# SVIES — Smart Vehicle Identification & Enforcement System

> AI-powered traffic violation detection and enforcement platform optimized for Indian roads.

SVIES is a comprehensive vehicle surveillance system that uses **YOLOv8** deep learning models to detect vehicles, read license plates, identify safety violations, and detect fake/cloned plates. It processes images, video files, and live camera streams in real-time with a 7-layer AI pipeline.

---

## Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [7-Layer Detection Pipeline](#7-layer-detection-pipeline)
- [Project Structure](#project-structure)
- [Modules Overview](#modules-overview)
- [Frontend Pages](#frontend-pages)
- [API Endpoints](#api-endpoints)
- [Getting Started](#getting-started)
- [Docker Deployment](#docker-deployment)
- [Environment Variables](#environment-variables)
- [Database Schema](#database-schema)
- [Active Learning Pipeline](#active-learning-pipeline)
- [Authentication & Roles](#authentication--roles)
- [Technology Stack](#technology-stack)
- [Indian Road Optimizations](#indian-road-optimizations)

---

## Features

### Core Detection Capabilities

| Feature | Description |
|---------|-------------|
| **Vehicle Detection** | YOLOv8-based detection of 11 Indian vehicle types: CAR, MOTORCYCLE, SCOOTER, AUTO (rickshaw), BUS, TRUCK, TEMPO, TRACTOR, E_RICKSHAW, VAN, SUV |
| **License Plate OCR** | Multi-engine OCR with EasyOCR + Tesseract + Groq AI LLM verification. Supports standard (AA00AA0000) and BH-series (00BH0000AA) formats |
| **Helmet Detection** | Dedicated YOLOv8 model for two-wheeler helmet/no-helmet classification |
| **Seatbelt Detection** | Safety violation detection for four-wheelers |
| **Vehicle Age Classification** | ResNet50-based model to classify vehicles as NEW (0-5yr), MODERATE (5-10yr), OLD (10-15yr), VINTAGE (15+yr) |
| **Fake Plate Detection** | 5-check system to detect counterfeit or cloned license plates |
| **Vehicle Color Recognition** | HSV-based 8-class color classification (WHITE, BLACK, RED, BLUE, GREEN, YELLOW, SILVER, GREY) |

### Enforcement Features

| Feature | Description |
|---------|-------------|
| **Live Detection** | Real-time webcam, video upload, and image scanning |
| **Geofenced Zones** | 14+ configurable enforcement zones with risk multipliers and speed limits |
| **Repeat Offender Detection** | Tracks multi-violation offenders with escalation scores |
| **Risk Scoring** | Multi-factor assessment (time, zone, vehicle type, speed, history) |
| **Alert System** | Email (Gmail SMTP) and SMS (Twilio) notifications |
| **Court Summons PDF** | Auto-generated PDF reports for violations |
| **Violation Snapshots** | Annotated images saved with detection details |

### System Features

| Feature | Description |
|---------|-------------|
| **Active Learning** | 3-model version management with feedback-driven YOLOv8 fine-tuning |
| **Role-Based Access** | Firebase Auth with ADMIN, POLICE, RTO, VIEWER roles |
| **Analytics Dashboard** | Charts, KPIs, violation trends, zone heatmaps |
| **Vehicle Management** | CRUD operations for VAHAN, PUCC, Insurance, Stolen databases |
| **Export Reports** | CSV/Excel export for violations and offenders |

---

## System Architecture

```
+------------------------------------------------------------------+
|                     SVIES System Architecture                      |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------------+    +-----------------------------+     |
|  |    React Frontend      |    |      FastAPI Backend        |     |
|  |      (Vite + SPA)      |<-->|    (Python + Uvicorn)       |     |
|  +------------------------+    +-----------------------------+     |
|           |                              |                         |
|           v                              v                         |
|  +------------------+         +------------------------+           |
|  | 12 React Pages   |         | 7-Layer AI Pipeline    |           |
|  | - Overview       |         | - Vehicle Detection    |           |
|  | - Live Detection |         | - Plate OCR            |           |
|  | - Image Verify   |         | - Fake Plate Check     |           |
|  | - Violations     |         | - Safety Detection     |           |
|  | - Analytics      |         | - Risk Scoring         |           |
|  | - Zone Map       |         | - Alert System         |           |
|  | - Offenders      |         | - DB Intelligence      |           |
|  | - Active Learning|         +------------------------+           |
|  | - User Management|                    |                         |
|  | - Vehicle Lookup |                    v                         |
|  | - Vehicle Mgmt   |         +------------------------+           |
|  | - Login          |         |   Database Layer       |           |
|  +------------------+         | - Supabase (PostgreSQL)|           |
|                               | - SQLite (fallback)    |           |
|                               +------------------------+           |
+------------------------------------------------------------------+
```

### WebSocket Connections

| Endpoint | Purpose |
|----------|---------|
| `ws://localhost:8000/ws/live` | Real-time violation alerts stream |
| `ws://localhost:8000/ws/live-feed` | Live video frames at ~10 FPS |

---

## 7-Layer Detection Pipeline

```
+------------------------------------------------------------------------+
|                    SVIES 7-Layer Detection Pipeline                     |
+------------------------------------------------------------------------+
|                                                                         |
|  INPUT: Image / Video Frame / Webcam Frame                              |
|                                                                         |
|  +------------------------------------------------------------------+  |
|  | LAYER 1: PREPROCESSING                                            |  |
|  | - CLAHE enhancement for low-light/dust conditions                 |  |
|  | - LAB color space conversion for contrast normalization           |  |
|  +------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +------------------------------------------------------------------+  |
|  | LAYER 2: VEHICLE DETECTION (YOLOv8)                               |  |
|  | - Primary: COCO YOLOv8n (car, motorcycle, bus, truck)             |  |
|  | - Custom: svies_vehicle_classifier.pt (Indian vehicles)           |  |
|  | - Output: Vehicle bbox, type, confidence, color                   |  |
|  +------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +------------------------------------------------------------------+  |
|  | LAYER 2.5: FAKE PLATE DETECTION [NOVEL]                           |  |
|  | 5 Checks:                                                         |  |
|  | 1. TYPE_MISMATCH - detected vs VAHAN registration                 |  |
|  | 2. COLOR_CODE_VIOLATION - plate color vs CMVR rules               |  |
|  | 3. FONT_ANOMALY - IS 10731 character spacing/height               |  |
|  | 4. DUPLICATE_PLATE_CLONE - same plate at multiple locations       |  |
|  | 5. STATE_MISMATCH - plate prefix vs registration state            |  |
|  +------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +------------------------------------------------------------------+  |
|  | LAYER 3: LICENSE PLATE OCR                                        |  |
|  | - Plate localization: svies_plate_detector.pt + ResNet50 fallback |  |
|  | - 6 preprocessing variants (grayscale, CLAHE, threshold, etc.)    |  |
|  | - Multi-attempt EasyOCR with confidence scoring                   |  |
|  | - Groq AI LLM verification and correction                         |  |
|  | - Indian plate regex validation (standard + BH-series)            |  |
|  +------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +------------------------------------------------------------------+  |
|  | LAYER 4: DATABASE INTELLIGENCE                                    |  |
|  | - VAHAN lookup (owner, vehicle type, registration)                |  |
|  | - PUCC status check (validity, expiry)                            |  |
|  | - Insurance verification                                          |  |
|  | - Stolen vehicle database check                                   |  |
|  | - Repeat offender history                                         |  |
|  +------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +------------------------------------------------------------------+  |
|  | LAYER 5: SAFETY DETECTION                                         |  |
|  | - Helmet detection for MOTORCYCLE/SCOOTER (svies_helmet_detector) |  |
|  | - Seatbelt detection for CAR/SUV/VAN                              |  |
|  | - Triple riding detection                                         |  |
|  +------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +------------------------------------------------------------------+  |
|  | LAYER 6: RISK SCORING                                             |  |
|  | Factors:                                                          |  |
|  | - Time of day (night = higher risk)                               |  |
|  | - Zone type (school zone, highway, residential)                   |  |
|  | - Vehicle type (two-wheeler = higher risk)                        |  |
|  | - Speed (if available)                                            |  |
|  | - Violation history (repeat offender escalation)                  |  |
|  | Output: Risk score 0-100, Alert level (LOW/MEDIUM/HIGH/CRITICAL)  |  |
|  +------------------------------------------------------------------+  |
|                              |                                          |
|                              v                                          |
|  +------------------------------------------------------------------+  |
|  | LAYER 7: ALERT & STORAGE                                          |  |
|  | - Real-time WebSocket broadcast to connected clients              |  |
|  | - Violation record in Supabase/SQLite                             |  |
|  | - Annotated snapshot saved to snapshots/violations/               |  |
|  | - Email/SMS alerts via Gmail SMTP & Twilio                        |  |
|  | - PDF summons generation for CRITICAL violations                  |  |
|  +------------------------------------------------------------------+  |
|                                                                         |
|  OUTPUT: Annotated frame + Detection results + Violation records        |
+------------------------------------------------------------------------+
```

---

## Project Structure

```
svies/
├── api/
│   ├── server.py              # FastAPI app (50+ endpoints + WebSocket)
│   └── database.py            # Supabase / SQLite unified database layer
│
├── modules/
│   ├── detector.py            # YOLOv8 vehicle + plate detection (Layer 2)
│   ├── ocr_parser.py          # License plate OCR with 6 variants (Layer 3)
│   ├── fake_plate.py          # 5-check fake plate detection (Layer 2.5)
│   ├── helmet_detector.py     # Helmet + seatbelt detection (Layer 5)
│   ├── db_intelligence.py     # Unified database lookups (Layer 4)
│   ├── mock_db_loader.py      # Mock VAHAN/PUCC/Insurance data
│   ├── risk_scorer.py         # Multi-factor risk scoring (Layer 6)
│   ├── alert_system.py        # Email + SMS alerts (Layer 7)
│   ├── geofence.py            # Zone-based enforcement
│   ├── speed_estimator.py     # Vehicle speed estimation
│   ├── offender_tracker.py    # Repeat offender detection
│   ├── age_classifier.py      # ResNet50 vehicle age classification
│   ├── plate_detector_resnet.py # ResNet50 plate localization fallback
│   ├── roboflow_trainer.py    # Roboflow integration for training
│   └── kaggle_trainer.py      # Kaggle dataset training utilities
│
├── frontend/
│   ├── src/
│   │   ├── pages/             # 12 React pages
│   │   │   ├── Overview.jsx       # Dashboard with KPIs
│   │   │   ├── LiveDetection.jsx  # Real-time webcam/video
│   │   │   ├── ImageVerify.jsx    # Upload image verification
│   │   │   ├── Violations.jsx     # Violation records table
│   │   │   ├── Analytics.jsx      # Charts and trends
│   │   │   ├── ZoneMap.jsx        # Leaflet geofence map
│   │   │   ├── Offenders.jsx      # Repeat offender list
│   │   │   ├── ActiveLearning.jsx # Model management
│   │   │   ├── UserManagement.jsx # Admin user controls
│   │   │   ├── VehicleLookup.jsx  # Search vehicle by plate
│   │   │   ├── VehicleManagement.jsx # CRUD for vehicle DB
│   │   │   └── Login.jsx          # Firebase authentication
│   │   ├── api.js             # API client with all endpoints
│   │   ├── App.jsx            # Router + layout
│   │   └── styles/            # CSS styles
│   └── package.json
│
├── models/                    # YOLOv8 .pt model files
│   ├── yolov8n.pt             # COCO pretrained (fallback)
│   ├── svies_vehicle_classifier.pt  # Indian vehicle detector
│   ├── svies_plate_detector.pt      # License plate localizer
│   ├── svies_helmet_detector.pt     # Helmet violation detector
│   └── svies_age_classifier.pt      # Vehicle age classifier
│
├── data/
│   ├── geozones/zones.json    # Geofence zone definitions
│   ├── violations/            # SQLite fallback database
│   └── firebase-service-account.json
│
├── snapshots/
│   ├── violations/            # Annotated violation images
│   └── feedback/              # User correction images
│
├── reports/                   # Generated PDF summons
├── edge/                      # Edge deployment scripts
├── scripts/                   # Training notebooks
├── runs/                      # YOLOv8 training outputs
│
├── config.py                  # Environment configuration
├── main.py                    # Main processing pipeline
├── docker-compose.yml         # Docker orchestration
├── Dockerfile                 # Backend container
├── Dockerfile.frontend        # Frontend container
├── requirements.txt           # Python dependencies
└── .env.example               # Environment template
```

---

## Modules Overview

### Core Detection Modules

| Module | Layer | Description |
|--------|-------|-------------|
| `detector.py` | 2 | YOLOv8 vehicle detection with COCO + Indian vehicle support. Detects vehicle bbox, type, color, and age. Uses size-based heuristics for Indian vehicle classification (auto-rickshaws, tempos, e-rickshaws). |
| `ocr_parser.py` | 3 | Multi-attempt OCR with 6 preprocessing variants (grayscale, CLAHE, Otsu, adaptive threshold). EasyOCR primary + Groq AI LLM verification. Validates against Indian plate regex. |
| `fake_plate.py` | 2.5 | 5-check fake plate detection: TYPE_MISMATCH, COLOR_CODE_VIOLATION, FONT_ANOMALY, DUPLICATE_PLATE_CLONE, STATE_MISMATCH. Integrates with VAHAN database. |
| `helmet_detector.py` | 5 | YOLOv8 helmet detection for two-wheelers. Also detects seatbelt violations for four-wheelers. Returns safety status with confidence. |
| `age_classifier.py` | 2 | ResNet50-based vehicle age classification into NEW/MODERATE/OLD/VINTAGE categories. |
| `plate_detector_resnet.py` | 3 | ResNet50 fallback for plate localization when YOLOv8 plate detector fails. |

### Intelligence Modules

| Module | Layer | Description |
|--------|-------|-------------|
| `db_intelligence.py` | 4 | Unified database lookup for VAHAN, PUCC, Insurance, and Stolen vehicle records. Works with both Supabase and SQLite. |
| `mock_db_loader.py` | 4 | Mock data loader for testing without real database. Provides sample VAHAN records. |
| `risk_scorer.py` | 6 | Multi-factor risk scoring algorithm. Considers time, zone, vehicle type, speed, and history. Outputs 0-100 score and alert level. |
| `offender_tracker.py` | 6 | Tracks repeat offenders and escalates risk scores based on violation history. |

### Enforcement Modules

| Module | Layer | Description |
|--------|-------|-------------|
| `geofence.py` | 6 | Shapely-based polygon operations for zone detection. 14+ predefined zones with speed limits and risk multipliers. |
| `alert_system.py` | 7 | Email (Gmail SMTP) and SMS (Twilio) alert dispatching. Supports WhatsApp via Twilio. |
| `speed_estimator.py` | 6 | Vehicle speed estimation using frame-to-frame tracking and known reference distances. |

### Training Modules

| Module | Description |
|--------|-------------|
| `roboflow_trainer.py` | Roboflow API integration for dataset management and training |
| `kaggle_trainer.py` | Kaggle dataset download and preprocessing utilities |

---

## Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| **Overview** | `/` | Dashboard with KPIs (total detections, violations, offenders), recent activity, and quick stats |
| **Live Detection** | `/live` | Real-time webcam/video detection with WebSocket streaming at 10 FPS |
| **Image Verify** | `/verify` | Upload image for single-frame detection with full 7-layer pipeline results |
| **Violations** | `/violations` | Paginated table of all violation records with filters and export |
| **Analytics** | `/analytics` | Recharts visualizations: daily trends, zone heatmaps, vehicle type distribution |
| **Zone Map** | `/zones` | Leaflet interactive map showing geofence zones with risk levels |
| **Offenders** | `/offenders` | Repeat offender list with escalation scores and history |
| **Active Learning** | `/learning` | Model management: version control, feedback stats, retraining trigger |
| **User Management** | `/users` | Admin page for user role assignment (ADMIN, POLICE, RTO, VIEWER) |
| **Vehicle Lookup** | `/lookup` | Search vehicle by plate number, view VAHAN/PUCC/Insurance details |
| **Vehicle Management** | `/vehicles` | CRUD operations for vehicle database records |
| **Login** | `/login` | Firebase authentication with email/password |

---

## API Endpoints

### Health & Statistics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System health check |
| GET | `/api/stats` | Dashboard statistics (detections, violations, offenders) |
| GET | `/api/analytics` | Chart data for analytics page |

### Detection & Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/process-image` | Process uploaded image through 7-layer pipeline |
| POST | `/api/process-video` | Process uploaded video file |
| GET | `/api/process-status` | Get video processing progress |
| POST | `/api/webcam/start` | Start live webcam detection |
| POST | `/api/webcam/stop` | Stop webcam detection |

### WebSocket Streams

| Endpoint | Description |
|----------|-------------|
| `ws://.../ws/live` | Real-time violation alerts |
| `ws://.../ws/live-feed` | Live video frames (~10 FPS) |

### Violations & Offenders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/violations` | List violations (paginated, filterable) |
| GET | `/api/offenders` | List repeat offenders |
| GET | `/api/violations/export` | Export violations as CSV/Excel |
| GET | `/api/offenders/export` | Export offenders as CSV/Excel |
| GET | `/api/generate-report` | Generate PDF summons for a plate |

### Vehicle Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vehicle/{plate}` | Lookup vehicle details |
| GET | `/api/vehicles` | List all vehicles in database |
| POST | `/api/vehicles` | Create new vehicle record |
| PUT | `/api/vehicles/{plate}` | Update vehicle details |
| DELETE | `/api/vehicles/{plate}` | Delete vehicle record |
| PUT | `/api/vehicles/{plate}/pucc` | Update PUCC status |
| PUT | `/api/vehicles/{plate}/insurance` | Update insurance status |
| PUT | `/api/vehicles/{plate}/stolen` | Mark as stolen/recovered |

### Zones

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/zones` | List all geofence zones |

### Active Learning

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/feedback` | Submit detection correction |
| POST | `/api/feedback/full-image` | Submit full image feedback |
| GET | `/api/feedback/stats` | Get feedback statistics |
| GET | `/api/model-info` | Get active model versions |
| GET | `/api/models/list` | List all model versions |
| POST | `/api/models/set-active` | Switch active model (admin) |
| POST | `/api/retrain` | Trigger 3-model retraining pipeline |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/verify` | Verify Firebase token |
| GET | `/api/auth/users` | List all users (admin) |
| POST | `/api/auth/set-role` | Set user role (admin) |
| POST | `/api/auth/bootstrap-admin` | Create initial admin user |
| POST | `/api/auth/create-user` | Create new user (admin) |
| DELETE | `/api/auth/delete-user` | Delete user (admin) |

### Demo & Seeding

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/seed-demo` | Seed demo data for testing |

---

## Getting Started

### Prerequisites

- **Python** 3.11+
- **Node.js** 20+ (for frontend)
- **Tesseract OCR** installed on system
- **CUDA** (optional, for GPU acceleration)
- **Supabase** project (or use local SQLite fallback)
- **Firebase** project for authentication

### 1. Clone & Setup Environment

```bash
git clone <repo-url>
cd svies
cp .env.example .env
# Edit .env with your API keys (see Environment Variables section)
```

### 2. Install Backend Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Download/Train Models

Place YOLOv8 models in the `models/` directory:
- `yolov8n.pt` — COCO pretrained (auto-downloads if missing)
- `svies_vehicle_classifier.pt` — Indian vehicle detector (optional)
- `svies_plate_detector.pt` — License plate localizer (optional)
- `svies_helmet_detector.pt` — Helmet detector (optional)

### 5. Setup Database

**Option A: Supabase (Recommended)**
```sql
-- Run in Supabase SQL Editor
-- Copy contents from supabase_setup.sql
```

**Option B: SQLite (Automatic fallback)**
- No setup required. SQLite DB created automatically at `data/violations/svies.db`

### 6. Run the Application

**Backend** (port 8000):
```bash
python -m api.server
```

**Frontend** (port 5173):
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Docker Deployment

### Quick Start

```bash
docker-compose up --build
```

### Services

| Service | URL | Internal Port |
|---------|-----|---------------|
| Backend | http://localhost:8000 | 8000 |
| Frontend | http://localhost:5173 | 5173 |
| API Docs | http://localhost:8000/docs | — |

### Individual Containers

```bash
# Build and run backend only
docker build -t svies-backend .
docker run -p 8000:8000 --env-file .env svies-backend

# Build and run frontend only
docker build -t svies-frontend -f Dockerfile.frontend .
docker run -p 5173:5173 svies-frontend
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

### Required

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon or service key |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to Firebase service account JSON |
| `VITE_FIREBASE_API_KEY` | Firebase API key (frontend) |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase auth domain |
| `VITE_FIREBASE_PROJECT_ID` | Firebase project ID |
| `VITE_FIREBASE_STORAGE_BUCKET` | Firebase storage bucket |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Firebase messaging sender ID |
| `VITE_FIREBASE_APP_ID` | Firebase app ID |

### AI/ML Services

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key for LLM-based OCR verification |
| `GROQ_MODEL` | Groq model name (default: `meta-llama/llama-4-scout-17b-16e-instruct`) |
| `ROBOFLOW_API_KEY` | Roboflow API key for training integration |

### Alerts (Optional)

| Variable | Description |
|----------|-------------|
| `TWILIO_SID` | Twilio Account SID for SMS |
| `TWILIO_TOKEN` | Twilio Auth Token |
| `TWILIO_FROM` | Twilio phone number |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp number |
| `GMAIL_USER` | Gmail address for email alerts |
| `GMAIL_PASSWORD` | Gmail app password |
| `POLICE_EMAIL` | Default police station email |
| `POLICE_PHONE` | Default police phone number |
| `RTO_EMAIL` | Default RTO office email |

### Detection Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIDENCE_THRESHOLD` | `0.35` | Minimum detection confidence (lower = more detections) |
| `OCR_MIN_CONFIDENCE` | `0.3` | Minimum OCR confidence for plate acceptance |
| `RATE_LIMIT_DEFAULT` | `60/minute` | API rate limit |
| `RATE_LIMIT_UPLOAD` | `10/minute` | Upload rate limit |

---

## Database Schema

### Supabase Tables

```sql
-- violations: Core violation records
CREATE TABLE violations (
    id UUID PRIMARY KEY,
    plate_number VARCHAR(20),
    vehicle_type VARCHAR(50),
    vehicle_color VARCHAR(30),
    violation_type VARCHAR(100),
    zone_id VARCHAR(50),
    camera_id VARCHAR(50),
    risk_score INTEGER,
    alert_level VARCHAR(20),
    snapshot_path TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- vehicles: VAHAN-like vehicle registry
CREATE TABLE vehicles (
    plate_number VARCHAR(20) PRIMARY KEY,
    owner_name VARCHAR(100),
    vehicle_type VARCHAR(50),
    vehicle_color VARCHAR(30),
    registration_date DATE,
    engine_number VARCHAR(50),
    chassis_number VARCHAR(50),
    pucc_valid BOOLEAN DEFAULT TRUE,
    pucc_expiry DATE,
    insurance_valid BOOLEAN DEFAULT TRUE,
    insurance_expiry DATE,
    is_stolen BOOLEAN DEFAULT FALSE
);

-- offenders: Repeat offender tracking
CREATE TABLE offenders (
    plate_number VARCHAR(20) PRIMARY KEY,
    violation_count INTEGER DEFAULT 0,
    escalation_level INTEGER DEFAULT 1,
    last_violation TIMESTAMP,
    total_fine_amount DECIMAL(10,2)
);

-- feedback: Active learning corrections
CREATE TABLE feedback (
    id UUID PRIMARY KEY,
    original_detection JSONB,
    corrected_detection JSONB,
    image_path TEXT,
    model_category VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Active Learning Pipeline

SVIES implements continuous improvement through user feedback:

### Flow

```
1. User Detection
   └─> User submits correction via Image Verify / Violations page

2. Feedback Collection
   └─> Correction stored in feedback table
   └─> Image saved to snapshots/feedback/

3. Retraining Trigger
   └─> Admin triggers retraining from Active Learning page
   └─> System validates minimum feedback count

4. 3-Model Training
   └─> Vehicle Detector: Fine-tune on vehicle type corrections
   └─> Helmet Detector: Fine-tune on helmet/no-helmet corrections
   └─> Plate Detector: Fine-tune on plate localization corrections

5. Model Versioning
   └─> New models saved as _v1.pt, _v2.pt, _v3.pt...
   └─> Previous versions retained for rollback

6. Admin Deployment
   └─> Admin selects which version to activate
   └─> Hot-swap without server restart
```

### Model Categories

| Category | Model File | Feedback Types |
|----------|-----------|----------------|
| `vehicle` | `svies_vehicle_classifier.pt` | Vehicle type corrections |
| `helmet` | `svies_helmet_detector.pt` | Helmet detection corrections |
| `plate` | `svies_plate_detector.pt` | Plate localization corrections |

---

## Authentication & Roles

### Role Hierarchy

| Role | Access Level |
|------|--------------|
| **ADMIN** | Full access: user management, model retraining, all data |
| **POLICE** | View violations, offenders, generate reports, lookup vehicles |
| **RTO** | View violations, analytics, vehicle management |
| **VIEWER** | Read-only dashboard access |

### Firebase Setup

1. Create Firebase project at https://console.firebase.google.com
2. Enable Email/Password authentication
3. Download service account JSON
4. Set `FIREBASE_SERVICE_ACCOUNT_PATH` in `.env`
5. Configure frontend Firebase config in `.env`

### Bootstrap Admin

```bash
# Create initial admin user
curl -X POST http://localhost:8000/api/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "securepassword"}'
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, React Router, Leaflet (maps), Recharts (charts), Lucide Icons |
| **Backend** | FastAPI, Uvicorn, WebSockets, Pydantic |
| **AI/ML** | YOLOv8 (Ultralytics), PyTorch, OpenCV, ResNet50 |
| **OCR** | EasyOCR, Tesseract, Groq LLM (Llama) |
| **Database** | Supabase (PostgreSQL), SQLite fallback |
| **Auth** | Firebase Admin SDK |
| **Alerts** | Twilio (SMS/WhatsApp), Gmail SMTP |
| **Reports** | ReportLab (PDF generation) |
| **Geofencing** | Shapely (polygon operations) |
| **Containerization** | Docker, Docker Compose |

---

## Indian Road Optimizations

SVIES is specifically optimized for Indian traffic conditions:

### Vehicle Types

Supports 11 Indian vehicle categories not in standard COCO:
- **AUTO** — Auto-rickshaws (three-wheelers)
- **TEMPO** — Small commercial vehicles
- **E_RICKSHAW** — Electric rickshaws
- **SCOOTER** — Distinct from motorcycles
- **TRACTOR** — Agricultural vehicles
- **VAN/SUV** — Indian market variants

### License Plate Formats

```
Standard:  AA00AA0000  (e.g., TN09BT9721)
BH-Series: 00BH0000AA  (Bharat series for inter-state)
```

All 36 Indian state/UT codes recognized.

### Detection Enhancements

- **CLAHE preprocessing** for dusty/low-light conditions
- **Lower confidence thresholds** (0.35) for motorcycle detection
- **Size-based heuristics** for auto-rickshaw/tempo classification
- **Multi-attempt OCR** with 6 preprocessing variants for worn plates

### Compliance Checks

- **CMVR color codes** — White (private), Yellow (commercial), Green (electric)
- **IS 10731 font** — Character spacing and height validation
- **State prefix** — Validates plate prefix matches registration state

---

## Team

**Group 3** — Digital Image Processing Project

---

## License

This project is developed for academic purposes as part of a Digital Image Processing course.
