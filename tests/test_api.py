"""
SVIES — API Endpoint Unit Tests
Tests the FastAPI backend using httpx AsyncClient.
Runs in NO_AUTH mode (no Firebase required).

The database singleton is mocked before api.server is imported so that
no real Supabase connection is needed.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ══════════════════════════════════════════════════════════
# Build mock db BEFORE importing api.server
# ══════════════════════════════════════════════════════════

def _make_mock_db() -> MagicMock:
    mock = MagicMock()
    mock.backend = "mock"
    mock.get_all_violations_count.return_value = {
        "total": 50, "critical": 5, "high": 10, "medium": 20, "low": 15, "unique_plates": 30,
    }
    mock.get_violations.return_value = {
        "violations": [
            {"plate": "TS09AB1234", "timestamp": "2025-01-15T10:00:00Z",
             "violation_types": "HELMET_VIOLATION", "risk_score": 10,
             "zone_id": "SCHOOL_JNTU", "alert_level": "LOW", "sha256_hash": "abc123"},
        ],
        "total": 1, "page": 1, "per_page": 25, "total_pages": 1,
    }
    mock.get_top_offenders.return_value = [
        {"plate": "TS09AB1234", "count": 5, "latest_timestamp": "2025-01-15T10:00:00Z"},
    ]
    mock.get_violation_history.return_value = [
        {"plate": "TS09AB1234", "timestamp": "2025-01-15T10:00:00Z",
         "violation_types": "HELMET_VIOLATION", "risk_score": 10, "alert_level": "LOW"},
    ]
    mock.lookup_vehicle.return_value = {
        "plate": "TS09AB1234", "owner": "Test Owner", "phone": "+919876543210",
        "email": "test@example.com", "vehicle_type": "CAR",
    }
    mock.lookup_pucc.return_value = {"plate": "TS09AB1234", "status": "VALID"}
    mock.lookup_insurance.return_value = {"plate": "TS09AB1234", "status": "VALID"}
    mock.is_stolen.return_value = False
    mock.get_feedback_stats.return_value = {"total_feedback": 3, "entries": []}
    mock.save_feedback.return_value = {"status": "ok", "total_feedback": 4}
    mock.seed_demo_data.return_value = {"status": "ok", "seeded": 10, "message": "Seeded 10 demo violations."}
    mock.get_offender_level.return_value = 0
    return mock


# Inject mock db into api.database BEFORE api.server loads it
_mock_db = _make_mock_db()

# Mock the database module so importing api.server doesn't need Supabase
import api.database as _db_module
_db_module.db = _mock_db  # type: ignore[attr-defined]

# Force NO_AUTH mode so all endpoints bypass Firebase authentication
import api.auth as _auth_module
_auth_module._NO_AUTH_MODE = True

# Ensure modules that depend on api.database.db re-use the mock
_patcher = patch("api.database.db", _mock_db)
_patcher.start()

# Now safe to import server
from api.server import app as _app  # noqa: E402
from api.auth import get_current_user, require_admin, require_police, require_rto, require_viewer  # noqa: E402

# Override auth dependencies with a mock admin user for all tests
_mock_user = {"uid": "test-uid", "email": "test@example.com", "role": "ADMIN"}

async def _mock_auth():
    return _mock_user

_app.dependency_overrides[get_current_user] = _mock_auth
_app.dependency_overrides[require_admin] = _mock_auth
_app.dependency_overrides[require_police] = _mock_auth
_app.dependency_overrides[require_rto] = _mock_auth
_app.dependency_overrides[require_viewer] = _mock_auth


# ══════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_mock_db():
    """Reset mock call counts before each test."""
    _mock_db.reset_mock()
    # Re-set return values after reset_mock clears them
    _mock_db.backend = "mock"
    _mock_db.get_all_violations_count.return_value = {
        "total": 50, "critical": 5, "high": 10, "medium": 20, "low": 15, "unique_plates": 30,
    }
    _mock_db.get_violations.return_value = {
        "violations": [
            {"plate": "TS09AB1234", "timestamp": "2025-01-15T10:00:00Z",
             "violation_types": "HELMET_VIOLATION", "risk_score": 10,
             "zone_id": "SCHOOL_JNTU", "alert_level": "LOW", "sha256_hash": "abc123"},
        ],
        "total": 1, "page": 1, "per_page": 25, "total_pages": 1,
    }
    _mock_db.get_top_offenders.return_value = [
        {"plate": "TS09AB1234", "count": 5, "latest_timestamp": "2025-01-15T10:00:00Z"},
    ]
    _mock_db.get_violation_history.return_value = [
        {"plate": "TS09AB1234", "timestamp": "2025-01-15T10:00:00Z",
         "violation_types": "HELMET_VIOLATION", "risk_score": 10, "alert_level": "LOW"},
    ]
    _mock_db.lookup_vehicle.return_value = {
        "plate": "TS09AB1234", "owner": "Test Owner", "phone": "+919876543210",
        "email": "test@example.com", "vehicle_type": "CAR",
    }
    _mock_db.lookup_pucc.return_value = {"plate": "TS09AB1234", "status": "VALID"}
    _mock_db.lookup_insurance.return_value = {"plate": "TS09AB1234", "status": "VALID"}
    _mock_db.is_stolen.return_value = False
    _mock_db.get_feedback_stats.return_value = {"total_feedback": 3, "entries": []}
    _mock_db.save_feedback.return_value = {"status": "ok", "total_feedback": 4}
    _mock_db.seed_demo_data.return_value = {"status": "ok", "seeded": 10, "message": "Seeded 10 demo violations."}
    _mock_db.get_offender_level.return_value = 0
    yield


@pytest_asyncio.fixture
async def client():
    """Async httpx client bound to the test server."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_app),
        base_url="http://testserver",
    ) as ac:
        yield ac


# ══════════════════════════════════════════════════════════
# Health endpoint
# ══════════════════════════════════════════════════════════

class TestHealth:

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


# ══════════════════════════════════════════════════════════
# Stats endpoint
# ══════════════════════════════════════════════════════════

class TestStats:

    @pytest.mark.asyncio
    async def test_stats_returns_200(self, client):
        resp = await client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_violations" in data
        assert "critical" in data
        assert "risk_weights" in data

    @pytest.mark.asyncio
    async def test_stats_custom_days(self, client):
        resp = await client.get("/api/stats?days=7")
        assert resp.status_code == 200
        _mock_db.get_all_violations_count.assert_called_once_with(days=7)

    @pytest.mark.asyncio
    async def test_stats_invalid_days_rejected(self, client):
        resp = await client.get("/api/stats?days=-1")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_stats_days_too_large_rejected(self, client):
        resp = await client.get("/api/stats?days=9999")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════
# Violations endpoint
# ══════════════════════════════════════════════════════════

class TestViolations:

    @pytest.mark.asyncio
    async def test_violations_returns_200(self, client):
        resp = await client.get("/api/violations")
        assert resp.status_code == 200
        data = resp.json()
        assert "violations" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_violations_with_filters(self, client):
        resp = await client.get("/api/violations?days=7&level=HIGH&page=1&per_page=10")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_violations_invalid_level_rejected(self, client):
        resp = await client.get("/api/violations?level=INVALID")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_violations_page_zero_rejected(self, client):
        resp = await client.get("/api/violations?page=0")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════
# Offenders endpoint
# ══════════════════════════════════════════════════════════

class TestOffenders:

    @pytest.mark.asyncio
    async def test_offenders_returns_200(self, client):
        resp = await client.get("/api/offenders")
        assert resp.status_code == 200
        data = resp.json()
        assert "offenders" in data
        assert isinstance(data["offenders"], list)

    @pytest.mark.asyncio
    async def test_offenders_custom_params(self, client):
        resp = await client.get("/api/offenders?limit=5&days=7")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════
# Zones endpoint
# ══════════════════════════════════════════════════════════

class TestZones:

    @pytest.mark.asyncio
    async def test_zones_returns_200(self, client):
        resp = await client.get("/api/zones")
        assert resp.status_code == 200
        data = resp.json()
        assert "zones" in data
        assert isinstance(data["zones"], list)
        assert len(data["zones"]) > 0


# ══════════════════════════════════════════════════════════
# Vehicle Lookup endpoint
# ══════════════════════════════════════════════════════════

class TestVehicleLookup:

    @pytest.mark.asyncio
    async def test_lookup_known_plate(self, client):
        resp = await client.get("/api/vehicle/TS09AB1234")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plate"] == "TS09AB1234"

    @pytest.mark.asyncio
    async def test_lookup_returns_vehicle_data(self, client):
        resp = await client.get("/api/vehicle/TS09AB1234")
        data = resp.json()
        assert "vahan" in data or "plate" in data


# ══════════════════════════════════════════════════════════
# Feedback endpoint
# ══════════════════════════════════════════════════════════

class TestFeedback:

    @pytest.mark.asyncio
    async def test_feedback_stats(self, client):
        resp = await client.get("/api/feedback/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_feedback" in data

    @pytest.mark.asyncio
    async def test_submit_feedback(self, client):
        form_data = {
            "feedback": json.dumps({
                "original_plate": "TS09AB1234",
                "correct_plate": "TS09AB1235",
                "correct_vehicle_type": "CAR",
                "notes": "OCR misread last digit",
            }),
        }
        resp = await client.post("/api/feedback", data=form_data)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "ok"


# ══════════════════════════════════════════════════════════
# Export endpoints
# ══════════════════════════════════════════════════════════

class TestExport:

    @pytest.mark.asyncio
    async def test_violations_export_csv(self, client):
        resp = await client.get("/api/violations/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_violations_export_invalid_format_rejected(self, client):
        resp = await client.get("/api/violations/export?format=xml")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_offenders_export_csv(self, client):
        resp = await client.get("/api/offenders/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")


# ══════════════════════════════════════════════════════════
# Model Info endpoint
# ══════════════════════════════════════════════════════════

class TestModelInfo:

    @pytest.mark.asyncio
    async def test_model_info_returns_200(self, client):
        resp = await client.get("/api/model-info")
        assert resp.status_code == 200
        data = resp.json()
        assert "model_version" in data
        assert "feedback_count" in data


# ══════════════════════════════════════════════════════════
# Risk weights (returned within /api/health)
# ══════════════════════════════════════════════════════════

class TestRiskWeights:

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
