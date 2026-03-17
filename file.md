# SVIES — Smart Vehicle Intelligence & Enforcement System

## 📌 Project Overview

**SVIES** (Smart Vehicle Intelligence & Enforcement System) is an AI-powered, real-time traffic surveillance and enforcement platform built specifically for **Indian roads**. It uses computer vision, deep learning, and OCR to detect vehicles, read license plates, identify violations, and dispatch automated alerts to law enforcement — all from a camera feed (live webcam, video file, or uploaded image).

The system is designed as a **Digital Image Processing (DIP)** project that combines multiple AI/ML techniques with a modern full-stack web application to create a production-grade traffic monitoring solution.

---
python -m api.server


## 🎯 Problem Statement

Indian traffic enforcement faces significant challenges:
- Manual monitoring is **slow**, **error-prone**, and **not scalable**
- Fake license plates and stolen vehicles are **hard to detect visually**
- India-specific vehicles like **auto-rickshaws, tempos, e-rickshaws, and tractors** are not in standard detection datasets (COCO)
- No unified system connects vehicle detection → plate reading → database lookup → violation scoring → alerting

**SVIES solves all of these** with an end-to-end, AI-driven pipeline.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        INPUT SOURCES                            │
│   📹 Webcam  │  🎥 Video File  │  🖼️ Image Upload              │
└──────────┬───────────┬────────────────┬─────────────────────────┘
           │           │                │
           ▼           ▼                ▼
┌──────────────────────────────────────────────────────────────────┐
│             LAYER 1: PREPROCESSING (CLAHE)                      │
│   Contrast enhancement for low-light, dust, glare conditions    │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│             LAYER 2: AI DETECTION ENGINE                        │
│   🚗 Vehicle Detection (YOLOv8n + Indian Vehicle Classifier)    │
│   🔲 License Plate Localization (YOLO Plate Detector)           │
│   🎨 Vehicle Color Classification (HSV Histogram)               │
│   📏 Indian Vehicle Type Heuristics (size/aspect ratio)         │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│             LAYER 3: OCR ENGINE                                  │
│   📝 Multi-attempt EasyOCR (5 preprocessing variants)            │
│   🔤 Indian plate regex validation (Standard + BH series)        │
│   ✏️  Context-aware character correction (0↔O, 1↔I, etc.)        │
│   🔁 Tesseract fallback (optional)                               │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│             LAYER 4: INTELLIGENCE & ANALYSIS                     │
│   🔍 Fake Plate Detection     │ 🗄️ Database Intelligence (VAHAN) │
│   ⛑️ Helmet/Seatbelt Check    │ 🏎️ Speed Estimation              │
│   📊 Risk Scoring Engine      │ 👮 Repeat Offender Tracking       │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│             LAYER 5: ENFORCEMENT & OUTPUT                        │
│   🌍 Geofence Zone Checking   │ 🚨 Alert Dispatch (SMS/Email)    │
│   📄 Court Summons PDF        │ 📤 CSV/PDF Export                 │
│   🛡️ SHA-256 Evidence Hashing │ 🖥️ Real-time WebSocket Feed      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 💻 Tech Stack

### Backend (Python)

| Technology       | Version   | Purpose                                      |
|------------------|-----------|----------------------------------------------|
| **Python**       | 3.11+     | Core language for backend & AI               |
| **FastAPI**      | ≥ 0.100   | REST API + WebSocket server                  |
| **Uvicorn**      | ≥ 0.23    | ASGI server to run FastAPI                   |
| **YOLOv8**       | (Ultralytics ≥ 8.0) | Vehicle & plate detection          |
| **OpenCV**       | ≥ 4.8     | Image/video processing, CLAHE, color analysis|
| **EasyOCR**      | ≥ 1.7     | Primary OCR engine for plate reading         |
| **PyTesseract**  | ≥ 0.3.10  | Fallback OCR engine                          |
| **PyTorch**      | ≥ 2.0     | Deep learning framework (YOLO backend)       |
| **NumPy**        | ≥ 1.24    | Numerical computations                       |
| **Shapely**      | ≥ 2.0     | Geofence polygon operations                  |
| **Pandas**       | ≥ 2.0     | Data manipulation                            |
| **Pillow**       | ≥ 10.0    | Image handling                               |
| **ReportLab**    | ≥ 4.0     | PDF report/summons generation                |
| **SlowAPI**      | ≥ 0.1.9   | API rate limiting                            |
| **python-dotenv**| ≥ 1.0     | Environment variable management              |

### Frontend (React)

| Technology         | Version  | Purpose                                    |
|--------------------|----------|--------------------------------------------|
| **React**          | 19.2     | UI framework                               |
| **Vite**           | 7.3      | Build tool & dev server                    |
| **React Router**   | 7.13     | Client-side routing                        |
| **Recharts**       | 3.7      | Charts & analytics visualization           |
| **Leaflet**        | 1.9.4    | Interactive geofence map                   |
| **React-Leaflet**  | 5.0      | React wrapper for Leaflet maps             |
| **Lucide React**   | 0.460    | Icon library                               |
| **React Hot Toast**| 2.5      | Toast notifications                        |
| **Firebase**       | 11.0     | Client-side authentication                 |

### Database & Cloud

| Technology         | Purpose                                        |
|--------------------|------------------------------------------------|
| **Supabase**       | Cloud PostgreSQL database (primary data store) |
| **Firebase Admin**  | JWT authentication & role management          |

### Alerts & Notifications

| Technology | Purpose                            |
|------------|------------------------------------|
| **Twilio** | SMS alerts to police/RTO offices   |
| **Gmail SMTP** | Email alerts (critical violations) |

### DevOps & Deployment

| Technology         | Purpose                             |
|--------------------|-------------------------------------|
| **Docker**         | Backend containerization            |
| **Docker Compose** | Multi-service orchestration         |
| **Nginx**          | Frontend static file serving        |

### Testing

| Technology         | Purpose                             |
|--------------------|-------------------------------------|
| **Pytest**         | Unit & integration testing          |
| **pytest-asyncio** | Async test support                  |
| **HTTPX**          | HTTP client for API testing         |

---

## 📁 Project Structure

```
svies/
├── api/                         # Backend API Layer
│   ├── server.py                # FastAPI REST + WebSocket server (1200+ lines)
│   ├── auth.py                  # Firebase JWT auth + RBAC middleware
│   ├── database.py              # Supabase database interface (singleton)
│   └── models.py                # Pydantic request/response models
│
├── modules/                     # Core AI & Processing Modules
│   ├── detector.py              # YOLOv8 vehicle & plate detection
│   ├── ocr_parser.py            # Multi-attempt EasyOCR + plate validation
│   ├── fake_plate.py            # Fake/cloned plate detection engine
│   ├── helmet_detector.py       # Helmet & seatbelt violation detection
│   ├── db_intelligence.py       # VAHAN/PUCC/Insurance/Stolen DB lookup
│   ├── risk_scorer.py           # Weighted risk scoring algorithm
│   ├── geofence.py              # GPS-based geofence zone detection
│   ├── speed_estimator.py       # Pixel-displacement speed estimation
│   ├── alert_system.py          # SMS (Twilio) + Email (Gmail) alerts
│   ├── offender_tracker.py      # Repeat offender level tracking
│   ├── mock_db_loader.py        # Mock data loader for development
│   ├── kaggle_trainer.py        # Kaggle dataset training pipeline
│   └── roboflow_trainer.py      # Roboflow model training pipeline
│
├── frontend/                    # React Frontend Dashboard
│   ├── src/                     # React components & pages
│   ├── package.json             # Node.js dependencies
│   ├── vite.config.js           # Vite bundler config
│   └── index.html               # Entry HTML
│
├── dashboard/                   # Streamlit Dashboard (legacy)
│   └── app.py                   # Streamlit analytics dashboard
│
├── models/                      # Trained YOLO Models
│   ├── yolov8n.pt               # General COCO vehicle detector
│   ├── svies_plate_detector.pt  # Custom plate detection model
│   ├── svies_vehicle_classifier.pt  # Indian vehicle classifier
│   └── svies_helmet_detector.pt # Helmet/seatbelt detector
│
├── data/                        # Static Data
│   └── geozones/zones.json      # Geofence zone definitions
│
├── main.py                      # Main processing pipeline orchestrator
├── config.py                    # Configuration (loads .env)
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Backend Docker image
├── Dockerfile.frontend          # Frontend Docker image
├── docker-compose.yml           # Multi-service Docker setup
├── supabase_setup.sql           # Database schema + seed data
├── pytest.ini                   # Test configuration
└── run_tests.py                 # Test runner script
```

---

## ⚙️ Features (A to Z)

### 1. 🚗 Vehicle Detection (YOLOv8)
- Detects vehicles using **YOLOv8n** (COCO pre-trained) as a fallback
- Custom **Indian Vehicle Classifier** model trained to detect: `CAR`, `MOTORCYCLE`, `SCOOTER`, `AUTO` (auto-rickshaw), `BUS`, `TRUCK`, `TEMPO`, `TRACTOR`, `E_RICKSHAW`, `VAN`, `SUV`
- CLAHE preprocessing for **low-light, dusty, and glare** conditions common on Indian roads
- Size-based heuristic classification for auto-rickshaws, tempos, and e-rickshaws

### 2. 🔲 License Plate Localization
- Dedicated **YOLO plate detector** model (`svies_plate_detector.pt`)
- Full-frame plate detection with **vehicle-matching** (plate center must overlap vehicle bbox)
- Fallback to **heuristic plate region estimation** based on vehicle type
- 10px padding around detected plates for better OCR

### 3. 🔤 OCR — License Plate Reading
- **Multi-attempt EasyOCR** with 5 preprocessing variants:
  - Standard Otsu thresholding
  - CLAHE (aggressive) + Otsu
  - Denoised + Otsu
  - Inverted (for dark plates with white text)
  - Raw upscaled grayscale
- **5x LANCZOS4 upscaling** for small plate crops
- Best result selected by **score = len(text) × confidence**
- **Context-aware character correction** for Indian plates:
  - Position 0-1 (state code): digits → letters (0→O, 1→I)
  - Position 2-3 (district code): letters → digits (O→0, I→1, B→8)
- Validates against **Indian plate regex patterns**:
  - Standard: `AA00AA0000` (e.g., TS09EF1234)
  - BH Series: `00BH0000AA` (e.g., 22BH1234AB)
- Tesseract OCR as optional fallback
- Character whitelist: `A-Z, 0-9` only

### 4. 🎨 Vehicle Color Classification
- HSV histogram-based color analysis
- 8 color classes: WHITE, BLACK, SILVER, RED, BLUE, GREEN, YELLOW, GREY
- Uses the vehicle bounding box crop for classification

### 5. 🔍 Fake Plate Detection
- Multi-factor fake plate analysis:
  - Font consistency check (character spacing & alignment from OCR bboxes)
  - Vehicle type mismatch (e.g., truck plate on a motorcycle)
  - Cross-camera plate reuse detection
  - Plate format anomaly detection
- Confidence score + detailed flag list

### 6. ⛑️ Helmet & Seatbelt Detection
- Checks for helmet on motorcycles/scooters
- Checks for seatbelt on cars/SUVs
- Uses vehicle type context to determine which check to apply
- Flags safety violations accordingly

### 7. 🏎️ Speed Estimation
- Pixel-displacement based speed calculation
- Tracks vehicle bounding box movement across consecutive frames
- Configurable speed limits per zone
- Flags overspeeding violations

### 8. 🗄️ Database Intelligence (VAHAN Integration)
- Looks up vehicle registration data (owner, type, color, make, year)
- Checks **PUCC** (Pollution Under Control Certificate) validity
- Checks **motor insurance** status and expiry
- Checks **stolen vehicle** registry
- All data stored in Supabase (PostgreSQL)

### 9. 📊 Risk Scoring Engine
- Weighted multi-factor risk calculation:
  - Stolen vehicle, fake plate, helmet violation, seatbelt violation
  - Expired PUCC, expired insurance, no registration
  - Overspeeding, repeat offender escalation
  - Geofence zone multiplier (school zones, hospital zones = higher risk)
- Risk levels: `LOW` (0-15), `MEDIUM` (16-34), `HIGH` (35-59), `CRITICAL` (60+)
- Detailed breakdown of score components

### 10. 🌍 Geofence Zone Monitoring
- GPS-based zone detection using **Shapely** polygon geometry
- Zone types:
  - 🏫 School Zones (high priority)
  - 🏥 Hospital Zones (high priority)
  - 🏛️ Government Areas
  - 🛣️ Highway Zones
  - 🌿 Low Emission Zones
- Priority multiplier applied to risk scores (e.g., violations near schools = higher score)

### 11. 👮 Repeat Offender Tracking
- Tracks violation count per plate over a rolling 30-day window
- Escalation levels:
  - Level 0: No violations
  - Level 1: 1–2 violations
  - Level 2: 3–5 violations
  - Level 3: 6+ violations (habitual offender)
- Higher levels increase the risk score

### 12. 🚨 Alert Dispatch System
- Automated alerts for HIGH and CRITICAL violations
- **SMS alerts** via Twilio (to police stations, RTO offices, vehicle owners)
- **Email alerts** via Gmail SMTP (detailed violation reports)
- Alert payload includes: plate, owner, violations, risk score, GPS location, snapshot

### 13. 📄 Court Summons & Reports
- Auto-generated **PDF court summons** using ReportLab
- Includes violation history, owner details, and evidence
- **CSV & PDF export** of violation logs
- Filterable by date range, alert level, and plate number

### 14. 🛡️ Evidence Integrity (SHA-256)
- Every violation record is hashed with SHA-256
- Hash = `SHA256(plate + timestamp + violation_types)`
- Creates a tamper-proof evidence chain for legal proceedings

### 15. 🔐 Authentication & Authorization
- **Firebase Authentication** with JWT tokens
- **Role-Based Access Control (RBAC)**:
  - `ADMIN` — Full access (manage users, seed data, all operations)
  - `POLICE` — View violations, offenders, generate reports
  - `RTO` — View violations, vehicle lookup
  - `VIEWER` — Read-only dashboard access
- **No-Auth Dev Mode**: falls back to mock admin when Firebase is not configured

### 16. 🖥️ Real-Time Dashboard (React Frontend)
- Modern React 19 dashboard with Vite
- Real-time violation feed via **WebSocket** (`ws://localhost:8000/ws/live`)
- Interactive charts & analytics (Recharts)
- Interactive geofence map (Leaflet)
- Vehicle lookup with full intelligence report
- Violation log with filtering, pagination, and export
- Toast notifications for critical alerts

### 17. 📡 WebSocket Live Feed
- Real-time video frame streaming via WebSocket (`/ws/live-feed`)
- Annotated frames with bounding boxes
- Detection metadata alongside each frame
- Supports multiple concurrent dashboard clients

### 18. 🎥 Video & Image Processing
- Supports three input modes:
  - **Webcam** (real-time): `python main.py`
  - **Video file**: `python main.py --source video.mp4`
  - **Single image**: `python main.py --source image.jpg --image`
- Video processing runs in a background thread
- Frame skipping (every Nth frame) for real-time performance
- Progress tracking via `/api/process-status`

### 19. ⚡ Rate Limiting
- API rate limiting via **SlowAPI**
- Default: 60 requests/minute per IP
- Upload endpoints: 10 requests/minute per IP
- Configurable via `.env`

### 20. 📊 Analytics Endpoints
- `/api/stats` — Dashboard KPI stats (total violations, by level, unique plates)
- `/api/analytics` — Daily/hourly breakdown, level distribution, score distribution
- `/api/offenders` — Top repeat offenders ranked by violation count
- `/api/zones` — Geofence zone data with center coordinates

### 21. 🐳 Docker Deployment
- **Backend Dockerfile** — Python/FastAPI container
- **Frontend Dockerfile** — React build served via Nginx
- **Docker Compose** — Orchestrates both services:
  - Backend on port `8000`
  - Frontend on port `3000`

### 22. 🗃️ Database Schema (Supabase/PostgreSQL)

| Table              | Purpose                                    |
|--------------------|--------------------------------------------|
| `violations`       | All detected traffic violations            |
| `vehicles`         | Vehicle registration data (VAHAN mirror)   |
| `pucc`             | Pollution Under Control Certificates       |
| `insurance`        | Motor insurance records                    |
| `stolen_vehicles`  | Stolen vehicle registry                    |
| `feedback`         | User correction/feedback (active learning) |

### 23. 🔄 Active Learning / Feedback Loop
- Users can submit corrections for:
  - Incorrectly read plates
  - Misclassified vehicle types
- Feedback is stored for future model retraining
- Feedback stats available via API

### 24. 🏋️ Model Training Pipelines
- **Kaggle Trainer** (`kaggle_trainer.py`): Train plate detector using Kaggle's `indian-number-plates-dataset`
- **Roboflow Trainer** (`roboflow_trainer.py`): Alternative training via Roboflow datasets
- Google Colab GPU training notebook included (`SVIES_V100_Training_fixed.ipynb`)

### 25. 🧪 Testing Suite
- **Pytest** with async support
- API endpoint tests via HTTPX
- Module-level test blocks (run any module directly for self-test)
- `run_tests.py` for full test execution

---

## 🚀 How to Run

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account (free tier works)
- (Optional) Firebase project for auth
- (Optional) Twilio account for SMS alerts

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase URL/Key, Firebase creds, Twilio creds

# Initialize database (run in Supabase SQL Editor)
# Paste contents of supabase_setup.sql

# Start the API server
uvicorn api.server:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
# Dashboard available at http://localhost:5173
```

### 3. Run Pipeline (CLI)

```bash
# Webcam (real-time)
python main.py

# Video file
python main.py --source path/to/video.mp4

# Single image
python main.py --source path/to/image.jpg --image
```

### 4. Docker Deployment

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## 🔌 API Endpoints Summary

| Method | Endpoint                  | Auth Level | Description                         |
|--------|---------------------------|------------|-------------------------------------|
| GET    | `/api/health`             | None       | Health check                        |
| GET    | `/api/stats`              | VIEWER     | Dashboard KPI stats                 |
| GET    | `/api/violations`         | VIEWER     | Paginated violation log             |
| GET    | `/api/offenders`          | VIEWER     | Top repeat offenders                |
| GET    | `/api/zones`              | VIEWER     | Geofence zone data                  |
| GET    | `/api/vehicle/{plate}`    | VIEWER     | Full vehicle intelligence           |
| GET    | `/api/analytics`          | VIEWER     | Charts & analytics data             |
| POST   | `/api/process-image`      | VIEWER     | Process single image                |
| POST   | `/api/process-video`      | VIEWER     | Upload & process video              |
| GET    | `/api/process-status`     | VIEWER     | Video processing progress           |
| GET    | `/api/generate-report`    | VIEWER     | Generate court summons PDF          |
| GET    | `/api/violations/export`  | VIEWER     | Export violations (CSV/PDF)         |
| POST   | `/api/seed-demo`          | ADMIN      | Seed demo violation data            |
| WS     | `/ws/live`                | —          | Real-time violation WebSocket       |
| WS     | `/ws/live-feed`           | —          | Live video frame WebSocket          |

---

## 🔑 Environment Variables (.env)

| Variable              | Description                          |
|-----------------------|--------------------------------------|
| `SUPABASE_URL`        | Supabase project URL (required)      |
| `SUPABASE_KEY`        | Supabase anon/service key (required) |
| `TWILIO_SID`          | Twilio Account SID                   |
| `TWILIO_TOKEN`        | Twilio Auth Token                    |
| `TWILIO_FROM`         | Twilio sender phone number           |
| `GMAIL_USER`          | Gmail address for email alerts       |
| `GMAIL_PASSWORD`      | Gmail App Password                   |
| `POLICE_EMAIL`        | Police station email                 |
| `POLICE_PHONE`        | Police station phone                 |
| `RTO_EMAIL`           | RTO office email                     |
| `CONFIDENCE_THRESHOLD`| Vehicle detection threshold (0.5)    |
| `OCR_MIN_CONFIDENCE`  | OCR minimum confidence (0.3)         |
| `RATE_LIMIT_DEFAULT`  | Default API rate limit (60/minute)   |
| `RATE_LIMIT_UPLOAD`   | Upload rate limit (10/minute)        |
| `MODEL_VERSION`       | Current model version tag            |

---

## 🇮🇳 Indian-Specific Features

1. **Indian Vehicle Types**: Auto-rickshaws, tempos, tractors, e-rickshaws, scooters — all recognized
2. **Indian Plate Formats**: Standard (`AA00AA0000`) and BH-series (`00BH0000AA`) validated
3. **All 35 Indian State RTO Codes**: AP, TS, KA, TN, MH, DL, etc. — all mapped
4. **OCR Character Correction**: Position-aware corrections tuned for Indian plates
5. **Indian Road Conditions**: CLAHE preprocessing for dust, low-light, and glare
6. **Mock VAHAN Database**: 16 Indian vehicles seeded with realistic data
7. **Indian City Geozones**: JNTU, OU, NIMS, Gandhi Hospital, Charminar, Gachibowli ORR, etc.

---

## 👥 Group Information

- **Project**: SVIES — Smart Vehicle Intelligence & Enforcement System
- **Course**: Digital Image Processing (DIP)
- **Group**: 3

---

## 📝 Summary

SVIES is a **comprehensive, end-to-end AI traffic enforcement system** that combines:
- **4 YOLO models** (vehicle, plate, helmet, Indian vehicle classifier)
- **Multi-attempt OCR** with Indian plate-specific processing
- **10+ intelligent modules** working in a layered pipeline
- **Real-time processing** (webcam, video, image)
- **Full-stack web dashboard** (React + FastAPI + Supabase)
- **Automated enforcement** (SMS/email alerts, PDF summons)
- **Tamper-proof evidence** (SHA-256 hashing)
- **Role-based access** (Firebase Auth with 4 roles)
- **Docker-ready deployment**

All purpose-built for the unique challenges of **Indian road traffic enforcement**.
