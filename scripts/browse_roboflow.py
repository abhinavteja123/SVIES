"""
SVIES — Roboflow Dataset Browser
Utility script for team members to browse and download
SVIES-relevant datasets from Roboflow Universe.

Usage:
    python scripts/browse_roboflow.py
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Search queries for SVIES-relevant datasets ──
SEARCH_QUERIES = [
    "indian number plate",
    "helmet detection",
    "indian vehicle",
]


def get_api_key() -> str:
    """Get Roboflow API key from .env or prompt user."""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("ROBOFLOW_API_KEY", "")
    if not api_key or api_key == "your_roboflow_api_key_here":
        api_key = input("Enter your Roboflow API key: ").strip()
    return api_key


def browse_datasets(api_key: str):
    """List all public SVIES-relevant datasets from Roboflow Universe."""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERROR] roboflow package not installed. Run: pip install roboflow")
        return []

    rf = Roboflow(api_key=api_key)
    all_datasets = []

    for query in SEARCH_QUERIES:
        print(f"\n{'─' * 50}")
        print(f"Searching: \"{query}\"")
        print(f"{'─' * 50}")

        try:
            results = rf.search(query)
            if not results:
                print(f"  No datasets found for \"{query}\"")
                continue

            for i, ds in enumerate(results[:5]):  # Top 5 per query
                name = getattr(ds, 'id', str(ds))
                image_count = getattr(ds, 'images', 'N/A')
                classes = getattr(ds, 'classes', {})
                class_names = list(classes.keys()) if isinstance(classes, dict) else []

                dataset_info = {
                    "name": name,
                    "images": image_count,
                    "classes": class_names,
                    "query": query,
                    "dataset": ds,
                }
                all_datasets.append(dataset_info)

                print(f"\n  [{len(all_datasets)}] {name}")
                print(f"      Images:  {image_count}")
                if class_names:
                    print(f"      Classes: {', '.join(class_names[:10])}")
                print(f"      Link:    https://universe.roboflow.com/{name}")

        except Exception as e:
            print(f"  [WARNING] Search failed for \"{query}\": {e}")

    return all_datasets


def download_selected(api_key: str, all_datasets: list):
    """Let user pick a dataset by number and auto-download it."""
    if not all_datasets:
        print("\nNo datasets available to download.")
        return

    print(f"\n{'=' * 50}")
    choice = input(f"Enter dataset number to download (1-{len(all_datasets)}) or 'q' to quit: ").strip()

    if choice.lower() == 'q':
        print("Exiting.")
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(all_datasets):
            print(f"[ERROR] Invalid selection. Choose 1-{len(all_datasets)}")
            return
    except ValueError:
        print("[ERROR] Please enter a number.")
        return

    selected = all_datasets[idx]
    print(f"\n[INFO] Downloading: {selected['name']}")

    output_dir = PROJECT_ROOT / "data" / "roboflow" / selected['name'].replace("/", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        ds = selected['dataset']
        if hasattr(ds, 'download'):
            ds.download("yolov8", location=str(output_dir))
            print(f"[✓] Downloaded to: {output_dir}")
        else:
            print("[INFO] This dataset does not support direct download.")
            print(f"[INFO] Visit: https://universe.roboflow.com/{selected['name']}")
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        print(f"[INFO] Try downloading manually from: https://universe.roboflow.com/{selected['name']}")


if __name__ == "__main__":
    print("=" * 60)
    print("SVIES — Roboflow Dataset Browser")
    print("=" * 60)

    api_key = get_api_key()
    if not api_key:
        print("[ERROR] No API key provided. Exiting.")
        sys.exit(1)

    datasets = browse_datasets(api_key)

    if datasets:
        download_selected(api_key, datasets)
    else:
        print("\nNo datasets found. Check your API key and try again.")

    print("\n[✓] Dataset browser finished!")
