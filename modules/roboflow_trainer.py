"""
SVIES — Roboflow Custom Model Trainer
Handles Roboflow dataset integration and custom YOLOv8 training for:
  - Indian license plate detection
  - Helmet detection

Usage:
    python -m modules.roboflow_trainer
"""

import os
import sys
from pathlib import Path

# ── Project paths ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data" / "roboflow"

# ── Default Roboflow dataset configs (India-specific) ──
PLATE_DATASET = {
    "workspace": "dip-zrgjd",
    "project": "vehicle-registration-plates-trudk-14wpm",
    "version": 1,
}

HELMET_DATASET = {
    "workspace": "dip-zrgjd",
    "project": "hard-hat-workers-68ds8",
    "version": 1,
}

FALLBACK_PLATE_DATASET = {
    "workspace": "roboflow-universe-projects",
    "project": "indian-number-plate-detection",
    "version": 5,
}

# ── Indian Vehicle Detection (auto-rickshaws, trucks, buses, etc.) ──
INDIAN_VEHICLE_DATASET = {
    "workspace": "roboflow-universe-projects",
    "project": "indian-vehicles-detection",
    "version": 1,
}


# ══════════════════════════════════════════════════════════
# 1. Download Dataset
# ══════════════════════════════════════════════════════════

def download_dataset(api_key: str, workspace: str, project: str,
                     version: int, output_dir: str = "data/roboflow") -> str:
    """Download a Roboflow dataset in YOLOv8 format.

    Args:
        api_key: Roboflow API key.
        workspace: Roboflow workspace name.
        project: Roboflow project name.
        version: Dataset version number.
        output_dir: Directory to save the dataset (relative to project root).

    Returns:
        Path to the downloaded dataset YAML file.
    """
    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERROR] roboflow package not installed. Run: pip install roboflow")
        return ""

    output_path = PROJECT_ROOT / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Connecting to Roboflow workspace: {workspace}")
    rf = Roboflow(api_key=api_key)
    ws = rf.workspace(workspace)
    proj = ws.project(project)
    ds = proj.version(version)

    print(f"[INFO] Downloading dataset: {project} v{version} → {output_path}")
    dataset = ds.download("yolov8", location=str(output_path))

    yaml_path = output_path / "data.yaml"
    if not yaml_path.exists():
        # Try to find any .yaml file in the output directory
        yaml_files = list(output_path.glob("*.yaml"))
        if yaml_files:
            yaml_path = yaml_files[0]
        else:
            print("[WARNING] No YAML file found in downloaded dataset.")
            return str(output_path)

    print(f"[✓] Dataset downloaded: {yaml_path}")
    return str(yaml_path)


# ══════════════════════════════════════════════════════════
# 2. Train Plate Detector
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
        import shutil
        shutil.copy2(str(best_pt), str(output_path))
        print(f"[✓] Plate detector saved: {output_path}")
    else:
        print("[WARNING] best.pt not found after training.")
        return ""

    return str(output_path)


# ══════════════════════════════════════════════════════════
# 3. Train Helmet Detector
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
        import shutil
        shutil.copy2(str(best_pt), str(output_path))
        print(f"[✓] Helmet detector saved: {output_path}")
    else:
        print("[WARNING] best.pt not found after training.")
        return ""

    return str(output_path)


# ══════════════════════════════════════════════════════════
# 4. Train Indian Vehicle Detector
# ══════════════════════════════════════════════════════════

def train_indian_vehicle_detector(dataset_yaml: str, epochs: int = 50,
                                  imgsz: int = 640, device: str = "cpu") -> str:
    """Fine-tune YOLOv8n on an Indian vehicle detection dataset.

    Detects India-specific vehicle types: auto-rickshaws, tempos,
    tractors, e-rickshaws, scooters, along with standard types.

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
    output_path = MODELS_DIR / "svies_vehicle_classifier.pt"

    print(f"[INFO] Training Indian vehicle detector...")
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
        name="indian_vehicle_detector",
        exist_ok=True,
    )

    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    if best_pt.exists():
        import shutil
        shutil.copy2(str(best_pt), str(output_path))
        print(f"[OK] Indian vehicle detector saved: {output_path}")
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
# 5. Load Custom Plate Model
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
# 6. Load Custom Helmet Model
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
    print("SVIES — Roboflow Custom Model Trainer")
    print("=" * 60)

    # ── Check for API key ──
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("ROBOFLOW_API_KEY", "")

    print(f"\n  MODELS_DIR:       {MODELS_DIR}")
    print(f"  DATA_DIR:         {DATA_DIR}")
    print(f"  ROBOFLOW_API_KEY: {'✅ Set' if api_key and api_key != 'your_roboflow_api_key_here' else '❌ Not set'}")

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
  1. Set your Roboflow API key in .env:
     ROBOFLOW_API_KEY=rf_xxxxxxx

  2. Get your API key from:
     https://app.roboflow.com → Profile → Settings → API Keys

  3. Run this script interactively to download and train:

     >>> from modules.roboflow_trainer import *
     >>> api_key = "rf_your_key_here"

     # Download plate detection dataset
     >>> yaml_path = download_dataset(
     ...     api_key=api_key,
     ...     workspace="augmented-startups",
     ...     project="vehicle-registration-plates-trudk",
     ...     version=1
     ... )

     # Train plate detector
     >>> train_plate_detector(yaml_path, epochs=50, device="cpu")

     # Download helmet detection dataset
     >>> yaml_path = download_dataset(
     ...     api_key=api_key,
     ...     workspace="helmet-detection-rqdos",
     ...     project="helmet-detection-v3",
     ...     version=1
     ... )

     # Train helmet detector
     >>> train_helmet_detector(yaml_path, epochs=50, device="cpu")

  4. After training, the models will be saved to:
     - models/svies_plate_detector.pt
     - models/svies_helmet_detector.pt

  5. detector.py and helmet_detector.py will automatically
     use these custom models when they exist.
""")

    print("=" * 60)
    print("[✓] Roboflow trainer module loaded successfully!")
