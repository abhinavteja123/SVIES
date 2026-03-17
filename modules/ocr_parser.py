"""
SVIES — OCR + Plate Parsing Module
Layer 3: OCR Engine
Multi-attempt EasyOCR with 6 preprocessing variants.
Groq AI vision LLM for OCR verification & correction.
Validates results against Indian plate regex patterns.

Usage:
    python -m modules.ocr_parser <plate_image_path>
"""

import base64
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("svies.ocr")

# ── Lazy-load OCR engines (they are slow to initialize) ──
_easyocr_reader = None
_groq_client = None
_plate_regex = re.compile(r'^[A-Z]{2}\d{2}[A-Z]{1,3}\d{1,4}$')
_bh_regex = re.compile(r'^\d{2}BH\d{4}[A-Z]{1,2}$')
_plate_search = re.compile(r'[A-Z]{2}\d{2}[A-Z]{1,3}\d{1,4}')
_bh_search = re.compile(r'\d{2}BH\d{4}[A-Z]{1,2}')

# ── OCR character whitelist ──
_CHAR_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _get_easyocr_reader():
    """Get or initialize the EasyOCR reader (singleton)."""
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            logger.info("Initializing EasyOCR reader (this may take a moment)...")
            _easyocr_reader = easyocr.Reader(['en'], gpu=True)
        except ImportError:
            logger.warning("EasyOCR not installed.")
            _easyocr_reader = None
        except Exception as e:
            logger.warning(f"EasyOCR initialization failed: {e}")
            _easyocr_reader = None
    return _easyocr_reader


def _get_groq_client():
    """Get or initialize the Groq client (singleton)."""
    global _groq_client
    if _groq_client is None:
        try:
            from config import GROQ_API_KEY
            if not GROQ_API_KEY:
                logger.info("GROQ_API_KEY not set — Groq AI verification disabled")
                return None
            from groq import Groq
            _groq_client = Groq(api_key=GROQ_API_KEY)
            logger.info("Groq AI client initialized for OCR verification")
        except ImportError:
            logger.warning("groq package not installed — pip install groq")
            _groq_client = None
        except Exception as e:
            logger.warning(f"Groq client initialization failed: {e}")
            _groq_client = None
    return _groq_client


# ══════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════

@dataclass
class OCRResult:
    """Result from the OCR plate parsing pipeline."""
    plate_number: str | None = None
    raw_text: str = ""
    confidence: float = 0.0
    format_type: str = "UNKNOWN"  # STANDARD / BH / UNKNOWN
    char_bboxes: list = field(default_factory=list)
    verified_by: str = "easyocr"  # "easyocr" | "groq_verified" | "groq_corrected"


# ══════════════════════════════════════════════════════════
# Multi-Attempt Preprocessing (from proven notebook approach)
# ══════════════════════════════════════════════════════════

def _generate_preprocessing_variants(plate_crop: np.ndarray) -> list[np.ndarray]:
    """Generate preprocessing variants for multi-attempt OCR.

    Matches the proven notebook approach: 5x upscale + multiple threshold variants.

    Args:
        plate_crop: BGR image of the cropped plate.

    Returns:
        List of preprocessed grayscale images.
    """
    if plate_crop is None or plate_crop.size == 0:
        return []

    # ── Convert to grayscale ──
    if len(plate_crop.shape) == 3:
        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = plate_crop.copy()

    # ── Adaptive upscale: target ~250px height for OCR, cap at 5x ──
    h_orig, w_orig = gray.shape[:2]
    target_h = 250
    scale = min(5.0, max(2.0, target_h / max(h_orig, 1)))
    upscaled = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_LANCZOS4)

    variants = []

    # Variant 1: Standard Otsu
    _, m1 = cv2.threshold(upscaled, 0, 255,
                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(m1)

    # Variant 2: CLAHE (aggressive) + Otsu
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(upscaled)
    _, m2 = cv2.threshold(enhanced, 0, 255,
                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(m2)

    # Variant 3: Denoised + Otsu
    denoised = cv2.fastNlMeansDenoising(upscaled, h=10)
    _, m3 = cv2.threshold(denoised, 0, 255,
                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(m3)

    # Variant 4: Inverted (for dark plates / white text)
    m4 = cv2.bitwise_not(m1)
    variants.append(m4)

    # Variant 5: Raw upscaled grayscale
    variants.append(upscaled)

    # Variant 6: Adaptive threshold (handles uneven lighting across plate)
    m6 = cv2.adaptiveThreshold(upscaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 31, 10)
    variants.append(m6)

    return variants


def preprocess_plate(plate_crop: np.ndarray) -> np.ndarray:
    """Preprocess plate image for optimal OCR recognition.

    Pipeline: Grayscale -> Adaptive upscale -> CLAHE -> Otsu

    Args:
        plate_crop: BGR image of the cropped plate.

    Returns:
        Preprocessed grayscale image ready for OCR.
    """
    if plate_crop is None or plate_crop.size == 0:
        return np.array([], dtype=np.uint8)

    if len(plate_crop.shape) == 3:
        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = plate_crop.copy()

    # Upscale first (target ~250px height, cap at 5x) — matches multi-attempt pipeline
    h, w = gray.shape[:2]
    scale = min(5.0, max(2.0, 250 / max(h, 1)))
    resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(resized)
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


# ══════════════════════════════════════════════════════════
# OCR Engine: Multi-Attempt EasyOCR
# ══════════════════════════════════════════════════════════

def _run_easyocr_multi(plate_crop: np.ndarray) -> tuple[str, float, list]:
    """Run EasyOCR across multiple preprocessing variants.

    Tries 5 different preprocessed versions of the plate crop,
    picks the result with the highest score (len(text) * confidence).

    Args:
        plate_crop: BGR image of the cropped plate.

    Returns:
        Tuple of (best_text, best_confidence, char_bboxes).
    """
    reader = _get_easyocr_reader()
    if reader is None:
        return ("", 0.0, [])

    variants = _generate_preprocessing_variants(plate_crop)
    if not variants:
        return ("", 0.0, [])

    best_text = ""
    best_conf = 0.0
    best_score = 0.0
    best_bboxes = []

    variant_names = ["Otsu", "CLAHE+Otsu", "Denoise+Otsu", "Inverted", "Raw", "Adaptive"]
    for vi, img_variant in enumerate(variants):
        vname = variant_names[vi] if vi < len(variant_names) else f"V{vi}"
        try:
            results = reader.readtext(
                img_variant,
                detail=1,
                allowlist=_CHAR_WHITELIST,
                paragraph=False,
                width_ths=0.7,
                mag_ratio=1.0,
            )
            if not results:
                logger.debug(f"  OCR variant [{vname}]: no text found")
                continue

            # ── Sort by x-coordinate (left to right) ──
            results_sorted = sorted(results, key=lambda r: r[0][0][0])

            text = "".join([r[1].upper().replace(" ", "")
                           for r in results_sorted])
            conf = sum(r[2] for r in results_sorted) / len(results_sorted)
            score = len(text) * conf
            logger.info(f"  OCR variant [{vname}]: text='{text}', conf={conf:.3f}, score={score:.1f}")

            if score > best_score:
                best_score = score
                best_text = text
                best_conf = conf
                best_bboxes = []
                for bbox, _, _ in results_sorted:
                    pts = np.array(bbox, dtype=np.int32)
                    x1, y1 = pts.min(axis=0)
                    x2, y2 = pts.max(axis=0)
                    best_bboxes.append([int(x1), int(y1), int(x2), int(y2)])

        except Exception as e:
            logger.debug(f"  OCR variant [{vname}] error: {e}")
            continue

    return (best_text, best_conf, best_bboxes)


def _run_easyocr(image: np.ndarray) -> tuple[str, float, list]:
    """Run EasyOCR on a single preprocessed plate image (legacy interface).

    Args:
        image: Preprocessed grayscale image.

    Returns:
        Tuple of (text, confidence, char_bboxes).
    """
    reader = _get_easyocr_reader()
    if reader is None:
        return ("", 0.0, [])

    try:
        results = reader.readtext(
            image,
            detail=1,
            allowlist=_CHAR_WHITELIST,
            paragraph=False,
            width_ths=0.7,
            mag_ratio=1.0,
        )
        if not results:
            return ("", 0.0, [])

        results_sorted = sorted(results, key=lambda r: r[0][0][0])

        full_text = "".join([r[1].upper().replace(" ", "")
                            for r in results_sorted])
        total_conf = sum(r[2] for r in results_sorted)
        char_bboxes = []

        for bbox, text, conf in results_sorted:
            pts = np.array(bbox, dtype=np.int32)
            x1, y1 = pts.min(axis=0)
            x2, y2 = pts.max(axis=0)
            char_bboxes.append([int(x1), int(y1), int(x2), int(y2)])

        avg_conf = total_conf / len(results_sorted)
        return (full_text, avg_conf, char_bboxes)

    except Exception as e:
        logger.warning(f"EasyOCR error: {e}")
        return ("", 0.0, [])


def _run_tesseract(image: np.ndarray) -> tuple[str, float, list]:
    """Run Tesseract OCR on preprocessed plate image.

    Args:
        image: Preprocessed grayscale image.

    Returns:
        Tuple of (text, confidence, char_bboxes).
    """
    try:
        import pytesseract

        config = '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(image, config=config).strip()
        data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)

        confidences = [int(c) for c in data['conf'] if int(c) > 0]
        avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

        char_bboxes = []
        for i, word in enumerate(data['text']):
            if word.strip():
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                char_bboxes.append([x, y, x + w, y + h])

        return (text, avg_conf, char_bboxes)

    except ImportError:
        return ("", 0.0, [])
    except Exception as e:
        logger.warning(f"Tesseract error: {e}")
        return ("", 0.0, [])


# ══════════════════════════════════════════════════════════
# Post-Processing & Character Correction
# ══════════════════════════════════════════════════════════

def _correct_characters(text: str) -> str:
    """Apply context-aware character corrections for Indian plates.

    Position-based rules:
    - Positions 0-1 (state code): only letters -> 0->O, 1->I
    - Positions 2-3 (district code): only digits -> O->0, I->1, B->8
    - Positions 4+ (series + number): standard substitutions
    """
    if len(text) < 6:
        return text

    corrected = list(text)

    for i, ch in enumerate(corrected):
        if i < 2:
            # State code positions (0-1): must be letters
            if ch == '0':
                corrected[i] = 'O'
            elif ch == '1':
                corrected[i] = 'I'
            elif ch == '8':
                corrected[i] = 'B'
            elif ch == 'l':  # lowercase L -> I
                corrected[i] = 'I'
        elif i < 4:
            # District code positions (2-3): must be digits
            if ch == 'O' or ch == 'o':
                corrected[i] = '0'
            elif ch == 'I' or ch == 'i' or ch == 'l':
                corrected[i] = '1'
            elif ch == 'B':
                corrected[i] = '8'
            elif ch == 'S':
                corrected[i] = '5'
            elif ch == 'Z':
                corrected[i] = '2'
        else:
            # In Indian plates (e.g., TS09EF1234), positions 4-5 are letters,
            # positions 6+ are always digits. Use both context and position.
            in_digit_tail = len(corrected) >= 8 and i >= len(corrected) - 4
            if ch == 'O' or ch == 'o':
                prev_is_digit = i > 0 and corrected[i - 1].isdigit()
                next_is_digit = i < len(corrected) - 1 and corrected[i + 1].isdigit()
                if prev_is_digit or next_is_digit or in_digit_tail:
                    corrected[i] = '0'
            elif ch == 'I' or ch == 'l':
                prev_is_digit = i > 0 and corrected[i - 1].isdigit()
                next_is_digit = i < len(corrected) - 1 and corrected[i + 1].isdigit()
                if prev_is_digit or next_is_digit or in_digit_tail:
                    corrected[i] = '1'
            elif ch == 'S' and in_digit_tail:
                corrected[i] = '5'
            elif ch == 'B' and in_digit_tail:
                corrected[i] = '8'
            elif ch == 'Z' and in_digit_tail:
                corrected[i] = '2'

    return ''.join(corrected)


def _clean_text(raw_text: str) -> str:
    """Clean and normalize OCR text."""
    cleaned = re.sub(r'[^A-Za-z0-9]', '', raw_text)
    return cleaned.upper()


def _validate_plate(text: str) -> tuple[str | None, str]:
    """Validate plate text against Indian format patterns.

    Tries strict match first, then searches within the text for a
    plate-like substring (handles OCR noise around the plate).
    """
    if _plate_regex.match(text):
        return (text, "STANDARD")
    elif _bh_regex.match(text):
        return (text, "BH")

    # ── Fallback: search for a plate pattern embedded in longer text ──
    m = _plate_search.search(text)
    if m and len(m.group()) >= 7:
        return (m.group(), "STANDARD")
    m = _bh_search.search(text)
    if m:
        return (m.group(), "BH")

    return (None, "UNKNOWN")


# ══════════════════════════════════════════════════════════
# Groq AI Vision — OCR Verification & Correction
# ══════════════════════════════════════════════════════════

def _encode_image_base64(image: np.ndarray) -> str:
    """Encode an OpenCV image to base64 JPEG string for Groq API."""
    success, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not success:
        return ""
    return base64.b64encode(buffer).decode('utf-8')


def _verify_with_groq(plate_crop: np.ndarray, ocr_text: str) -> tuple[str | None, str]:
    """Send plate crop image + EasyOCR text to Groq vision LLM for verification.

    The LLM sees the actual plate image and the OCR's best guess, then either
    confirms the reading or provides a corrected plate number.

    Args:
        plate_crop: BGR image of the cropped license plate.
        ocr_text: The plate text extracted by EasyOCR (may be wrong).

    Returns:
        Tuple of (verified_plate, source) where source is:
            "groq_verified"  — Groq confirmed the EasyOCR reading
            "groq_corrected" — Groq provided a different (corrected) plate
            None, "easyocr"  — Groq unavailable, fall back to EasyOCR
    """
    client = _get_groq_client()
    if client is None:
        return (None, "easyocr")

    image_b64 = _encode_image_base64(plate_crop)
    if not image_b64:
        logger.warning("Groq: failed to encode plate image")
        return (None, "easyocr")

    try:
        from config import GROQ_MODEL
    except ImportError:
        GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

    prompt = (
        "You are an Indian license plate reader. "
        "Look at this image of an Indian vehicle license plate. "
        f"An OCR system read it as: \"{ocr_text}\". "
        "Indian plates follow these formats:\n"
        "- Standard: SS DD XX NNNN (e.g., TS09EF1234) where SS=state code (2 letters), "
        "DD=district (2 digits), XX=series (1-3 letters), NNNN=number (1-4 digits)\n"
        "- BH series: NN BH NNNN XX (e.g., 22BH1234AB)\n\n"
        "Read the plate from the image carefully. "
        "Reply with ONLY the plate number in uppercase, no spaces, no explanation. "
        "Example: TS09EF1234"
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            max_tokens=30,
            temperature=0.0,
        )

        groq_text = response.choices[0].message.content.strip()
        # Clean: keep only alphanumeric, uppercase
        groq_plate = re.sub(r'[^A-Za-z0-9]', '', groq_text).upper()

        if not groq_plate or len(groq_plate) < 4:
            logger.warning(f"Groq: response too short or empty: '{groq_text}'")
            return (None, "easyocr")

        logger.info(f"Groq AI: raw='{groq_text}' -> cleaned='{groq_plate}' (OCR was: '{ocr_text}')")

        # Determine if Groq confirmed or corrected
        if groq_plate == ocr_text:
            return (groq_plate, "groq_verified")
        else:
            return (groq_plate, "groq_corrected")

    except Exception as e:
        logger.warning(f"Groq API call failed: {e}")
        return (None, "easyocr")


# ══════════════════════════════════════════════════════════
# Main OCR Function
# ══════════════════════════════════════════════════════════

def extract_plate(plate_crop: np.ndarray, min_confidence: float = 0.3) -> OCRResult:
    """Extract and validate a license plate number from a plate crop image.

    Pipeline:
    1. Generate 6 preprocessing variants (Otsu, CLAHE+Otsu, denoise+Otsu, inverted, raw, adaptive)
    2. Run EasyOCR on each variant with character whitelist
    3. Pick best result by score (len(text) * confidence)
    4. Clean text, apply character corrections
    5. Validate against Indian plate regex (with fallback substring search)
    6. Send plate crop + EasyOCR text to Groq AI for verification/correction
    7. Return best result with source attribution
    """
    if plate_crop is None or plate_crop.size == 0:
        logger.warning("OCR called with empty plate crop")
        return OCRResult(raw_text="", confidence=0.0)

    logger.info(f"OCR input: plate_crop shape={plate_crop.shape}, min_confidence={min_confidence}")

    # ── Step 1-3: Multi-attempt OCR across 6 variants ──
    raw_text, confidence, char_bboxes = _run_easyocr_multi(plate_crop)

    if not raw_text:
        logger.warning("OCR: all variants returned empty text")
        # Even if EasyOCR failed, try Groq directly on the image
        groq_plate, groq_source = _verify_with_groq(plate_crop, "")
        if groq_plate:
            groq_validated, groq_fmt = _validate_plate(groq_plate)
            plate_out = groq_validated if groq_validated else groq_plate
            fmt_out = groq_fmt if groq_validated else "RAW"
            logger.info(f"Groq rescued empty OCR: plate='{plate_out}' format={fmt_out}")
            return OCRResult(
                plate_number=plate_out,
                raw_text=groq_plate,
                confidence=0.85,
                format_type=fmt_out,
                char_bboxes=[],
                verified_by=groq_source,
            )
        return OCRResult(raw_text="", confidence=0.0)

    # ── Step 4: Clean and correct ──
    cleaned = _clean_text(raw_text)
    corrected = _correct_characters(cleaned)
    logger.info(f"OCR: raw='{raw_text}' -> cleaned='{cleaned}' -> corrected='{corrected}' (conf={confidence:.3f})")

    # ── Step 5: Validate ──
    plate_number, format_type = _validate_plate(corrected)
    logger.info(f"OCR: regex validation -> plate={plate_number}, format={format_type}")

    # ── Step 6: Groq AI verification/correction ──
    verified_by = "easyocr"
    easyocr_plate = plate_number if plate_number else corrected
    groq_plate, groq_source = _verify_with_groq(plate_crop, easyocr_plate)

    if groq_plate:
        groq_validated, groq_fmt = _validate_plate(groq_plate)

        if groq_validated:
            # Groq returned a valid Indian plate
            if groq_validated == plate_number:
                # Groq confirmed EasyOCR — boost confidence
                verified_by = "groq_verified"
                confidence = min(1.0, confidence + 0.15)
                logger.info(f"Groq VERIFIED EasyOCR: '{plate_number}' (conf boosted to {confidence:.3f})")
            else:
                # Groq corrected EasyOCR — use Groq's answer
                logger.info(f"Groq CORRECTED: '{plate_number}' -> '{groq_validated}' (format={groq_fmt})")
                plate_number = groq_validated
                format_type = groq_fmt
                verified_by = "groq_corrected"
                confidence = max(confidence, 0.85)
        elif not plate_number and len(groq_plate) >= 6:
            # EasyOCR regex failed but Groq gave something reasonable
            logger.info(f"Groq provided plate (no regex match): '{groq_plate}'")
            plate_number = groq_plate
            format_type = "RAW"
            verified_by = "groq_corrected"
            confidence = max(confidence, 0.75)

    # ── Step 7: Return result ──
    if plate_number and confidence >= min_confidence:
        logger.info(f"OCR PASS: plate='{plate_number}' conf={confidence:.3f} verified_by={verified_by}")
        return OCRResult(
            plate_number=plate_number,
            raw_text=raw_text,
            confidence=confidence,
            format_type=format_type,
            char_bboxes=char_bboxes,
            verified_by=verified_by,
        )
    elif len(corrected) >= 3 and confidence >= min_confidence:
        logger.info(f"OCR PASS (raw fallback): plate='{corrected}' conf={confidence:.3f} verified_by={verified_by}")
        return OCRResult(
            plate_number=corrected,
            raw_text=raw_text,
            confidence=confidence,
            format_type="RAW",
            char_bboxes=char_bboxes,
            verified_by=verified_by,
        )
    else:
        logger.warning(f"OCR FAIL: corrected='{corrected}' conf={confidence:.3f} verified_by={verified_by}")
        return OCRResult(
            plate_number=None,
            raw_text=raw_text,
            confidence=confidence,
            format_type=format_type,
            char_bboxes=char_bboxes,
            verified_by=verified_by,
        )


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 60)
        print("SVIES — OCR Module Test (Synthetic)")
        print("=" * 60)
        print("\nNo image path provided. Creating synthetic plate for testing...")

        plate_img = np.ones((80, 300, 3), dtype=np.uint8) * 255
        cv2.putText(plate_img, "TS09EF1234", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)

        print("  Synthetic plate created: TS09EF1234")
        print("\n[1] Running OCR pipeline...")
        result = extract_plate(plate_img)
        print(f"  Plate Number: {result.plate_number}")
        print(f"  Raw Text:     {result.raw_text}")
        print(f"  Confidence:   {result.confidence:.3f}")
        print(f"  Format Type:  {result.format_type}")
        print(f"  Verified By:  {result.verified_by}")
        print(f"  Char BBoxes:  {len(result.char_bboxes)} boxes")

        if result.plate_number:
            print("\n  [OK] OCR extraction PASSED!")
        else:
            print(f"\n  [!] OCR could not validate plate (raw: '{result.raw_text}', conf: {result.confidence:.3f})")
            print("      This may be normal with synthetic images — test with real plates for best results.")

        print("\n[2] Testing preprocessing pipeline...")
        processed = preprocess_plate(plate_img)
        print(f"  Preprocessed shape: {processed.shape}")
        print("  [OK] Preprocessing PASSED!")

        print("\n[3] Testing character correction...")
        test_cases = [
            ("0S09EF1234", "OS09EF1234"),
            ("TS09EF12O4", "TS09EF1204"),
        ]
        for raw, expected in test_cases:
            corrected_val = _correct_characters(raw)
            status = "OK" if corrected_val == expected else "FAIL"
            print(f"  [{status}] '{raw}' -> '{corrected_val}' (expected: '{expected}')")

        print("\n[4] Testing plate validation...")
        valid_tests = [
            ("TS09EF1234", "STANDARD"),
            ("22BH1234AB", "BH"),
            ("INVALID123", None),
        ]
        for plate, expected_fmt in valid_tests:
            result_plate, fmt = _validate_plate(plate)
            if expected_fmt is None:
                status = "OK" if result_plate is None else "FAIL"
            else:
                status = "OK" if fmt == expected_fmt else "FAIL"
            print(f"  [{status}] '{plate}' -> plate={result_plate}, format={fmt}")

        print("\n" + "=" * 60)
        print("[OK] OCR module tests completed!")

    else:
        image_path = Path(sys.argv[1])
        if not image_path.exists():
            print(f"[ERROR] Image not found: {image_path}")
            sys.exit(1)

        print("=" * 60)
        print("SVIES — OCR Module Test")
        print("=" * 60)

        print(f"\n[1] Loading image: {image_path}")
        plate_img = cv2.imread(str(image_path))
        if plate_img is None:
            print("[ERROR] Failed to load image!")
            sys.exit(1)
        print(f"    Image shape: {plate_img.shape}")

        print("\n[2] Running OCR pipeline...")
        result = extract_plate(plate_img)
        print(f"    Plate Number: {result.plate_number}")
        print(f"    Raw Text:     {result.raw_text}")
        print(f"    Confidence:   {result.confidence:.3f}")
        print(f"    Format Type:  {result.format_type}")
        print(f"    Verified By:  {result.verified_by}")
        print(f"    Char BBoxes:  {len(result.char_bboxes)} boxes")

        print("\n" + "=" * 60)
        print("[OK] OCR extraction test completed!")
