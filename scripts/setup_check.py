"""
SVIES — Setup Checker
Verifies all dependencies and configuration are in place.

Usage:
    python scripts/setup_check.py
"""

import importlib
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, fix: str = ""):
    """Record a check result."""
    results.append((name, condition, fix))
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}")
    if not condition and fix:
        print(f"     Fix: {fix}")


def main():
    print("=" * 60)
    print("SVIES — Setup Checker")
    print("=" * 60)

    # ── 1. Python version ──
    print("\n[1] Python Version")
    py_ver = sys.version_info
    check(
        f"Python >= 3.10 (found {py_ver.major}.{py_ver.minor}.{py_ver.micro})",
        py_ver >= (3, 10),
        "Install Python 3.10+: https://www.python.org/downloads/"
    )

    # ── 2. Required packages ──
    print("\n[2] Required Packages")
    req_file = PROJECT_ROOT / "requirements.txt"
    if req_file.exists():
        packages = []
        for line in req_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # Extract package name (before >= or == etc.)
                pkg = line.split(">=")[0].split("==")[0].split("[")[0].strip()
                packages.append(pkg)

        # Map pip names to import names
        import_map = {
            "opencv-python": "cv2",
            "python-dotenv": "dotenv",
            "python-multipart": "multipart",
            "uvicorn": "uvicorn",
            "pillow": "PIL",
            "pytesseract": "pytesseract",
            "torch": "torch",
            "torchvision": "torchvision",
        }

        for pkg in packages:
            import_name = import_map.get(pkg, pkg.replace("-", "_"))
            try:
                importlib.import_module(import_name)
                check(f"{pkg}", True)
            except ImportError:
                check(f"{pkg}", False, f"pip install {pkg}")
    else:
        check("requirements.txt exists", False, "File not found at project root")

    # ── 3. Tesseract OCR ──
    print("\n[3] Tesseract OCR")
    tess_path = shutil.which("tesseract")
    check(
        f"Tesseract in PATH {'(' + tess_path + ')' if tess_path else ''}",
        tess_path is not None,
        "Install Tesseract: https://github.com/tesseract-ocr/tesseract\n"
        "         Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
        "         Add to PATH after installation"
    )

    # ── 4. .env file ──
    print("\n[4] Environment Configuration")
    env_path = PROJECT_ROOT / ".env"
    check(
        ".env file exists",
        env_path.exists(),
        f"Create .env file at {env_path}"
    )

    if env_path.exists():
        env_content = env_path.read_text(encoding="utf-8", errors="ignore")
        required_keys = [
            "TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM",
            "GMAIL_USER", "GMAIL_PASSWORD",
            "POLICE_EMAIL", "POLICE_PHONE",
            "ROBOFLOW_API_KEY",
        ]
        for key in required_keys:
            has_key = key in env_content
            check(f"  {key} defined", has_key, f"Add {key}=... to .env")

    # ── 5. Models directory ──
    print("\n[5] Models Directory")
    models_dir = PROJECT_ROOT / "models"
    check(
        "models/ directory exists",
        models_dir.exists(),
        f"mkdir {models_dir}"
    )

    if models_dir.exists():
        model_files = list(models_dir.glob("*.pt"))
        if model_files:
            for mf in model_files:
                size_mb = mf.stat().st_size / (1024 * 1024)
                check(f"  {mf.name} ({size_mb:.1f} MB)", True)
        else:
            check(
                "  Model weights (.pt files)",
                False,
                "Download yolov8n.pt or train custom models using roboflow_trainer.py"
            )

    # ── 6. Mock DB files ──
    print("\n[6] Mock Database Files")
    mock_db = PROJECT_ROOT / "data" / "mock_db"
    required_jsons = ["vahan.json", "stolen.json", "pucc.json", "insurance.json"]
    for jf in required_jsons:
        fp = mock_db / jf
        check(
            f"data/mock_db/{jf}",
            fp.exists(),
            f"Create {fp} with sample data"
        )

    # ── 7. Geozones ──
    print("\n[7] Geozones")
    zones_file = PROJECT_ROOT / "data" / "geozones" / "zones.json"
    check(
        "data/geozones/zones.json",
        zones_file.exists(),
        f"Create {zones_file} with zone polygons"
    )

    # ── Summary ──
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed")

    if passed == total:
        print("[OK] All checks passed! SVIES is ready to run.")
    else:
        failed = [(name, fix) for name, ok, fix in results if not ok]
        print(f"\n{len(failed)} issue(s) found:")
        for name, fix in failed:
            print(f"  [FAIL] {name}")
            if fix:
                print(f"     -> {fix}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
