# 🛡️ SVIES — Smart Vehicle Identification & Enforcement System

> AI-powered traffic violation detection and enforcement platform for Indian roads.

SVIES uses **YOLOv8** deep learning models to detect vehicles, license plates, and helmet violations from images, video feeds, and live camera streams. It combines real-time detection with OCR-based plate reading, geofenced zone enforcement, risk scoring, and an active learning pipeline for continuous model improvement.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Vehicle Detection** | YOLOv8-based detection of cars, motorcycles, auto-rickshaws, buses, trucks, tempos, tractors, e-rickshaws |
| **License Plate OCR** | EasyOCR + Tesseract + Groq AI verification for Indian plates (IND format) |
| **Helmet Detection** | Dedicated YOLOv8 model for two-wheeler helmet violation detection |
| **Live Detection** | Real-time webcam, video upload, and photo scanning with zone selection |
| **Geofenced Zones** | 14 configurable enforcement zones with risk multipliers and speed limits |
| **Active Learning** | 3-model version management (vehicle/helmet/plate) with feedback-driven YOLOv8 fine-tuning |
| **Violation Tracking** | Automatic violation logging with annotated snapshots to Supabase |
| **Repeat Offender Detection** | Tracks multi-violation offenders with escalation scores |
| **Risk Scoring** | Multi-factor risk assessment (time, zone, vehicle type, speed, history) |
| **Alert System** | Email (Gmail SMTP) and SMS (Twilio) notifications for violations |
| **Court Summons PDF** | Auto-generated PDF reports for offending vehicles |
| **Role-Based Access** | Firebase Auth with ADMIN, POLICE, RTO, VIEWER roles |
| **Analytics Dashboard** | Charts, KPIs, violation trends, zone heatmaps |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                     │
│  Overview │ Live Detection │ Image Verify │ Violations │ ... │
├─────────────────────────────────────────────────────────────┤
│                  FastAPI Backend (Python)                    │
│         REST API  │  WebSocket (live feed)  │  Auth          │
├───────────┬───────────┬───────────┬─────────────────────────┤
│ Detector  │ OCR       │ Helmet    │ Geofence │ Alert System  │
│ (YOLOv8)  │ (EasyOCR) │ (YOLOv8)  │ (Shapely)│ (Twilio/SMTP)│
├───────────┴───────────┴───────────┴─────────────────────────┤
│            Supabase (PostgreSQL) / SQLite                    │
└─────────────────────────────────────────────────────────────┘
```

### Detection Pipeline

```
Image/Frame → Vehicle Detection (YOLOv8) → Plate Crop → OCR (EasyOCR + Groq AI)
           → Helmet Detection (YOLOv8)   → Violation Check
           → Geofence Lookup             → Risk Scoring → Alert / DB Save
```

### 3-Model System

| Model | File | Purpose |
|---|---|---|
| Vehicle Detector | `svies_vehicle_classifier.pt` | Detects vehicles on Indian roads |
| Helmet Detector | `svies_helmet_detector.pt` | Detects missing helmets on two-wheelers |
| Plate Detector | `svies_plate_detector.pt` | Localizes license plate regions |

---

## 📁 Project Structure

```
svies/
├── api/
│   ├── server.py          # FastAPI app (all endpoints + WebSocket)
│   └── database.py        # Supabase / SQLite database layer
├── modules/
│   ├── detector.py        # YOLOv8 vehicle + plate detection
│   ├── helmet_detector.py # Helmet violation detection
│   ├── ocr_parser.py      # License plate OCR (EasyOCR + Groq)
│   ├── geofence.py        # Zone-based enforcement
│   ├── risk_scorer.py     # Multi-factor risk scoring
│   ├── alert_system.py    # Email + SMS alerts
│   ├── speed_estimator.py # Vehicle speed estimation
│   ├── offender_tracker.py# Repeat offender detection
│   └── fake_plate.py      # Fake/cloned plate detection
├── frontend/
│   ├── src/
│   │   ├── pages/         # 12 React pages
│   │   ├── api.js         # API client
│   │   └── App.jsx        # Router + layout
│   └── package.json
├── models/                # YOLOv8 .pt model files
├── data/
│   ├── geozones/zones.json
│   └── firebase-service-account.json
├── config.py              # Environment configuration
├── docker-compose.yml     # Dev-mode Docker setup
├── Dockerfile             # Backend container
├── Dockerfile.frontend    # Frontend container
├── requirements.txt       # Python dependencies
└── .env.example           # Environment template
```

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.11+
- **Node.js** 20+
- **Tesseract OCR** installed on system
- **Supabase** project (or use local SQLite fallback)
- **Firebase** project for authentication

### 1. Clone & Setup Environment

```bash
git clone <repo-url>
cd svies
cp .env.example .env
# Edit .env with your Supabase, Firebase, Twilio, and Groq API keys
```

### 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Setup Database

```bash
# Run the Supabase SQL setup
# Copy supabase_setup.sql contents into your Supabase SQL editor
```

### 5. Run the Application

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

## 🐳 Docker

Run both services with Docker Compose:

```bash
docker-compose up --build
```

| Service | URL | Command |
|---|---|---|
| Backend | http://localhost:8000 | `python -m api.server` |
| Frontend | http://localhost:5173 | `npm run dev` |
| API Docs | http://localhost:8000/docs | Swagger UI |

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon/service key |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | ✅ | Path to Firebase service account JSON |
| `VITE_FIREBASE_*` | ✅ | Firebase frontend config (6 variables) |
| `GROQ_API_KEY` | ✅ | Groq API key for AI-powered OCR verification |
| `TWILIO_SID` / `TWILIO_TOKEN` | Optional | Twilio SMS alerts |
| `GMAIL_USER` / `GMAIL_PASSWORD` | Optional | Gmail SMTP for email alerts |
| `ROBOFLOW_API_KEY` | Optional | Roboflow integration |

---

## 📡 API Endpoints

### Core Detection
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/detect` | Detect vehicles in uploaded image |
| `POST` | `/api/process-video` | Process video for violations |
| `POST` | `/api/start-webcam` | Start live webcam detection |
| `WS` | `/ws/live` | WebSocket for real-time detection |
| `WS` | `/ws/live-feed` | WebSocket for live video feed |

### Data & Analytics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats` | Dashboard statistics |
| `GET` | `/api/analytics` | Charts and trend data |
| `GET` | `/api/violations` | Violation records (paginated) |
| `GET` | `/api/offenders` | Repeat offender list |
| `GET` | `/api/zones` | Geofence zones |

### Active Learning
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/feedback` | Submit detection correction |
| `GET` | `/api/feedback/stats` | Feedback statistics |
| `GET` | `/api/model-info` | Model versions by category |
| `POST` | `/api/models/set-active` | Switch active model (admin) |
| `POST` | `/api/retrain` | Trigger 3-model retraining pipeline |

---

## 🧠 Active Learning Pipeline

The system continuously improves through user feedback:

1. **Corrections** — Users submit corrections via Image Verify and Violations pages
2. **Data Collection** — Feedback images stored in `snapshots/feedback/`
3. **Retraining** — Admin triggers retraining from Active Learning page
4. **3-Model Training** — Vehicle, Helmet, and Plate detectors each fine-tuned
5. **Versioned Deploy** — Models saved as `_v1.pt`, `_v2.pt`, `_v3.pt`…
6. **Model Selection** — Admin can switch any model version as active

---

## 🔐 Authentication & Roles

| Role | Access |
|---|---|
| **ADMIN** | Full access + user management + model retraining |
| **POLICE** | View violations, offenders, generate reports |
| **RTO** | Vehicle lookup, violations, analytics |
| **VIEWER** | Read-only dashboard access |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, React Router, Leaflet, Recharts, Lucide Icons |
| **Backend** | FastAPI, Uvicorn, WebSockets |
| **AI/ML** | YOLOv8 (Ultralytics), PyTorch, OpenCV |
| **OCR** | EasyOCR, Tesseract, Groq LLM |
| **Database** | Supabase (PostgreSQL) / SQLite fallback |
| **Auth** | Firebase Admin SDK |
| **Alerts** | Twilio (SMS), Gmail SMTP (Email) |
| **Reports** | ReportLab (PDF generation) |
| **Geofencing** | Shapely (polygon operations) |

---

## 👥 Team

**Group 3** — Digital Image Processing Project

---

## 📄 License

This project is developed for academic purposes as part of a Digital Image Processing course.
