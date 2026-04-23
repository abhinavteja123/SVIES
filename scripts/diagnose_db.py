"""
SVIES — Diagnose vehicle lookup issues
Run: python scripts/diagnose_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

client = create_client(SUPABASE_URL, SUPABASE_KEY)

TEST_PLATES = ["TN09BT9721", "TN02AV6447"]

print("=" * 60)
print("  SVIES — Supabase DB Diagnostic")
print(f"  URL: {SUPABASE_URL}")
print(f"  Key: {SUPABASE_KEY[:30]}...")
print("=" * 60)

# 1. Check total vehicle count
all_resp = client.table("vehicles").select("plate", count="exact").execute()
print(f"\n[vehicles] Total rows: {all_resp.count}")

# 2. Check first 5 plates stored
sample = client.table("vehicles").select("plate").limit(5).execute()
print(f"[vehicles] Sample plates in DB: {[r['plate'] for r in sample.data]}")

# 3. Check each test plate
print()
for plate in TEST_PLATES:
    plate_upper = plate.upper().strip()

    # Exact match
    r_eq = client.table("vehicles").select("*").eq("plate", plate_upper).limit(1).execute()
    # ilike match
    r_il = client.table("vehicles").select("*").ilike("plate", plate_upper).limit(1).execute()

    print(f"--- Plate: {plate_upper} ---")
    print(f"  eq()    → {r_eq.data}")
    print(f"  ilike() → {r_il.data}")

    # PUCC
    pucc = client.table("pucc").select("*").eq("plate", plate_upper).execute()
    print(f"  pucc    → {pucc.data}")

    # Insurance
    ins = client.table("insurance").select("*").eq("plate", plate_upper).execute()
    print(f"  insurance → {ins.data}")
    print()

print("Done. If eq() returns empty but the vehicle is in the web UI, there's a casing mismatch.")
print("The ilike() fallback in lookup_vehicle() will now handle this automatically.")
