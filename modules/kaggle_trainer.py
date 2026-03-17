"""
SVIES — Kaggle Dataset Trainer
Handles Kaggle dataset integration and custom YOLOv8 training for:
  - Indian license plate detection (dataclusterlabs/indian-number-plates-dataset)
  - Helmet detection (andrewmvd/helmet-detection)

Usage:
    python -m modules.kaggle_trainer
"""

import os
import sys
import shutil
import random
from pathlib import Path

# ── Project paths ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data" / "kaggle"


# ══════════════════════════════════════════════════════════
# 1. Download Plate Dataset from Kaggle
# ══════════════════════════════════════════════════════════

def download_plate_dataset(output_dir: str = "data/kaggle/plates") -> str:
    """Download the Indian Number Plates dataset from Kaggle.

    Uses kagglehub to download 'dataclusterlabs/indian-number-plates-dataset'.
    Organizes data into YOLOv8 format with train/val/test splits and data.yaml.

    Args:
        output_dir: Directory to save the organized dataset (relative to project root).

    Returns:
        Path to the generated data.yaml file.
    """
    try:
        import kagglehub
    except ImportError:
        print("[ERROR] kagglehub package not installed. Run: pip install kagglehub")
        return ""

    output_path = PROJECT_ROOT / output_dir
    yaml_path = output_path / "data.yaml"

    # ── Skip download if already organized ──
    if yaml_path.exists():
        print(f"[INFO] Dataset already organized at: {yaml_path}")
        return str(yaml_path)

    output_path.mkdir(parents=True, exist_ok=True)

    print("[INFO] Downloading Indian Number Plates dataset from Kaggle...")
    try:
        dataset_path = kagglehub.dataset_download(
            "dataclusterlabs/indian-number-plates-dataset"
        )
        print(f"[✓] Dataset downloaded to: {dataset_path}")
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        print("[INFO] Make sure KAGGLE_USERNAME and KAGGLE_KEY are set in your environment.")
        return ""

    # ── Organize into YOLOv8 format ──
    dataset_path = Path(dataset_path)
    organized = _organize_yolo_dataset(dataset_path, output_path)

    if organized:
        print(f"[✓] Dataset organized at: {yaml_path}")
        return str(yaml_path)
    else:
        print("[ERROR] Failed to organize dataset into YOLOv8 format.")
        return ""


def _organize_yolo_dataset(source_dir: Path, output_dir: Path,
                           train_ratio: float = 0.7,
                           val_ratio: float = 0.2) -> bool:
    """Organize raw Kaggle dataset into YOLOv8 directory structure.

    Creates:
        output_dir/
            train/images/ , train/labels/
            valid/images/ , valid/labels/
            test/images/  , test/labels/
            data.yaml

    Args:
        source_dir: Path to the raw downloaded dataset.
        output_dir: Path to the organized output directory.
        train_ratio: Fraction for training split.
        val_ratio: Fraction for validation split.

    Returns:
        True if successful, False otherwise.
    """
    # ── Find all image files ──
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    all_images = []
    for ext in image_exts:
        all_images.extend(source_dir.rglob(f"*{ext}"))

    if not all_images:
        print(f"[ERROR] No images found in {source_dir}")
        return False

    print(f"[INFO] Found {len(all_images)} images in dataset")

    # ── Find corresponding label files ──
    paired = []
    for img_path in all_images:
        # Look for .txt label file with same stem
        label_candidates = [
            img_path.with_suffix(".txt"),
            img_path.parent / "labels" / (img_path.stem + ".txt"),
            img_path.parent.parent / "labels" / (img_path.stem + ".txt"),
        ]
        label_path = None
        for candidate in label_candidates:
            if candidate.exists():
                label_path = candidate
                break

        if label_path:
            paired.append((img_path, label_path))

    if not paired:
        print(f"[WARNING] No label files found. Creating dataset with images only.")
        # Use images without labels — user can annotate later
        paired = [(img, None) for img in all_images]
    else:
        print(f"[INFO] Found {len(paired)} image-label pairs")

    # ── Shuffle and split ──
    random.seed(42)
    random.shuffle(paired)

    n = len(paired)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    splits = {
        "train": paired[:n_train],
        "valid": paired[n_train:n_train + n_val],
        "test": paired[n_train + n_val:],
    }

    # ── Copy files into splits ──
    for split_name, split_data in splits.items():
        img_dir = output_dir / split_name / "images"
        lbl_dir = output_dir / split_name / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_path, label_path in split_data:
            shutil.copy2(str(img_path), str(img_dir / img_path.name))
            if label_path:
                shutil.copy2(str(label_path), str(lbl_dir / label_path.name))

        print(f"  {split_name}: {len(split_data)} images")

    # ── Create data.yaml ──
    yaml_content = f"""# SVIES — Indian Number Plates Dataset (Kaggle)
# Source: dataclusterlabs/indian-number-plates-dataset

names:
- number_plate
nc: 1
train: {output_dir / 'train' / 'images'}
val: {output_dir / 'valid' / 'images'}
test: {output_dir / 'test' / 'images'}
"""
    yaml_path = output_dir / "data.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    return True


# ══════════════════════════════════════════════════════════
# 2. Download Helmet Dataset from Kaggle
# ══════════════════════════════════════════════════════════

def download_helmet_dataset(output_dir: str = "data/kaggle/helmets") -> str:
    """Download a helmet detection dataset from Kaggle.

    Uses kagglehub to download 'andrewmvd/helmet-detection'.
    Organizes into YOLOv8 format.

    Args:
        output_dir: Directory to save the organized dataset (relative to project root).

    Returns:
        Path to the generated data.yaml file.
    """
    try:
        import kagglehub
    except ImportError:
        print("[ERROR] kagglehub package not installed. Run: pip install kagglehub")
        return ""

    output_path = PROJECT_ROOT / output_dir
    yaml_path = output_path / "data.yaml"

    if yaml_path.exists():
        print(f"[INFO] Helmet dataset already organized at: {yaml_path}")
        return str(yaml_path)

    output_path.mkdir(parents=True, exist_ok=True)

    print("[INFO] Downloading Helmet Detection dataset from Kaggle...")
    try:
        dataset_path = kagglehub.dataset_download("andrewmvd/helmet-detection")
        print(f"[✓] Helmet dataset downloaded to: {dataset_path}")
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        print("[INFO] Make sure KAGGLE_USERNAME and KAGGLE_KEY are set in your environment.")
        return ""

    dataset_path = Path(dataset_path)

    # ── Convert VOC XML annotations to YOLO format ──
    _convert_voc_to_yolo_helmet(dataset_path, output_path)

    if yaml_path.exists():
        print(f"[✓] Helmet dataset organized at: {yaml_path}")
        return str(yaml_path)
    else:
        print("[ERROR] Failed to organize helmet dataset.")
        return ""


def _convert_voc_to_yolo_helmet(source_dir: Path, output_dir: Path) -> bool:
    """Convert helmet detection dataset (VOC XML format) to YOLO format.

    The andrewmvd/helmet-detection dataset uses Pascal VOC XML annotations.
    Classes: helmet, head, person → mapped to: helmet (0), no_helmet (1)
    """
    import xml.etree.ElementTree as ET

    # ── Find annotation files ──
    xml_files = list(source_dir.rglob("*.xml"))
    image_exts = {".jpg", ".jpeg", ".png", ".bmp"}

    if not xml_files:
        print("[WARNING] No XML annotations found. Trying YOLO format...")
        return _organize_yolo_dataset(source_dir, output_dir)

    print(f"[INFO] Found {len(xml_files)} XML annotation files")

    # ── Class mapping ──
    class_map = {
        "helmet": 0, "with_helmet": 0, "With Helmet": 0,
        "head": 1, "without_helmet": 1, "Without Helmet": 1, "no_helmet": 1,
        "person": 2,
    }

    paired = []
    for xml_path in xml_files:
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # ── Find corresponding image ──
            filename = root.findtext("filename", "")
            img_path = None
            for ext in image_exts:
                candidates = [
                    xml_path.parent / filename,
                    xml_path.parent / (xml_path.stem + ext),
                    xml_path.parent.parent / "images" / filename,
                    xml_path.parent.parent / "images" / (xml_path.stem + ext),
                ]
                for c in candidates:
                    if c.exists():
                        img_path = c
                        break
                if img_path:
                    break

            if not img_path:
                continue

            # ── Parse image size ──
            size = root.find("size")
            if size is None:
                continue
            img_w = int(size.findtext("width", "0"))
            img_h = int(size.findtext("height", "0"))
            if img_w == 0 or img_h == 0:
                continue

            # ── Convert bounding boxes ──
            yolo_lines = []
            for obj in root.findall("object"):
                cls_name = obj.findtext("name", "")
                cls_id = class_map.get(cls_name, -1)
                if cls_id == -1:
                    continue

                bndbox = obj.find("bndbox")
                if bndbox is None:
                    continue

                xmin = float(bndbox.findtext("xmin", "0"))
                ymin = float(bndbox.findtext("ymin", "0"))
                xmax = float(bndbox.findtext("xmax", "0"))
                ymax = float(bndbox.findtext("ymax", "0"))

                # ── Convert to YOLO format (normalized) ──
                x_center = ((xmin + xmax) / 2) / img_w
                y_center = ((ymin + ymax) / 2) / img_h
                w = (xmax - xmin) / img_w
                h = (ymax - ymin) / img_h

                yolo_lines.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")

            if yolo_lines:
                paired.append((img_path, yolo_lines))

        except Exception as e:
            print(f"[WARNING] Failed to parse {xml_path}: {e}")
            continue

    if not paired:
        print("[ERROR] No valid image-annotation pairs found")
        return False

    print(f"[INFO] Converted {len(paired)} annotations to YOLO format")

    # ── Split and write ──
    random.seed(42)
    random.shuffle(paired)
    n = len(paired)
    n_train = int(n * 0.7)
    n_val = int(n * 0.2)

    splits = {
        "train": paired[:n_train],
        "valid": paired[n_train:n_train + n_val],
        "test": paired[n_train + n_val:],
    }

    for split_name, split_data in splits.items():
        img_dir = output_dir / split_name / "images"
        lbl_dir = output_dir / split_name / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_path, yolo_lines in split_data:
            shutil.copy2(str(img_path), str(img_dir / img_path.name))
            label_file = lbl_dir / (img_path.stem + ".txt")
            label_file.write_text("\n".join(yolo_lines), encoding="utf-8")

        print(f"  {split_name}: {len(split_data)} images")

    # ── Create data.yaml ──
    yaml_content = f"""# SVIES — Helmet Detection Dataset (Kaggle)
# Source: andrewmvd/helmet-detection

names:
- helmet
- no_helmet
- person
nc: 3
train: {output_dir / 'train' / 'images'}
val: {output_dir / 'valid' / 'images'}
test: {output_dir / 'test' / 'images'}
"""
    yaml_path = output_dir / "data.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    return True


# ══════════════════════════════════════════════════════════
# 3. Train Plate Detector
# ══════════════════════════════════════════════════════════

def train_plate_detector(dataset_yaml: str, epochs: int = 50,
                         imgsz: int = 640, device: str = "cpu") -> str:
    """Fine-tune YOLOv8n on a plate detection dataset.

    Args:
        dataset_yaml: Path to the dataset YAML file.
        epochs: Number of training epochs (default 50).
        imgsz: Image size for training (default 640).
        device: Training device — 'cpu' or 'cuda' (default 'cpu').

    Returns:
        Path to the saved best model weights.
    """
    from ultralytics import YOLO

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = MODELS_DIR / "svies_plate_detector.pt"

    print(f"[INFO] Training plate detector...")
    print(f"  Dataset:  {dataset_yaml}")
    print(f"  Epochs:   {epochs}")
    print(f"  ImgSize:  {imgsz}")
    print(f"  Device:   {device}")

    model = YOLO("yolov8n.pt")
    results = model.train(
        data=dataset_yaml,
        epochs=epochs,
        imgsz=imgsz,
        device=device,
        project=str(MODELS_DIR / "training"),
        name="plate_detector",
        exist_ok=True,
    )

    # ── Copy best weights to models/ ──
    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    if best_pt.exists():
        shutil.copy2(str(best_pt), str(output_path))
        print(f"[✓] Plate detector saved: {output_path}")
    else:
        print("[WARNING] best.pt not found after training.")
        return ""

    return str(output_path)


# ══════════════════════════════════════════════════════════
# 4. Train Helmet Detector
# ══════════════════════════════════════════════════════════

def train_helmet_detector(dataset_yaml: str, epochs: int = 50,
                          imgsz: int = 416, device: str = "cpu") -> str:
    """Fine-tune YOLOv8n on a helmet detection dataset.

    Args:
        dataset_yaml: Path to the dataset YAML file.
        epochs: Number of training epochs (default 50).
        imgsz: Image size for training (default 416).
        device: Training device — 'cpu' or 'cuda' (default 'cpu').

    Returns:
        Path to the saved best model weights.
    """
    from ultralytics import YOLO

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = MODELS_DIR / "svies_helmet_detector.pt"

    print(f"[INFO] Training helmet detector...")
    print(f"  Dataset:  {dataset_yaml}")
    print(f"  Epochs:   {epochs}")
    print(f"  ImgSize:  {imgsz}")
    print(f"  Device:   {device}")

    model = YOLO("yolov8n.pt")
    results = model.train(
        data=dataset_yaml,
        epochs=epochs,
        imgsz=imgsz,
        device=device,
        project=str(MODELS_DIR / "training"),
        name="helmet_detector",
        exist_ok=True,
    )

    # ── Copy best weights to models/ ──
    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    if best_pt.exists():
        shutil.copy2(str(best_pt), str(output_path))
        print(f"[✓] Helmet detector saved: {output_path}")
    else:
        print("[WARNING] best.pt not found after training.")
        return ""

    return str(output_path)


# ══════════════════════════════════════════════════════════
# 5. Validate Model
# ══════════════════════════════════════════════════════════

def validate_model(model_path: str, dataset_yaml: str) -> dict:
    """Run validation on a trained model and return metrics.

    Args:
        model_path: Path to the trained .pt model file.
        dataset_yaml: Path to the dataset YAML file.

    Returns:
        Dict with mAP50, mAP50-95, precision, recall.
    """
    from ultralytics import YOLO

    print(f"[INFO] Validating model: {model_path}")
    model = YOLO(model_path)
    results = model.val(data=dataset_yaml)

    metrics = {
        "mAP50": round(float(results.box.map50), 4),
        "mAP50_95": round(float(results.box.map), 4),
        "precision": round(float(results.box.mp), 4),
        "recall": round(float(results.box.mr), 4),
    }

    print("\n" + "=" * 50)
    print("Validation Results")
    print("=" * 50)
    print(f"  {'Metric':<15} {'Value':>10}")
    print(f"  {'-' * 25}")
    for k, v in metrics.items():
        print(f"  {k:<15} {v:>10.4f}")
    print("=" * 50)

    return metrics


# ══════════════════════════════════════════════════════════
# 6. Load Custom Plate Model
# ══════════════════════════════════════════════════════════

def load_custom_plate_model():
    """Load the custom plate detector model if it exists.

    Returns:
        YOLO model object, or None if not available.
        Falls back to yolov8n.pt if custom model not found.
    """
    from ultralytics import YOLO

    custom_path = MODELS_DIR / "svies_plate_detector.pt"
    if custom_path.exists():
        print(f"[INFO] Loading custom plate detector: {custom_path}")
        return YOLO(str(custom_path))

    fallback = MODELS_DIR / "yolov8n.pt"
    if fallback.exists():
        print(f"[INFO] Custom plate model not found. Using fallback: {fallback}")
        return YOLO(str(fallback))

    print("[INFO] Custom plate model not found. Using default yolov8n.pt")
    return YOLO("yolov8n.pt")


# ══════════════════════════════════════════════════════════
# 7. Load Custom Helmet Model
# ══════════════════════════════════════════════════════════

def load_custom_helmet_model():
    """Load the custom helmet detector model if it exists.

    Returns:
        YOLO model object, or None if not available.
        Falls back to yolov8n-pose.pt if custom model not found.
    """
    from ultralytics import YOLO

    custom_path = MODELS_DIR / "svies_helmet_detector.pt"
    if custom_path.exists():
        print(f"[INFO] Loading custom helmet detector: {custom_path}")
        return YOLO(str(custom_path))

    fallback = MODELS_DIR / "yolov8n-pose.pt"
    if fallback.exists():
        print(f"[INFO] Custom helmet model not found. Using fallback: {fallback}")
        return YOLO(str(fallback))

    print("[INFO] Custom helmet model not found. Using default yolov8n-pose.pt")
    return YOLO("yolov8n-pose.pt")


# ══════════════════════════════════════════════════════════
# Test Block
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Kaggle Custom Model Trainer")
    print("=" * 60)

    # ── Check for Kaggle credentials ──
    kaggle_user = os.getenv("KAGGLE_USERNAME", "")
    kaggle_key = os.getenv("KAGGLE_KEY", "")

    print(f"\n  MODELS_DIR:       {MODELS_DIR}")
    print(f"  DATA_DIR:         {DATA_DIR}")
    print(f"  KAGGLE_USERNAME:  {'✅ Set' if kaggle_user else '❌ Not set'}")
    print(f"  KAGGLE_KEY:       {'✅ Set' if kaggle_key else '❌ Not set'}")

    # ── Check existing models ──
    plate_model = MODELS_DIR / "svies_plate_detector.pt"
    helmet_model = MODELS_DIR / "svies_helmet_detector.pt"

    print(f"\n  Plate Model:  {'✅ ' + str(plate_model) if plate_model.exists() else '❌ Not trained yet'}")
    print(f"  Helmet Model: {'✅ ' + str(helmet_model) if helmet_model.exists() else '❌ Not trained yet'}")

    # ── Training instructions ──
    if not plate_model.exists() or not helmet_model.exists():
        print("\n" + "-" * 60)
        print("TRAINING INSTRUCTIONS")
        print("-" * 60)
        print("""
  1. Set your Kaggle credentials in .env:
     KAGGLE_USERNAME=your_username
     KAGGLE_KEY=your_api_key

  2. Get your API key from:
     https://www.kaggle.com/settings → API → Create New Token

  3. Run this script interactively to download and train:

     >>> from modules.kaggle_trainer import *

     # Download plate detection dataset
     >>> yaml_path = download_plate_dataset()

     # Train plate detector
     >>> train_plate_detector(yaml_path, epochs=50, device="cpu")

     # Download helmet detection dataset
     >>> yaml_path = download_helmet_dataset()

     # Train helmet detector
     >>> train_helmet_detector(yaml_path, epochs=50, device="cpu")

  4. After training, the models will be saved to:
     - models/svies_plate_detector.pt
     - models/svies_helmet_detector.pt

  5. detector.py and helmet_detector.py will automatically
     use these custom models when they exist.

  TIP: For faster training, use the Colab notebook:
       scripts/SVIES_Model_Training.ipynb
""")

    print("=" * 60)
    print("[✓] Kaggle trainer module loaded successfully!")
