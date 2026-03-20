"""
SVIES — ResNet50 Plate Region Detector Module
Layer 2.5: Plate Region Detection (Fallback)
Uses ResNet50 feature extraction to detect and localize license plate
regions within a vehicle crop when the primary YOLO plate detector fails.

This acts as a secondary/fallback plate detector that runs on the
vehicle crop after the YOLO pipeline, using ResNet50's learned features
to identify the plate region via a classification+regression approach.

Usage:
    python -m modules.plate_detector_resnet <image_path>
"""

import logging
import sys
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("svies.plate_resnet")

# ── Lazy-load model ──
_resnet_model = None
_resnet_model_checked = False


def _get_resnet_plate_model():
    """Load a ResNet50 model for plate region detection (singleton).

    Uses torchvision's pretrained ResNet50 as a feature extractor.
    The model generates feature maps that help localize plate regions
    via gradient-weighted activation (heatmap approach).
    """
    global _resnet_model, _resnet_model_checked
    if _resnet_model_checked:
        return _resnet_model
    _resnet_model_checked = True

    try:
        import torch
        import torchvision.models as models
        import torchvision.transforms as transforms

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Use pretrained ResNet50 as feature extractor
        # We use the conv layers up to layer4 to generate spatial feature maps
        model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        model.to(device)
        model.eval()

        _resnet_model = model
        logger.info(f"ResNet50 plate detector loaded on {device}")
        return _resnet_model

    except ImportError:
        logger.warning("PyTorch/torchvision not installed — ResNet50 plate detector disabled")
    except Exception as e:
        logger.warning(f"ResNet50 plate detector load failed: {e}")

    _resnet_model = None
    return None


def _extract_plate_region_heatmap(vehicle_crop: np.ndarray) -> tuple[int, int, int, int] | None:
    """Use ResNet50 feature maps to detect plate-like regions via activation analysis.

    Strategy:
    1. Run vehicle crop through ResNet50 conv layers
    2. Extract feature maps from layer4 (final conv block)
    3. Average feature maps to create a spatial attention heatmap
    4. Find the region with highest activation in the lower portion
       (plates are typically in the lower 40% of vehicles)
    5. Map the heatmap coordinates back to pixel coordinates

    Args:
        vehicle_crop: BGR image of the vehicle.

    Returns:
        (x1, y1, x2, y2) plate region or None.
    """
    model = _get_resnet_plate_model()
    if model is None:
        return None

    try:
        import torch

        h_orig, w_orig = vehicle_crop.shape[:2]
        if h_orig < 30 or w_orig < 30:
            return None

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Preprocess for ResNet50
        resized = cv2.resize(vehicle_crop, (224, 224), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        tensor = rgb.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        tensor = (tensor - mean) / std
        tensor = np.transpose(tensor, (2, 0, 1))
        input_tensor = torch.from_numpy(np.expand_dims(tensor, 0)).to(device)

        # Extract feature maps from ResNet50's layer4
        # We register a forward hook to capture the output
        feature_maps = []

        def hook_fn(module, input, output):
            feature_maps.append(output)

        handle = model.layer4.register_forward_hook(hook_fn)

        with torch.no_grad():
            model(input_tensor)

        handle.remove()

        if not feature_maps:
            return None

        # Average across all channels to get a spatial attention map
        fmap = feature_maps[0]  # Shape: [1, 2048, 7, 7]
        heatmap = torch.mean(fmap, dim=1).squeeze()  # Shape: [7, 7]
        heatmap = heatmap.cpu().numpy()

        # Normalize heatmap to [0, 1]
        heatmap = (heatmap - heatmap.min()) / (heatmap.max() - heatmap.min() + 1e-8)

        # Focus on lower portion of the vehicle (plates are usually in the bottom 40%)
        fh, fw = heatmap.shape
        # Mask out top 50% — plates are rarely in the top half of a vehicle
        weight_mask = np.ones_like(heatmap)
        weight_mask[:fh // 2, :] = 0.2  # Reduce weight of upper half
        weighted_heatmap = heatmap * weight_mask

        # Resize heatmap to original image dimensions
        heatmap_resized = cv2.resize(weighted_heatmap, (w_orig, h_orig),
                                      interpolation=cv2.INTER_LINEAR)

        # Threshold to find plate-like regions
        threshold = 0.5 * heatmap_resized.max()
        binary = (heatmap_resized > threshold).astype(np.uint8) * 255

        # Find contours in the thresholded heatmap
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Find the contour in the lower half with the best plate-like aspect ratio
        best_bbox = None
        best_score = 0.0

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < 20 or h < 10:
                continue

            aspect_ratio = w / max(h, 1)
            area = w * h
            area_ratio = area / (w_orig * h_orig)

            # Plates have aspect ratios typically between 2:1 and 5:1
            # and occupy a small portion of the vehicle
            is_plate_like = (
                1.5 <= aspect_ratio <= 6.0 and
                0.005 <= area_ratio <= 0.15 and
                y > h_orig * 0.3  # Must be in lower 70% of vehicle
            )

            if is_plate_like:
                # Score based on: aspect ratio closeness to 3.5, position in lower half, activation strength
                ar_score = 1.0 - abs(aspect_ratio - 3.5) / 3.5
                pos_score = (y + h / 2) / h_orig  # Higher = lower in image = better
                region_heat = float(np.mean(heatmap_resized[y:y+h, x:x+w]))
                score = ar_score * 0.3 + pos_score * 0.3 + region_heat * 0.4

                if score > best_score:
                    best_score = score
                    # Add small padding
                    pad = 5
                    best_bbox = (
                        max(0, x - pad),
                        max(0, y - pad),
                        min(w_orig, x + w + pad),
                        min(h_orig, y + h + pad),
                    )

        if best_bbox is not None:
            logger.info(f"  ResNet50 plate region: bbox={best_bbox}, score={best_score:.3f}")

        return best_bbox

    except Exception as e:
        logger.warning(f"ResNet50 plate detection error: {e}")
        return None


def detect_plate_resnet(
    vehicle_crop: np.ndarray,
) -> tuple[tuple[int, int, int, int] | None, np.ndarray | None]:
    """Detect the license plate region in a vehicle crop using ResNet50 features.

    This is a fallback detector — use it when the primary YOLO plate detector
    fails to find a plate in the vehicle region.

    Args:
        vehicle_crop: BGR image crop of a detected vehicle.

    Returns:
        (plate_bbox, plate_crop) where plate_bbox is (x1, y1, x2, y2)
        relative to the vehicle crop, or (None, None) if no plate found.
    """
    if vehicle_crop is None or vehicle_crop.size == 0:
        return None, None

    bbox = _extract_plate_region_heatmap(vehicle_crop)
    if bbox is None:
        return None, None

    x1, y1, x2, y2 = bbox
    h, w = vehicle_crop.shape[:2]

    # Validate the detected region
    if x2 - x1 < 15 or y2 - y1 < 8:
        return None, None

    plate_crop = vehicle_crop[y1:y2, x1:x2].copy()
    if plate_crop.size == 0:
        return None, None

    logger.info(f"  ResNet50 plate crop: shape={plate_crop.shape}")
    return (x1, y1, x2, y2), plate_crop


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — ResNet50 Plate Detector Test")
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

        print("\n[2] Running ResNet50 plate detection...")
        plate_bbox, plate_crop = detect_plate_resnet(img)
        if plate_bbox is not None:
            print(f"    Plate found: bbox={plate_bbox}")
            print(f"    Crop shape: {plate_crop.shape}")
            out_path = image_path.parent / f"resnet_plate_{image_path.name}"
            cv2.imwrite(str(out_path), plate_crop)
            print(f"    Saved crop: {out_path}")
        else:
            print("    No plate region detected")
    else:
        print("\n[1] Running synthetic test...")
        test_img = np.ones((480, 640, 3), dtype=np.uint8) * 180
        cv2.rectangle(test_img, (50, 50), (590, 430), (128, 128, 128), -1)
        # Draw a fake plate region
        cv2.rectangle(test_img, (200, 350), (440, 400), (255, 255, 255), -1)
        cv2.putText(test_img, "TS09AB1234", (210, 385),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        plate_bbox, plate_crop = detect_plate_resnet(test_img)
        print(f"    Plate bbox: {plate_bbox}")
        print(f"    Plate crop: {plate_crop.shape if plate_crop is not None else 'None'}")

    print("\n" + "=" * 60)
    print("[✓] ResNet50 plate detector test completed!")
