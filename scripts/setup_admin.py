"""
SVIES — One-time Admin Setup Script
Creates mariyalaabhinavteja@gmail.com as ADMIN in Firebase.
Run once: python scripts/setup_admin.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

ADMIN_EMAIL    = "mariyalaabhinavteja@gmail.com"
ADMIN_PASSWORD = "abhinavteja12"
ADMIN_DISPLAY  = "SVIES Administrator"
SERVICE_ACCOUNT = PROJECT_ROOT / "data" / "firebase-service-account.json"

def main():
    print("=" * 55)
    print("  SVIES — Admin Account Setup")
    print("=" * 55)

    if not SERVICE_ACCOUNT.exists():
        print(f"[ERROR] Service account not found: {SERVICE_ACCOUNT}")
        sys.exit(1)

    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth, credentials
    except ImportError:
        print("[ERROR] firebase-admin not installed.")
        print("        Run: pip install firebase-admin")
        sys.exit(1)

    # Initialise Firebase Admin SDK
    if not firebase_admin._apps:
        cred = credentials.Certificate(str(SERVICE_ACCOUNT))
        firebase_admin.initialize_app(cred)
    print(f"[OK] Firebase Admin SDK initialised")

    # ── Try to get existing user ──
    existing_user = None
    try:
        existing_user = firebase_auth.get_user_by_email(ADMIN_EMAIL)
        print(f"[OK] Found existing user: {ADMIN_EMAIL} (UID: {existing_user.uid})")
    except firebase_auth.UserNotFoundError:
        print(f"[INFO] User not found — creating {ADMIN_EMAIL} ...")

    # ── Create user if not exists ──
    if existing_user is None:
        try:
            existing_user = firebase_auth.create_user(
                email=ADMIN_EMAIL,
                password=ADMIN_PASSWORD,
                display_name=ADMIN_DISPLAY,
            )
            print(f"[OK] Created user: {ADMIN_EMAIL} (UID: {existing_user.uid})")
        except Exception as e:
            print(f"[ERROR] Failed to create user: {e}")
            sys.exit(1)

    uid = existing_user.uid

    # ── Check current role ──
    current_claims = existing_user.custom_claims or {}
    current_role   = current_claims.get("role", "none")
    print(f"[INFO] Current role: {current_role}")

    # ── Set ADMIN role ──
    try:
        firebase_auth.set_custom_user_claims(uid, {"role": "ADMIN"})
        print(f"[OK] Role set to ADMIN for {ADMIN_EMAIL}")
    except Exception as e:
        print(f"[ERROR] Failed to set role: {e}")
        sys.exit(1)

    # ── Verify ──
    updated = firebase_auth.get_user(uid)
    final_role = (updated.custom_claims or {}).get("role", "none")

    print()
    print("=" * 55)
    print("  Setup Complete!")
    print(f"  Email    : {ADMIN_EMAIL}")
    print(f"  Password : abhinavteja12")
    print(f"  UID      : {uid}")
    print(f"  Role     : {final_role}")
    print("=" * 55)
    print()
    print("[NEXT] Go to the login page and sign in with:")
    print(f"       {ADMIN_EMAIL} / abhinavteja12")
    print("[NEXT] After login you can create other users from the")
    print("       User Management page in the dashboard.")

if __name__ == "__main__":
    main()
