SVIES Complete Rebuild Plan
Context
SVIES (Smart Vehicle Intelligence & Enforcement System) is a B.Tech CSE-AIML final year project at SRM University AP. The current codebase has a working 7-layer Python backend pipeline but lacks authentication, uses emoji icons, has no trained models (only generic YOLOv8n), thin mock data (27 vehicles), and a basic React frontend. The user wants a professional, presentation-ready rebuild with Firebase multi-role auth, 3 custom-trained YOLO models (using V100 GPU), expanded mock data, and a completely rebuilt attractive frontend.

Key Decisions
UI: Dark government dashboard with glassmorphism cards — navy/slate base + glass blur effects + indigo accents
Models: YOLOv8s (Small, 11.2M params) for best accuracy-speed balance on V100
Database: PostgreSQL via Supabase (scalable, real-time) with SQLite fallback for offline/demo
Auth: Firebase Authentication with custom claims for multi-role access
Icons: Lucide React (professional SVG icons, no emojis)
Phase 0: Firebase Project Setup (User Must Do)
Steps:
Go to https://console.firebase.google.com/ → Create project "SVIES"
Enable Authentication → Sign-in method → Enable Email/Password
Create 4 test users in Firebase Console → Authentication → Users:
admin@svies.gov.in (password: Admin@123)
police@svies.gov.in (password: Police@123)
rto@svies.gov.in (password: Rto@123)
viewer@svies.gov.in (password: Viewer@123)
Go to Project Settings → General → scroll to "Your apps" → Add Web app → Copy firebaseConfig object
Go to Project Settings → Service accounts → Generate new private key → save as data/firebase-service-account.json
After code is deployed, hit POST /api/auth/set-role with admin token to assign roles to each user
Phase 1: Database Migration to Supabase + Firebase Auth
1A. Supabase Database Setup
New file: api/database.py

Supabase Python client (supabase-py package) initialization
Tables to create in Supabase:
violations (id, plate, timestamp, violation_types, risk_score, zone_id, alert_level, sha256_hash, evidence_snapshot_url)
vehicles (plate PK, owner, phone, email, vehicle_type, color, make, year, state, registration_state_code, status)
pucc_records (plate FK, valid_until, status)
insurance_records (plate FK, valid_until, type, status)
stolen_vehicles (plate FK, reported_date, police_station)
feedback (id, timestamp, original_plate, correct_plate, correct_vehicle_type, notes, image_url)
Database abstraction layer: get_vehicle(), log_violation(), get_violations(), etc.
Fallback to SQLite when SUPABASE_URL env var is not set (for offline demos)
Seed function to populate Supabase tables from expanded JSON mock data
Modify: modules/offender_tracker.py — Use new database layer instead of direct SQLite Modify: modules/mock_db_loader.py — Use Supabase as primary, JSON as seed/fallback Modify: .env — Add SUPABASE_URL and SUPABASE_KEY Add to requirements.txt: supabase, firebase-admin

1B. Backend — Firebase Admin SDK Middleware
New file: api/auth.py

Firebase Admin SDK initialization (reads service account JSON from data/firebase-service-account.json)
verify_token() FastAPI dependency — extracts & verifies Firebase ID token from Authorization: Bearer <token> header
Role-based dependencies: require_admin(), require_police(), require_rto(), require_viewer()
Roles stored in Firebase custom claims: { role: "ADMIN" | "POLICE" | "RTO" | "VIEWER" }
Higher roles include lower permissions: ADMIN > POLICE > RTO > VIEWER
Modify: api/server.py

Import auth dependencies, add to all endpoints except /api/health
Role-based endpoint access:
ADMIN: /api/seed-demo, /api/retrain, /api/feedback/*, /api/auth/*
POLICE: /api/violations, /api/offenders, /api/generate-report, /api/process-image, /api/process-video
RTO: /api/vehicle/*, /api/zones, /api/analytics
VIEWER (all roles): /api/stats, /api/health, read-only endpoints
New auth endpoints: POST /api/auth/verify, POST /api/auth/set-role, GET /api/auth/users
Tighten CORS to ["http://localhost:5173", "http://localhost:3000"]
1C. Frontend — Firebase JS SDK + Auth Context
New npm deps: firebase, lucide-react, react-hot-toast

New files:

src/config/firebase.js — Firebase config + initialization
src/context/AuthContext.jsx — Auth state Context (user, role, loading, login, logout)
src/components/ProtectedRoute.jsx — Route guard with role checking
Modify: src/api.js

Add Authorization: Bearer <token> to all fetch requests
Use import.meta.env.VITE_API_URL for API base URL
Phase 2: Frontend Complete Rebuild
2A. Project Structure
frontend/src/
├── main.jsx                    # Entry point
├── App.jsx                     # Router + Layout
├── api.js                      # API client (with auth headers)
├── config/
│   └── firebase.js             # Firebase initialization
├── context/
│   └── AuthContext.jsx          # Auth state management
├── components/
│   ├── ProtectedRoute.jsx       # Route guard
│   ├── Sidebar.jsx              # Navigation sidebar
│   ├── Header.jsx               # Top bar with user info + role badge
│   ├── KPICard.jsx              # Reusable KPI card component
│   ├── StatusBadge.jsx          # Alert level badge (CRITICAL/HIGH/MEDIUM/LOW)
│   ├── DataTable.jsx            # Reusable data table with sorting
│   ├── PipelineStep.jsx         # Pipeline step visualization
│   ├── LoadingSpinner.jsx       # Loading state
│   └── EmptyState.jsx           # Empty data state
├── pages/
│   ├── Login.jsx                # Login page (email/password)
│   ├── Overview.jsx             # Dashboard
│   ├── LiveDetection.jsx        # Video processing
│   ├── ImageVerify.jsx          # Image pipeline verification
│   ├── VehicleLookup.jsx        # Vehicle search
│   ├── Violations.jsx           # Violation log
│   ├── Analytics.jsx            # Charts & trends
│   ├── Offenders.jsx            # Repeat offenders
│   ├── ZoneMap.jsx              # Geofence map
│   ├── ActiveLearning.jsx       # Feedback & retraining
│   └── UserManagement.jsx       # Admin: manage users & roles
└── styles/
    └── index.css                # Complete rebuilt stylesheet
2B. Design System — Dark Govt Dashboard + Glassmorphism
Theme: Dark government intelligence dashboard with glass card effects
Backgrounds: Deep navy (#0a0e1a) base, slate (#111827) surfaces, glass cards with backdrop-filter: blur(12px) + semi-transparent backgrounds (rgba(17,24,39,0.7))
Accents: Indigo primary (#6366f1), cyan secondary (#06b6d4), gradient buttons (indigo→purple)
Glass effects: Cards with border: 1px solid rgba(99,102,241,0.15), subtle glow on hover, frosted glass overlays
Font: Inter (Google Fonts)
Icons: Lucide React — all SVG, no emojis anywhere
Tables: Semi-transparent rows, alternating rgba(255,255,255,0.02), hover glow
Inputs: Dark glass inputs with indigo focus border
Badges: Pill-shaped with semi-transparent backgrounds — Critical=rgba(239,68,68,0.15), High=rgba(249,115,22,0.15), Medium=rgba(245,158,11,0.15), Low=rgba(34,197,94,0.15)
Shadows: Indigo glow shadows on important elements (box-shadow: 0 0 20px rgba(99,102,241,0.1))
Responsive: 768px (sidebar collapse) and 1200px breakpoints
Animations: fadeIn page transitions, glass hover shimmer, smooth 200ms transitions
Government branding: "Government of India — Ministry of Road Transport" subtitle, Ashoka emblem reference in header
2C. Page-by-Page Rebuild Plan
Login.jsx (NEW)

SVIES branded login card (logo, title, subtitle)
Email + password form
Role indicator after login
Firebase signInWithEmailAndPassword
Redirect to dashboard on success
Overview.jsx (REBUILD)

Header with greeting + role badge
6 KPI cards: Total Violations, Critical, High, Medium, Unique Vehicles, Active Zones
Live camera feed (WebSocket) with detection overlays
Real-time violation feed (WebSocket)
Area chart: violations over time (Recharts)
Pie chart: alert level distribution (Recharts)
Recent violations table (last 10)
Quick actions: Seed Demo, Export Report
LiveDetection.jsx (REBUILD)

Drag-and-drop video upload zone
Processing progress bar with frame count
3 KPI cards: Detections, Violations, Frames Processed
Live annotated video feed (WebSocket)
Real-time detection panel: plate, vehicle type, risk score, violations
Detection history table
ImageVerify.jsx (REBUILD)

Image upload with preview
Full 7-layer pipeline visualization (step-by-step timeline)
Annotated detection image display
Per-vehicle results with expandable pipeline steps
Inline feedback/correction form
Show SHA-256 integrity hash for each logged violation
VehicleLookup.jsx (REBUILD)

Plate number search (formatted Indian plate input)
Image-based plate detection option
VAHAN Registration card (structured like real Parivahan output)
Compliance status: PUCC, Insurance, Stolen check
Offender level with visual escalation indicator
Violation history table
Court Summons PDF generation button
Violations.jsx (REBUILD)

Filter bar: plate search, severity dropdown, date range
Server-side paginated table
Columns: Plate, Timestamp, Violations, Risk Score, Level (badge), Zone
Export functionality
Analytics.jsx (REBUILD)

Time range selector (7/30/90 days)
4 charts in 2x2 grid:
Top Violation Types (horizontal bar)
Risk Score Distribution (histogram)
Hourly Activity Pattern (bar)
Alert Level Breakdown (stacked bar)
Summary statistics below charts
Offenders.jsx (REBUILD)

Top 10 offenders bar chart
Full leaderboard table with rank, plate, owner, type, count, level
Expandable violation history per offender
Court Summons button for Level 3 (Red Flag) offenders
ZoneMap.jsx (REBUILD)

Full-height Leaflet map with dark tiles
Colored zone polygons (school=amber, hospital=red, govt=indigo, low_emission=green)
Zone popups with details and multiplier
Zone list panel on the side
Legend
ActiveLearning.jsx (REBUILD)

KPI cards: Total Corrections, Ready for Training, Model Version
Retrain button with pipeline step visualization
Recent corrections table
Link to ImageVerify for submitting new corrections
UserManagement.jsx (NEW — ADMIN only)

User list with email, role, last login
Change role dropdown
Firebase user management via backend API
Phase 3: Model Training Jupyter Notebook
New file: scripts/SVIES_V100_Training.ipynb

A comprehensive notebook for training all 3 models on the V100 GPU server.

Notebook Structure (cells):
Cell 1: Environment Setup
  - pip install ultralytics roboflow torch torchvision
  - Verify CUDA availability, print GPU info (V100 32GB)

Cell 2: Configuration
  - ROBOFLOW_API_KEY
  - DEVICE = "cuda"
  - Model configs: epochs, batch_size, imgsz, patience

Cell 3: Download All 3 Datasets from Roboflow
  - Plate dataset: dip-zrgjd/vehicle-registration-plates-trudk-14wpm v1
  - Helmet dataset: dip-zrgjd/hard-hat-workers-68ds8 v1
  - Indian Vehicle dataset: roboflow-universe-projects/indian-vehicles-detection v1

Cell 4: Dataset Analysis
  - Print class distributions, sample counts, image sizes
  - Display sample images from each dataset

Cell 5: Train Model 1 — Indian License Plate Detector
  - Base: yolov8s.pt (small, not nano — V100 can handle it)
  - epochs=80, imgsz=640, batch=64, patience=15, workers=4
  - Training with augmentation (mosaic, mixup, hsv adjustments)
  - Save: svies_plate_detector.pt

Cell 6: Plate Detector Results
  - Confusion matrix, P-R curve, F1 curve
  - Sample predictions on validation set
  - mAP50, mAP50-95 metrics

Cell 7: Train Model 2 — Helmet/No-Helmet Detector
  - Base: yolov8s.pt
  - epochs=80, imgsz=640, batch=64, patience=15, workers=4
  - Save: svies_helmet_detector.pt

Cell 8: Helmet Detector Results
  - Same metrics + visualizations as Cell 6

Cell 9: Train Model 3 — Indian Vehicle Type Detector
  - Base: yolov8s.pt
  - epochs=100, imgsz=640, batch=64, patience=15, workers=4
  - Classes: auto-rickshaw, bus, car, motorcycle, truck, etc.
  - Save: svies_indian_vehicle_detector.pt

Cell 10: Vehicle Detector Results
  - Same metrics + visualizations

Cell 11: Export & Download Instructions
  - How to scp/download the 3 .pt files to local project
  - File placement: models/svies_plate_detector.pt, etc.
  - Verification: load each model and run a test prediction

Cell 12: Combined Performance Summary
  - Table of all 3 models with mAP, precision, recall, size, FPS
V100-Optimized Hyperparameters:
Model	Base	Epochs	ImgSize	Batch	Patience
Plate Detector	yolov8s.pt	80	640	64	15
Helmet Detector	yolov8s.pt	80	640	64	15
Indian Vehicle	yolov8s.pt	100	640	64	15
Using YOLOv8s (11.2M params) instead of YOLOv8n (3.2M) for better accuracy. V100 32GB handles this easily.

Phase 4: Backend Fixes & Data Expansion
4A. Expand Mock Data
Modify: data/mock_db/vahan.json

Expand from 27 to 200+ vehicle records
Cover all 36 Indian state/UT codes
Realistic Indian names, makes (Maruti, Hyundai, Tata, TVS, Hero, Bajaj, etc.)
Mix of statuses (Active, Suspended, Blacklisted)
Include 10+ BH-series plates
Modify: data/mock_db/pucc.json

Matching 200+ records, ~20% expired
Modify: data/mock_db/insurance.json

Matching 200+ records, ~15% expired
Modify: data/mock_db/stolen.json

Expand to 10-15 stolen plates
4B. Backend Bug Fixes
Fix: modules/alert_system.py

Fix owner email dispatch (lines 271-274 incomplete)
Add WhatsApp alert placeholder via Twilio WhatsApp API
Fix: modules/speed_estimator.py

Use zone-specific speed limits from INDIAN_SPEED_LIMITS dict instead of fixed 40 km/h
Fix: api/server.py

Add Firebase auth middleware
Fix CORS to specific origins
Add new auth endpoints
4C. New Backend Endpoints
POST /api/auth/verify — verify token and return user role
POST /api/auth/set-role — ADMIN: set user role via custom claims
GET /api/auth/users — ADMIN: list all users
Add evidence_hash field to violation responses (expose SHA-256 for integrity verification)
Phase 5: Integration & Polish
5A. End-to-End Testing
Start backend: uvicorn api.server:app --reload --port 8000
Start frontend: cd frontend && npm run dev
Login with test accounts (create 4 users: admin, police, rto, viewer)
Test each page:
Overview: verify KPIs load, seed demo data, check charts
LiveDetection: upload a test video, verify processing pipeline
ImageVerify: upload a test image, verify 7-layer pipeline steps
VehicleLookup: search a known plate (e.g., "TS09EF1234")
Violations: verify pagination, filtering
Analytics: check all 4 charts render
Offenders: verify leaderboard + history expansion
ZoneMap: verify map loads with colored zones
ActiveLearning: submit feedback, trigger retrain
UserManagement: change roles (admin only)
Test role-based access: police cannot access UserManagement, viewer is read-only, etc.
5B. Demo Data Seeding
Enhance POST /api/seed-demo to create 100+ realistic violations
Cover all violation types, zones, severity levels
Create 2-3 repeat offenders at Level 3 (Red Flag)
5C. Final Polish
Error boundaries in React
Loading states for all pages
Empty states with helpful messages
Toast notifications for actions (seed, feedback, retrain)
Proper favicon and page title
Implementation Order
#	Task	Files	Priority
1	Expand mock data (200+ vehicles)	4 JSON files	HIGH — everything depends on this
2	Create Supabase database layer (api/database.py)	1 new file	HIGH — backend data layer
3	Firebase backend auth (api/auth.py)	1 new file	HIGH — security foundation
4	Update api/server.py with auth + Supabase	1 modify	HIGH — connect everything
5	Fix backend bugs (alert_system, speed_estimator)	2 modify	MEDIUM
6	Frontend: install deps, create firebase config	package.json, firebase.js	HIGH
7	Frontend: Auth Context + ProtectedRoute	2 new files	HIGH
8	Frontend: Rebuild CSS design system (glassmorphism)	1 file (index.css)	HIGH — visual foundation
9	Frontend: Reusable components (Sidebar, Header, KPICard, etc.)	8 new files	HIGH
10	Frontend: Login page	1 new file	HIGH
11	Frontend: Rebuild App.jsx with auth + routes	1 file	HIGH
12	Frontend: Rebuild api.js with auth headers	1 file	HIGH
13	Frontend: Rebuild all 9 pages + UserManagement	10 files	HIGH — core UI
14	Create V100 training notebook	1 new notebook	MEDIUM — parallel task
15	Integration testing & polish	Various	HIGH — final
Total new files: ~30 | Modified files: ~8 | This is a major rebuild.

Critical Files Summary
Backend (modify)
api/server.py — Add auth middleware, Supabase integration, new auth endpoints
modules/offender_tracker.py — Use Supabase database layer
modules/mock_db_loader.py — Use Supabase as primary, JSON as fallback
modules/alert_system.py — Fix owner email, add WhatsApp placeholder
modules/speed_estimator.py — Zone-specific speed limits
requirements.txt — Add firebase-admin, supabase
config.py — Add Supabase config vars
.env — Add SUPABASE_URL, SUPABASE_KEY
data/mock_db/*.json — Expand all 4 mock databases to 200+ records
Backend (new)
api/auth.py — Firebase auth middleware + role verification
api/database.py — Supabase PostgreSQL abstraction + SQLite fallback
Frontend (new — complete rebuild of src/)
src/config/firebase.js
src/context/AuthContext.jsx
src/components/ProtectedRoute.jsx
src/components/Sidebar.jsx
src/components/Header.jsx
src/components/KPICard.jsx
src/components/StatusBadge.jsx
src/components/DataTable.jsx
src/components/PipelineStep.jsx
src/components/LoadingSpinner.jsx
src/components/EmptyState.jsx
src/pages/Login.jsx
src/pages/Overview.jsx
src/pages/LiveDetection.jsx
src/pages/ImageVerify.jsx
src/pages/VehicleLookup.jsx
src/pages/Violations.jsx
src/pages/Analytics.jsx
src/pages/Offenders.jsx
src/pages/ZoneMap.jsx
src/pages/ActiveLearning.jsx
src/pages/UserManagement.jsx
src/styles/index.css
src/App.jsx
src/api.js
src/main.jsx
Training (new)
scripts/SVIES_V100_Training.ipynb — Comprehensive 3-model training notebook
Plan approved. Let me start the implementation. This is a massive rebuild — I'll track progress carefully and work through it systematically.