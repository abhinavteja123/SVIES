"""
SVIES -- Firebase Authentication Middleware
Provides JWT-based auth via Firebase Admin SDK with role-based access control.

Role Hierarchy (highest to lowest):
    ADMIN > POLICE > RTO > VIEWER

Usage:
    from api.auth import get_current_user, require_admin, require_police

    @app.get("/api/admin-only")
    async def admin_route(user=Depends(require_admin)):
        return {"message": f"Hello {user['email']}"}

If the Firebase service account JSON is not found on disk, the module falls
back to "no-auth" mode: every request is treated as an ADMIN user.  This
lets developers run the backend locally without setting up Firebase.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

logger = logging.getLogger("svies.auth")

# ── Resolve project root (api/ is one level below root) ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ══════════════════════════════════════════════════════════
# Firebase Admin SDK Initialization
# ══════════════════════════════════════════════════════════

_firebase_app = None
_NO_AUTH_MODE = False

_SERVICE_ACCOUNT_PATH = PROJECT_ROOT / "data" / "firebase-service-account.json"

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials

    if _SERVICE_ACCOUNT_PATH.exists():
        _cred = credentials.Certificate(str(_SERVICE_ACCOUNT_PATH))
        # Only initialise once (guard against double-init on hot reload)
        if not firebase_admin._apps:
            _firebase_app = firebase_admin.initialize_app(_cred)
        else:
            _firebase_app = firebase_admin.get_app()
        logger.info(f"Firebase Admin SDK initialised from {_SERVICE_ACCOUNT_PATH}")
    else:
        _NO_AUTH_MODE = True
        logger.warning(
            f"Service account not found at {_SERVICE_ACCOUNT_PATH} — "
            f"Running in NO-AUTH mode (all requests pass as mock admin)."
        )
except ImportError:
    _NO_AUTH_MODE = True
    firebase_auth = None  # type: ignore[assignment]
    logger.warning(
        "firebase-admin package is not installed — "
        "Running in NO-AUTH mode (all requests pass as mock admin)."
    )

# ══════════════════════════════════════════════════════════
# Role Hierarchy
# ══════════════════════════════════════════════════════════

ROLE_HIERARCHY: dict[str, int] = {
    "VIEWER": 0,
    "RTO":    1,
    "POLICE": 2,
    "ADMIN":  3,
}

_MOCK_ADMIN_USER: dict = {
    "uid": "dev-mock-uid",
    "email": "admin@svies.dev",
    "role": "ADMIN",
}


def _role_level(role: str) -> int:
    """Return the numeric privilege level for a role string."""
    return ROLE_HIERARCHY.get(role.upper(), -1)


# ══════════════════════════════════════════════════════════
# FastAPI Dependency -- Current User
# ══════════════════════════════════════════════════════════

async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> dict:
    """Extract and verify the Firebase JWT from the ``Authorization`` header.

    Returns a dict with at least ``uid``, ``email``, and ``role`` keys.

    In *no-auth* mode (service account missing or firebase-admin not
    installed), a mock admin user is returned for every request so that
    the development server remains fully functional without Firebase.
    """

    # -- No-auth development bypass --
    if _NO_AUTH_MODE:
        return _MOCK_ADMIN_USER.copy()

    # -- Token presence --
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # -- Verify with Firebase --
    try:
        decoded = firebase_auth.verify_id_token(token, check_revoked=False)
    except firebase_auth.ExpiredIdTokenError:
        logger.warning("Auth: Token expired for request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.RevokedIdTokenError:
        logger.warning("Auth: Token revoked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.InvalidIdTokenError as exc:
        logger.warning("Auth: Invalid token — %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token. Please provide a valid Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.error("Auth: Token verification failed — %s: %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -- Build user dict --
    # Custom claims can carry a ``role`` field set via Firebase Admin SDK.
    # Fall back to VIEWER if no role claim is present.
    role = decoded.get("role", "VIEWER").upper()
    if role not in ROLE_HIERARCHY:
        role = "VIEWER"

    return {
        "uid": decoded["uid"],
        "email": decoded.get("email", ""),
        "role": role,
    }


# ══════════════════════════════════════════════════════════
# FastAPI Dependency -- Role Gate
# ══════════════════════════════════════════════════════════

def require_role(minimum_role: str):
    """Return a FastAPI dependency that enforces a minimum role level.

    Example::

        @app.get("/api/police-data")
        async def police_data(user=Depends(require_role("POLICE"))):
            ...

    The dependency first resolves the current user (which handles token
    verification), then checks whether the user's role meets or exceeds
    the required minimum according to ``ROLE_HIERARCHY``.
    """

    minimum_level = _role_level(minimum_role)
    if minimum_level < 0:
        raise ValueError(
            f"Unknown role '{minimum_role}'. "
            f"Valid roles: {', '.join(ROLE_HIERARCHY.keys())}"
        )

    async def _role_checker(
        user: dict = Depends(get_current_user),
    ) -> dict:
        user_level = _role_level(user.get("role", ""))
        if user_level < minimum_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient permissions. "
                    f"Required role: {minimum_role}, your role: {user.get('role')}."
                ),
            )
        return user

    return _role_checker


# ══════════════════════════════════════════════════════════
# Convenience Dependencies
# ══════════════════════════════════════════════════════════

require_admin = require_role("ADMIN")
require_police = require_role("POLICE")
require_rto = require_role("RTO")
require_viewer = require_role("VIEWER")
