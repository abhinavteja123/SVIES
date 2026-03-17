"""
SVIES — Run Model Training (Indian Roads)
Trains 3 models specifically for Indian road conditions:
  1. Indian License Plate Detector (Roboflow dataset)
  2. Helmet Detector (Roboflow dataset)
  3. Indian Vehicle Detector (auto-rickshaws, tempos, scooters, etc.)
"""
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import config


def train(name, data_yaml, output_name, epochs=25, imgsz=640):
    from ultralytics import YOLO
    models_dir = PROJECT_ROOT / "models"
    models_dir.mkdir(exist_ok=True)
    out = models_dir / output_name

    print(f"\n  Training: {name}")
    print(f"  Data:     {data_yaml}")
    print(f"  Epochs:   {epochs} | ImgSize: {imgsz} | Device: cpu")

    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(data_yaml),
        epochs=epochs, imgsz=imgsz, device="cpu",
        project=str(models_dir / "training"), name=name,
        exist_ok=True, patience=10, batch=8, workers=2, verbose=True,
    )

    best = Path(results.save_dir) / "weights" / "best.pt"
    last = Path(results.save_dir) / "weights" / "last.pt"
    src = best if best.exists() else (last if last.exists() else None)
    if src:
        shutil.copy2(str(src), str(out))
        print(f"  [OK] Saved: {out} ({out.stat().st_size / 1048576:.1f} MB)")
        return True
    print("  [ERROR] No weights file found")
    return False


def main():
    api_key = config.ROBOFLOW_API_KEY
    print("=" * 60)
    print("SVIES — Indian Roads Model Training")
    print("=" * 60)

    # ── 1: Train Plate Detector (already downloaded) ──
    plate_yaml = PROJECT_ROOT / "Vehicle-Registration-Plates-1" / "data.yaml"
    if plate_yaml.exists():
        print("\n[1/3] INDIAN PLATE DETECTOR")
        train("plate_detector", plate_yaml, "svies_plate_detector.pt",
              epochs=25, imgsz=640)
    else:
        print(f"\n[1/3] INDIAN PLATE DETECTOR — SKIP (no data.yaml at {plate_yaml})")

    # ── 2: Download + Train Helmet Detector ──
    print("\n[2/3] HELMET DETECTOR")
    helmet_yaml = None

    # Check if already downloaded
    for candidate in [
        PROJECT_ROOT / "Hard-Hat-Workers-1" / "data.yaml",
        PROJECT_ROOT / "hard-hat-workers-1" / "data.yaml",
    ]:
        if candidate.exists():
            helmet_yaml = candidate
            print(f"  Dataset found: {helmet_yaml}")
            break

    if not helmet_yaml:
        print("  Downloading helmet dataset...")
        try:
            from roboflow import Roboflow
            rf = Roboflow(api_key=api_key)
            proj = rf.workspace("dip-zrgjd").project("hard-hat-workers-68ds8")
            ver = proj.version(1)
            ds = ver.download("yolov8")
            dl_path = Path(ds.location)
            yamls = list(dl_path.rglob("data.yaml"))
            if yamls:
                helmet_yaml = yamls[0]
                print(f"  [OK] Downloaded: {helmet_yaml}")
            else:
                print(f"  [ERROR] No data.yaml in {dl_path}")
        except Exception as e:
            print(f"  [ERROR] Download failed: {e}")

    if helmet_yaml and helmet_yaml.exists():
        train("helmet_detector", helmet_yaml, "svies_helmet_detector.pt",
              epochs=25, imgsz=416)
    else:
        print("  [SKIP] No helmet dataset")

    # ── 3: Download + Train Indian Vehicle Detector ──
    print("\n[3/3] INDIAN VEHICLE DETECTOR (autos, tempos, scooters, etc.)")
    indian_vehicle_yaml = None

    # Check if already downloaded
    for candidate in [
        PROJECT_ROOT / "Indian-Vehicles-1" / "data.yaml",
        PROJECT_ROOT / "indian-vehicles-1" / "data.yaml",
        PROJECT_ROOT / "data" / "roboflow" / "indian_vehicles" / "data.yaml",
    ]:
        if candidate.exists():
            indian_vehicle_yaml = candidate
            print(f"  Dataset found: {indian_vehicle_yaml}")
            break

    if not indian_vehicle_yaml:
        print("  Downloading Indian vehicle dataset...")
        try:
            from roboflow import Roboflow
            rf = Roboflow(api_key=api_key)
            proj = rf.workspace("roboflow-universe-projects").project("indian-vehicles-detection")
            ver = proj.version(1)
            dl_dir = PROJECT_ROOT / "data" / "roboflow" / "indian_vehicles"
            dl_dir.mkdir(parents=True, exist_ok=True)
            ds = ver.download("yolov8", location=str(dl_dir))
            dl_path = Path(ds.location)
            yamls = list(dl_path.rglob("data.yaml"))
            if yamls:
                indian_vehicle_yaml = yamls[0]
                print(f"  [OK] Downloaded: {indian_vehicle_yaml}")
            else:
                print(f"  [ERROR] No data.yaml in {dl_path}")
        except Exception as e:
            print(f"  [ERROR] Download failed: {e}")
            print("  [INFO] You can manually download an Indian vehicle dataset from Roboflow")
            print("         and place data.yaml in data/roboflow/indian_vehicles/")

    if indian_vehicle_yaml and indian_vehicle_yaml.exists():
        train("indian_vehicle_detector", indian_vehicle_yaml,
              "svies_vehicle_classifier.pt", epochs=30, imgsz=640)
    else:
        print("  [SKIP] No Indian vehicle dataset")

    # ── Summary ──
    print("\n" + "=" * 60)
    models = PROJECT_ROOT / "models"
    plate_ok = (models / "svies_plate_detector.pt").exists()
    helmet_ok = (models / "svies_helmet_detector.pt").exists()
    indian_vehicle_ok = (models / "svies_vehicle_classifier.pt").exists()
    print(f"  Plate Detector:          {'TRAINED' if plate_ok else 'NOT TRAINED'}")
    print(f"  Helmet Detector:         {'TRAINED' if helmet_ok else 'NOT TRAINED'}")
    print(f"  Indian Vehicle Detector: {'TRAINED' if indian_vehicle_ok else 'NOT TRAINED'}")
    print("=" * 60)
    if plate_ok and helmet_ok:
        print("\n  Models are ready! detector.py and helmet_detector.py")
        print("  will automatically load them on next run.")
    if indian_vehicle_ok:
        print("  Indian vehicle detector will detect autos, tempos, scooters, etc.")


if __name__ == "__main__":
    main()
