"""
SVIES — Vehicle Age Classifier Module
Layer 2.5: Vehicle Age Classification
Uses ResNet50 (svies_age_classifier.pt) to classify the approximate age
of a detected vehicle from its crop.

Age Categories:
    NEW          — 0-1 years old (showroom condition)
    1-3 YEARS    — slight wear, recent model
    3-5 YEARS    — moderate wear
    5-10 YEARS   — visible aging, older model
    OLD          — 10+ years, significant wear

Usage:
    python -m modules.age_classifier <image_path>
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("svies.age_classifier")

# ── Lazy-load model to avoid import overhead ──
_age_model = None
_age_model_checked = False

# Age category labels (order must match training)
AGE_CATEGORIES = ["NEW", "1-3 YEARS", "3-5 YEARS", "5-10 YEARS", "OLD"]


@dataclass
class AgeResult:
    """Result from vehicle age classification."""
    age_category: str = "UNKNOWN"
    confidence: float = 0.0
    all_scores: dict | None = None  # scores for each category


def _get_age_model():
    """Load the ResNet50 age classifier model (singleton).

    The model is a PyTorch checkpoint saved with torch.save().
    The checkpoint may use 'backbone.' prefixed keys and a custom Sequential FC head.
    """
    global _age_model, _age_model_checked
    if _age_model_checked:
        return _age_model
    _age_model_checked = True

    try:
        import torch
        import torchvision.models as models

        models_dir = Path(__file__).resolve().parent.parent / "models"
        model_path = models_dir / "svies_age_classifier.pt"

        if not model_path.exists():
            logger.warning(f"Age classifier model not found: {model_path}")
            return None

        logger.info(f"Loading ResNet50 age classifier: {model_path}")

        # Determine device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Try loading as a full model first (torch.save(model))
        try:
            loaded = torch.load(str(model_path), map_location=device, weights_only=False)
            if hasattr(loaded, 'eval') and hasattr(loaded, 'forward'):
                loaded.eval()
                _age_model = loaded
                logger.info(f"  Age classifier loaded (full model) on {device}")
                return _age_model
        except Exception:
            pass

        # Load as state_dict
        checkpoint = torch.load(str(model_path), map_location=device, weights_only=False)

        if not isinstance(checkpoint, dict):
            logger.warning("  Age classifier: checkpoint is not a dict, cannot load")
            return None

        # Extract actual state dict from wrapper formats
        if 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
        elif 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        else:
            state_dict = checkpoint

        # Strip 'backbone.' prefix if present
        stripped = {}
        for k, v in state_dict.items():
            new_key = k.replace("backbone.", "", 1) if k.startswith("backbone.") else k
            stripped[new_key] = v

        # Detect FC head structure from checkpoint keys
        fc_keys = sorted([k for k in stripped if k.startswith("fc.")])

        # Build ResNet50 backbone
        model = models.resnet50(weights=None)
        num_features = model.fc.in_features  # 2048

        if any("fc.1." in k or "fc.4." in k for k in fc_keys):
            # Custom Sequential FC head: Dropout → Linear(2048,512) → ReLU → Dropout → Linear(512, num_classes)
            # Detect hidden size from fc.1.weight shape
            hidden_size = 512
            if "fc.1.weight" in stripped:
                hidden_size = stripped["fc.1.weight"].shape[0]
            # Detect num_classes from fc.4.weight shape
            num_classes = len(AGE_CATEGORIES)
            if "fc.4.weight" in stripped:
                num_classes = stripped["fc.4.weight"].shape[0]

            model.fc = torch.nn.Sequential(
                torch.nn.Dropout(0.3),
                torch.nn.Linear(num_features, hidden_size),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.3),
                torch.nn.Linear(hidden_size, num_classes),
            )
            logger.info(f"  FC head: Sequential({num_features} → {hidden_size} → {num_classes})")
        else:
            # Simple Linear head
            num_classes = len(AGE_CATEGORIES)
            if "fc.weight" in stripped:
                num_classes = stripped["fc.weight"].shape[0]
            model.fc = torch.nn.Linear(num_features, num_classes)

        model.load_state_dict(stripped, strict=False)
        model.to(device)
        model.eval()
        _age_model = model
        logger.info(f"  Age classifier loaded (state_dict) on {device}")
        return _age_model

    except ImportError:
        logger.warning("PyTorch not installed — age classifier disabled")
    except Exception as e:
        logger.warning(f"Age classifier load failed: {e}")

    _age_model = None
    return None


def _preprocess_crop(crop: np.ndarray):
    """Preprocess a vehicle crop for ResNet50 input.

    Applies standard ImageNet normalization:
    - Resize to 224x224
    - Convert BGR→RGB
    - Normalize with mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    - Convert to tensor [1, 3, 224, 224]
    """
    import torch

    if crop is None or crop.size == 0:
        return None

    # Resize to 224x224 (ResNet50 standard input)
    resized = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_LINEAR)

    # BGR → RGB
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

    # Normalize to [0, 1] then apply ImageNet normalization
    tensor = rgb.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    tensor = (tensor - mean) / std

    # HWC → CHW → NCHW
    tensor = np.transpose(tensor, (2, 0, 1))
    tensor = np.expand_dims(tensor, axis=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.from_numpy(tensor).to(device)


def classify_age(vehicle_crop: np.ndarray) -> AgeResult:
    """Classify the approximate age of a vehicle from its image crop.

    Args:
        vehicle_crop: BGR image crop of the detected vehicle.

    Returns:
        AgeResult with age_category, confidence, and per-class scores.
    """
    if vehicle_crop is None or vehicle_crop.size == 0:
        return AgeResult()

    model = _get_age_model()
    if model is None:
        return AgeResult()

    try:
        import torch

        input_tensor = _preprocess_crop(vehicle_crop)
        if input_tensor is None:
            return AgeResult()

        with torch.no_grad():
            outputs = model(input_tensor)

            # Apply softmax to get probabilities
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            probs = probabilities[0].cpu().numpy()

            # Get best prediction
            best_idx = int(np.argmax(probs))
            best_conf = float(probs[best_idx])

            # Build all scores dict
            all_scores = {
                AGE_CATEGORIES[i]: round(float(probs[i]), 4)
                for i in range(min(len(AGE_CATEGORIES), len(probs)))
            }

            age_category = AGE_CATEGORIES[best_idx] if best_idx < len(AGE_CATEGORIES) else "UNKNOWN"

            logger.info(
                f"  Age classification: {age_category} (conf={best_conf:.3f}) "
                f"scores={all_scores}"
            )

            return AgeResult(
                age_category=age_category,
                confidence=best_conf,
                all_scores=all_scores,
            )

    except Exception as e:
        logger.warning(f"Age classification error: {e}")
        return AgeResult()


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Vehicle Age Classifier Test")
    print("=" * 60)

    if len(sys.argv) >= 2:
        image_path = Path(sys.argv[1])
        if not image_path.exists():
            print(f"[ERROR] Image not found: {image_path}")
            sys.exit(1)

        print(f"\n[1] Loading image: {image_path}")
        img = cv2.imread(str(image_path))
        if img is None:
            print("[ERROR] Failed to load image!")
            sys.exit(1)
        print(f"    Image shape: {img.shape}")

        print("\n[2] Running age classification...")
        result = classify_age(img)
        print(f"    Age Category: {result.age_category}")
        print(f"    Confidence:   {result.confidence:.3f}")
        if result.all_scores:
            print(f"    All Scores:")
            for cat, score in result.all_scores.items():
                bar = "█" * int(score * 30)
                print(f"      {cat:12s}: {score:.4f} {bar}")
    else:
        # Synthetic test with a blank image
        print("\n[1] Running synthetic test...")
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(test_img, (50, 50), (590, 430), (128, 128, 128), -1)
        result = classify_age(test_img)
        print(f"    Age Category: {result.age_category}")
        print(f"    Confidence:   {result.confidence:.3f}")

    print("\n" + "=" * 60)
    print("[✓] Age classifier test completed!")
