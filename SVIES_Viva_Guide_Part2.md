# SVIES — Complete Viva Reference Guide (Part 2)

---

## 6. RISK SCORING ENGINE (Theory + Math)

### 6.1 Weighted Score Table

| Violation | Weight | Severity |
|---|---|---|
| STOLEN_VEHICLE | 40 | CRITICAL |
| FAKE_PLATE | 35 | CRITICAL |
| UNREGISTERED / NO_REGISTRATION | 25 | HIGH |
| EXPIRED_INSURANCE / NO_INSURANCE | 20 | HIGH |
| REPEAT_OFFENDER | 20 | HIGH |
| NO_NUMBER_PLATE | 20 | HIGH |
| BLACKLIST_ZONE | 15 | HIGH |
| OVERSPEEDING | 15 | MEDIUM |
| NO_PUCC / EXPIRED_PUCC | 15 | MEDIUM |
| WRONG_SIDE_DRIVING | 15 | MEDIUM |
| RED_LIGHT_VIOLATION | 15 | MEDIUM |
| HELMET_VIOLATION | 10 | MEDIUM |
| SEATBELT_VIOLATION | 10 | MEDIUM |
| TRIPLE_RIDING | 10 | MEDIUM |

### 6.2 Composite Score Formula

```
S_base = Σ w_i  (for each detected violation i)

S_zone = S_base × zone_multiplier
  where zone_multiplier:
    SCHOOL:       1.5×
    HOSPITAL:     1.5×
    HIGHWAY:      1.4×
    GOVT:         1.3×
    LOW_EMISSION: 1.2×
    Default:      1.0×

S_final = S_zone
```

### 6.3 Alert Level Thresholds

```
if S_final ≥ 61 → CRITICAL  (e.g., stolen + fake plate = 75)
if S_final ≥ 41 → HIGH      (e.g., insurance + PUCC + helmet = 45)
if S_final ≥ 21 → MEDIUM    (e.g., PUCC + helmet = 25)
if S_final < 21 → LOW       (e.g., single helmet = 10)
```

### 6.4 Example Calculation

```
Vehicle: TS09EF1234 in SCHOOL zone
Violations: EXPIRED_INSURANCE(20) + NO_PUCC(15) + HELMET(10)

S_base = 20 + 15 + 10 = 45
S_zone = 45 × 1.5 = 67 (SCHOOL zone)
Alert Level = CRITICAL (≥61)
```

---

## 7. HELMET & SEATBELT DETECTION

### 7.1 Helmet Detection Pipeline

**For 2W/3W vehicles (motorcycle, scooter, auto):**

```
Step 1: Try custom Roboflow model (svies_helmet_detector.pt)
  → Look for classes: "helmet" vs "no_helmet"

Step 2: If no custom model → YOLOv8n-pose
  → Detect person keypoints
  → Extract head region from keypoint[0] (nose)
  → head_crop = vehicle_crop[hy-40 : hy+20, hx-40 : hx+40]

Step 3: Heuristic analysis on head_crop
```

### 7.2 Skin Detection (Multi-Range HSV + YCrCb)

```
HSV Range 1 (lighter Indian skin):
  H=[0,25], S=[30,180], V=[80,255]

HSV Range 2 (darker Indian skin):
  H=[0,20], S=[20,200], V=[50,180]

YCrCb Range (best for very dark skin):
  Y=[0,255], Cr=[133,173], Cb=[77,127]

Combined: skin_mask = HSV1 | HSV2 | YCrCb
```

### 7.3 Helmet Heuristic Decision

```
Analyze top 40% of head crop:
  skin_ratio = count_nonzero(skin_mask) / total_pixels
  non_skin = 1.0 - skin_ratio
  edge_ratio = count_nonzero(Canny(gray, 50, 150)) / total_pixels

Helmet present if:
  non_skin > 0.75 AND edge_ratio > 0.08

Confidence = min(non_skin × 0.5 + edge_ratio × 2.5, 1.0)

Logic: Helmets cover skin → low skin ratio
       Helmets have hard edges → high edge ratio
```

### 7.4 Seatbelt Detection (4W vehicles)

```
1. Extract driver region: left 40%, top 60% of vehicle bbox
2. Canny edge detection (50, 150)
3. HoughLinesP(threshold=30, minLineLength=40, maxLineGap=10)
4. Count diagonal lines (30°-70° or 110°-150°)
5. Seatbelt present if diagonal_count ≥ 3
6. Confidence = min(diagonal_count / 5.0, 1.0)
```

---

## 8. SPEED ESTIMATION (Optical Flow)

### 8.1 Algorithm

```
For each tracked vehicle (by plate number):
  Store: prev_positions = {track_id: (cx, cy, frame_num)}

  Pixel displacement:
    dx = cx_current - cx_prev
    dy = cy_current - cy_prev
    pixel_dist = √(dx² + dy²)

  Real-world conversion:
    meter_dist = pixel_dist / PIXELS_PER_METER  (default: 8.0)
    time_sec = frame_diff / FPS  (default: 30.0)
    speed_m/s = meter_dist / time_sec
    speed_km/h = speed_m/s × 3.6

  Overspeeding = speed_km/h > speed_limit AND confidence > 0.3
  Clamp: speeds > 200 km/h → reset to 0 (noise)
```

### 8.2 Indian Speed Limits (by zone)

| Zone | Speed Limit |
|---|---|
| School | 25 km/h |
| Hospital | 25 km/h |
| Residential | 30 km/h |
| City | 50 km/h |
| State Highway | 80 km/h |
| National Highway | 100 km/h |
| Expressway | 120 km/h |

---

## 9. GEOFENCING (Shapely + OpenStreetMap)

### 9.1 Point-in-Polygon (Ray Casting Algorithm)

```
Shapely uses: Point(lon, lat).within(Polygon(coords))

Ray Casting: Cast a ray from point to infinity.
  Count intersections with polygon edges.
  Odd count → inside, Even count → outside.

Time complexity: O(n) where n = number of polygon edges
```

### 9.2 Zone Priority Multipliers

```
SCHOOL:       1.5× (MV Act, children safety)
HOSPITAL:     1.5× (silence zone, emergency access)
HIGHWAY:      1.4× (high-speed enforcement)
GOVT:         1.3× (security zones)
LOW_EMISSION: 1.2× (pollution control)
```

### 9.3 OpenStreetMap Dynamic Zones

```
1. Query Overpass API: schools, hospitals, govt buildings
   within radius_m (default 2000m) of camera GPS
2. Convert OSM ways → Shapely Polygons
3. Merge with manual zones (manual zones take priority)
4. Dedup by zone_id (prefix: "osm_")
```

---

## 10. DATABASE INTELLIGENCE (Parallel Threads)

### 10.1 Concurrent Lookups

```python
threads = [
    Thread(target=lookup_vahan,     args=(plate, results)),  # Vehicle registration
    Thread(target=lookup_pucc,      args=(plate, results)),  # Pollution certificate
    Thread(target=lookup_insurance, args=(plate, results)),  # Motor insurance
    Thread(target=check_stolen,     args=(plate, results)),  # Stolen vehicle DB
]
# All 4 run concurrently with 5-second timeout each
```

### 10.2 Violation Code Generation

```
VAHAN not found     → UNREGISTERED_VEHICLE
PUCC not found      → NO_PUCC
PUCC expired        → EXPIRED_PUCC
Insurance not found → NO_INSURANCE
Insurance expired   → EXPIRED_INSURANCE
Stolen = True       → STOLEN_VEHICLE
```

### 10.3 Repeat Offender Escalation

```
Violations in last 30 days:
  0       → Level 0 (clean)
  1-2     → Level 1 (warning)
  3-5     → Level 2 (adds +20 REPEAT_OFFENDER to score)
  6+      → Level 3 (adds +20, triggers court summons)
```

---

## 11. SHA-256 CRYPTOGRAPHIC EVIDENCE CHAIN

### 11.1 Two SHA-256 Hashes

**Hash A — Filename prefix (server.py):**
```
input  = f"{plate_number}{risk_score}"
sha    = hashlib.sha256(input.encode()).hexdigest()
prefix = sha[:8]  # first 8 hex chars

Filename: 20240423_120530_MH12AB1234_a3f7c9e1_captured.jpg
Purpose:  Unique, collision-free evidence filenames
Stored:   Local disk (snapshots/violations/)
```

**Hash B — Database integrity (database.py):**
```
input = f"{plate}{timestamp_utc}{violation_types}"
sha   = hashlib.sha256(input.encode()).hexdigest()

Stored: Supabase violations table → sha256_hash column (full 64 chars)
Purpose: Tamper detection / audit trail
```

### 11.2 SHA-256 Math

```
SHA-256: Merkle–Damgård construction
  - Message → pad to 512-bit blocks
  - 64 rounds of compression per block
  - Uses: Ch, Maj, Σ₀, Σ₁, σ₀, σ₁ functions
  - Output: 256-bit (32-byte) digest → 64 hex characters
  
Properties:
  - Deterministic: same input → same hash always
  - Avalanche: 1-bit change → ~50% output bits change
  - Pre-image resistant: cannot reverse hash → input
  - Collision resistant: infeasible to find two inputs with same hash
```

### 11.3 Tamper Detection Demo

```python
import hashlib
plate, ts, vt = "TS09EF1234", "2026-04-23T08:21:50Z", "FAKE_PLATE,NO_INSURANCE"
original = hashlib.sha256(f"{plate}{ts}{vt}".encode()).hexdigest()

# Tamper attempt: change plate
tampered = hashlib.sha256(f"XX00FAKE{ts}{vt}".encode()).hexdigest()
print(original == tampered)  # False → tampered!
```

---

## 12. ALERT SYSTEM

### 12.1 Severity-Based Routing

| Level | SMS | WhatsApp | Email | Recipients |
|---|---|---|---|---|
| CRITICAL | ✅ | ✅ | ✅ | Police + Owner |
| HIGH | ✅ | ✅ | ✅ | Police + Owner |
| MEDIUM | ❌ | ❌ | ✅ | RTO + Owner |
| LOW | ❌ | ❌ | ❌ | Log only |

### 12.2 Twilio Integration
```
SMS:      Twilio REST API → client.messages.create()
WhatsApp: Same API with "whatsapp:" prefix on phone numbers
```

### 12.3 Email (Gmail SMTP)
```
SMTP server: smtp.gmail.com:587 (STARTTLS)
Attachments: Violation snapshot (JPEG) via MIMEImage
```

---

## 13. FRONTEND DASHBOARD (React + Vite)

### Pages:
1. **Dashboard** — KPI cards (total violations, critical, unique plates) + Recharts bar/line charts
2. **Violations** — Paginated table with level filters, plate search, image previews
3. **Offenders** — Top repeat offenders ranked by count, expandable history with violation badges
4. **Vehicles** — Full CRUD for vehicle registry (VAHAN), PUCC, insurance, stolen flag
5. **Geofence** — Interactive map with zone polygons, OpenStreetMap tile layer
6. **Upload** — Drag-drop image/video upload for batch processing
7. **Feedback** — Active learning: officers correct OCR misreads → stored for retraining

### Auth: Supabase Auth with role-based access (admin, officer, viewer)

---

## 14. COURT SUMMONS PDF (ReportLab)

```
Page: A4 (210mm × 297mm)
Margins: 20mm each side → 170mm usable width

Table columns: [#=10mm, Date=34mm, Violations=80mm, Score=18mm, Level=28mm]

Violations cell: ParagraphStyle(fontSize=7, wordWrap='CJK')
  → auto-wraps comma-separated violations within 80mm column

Features:
  - Dark header row (#1a1a2e)
  - Alternating row shading (#F5F5F5)
  - Color-coded severity levels (red/orange/yellow/green)
  - Legal summons text + SVIES footer with timestamp
```

---

## 15. KEY DIP CONCEPTS USED

| Concept | Where Used | Details |
|---|---|---|
| Histogram Equalization | CLAHE preprocessing | Adaptive on 8×8 tiles, clipLimit=2.0 |
| Color Space Conversion | Vehicle color, plate color | BGR→HSV, BGR→LAB, BGR→YCrCb |
| Thresholding | OCR preprocessing | Otsu (global), Adaptive (Gaussian) |
| Edge Detection | Helmet heuristic, seatbelt | Canny (thresholds 50,150) |
| Line Detection | Seatbelt detection | HoughLinesP (probabilistic) |
| Image Resizing | OCR upscaling, ResNet input | Lanczos4 interpolation |
| Denoising | OCR variant 3 | fastNlMeansDenoising (h=10) |
| Morphological Ops | Plate region cleanup | Implicit in YOLO post-processing |
| Convolution | YOLOv8, ResNet50 | 3×3, 1×1 conv kernels |
| Pooling | ResNet50 | Global Average Pooling before FC |
| Batch Normalization | YOLOv8, ResNet50 | Normalize activations per mini-batch |
| Skip Connections | ResNet50 residual blocks | y = F(x) + x |
| Feature Pyramid | YOLOv8 PANet neck | Multi-scale detection |
| Optical Flow | Speed estimation | Frame-to-frame displacement |

---

## 16. POTENTIAL VIVA QUESTIONS & ANSWERS

**Q: Why YOLOv8 over YOLOv5 or Faster R-CNN?**
A: YOLOv8 has anchor-free detection (no manual anchor tuning), decoupled head (better accuracy), and YOLOv8n runs at ~45 FPS on GPU making it suitable for real-time traffic surveillance.

**Q: Why EasyOCR + Groq LLM instead of just Tesseract?**
A: Indian plates have diverse fonts, dirt, angles. EasyOCR with 6 preprocessing variants handles this better. Groq LLM acts as a "second opinion" — it sees the actual image and can correct OCR errors that pattern-matching cannot.

**Q: How does fake plate detection work?**
A: We run 8 independent forensic checks (type mismatch, color code, font anomaly, clone detection, state mismatch, registration exists, PUCC, insurance). If ≥2 forgery signals fire, confidence exceeds 0.40 and the plate is flagged as fake.

**Q: What is the role of SHA-256?**
A: Two roles: (1) Unique evidence filenames (collision-free, 8-char prefix), (2) Database integrity — the hash stored with each violation record allows verification that no field was tampered with after creation.

**Q: How does geofencing increase risk scores?**
A: Violations in sensitive zones (school/hospital) get a 1.5× multiplier. A 45-point violation becomes 67 points (CRITICAL) in a school zone, triggering immediate police alerts.

**Q: What happens when a vehicle is detected?**
A: Full pipeline: Frame → CLAHE → YOLOv8 vehicle detection → plate localization → OCR (6 variants + Groq) → DB cross-check (4 parallel threads) → fake plate check (8 checks) → helmet/seatbelt → risk score → geofence multiplier → alert dispatch → DB log with SHA-256.

**Q: How is the system different from a simple ANPR?**
A: ANPR only reads plates. SVIES does: plate reading + vehicle type classification + color detection + age estimation + fake plate forensics + helmet/seatbelt detection + multi-database cross-checking + geofenced risk scoring + automated alerts + court summons generation. It's a complete enforcement ecosystem.

**Q: What Indian laws does this system enforce?**
A: Motor Vehicles Act 1988 (Sec 39 - registration, Sec 128 - triple riding, Sec 129 - helmets, Sec 177 - general violations), CMVR 1989 (plate color codes), IS 10731 (plate font standards), Air Act 1981 (PUCC requirements).

**Q: How do you handle low-light / night conditions?**
A: CLAHE preprocessing on the L-channel of LAB color space enhances contrast adaptively. The 6-variant OCR pipeline includes denoised and inverted variants specifically for challenging lighting.

**Q: What is the database architecture?**
A: Primary: Supabase (hosted PostgreSQL) with tables: violations, vehicles, pucc, insurance, stolen_vehicles, feedback. Fallback: Local SQLite with JSON mock data. All queries go through a unified SVIESDatabase class.

---

## 17. PROJECT FILE STRUCTURE

```
svies/
├── api/
│   ├── server.py          # FastAPI backend (2354 lines)
│   ├── database.py        # Supabase + SQLite database layer
│   └── auth.py            # Role-based authentication
├── modules/
│   ├── detector.py        # YOLOv8 vehicle + plate detection
│   ├── ocr_parser.py      # EasyOCR + Groq LLM verification
│   ├── fake_plate.py      # 8-check forensic detection
│   ├── db_intelligence.py # Parallel multi-DB cross-check
│   ├── risk_scorer.py     # Weighted risk scoring engine
│   ├── helmet_detector.py # Helmet/seatbelt detection
│   ├── speed_estimator.py # Optical flow speed estimation
│   ├── geofence.py        # Shapely + OpenStreetMap zones
│   ├── alert_system.py    # Twilio SMS/WhatsApp + Gmail
│   ├── offender_tracker.py# Repeat offender + court summons PDF
│   ├── age_classifier.py  # ResNet50 vehicle age
│   └── plate_detector_resnet.py  # ResNet50 plate fallback
├── frontend/src/
│   ├── pages/             # React pages (Dashboard, Violations, etc.)
│   └── App.jsx            # Router + layout
├── models/                # YOLOv8, ResNet50 weights (.pt files)
├── config.py              # All env vars + paths
├── main.py                # Streamlit demo interface
└── data/
    ├── geozones/zones.json
    └── mock_db/           # VAHAN, PUCC, insurance, stolen JSON
```

---

*End of SVIES Viva Guide. Good luck! 🎓*
