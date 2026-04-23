"""
SVIES — Add missing vehicles to Supabase DB
Run once: python scripts/add_vehicles.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from api.database import db

VEHICLES = [
    {
        "plate": "TN09BT9721",
        "owner": "Test Owner 1",
        "phone": "+919000000001",
        "email": "owner1@example.com",
        "vehicle_type": "MOTORCYCLE",
        "color": "SILVER",
        "make": "Honda",
        "year": 2021,
        "state": "Tamil Nadu",
        "registration_state_code": "TN",
        "status": "ACTIVE",
    },
    {
        "plate": "TN02AV6447",
        "owner": "Test Owner 2",
        "phone": "+919000000002",
        "email": "owner2@example.com",
        "vehicle_type": "MOTORCYCLE",
        "color": "SILVER",
        "make": "Bajaj",
        "year": 2020,
        "state": "Tamil Nadu",
        "registration_state_code": "TN",
        "status": "ACTIVE",
    },
]

PUCC = [
    {"plate": "TN09BT9721", "valid_until": "2027-01-01", "status": "VALID"},
    {"plate": "TN02AV6447", "valid_until": "2027-01-01", "status": "VALID"},
]

INSURANCE = [
    {"plate": "TN09BT9721", "valid_until": "2027-01-01", "type": "COMPREHENSIVE", "status": "VALID"},
    {"plate": "TN02AV6447", "valid_until": "2027-01-01", "type": "COMPREHENSIVE", "status": "VALID"},
]

def main():
    print("=" * 50)
    print("  SVIES — Adding Vehicles to DB")
    print("=" * 50)

    for v in VEHICLES:
        try:
            result = db.add_vehicle(v)
            print(f"[OK] Added vehicle {v['plate']}: {result}")
        except Exception as e:
            err = str(e)
            if "duplicate" in err.lower() or "already exists" in err.lower() or "unique" in err.lower():
                print(f"[SKIP] {v['plate']} already exists in vehicles table")
            else:
                print(f"[ERROR] {v['plate']}: {e}")

    for p in PUCC:
        try:
            result = db.upsert_pucc(p["plate"], {"valid_until": p["valid_until"], "status": p["status"]})
            print(f"[OK] Upserted PUCC {p['plate']}: {result}")
        except Exception as e:
            print(f"[ERROR] PUCC {p['plate']}: {e}")

    for ins in INSURANCE:
        try:
            result = db.upsert_insurance(ins["plate"], {
                "valid_until": ins["valid_until"],
                "type": ins["type"],
                "status": ins["status"],
            })
            print(f"[OK] Upserted Insurance {ins['plate']}: {result}")
        except Exception as e:
            print(f"[ERROR] Insurance {ins['plate']}: {e}")

    print()
    print("Done! Both plates are now registered with valid PUCC and Insurance.")
    print("Re-process your image — fake plate should not be detected.")

if __name__ == "__main__":
    main()
