# SVIES — Complete Viva Reference Guide (Part 1)
## Smart Vehicle Intelligence & Enforcement System

---

## 1. PROJECT OVERVIEW

**Full Name:** Smart Vehicle Intelligence & Enforcement System (SVIES)

**Domain:** Digital Image Processing + Computer Vision + AI/ML

**Problem Statement:** Indian roads have ~4.5 lakh accidents annually. Manual traffic enforcement is slow, biased, and limited. SVIES automates violation detection, vehicle identification, and enforcement using a 7-layer AI pipeline.

**Key Innovation:** Unlike single-purpose systems (just ANPR or just helmet detection), SVIES is an **end-to-end enforcement pipeline** — from camera frame to court summons — with novel fake-plate forensics and LLM-augmented OCR.

**Tech Stack:**
| Layer | Technology |
|---|---|
| Detection | YOLOv8n (Ultralytics), ResNet50 |
| OCR | EasyOCR + Groq LLaMA-4 Vision LLM |
| Database | Supabase (PostgreSQL) + SQLite fallback |
| Backend | FastAPI (Python 3.11+) |
| Frontend | React 18 + Vite + Recharts |
| Geofencing | Shapely + OpenStreetMap Overpass API |
| Alerts | Twilio (SMS/WhatsApp) + Gmail SMTP |
| PDF Reports | ReportLab |
| Cryptography | SHA-256 (hashlib) |

---

## 2. SYSTEM ARCHITECTURE — 7 LAYERS

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Frame Acquisition (OpenCV VideoCapture)   │
├─────────────────────────────────────────────────────┤
│  Layer 2: AI Detection (YOLOv8n + ResNet50)         │
│    → Vehicle detection, type classification, color  │
│    → License plate localization                     │
│    → Vehicle age classification (ResNet50)          │
├─────────────────────────────────────────────────────┤
│  Layer 3: OCR Engine                                │
│    → 6-variant preprocessing + EasyOCR              │
│    → Groq LLaMA-4 Vision verification               │
│    → Indian plate regex validation                  │
├─────────────────────────────────────────────────────┤
│  Layer 4: Multi-Database Intelligence               │
│    → VAHAN + PUCC + Insurance + Stolen (parallel)   │
│    → Fake Plate Detection (8 forensic checks)       │
│    → Helmet/Seatbelt detection (YOLOv8n-pose)       │
│    → Weighted Risk Scoring                          │
├─────────────────────────────────────────────────────┤
│  Layer 5: Geofencing + Speed Estimation             │
│    → Shapely point-in-polygon                       │
│    → OpenStreetMap dynamic zones                    │
│    → Optical flow speed estimation                  │
├─────────────────────────────────────────────────────┤
│  Layer 6: Alert & Enforcement                       │
│    → Twilio SMS/WhatsApp + Gmail SMTP               │
│    → Severity-based routing                         │
│    → Court summons PDF generation                   │
├─────────────────────────────────────────────────────┤
│  Layer 7: Dashboard & Analytics (React + FastAPI)   │
│    → Real-time violation feed                       │
│    → Offender tracking + history                    │
│    → Vehicle CRUD + geofence map                    │
└─────────────────────────────────────────────────────┘
```

---

## 3. LAYER 2 — VEHICLE DETECTION (Theory + Math)

### 3.1 YOLOv8n Architecture

**YOLO = You Only Look Once.** Single-pass object detector (vs two-stage like Faster R-CNN).

**YOLOv8n** (nano variant, 3.2M params) uses:
- **Backbone:** CSPDarknet53 with C2f blocks (Cross Stage Partial)
- **Neck:** PANet (Path Aggregation Network) for multi-scale feature fusion
- **Head:** Decoupled head (separate classification + regression branches)
- **Loss:** CIoU loss for bounding box regression + BCE for classification

**Detection Math:**
```
Input: Frame I ∈ ℝ^(H×W×3)
Output: Set of detections {(bbox_i, class_i, conf_i)}

bbox = (x_center, y_center, width, height)
conf = P(object) × IoU(pred, truth)

Non-Maximum Suppression (NMS):
  For each class:
    1. Sort detections by confidence (descending)
    2. Keep highest conf detection
    3. Remove all detections with IoU > threshold (0.45) with kept detection
    4. Repeat until no detections remain
```

**IoU (Intersection over Union):**
```
IoU(A, B) = |A ∩ B| / |A ∪ B|
         = Area of Overlap / Area of Union
```

**CIoU Loss (Complete IoU):**
```
L_CIoU = 1 - IoU + ρ²(b, b_gt) / c² + αv

where:
  ρ = Euclidean distance between predicted and GT box centers
  c = diagonal length of smallest enclosing box
  v = (4/π²)(arctan(w_gt/h_gt) - arctan(w/h))²
  α = v / ((1 - IoU) + v)
```

### 3.2 CLAHE Preprocessing

Before detection, frames pass through CLAHE (Contrast Limited Adaptive Histogram Equalization) for Indian road conditions (dust, glare, low-light).

**Algorithm:**
```
1. Convert BGR → LAB color space
2. Split into L, A, B channels
3. Apply CLAHE on L channel only:
   - Divide image into 8×8 tiles
   - Compute histogram for each tile
   - Clip histogram at clipLimit=2.0
   - Redistribute clipped pixels uniformly
   - Apply bilinear interpolation at tile borders
4. Merge enhanced L with original A, B
5. Convert LAB → BGR
```

**Math — Histogram Equalization:**
```
For pixel intensity r (0-255):
  s = T(r) = (L-1) × CDF(r)

where CDF(r) = Σ_{j=0}^{r} p(j)
  p(j) = n_j / N  (probability of intensity j)
```

### 3.3 Vehicle Color Classification (HSV)

Uses HSV color space (better for color-based segmentation than BGR):

```
BGR → HSV conversion:
  H = hue (0-180 in OpenCV)
  S = saturation (0-255)
  V = value/brightness (0-255)

Color masks defined:
  WHITE:  H=[0,180], S=[0,30],   V=[200,255]
  BLACK:  H=[0,180], S=[0,30],   V=[0,50]
  RED:    H=[0,10]∪[160,180], S=[100,255], V=[100,255]
  BLUE:   H=[100,130], S=[100,255], V=[100,255]
  ...etc

Classification:
  ratio(color) = count_nonzero(mask) / total_pixels
  vehicle_color = argmax(ratio)
```

### 3.4 Vehicle Age Classification (ResNet50)

**ResNet50** (50-layer Residual Network, 25.6M params):

**Residual Block Math:**
```
Standard: y = F(x)                    ← vanishing gradient problem
Residual: y = F(x) + x               ← skip connection

F(x) = W₂ · σ(W₁ · x + b₁) + b₂
Output: H(x) = F(x) + x              ← identity shortcut

This solves: ∂L/∂x = ∂L/∂H · (∂F/∂x + 1)
The "+1" ensures gradients always flow back.
```

**Preprocessing (ImageNet normalization):**
```
1. Resize to 224×224
2. BGR → RGB
3. Scale to [0,1]: pixel / 255.0
4. Normalize: (pixel - mean) / std
   mean = [0.485, 0.456, 0.406]
   std  = [0.229, 0.224, 0.225]
5. HWC → CHW → NCHW (batch dimension)
```

**Age Categories:** NEW, 1-3 YEARS, 3-5 YEARS, 5-10 YEARS, OLD

**Softmax Output:**
```
P(class_i) = exp(z_i) / Σ_j exp(z_j)
```

---

## 4. LAYER 3 — OCR ENGINE (Theory + Math)

### 4.1 Multi-Attempt Preprocessing Pipeline

6 variants generated from each plate crop:

| # | Variant | Technique |
|---|---------|-----------|
| 1 | Otsu | Global threshold via Otsu's method |
| 2 | CLAHE+Otsu | CLAHE(clipLimit=4.0) then Otsu |
| 3 | Denoise+Otsu | fastNlMeansDenoising(h=10) then Otsu |
| 4 | Inverted | Bitwise NOT of variant 1 |
| 5 | Raw | Upscaled grayscale (no threshold) |
| 6 | Adaptive | adaptiveThreshold (Gaussian, blockSize=31) |

**Otsu's Threshold Math:**
```
Objective: Find threshold t* that minimizes intra-class variance

σ²_w(t) = w₀(t)·σ²₀(t) + w₁(t)·σ²₁(t)

Equivalently, maximize inter-class variance:
σ²_b(t) = w₀·w₁·(μ₀ - μ₁)²

where:
  w₀ = Σ_{i=0}^{t} p(i)     (weight of background)
  w₁ = Σ_{i=t+1}^{255} p(i)  (weight of foreground)
  μ₀, μ₁ = class means

t* = argmax_t σ²_b(t)
```

**Adaptive Upscaling:**
```
scale = min(5.0, max(2.0, 250 / plate_height))
Interpolation: Lanczos4 (8×8 sinc-based kernel)
```

### 4.2 EasyOCR Engine

- CRAFT text detector (Character Region Awareness for Text)
- ResNet + LSTM + CTC decoder
- Character whitelist: `A-Z 0-9` (36 chars)
- Scoring: `score = len(text) × confidence` → best variant wins

### 4.3 Indian Plate Format Validation

**Regex patterns:**
```
Standard: ^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$
  Example: TS09EF1234  →  TS=Telangana, 09=district, EF=series, 1234=number

BH-series: ^\d{2}BH\d{4}[A-Z]{1,2}$
  Example: 22BH1234AB  →  Bharat series (transferable across states)
```

### 4.4 Context-Aware Character Correction

Position-based rules for OCR confusion pairs:
```
Positions 0-1 (state code, must be letters):
  0 → O,  1 → I,  8 → B

Positions 2-3 (district code, must be digits):
  O → 0,  I → 1,  B → 8,  S → 5,  Z → 2

Positions 6+ (trailing digits):
  Context-aware: check if neighbors are digits
  O → 0 (if surrounded by digits)
  I → 1 (if surrounded by digits)
```

### 4.5 Groq LLaMA-4 Vision Verification

**Model:** `meta-llama/llama-4-scout-17b-16e-instruct`

**Flow:**
```
1. Encode plate crop → base64 JPEG
2. Send to Groq API with prompt:
   "You are an Indian license plate reader..."
3. If Groq confirms EasyOCR → boost confidence by +0.15
4. If Groq corrects EasyOCR → use Groq's answer (conf ≥ 0.85)
5. If Groq returns NONE → fall back to EasyOCR
```

---

## 5. FAKE PLATE DETECTION — 8 FORENSIC CHECKS

### Check 0: Stolen Vehicle
```
Query: stolen_vehicles table
Result: CRITICAL if plate found
```

### Check 0.5: VAHAN Registration Exists
```
Query: vehicles table (VAHAN database)
Result: HIGH if plate NOT found → unregistered/fake
```

### Check 1: Type Mismatch
```
Compare: detected_vehicle_category vs VAHAN registered category
Categories: 2W (motorcycle/scooter), 3W (auto), 4W (car/truck/bus), FARM
Example: Plate says MOTORCYCLE but camera sees CAR → FAKE
```

### Check 2: Color Code Violation (CMVR Rules)
```
Plate color classification via HSV on top 10px strip:
  WHITE  → PRIVATE vehicle
  YELLOW → COMMERCIAL (truck/bus/auto)
  GREEN  → Electric Vehicle
  BLACK  → RENTAL/DIPLOMATIC

Rule: Yellow plate on CAR = violation
Rule: White plate on TRUCK = violation
Threshold: ≥30% color coverage required
```

### Check 3: Font Anomaly (IS 10731 Standard)
```
Indian standard IS 10731 mandates:
  char_height / plate_height ∈ [0.5, 0.7]
  char_spacing / char_width  ∈ [0.1, 0.3]

For each OCR bounding box:
  height_ratio = char_h / plate_h
  spacing_ratio = gap_to_next / char_w

Flag if >30% characters fail these ratios.
```

### Check 4: Duplicate Plate / Clone Detection
```
Maintain: _seen_plates = {plate: (last_seen_utc, camera_id)}

If same plate seen on DIFFERENT camera within 600 seconds (10 min):
  → CLONE_ALERT (physically impossible to be at two locations)
```

### Check 5: State Code Mismatch
```
Extract first 2 chars of plate → state code (e.g., TS=Telangana)
Compare with VAHAN registration_state_code
Mismatch → potential fake plate
Exception: BH-series plates (position 2-3 = "BH")
```

### Checks 6-7: PUCC & Insurance Validity
```
Query pucc/insurance tables
Status: VALID / EXPIRED / NOT_FOUND
These are compliance violations, NOT forgery indicators
```

### Confidence Aggregation
```
FORGERY_FLAGS = {STOLEN, VAHAN_NOT_EXISTS, TYPE_MISMATCH,
                 COLOR_CODE, FONT_ANOMALY, DUPLICATE, STATE_MISMATCH}

Rules:
  STOLEN alone         → is_fake=True,  confidence=0.95
  ≥2 forgery flags     → is_fake=True,  confidence=min(1.0, count×0.20)
  1 forgery flag       → is_fake=True,  confidence=0.35
  VAHAN_NOT_EXISTS only → is_fake=True,  confidence=0.15
  No forgery flags     → is_fake=False, confidence=0.0
```

---

*Continued in Part 2...*
