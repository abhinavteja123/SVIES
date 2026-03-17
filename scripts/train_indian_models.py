"""
SVIES — Train Models for Indian Roads (Comprehensive)

This script trains all 3 detection models specifically for Indian roads:
  1. Indian License Plate Detector
     - Dataset: Indian vehicle registration plates (Roboflow)
     - Detects: Standard Indian plates (white/yellow, IND hologram)

  2. Helmet Detector
     - Dataset: Helmet/no-helmet classification
     - Purpose: Detect 2-wheeler riders without helmets (MV Act Section 129)

  3. Indian Vehicle Detector
     - Dataset: Indian road vehicles
     - Detects: Auto-rickshaws, tempos, tractors, e-rickshaws, scooters,
                cars, motorcycles, buses, trucks

Datasets are automatically downloaded from Roboflow. Set ROBOFLOW_API_KEY
in your .env file or environment for automatic download.

Usage:
    python scripts/train_indian_models.py
    python scripts/train_indian_models.py --epochs 50 --device cuda
"""

import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import config


def train_model(name: str, data_yaml: Path, output_name: str,
                epochs: int = 25, imgsz: int = 640, device: str = "cpu") -> bool:
    """Train a YOLOv8n model on a dataset."""
    from ultralytics import YOLO

    models_dir = PROJECT_ROOT / "models"
    models_dir.mkdir(exist_ok=True)
    out = models_dir / output_name

    print(f"\n{'─' * 50}")
    print(f"  Training: {name}")
    print(f"  Data:     {data_yaml}")
    print(f"  Output:   {out}")
    print(f"  Epochs:   {epochs} | ImgSize: {imgsz} | Device: {device}")
    print(f"{'─' * 50}")

    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(data_yaml),
        epochs=epochs, imgsz=imgsz, device=device,
        project=str(models_dir / "training"), name=name.replace(" ", "_"),
        exist_ok=True, patience=10, batch=8, workers=2, verbose=True,
    )

    best = Path(results.save_dir) / "weights" / "best.pt"
    last = Path(results.save_dir) / "weights" / "last.pt"
    src = best if best.exists() else (last if last.exists() else None)
    if src:
        shutil.copy2(str(src), str(out))
        size_mb = out.stat().st_size / 1048576
        print(f"  [OK] Saved: {out} ({size_mb:.1f} MB)")
        return True
    print("  [ERROR] No weights file found after training")
    return False


def download_roboflow_dataset(workspace: str, project: str, version: int,
                               output_dir: Path, api_key: str) -> Path | None:
    """Download a dataset from Roboflow."""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("  [ERROR] roboflow not installed. Run: pip install roboflow")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading: {workspace}/{project} v{version}")

    try:
        rf = Roboflow(api_key=api_key)
        proj = rf.workspace(workspace).project(project)
        ds = proj.version(version).download("yolov8", location=str(output_dir))
        dl_path = Path(ds.location)
        yamls = list(dl_path.rglob("data.yaml"))
        if yamls:
            print(f"  [OK] Downloaded: {yamls[0]}")
            return yamls[0]
        print(f"  [ERROR] No data.yaml in {dl_path}")
    except Exception as e:
        print(f"  [ERROR] Download failed: {e}")
    return None


def main():
    parser = argparse.ArgumentParser(description="SVIES Indian Roads Model Training")
    parser.add_argument("--epochs", type=int, default=25, help="Training epochs")
    parser.add_argument("--device", type=str, default="cpu",
                        help="Device: 'cpu' or 'cuda' (GPU)")
    parser.add_argument("--skip-plate", action="store_true", help="Skip plate detector")
    parser.add_argument("--skip-helmet", action="store_true", help="Skip helmet detector")
    parser.add_argument("--skip-vehicle", action="store_true", help="Skip vehicle detector")
    args = parser.parse_args()

    api_key = config.ROBOFLOW_API_KEY
    data_dir = PROJECT_ROOT / "data" / "roboflow"

    print("=" * 60)
    print("  SVIES — Indian Roads Model Training Pipeline")
    print("  Training models optimized for Indian traffic conditions")
    print("=" * 60)

    if not api_key:
        print("\n[WARNING] ROBOFLOW_API_KEY not set in .env")
        print("  Some datasets may need manual download.")
        print("  Set it via: echo ROBOFLOW_API_KEY=your_key >> .env\n")

    results = {}

    # ═══════════════════════════════════════════════════════
    # 1. INDIAN LICENSE PLATE DETECTOR
    # ═══════════════════════════════════════════════════════
    if not args.skip_plate:
        print("\n" + "=" * 60)
        print("  [1/3] INDIAN LICENSE PLATE DETECTOR")
        print("  Detects Indian number plates (white/yellow backgrounds)")
        print("=" * 60)

        plate_yaml = PROJECT_ROOT / "Vehicle-Registration-Plates-1" / "data.yaml"

        if not plate_yaml.exists():
            plate_yaml = download_roboflow_dataset(
                "dip-zrgjd", "vehicle-registration-plates-trudk-14wpm", 1,
                data_dir / "plates", api_key,
            )

        if plate_yaml and plate_yaml.exists():
            results["plate"] = train_model(
                "indian_plate_detector", plate_yaml,
                "svies_plate_detector.pt",
                epochs=args.epochs, imgsz=640, device=args.device,
            )
        else:
            print("  [SKIP] No plate dataset available")
            results["plate"] = False

    # ═══════════════════════════════════════════════════════
    # 2. HELMET DETECTOR
    # ═══════════════════════════════════════════════════════
    if not args.skip_helmet:
        print("\n" + "=" * 60)
        print("  [2/3] HELMET DETECTOR")
        print("  Detects helmet/no-helmet on 2-wheeler riders")
        print("=" * 60)

        helmet_yaml = None
        for candidate in [
            PROJECT_ROOT / "Hard-Hat-Workers-1" / "data.yaml",
            data_dir / "helmets" / "data.yaml",
        ]:
            if candidate.exists():
                helmet_yaml = candidate
                break

        if not helmet_yaml and api_key:
            helmet_yaml = download_roboflow_dataset(
                "dip-zrgjd", "hard-hat-workers-68ds8", 1,
                data_dir / "helmets", api_key,
            )

        if helmet_yaml and helmet_yaml.exists():
            results["helmet"] = train_model(
                "helmet_detector", helmet_yaml,
                "svies_helmet_detector.pt",
                epochs=args.epochs, imgsz=416, device=args.device,
            )
        else:
            print("  [SKIP] No helmet dataset available")
            results["helmet"] = False

    # ═══════════════════════════════════════════════════════
    # 3. INDIAN VEHICLE DETECTOR
    # ═══════════════════════════════════════════════════════
    if not args.skip_vehicle:
        print("\n" + "=" * 60)
        print("  [3/3] INDIAN VEHICLE DETECTOR")
        print("  Detects: Auto-rickshaws, tempos, tractors, e-rickshaws,")
        print("           scooters, cars, motorcycles, buses, trucks")
        print("=" * 60)

        vehicle_yaml = None
        for candidate in [
            data_dir / "indian_vehicles" / "data.yaml",
            PROJECT_ROOT / "Indian-Vehicles-1" / "data.yaml",
        ]:
            if candidate.exists():
                vehicle_yaml = candidate
                break

        if not vehicle_yaml and api_key:
            vehicle_yaml = download_roboflow_dataset(
                "roboflow-universe-projects", "indian-vehicles-detection", 1,
                data_dir / "indian_vehicles", api_key,
            )

        if vehicle_yaml and vehicle_yaml.exists():
            results["vehicle"] = train_model(
                "indian_vehicle_detector", vehicle_yaml,
                "svies_vehicle_classifier.pt",
                epochs=args.epochs + 5, imgsz=640, device=args.device,
            )
        else:
            print("  [SKIP] No Indian vehicle dataset available")
            print("  [INFO] To train manually, download an Indian vehicle dataset")
            print("         with classes: auto, tempo, tractor, e-rickshaw, scooter, etc.")
            print("         Place data.yaml in: data/roboflow/indian_vehicles/")
            results["vehicle"] = False

    # ═══════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  TRAINING SUMMARY — Indian Roads Models")
    print("=" * 60)

    models_dir = PROJECT_ROOT / "models"
    models_status = {
        "Indian Plate Detector": models_dir / "svies_plate_detector.pt",
        "Helmet Detector": models_dir / "svies_helmet_detector.pt",
        "Indian Vehicle Detector": models_dir / "svies_vehicle_classifier.pt",
    }

    all_ok = True
    for name, path in models_status.items():
        exists = path.exists()
        size = f"({path.stat().st_size / 1048576:.1f} MB)" if exists else ""
        status = f"READY {size}" if exists else "NOT TRAINED"
        print(f"  {name:30s} {status}")
        if not exists:
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("\n  All models trained for Indian roads!")
        print("  detector.py and helmet_detector.py will auto-load them.")
        print("  Start the system: python main.py")
    else:
        print("\n  Some models were not trained. The system will use")
        print("  generic YOLOv8n as fallback for missing models.")
    print()


if __name__ == "__main__":
    main()
