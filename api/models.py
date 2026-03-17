"""
SVIES — Pydantic Request/Response Models
Provides input validation for all API endpoints.
"""

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════
# Query Parameter Models
# ══════════════════════════════════════════════════════════

class StatsQuery(BaseModel):
    days: int = Field(30, ge=1, le=365, description="Look-back window in days")


class ViolationQuery(BaseModel):
    days: int = Field(30, ge=1, le=365)
    level: str | None = Field(None, pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$")
    plate: str | None = Field(None, max_length=15)
    page: int = Field(1, ge=1)
    per_page: int = Field(25, ge=1, le=100)


class OffenderQuery(BaseModel):
    limit: int = Field(20, ge=1, le=100)
    days: int = Field(30, ge=1, le=365)


class ReportQuery(BaseModel):
    plate: str = Field(..., min_length=1, max_length=15)
    days: int = Field(30, ge=1, le=365)


class ExportQuery(BaseModel):
    format: str = Field("csv", pattern=r"^(csv|pdf)$")
    days: int = Field(30, ge=1, le=365)
    level: str | None = Field(None, pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$")
    plate: str | None = Field(None, max_length=15)


class OffenderExportQuery(BaseModel):
    format: str = Field("csv", pattern=r"^(csv|pdf)$")
    days: int = Field(30, ge=1, le=365)
    limit: int = Field(50, ge=1, le=500)


# ══════════════════════════════════════════════════════════
# Request Body Models
# ══════════════════════════════════════════════════════════

class FeedbackRequest(BaseModel):
    original_plate: str = Field("", max_length=15)
    correct_plate: str = Field("", max_length=15)
    correct_vehicle_type: str = Field("", max_length=30)
    notes: str = Field("", max_length=500)


class SetRoleRequest(BaseModel):
    uid: str = Field(..., min_length=1)
    role: str = Field(..., pattern=r"^(VIEWER|RTO|POLICE|ADMIN)$")


class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)
    role: str = Field("VIEWER", pattern=r"^(VIEWER|RTO|POLICE|ADMIN)$")
    display_name: str = ""


class DeleteUserRequest(BaseModel):
    uid: str = Field(..., min_length=1)


# ══════════════════════════════════════════════════════════
# Vehicle Management Models
# ══════════════════════════════════════════════════════════

class VehicleCreateRequest(BaseModel):
    plate: str = Field(..., min_length=1, max_length=15)
    owner: str = Field(..., min_length=1)
    phone: str = Field("", max_length=15)
    email: str = Field("")
    vehicle_type: str = Field("CAR", pattern=r"^(CAR|MOTORCYCLE|AUTO|BUS|TRUCK|VAN|OTHER)$")
    color: str = Field("")
    make: str = Field("")
    year: int = Field(2024, ge=1900, le=2100)
    state: str = Field("")
    registration_state_code: str = Field("", max_length=5)
    status: str = Field("ACTIVE", pattern=r"^(ACTIVE|SUSPENDED|BLACKLISTED)$")


class VehicleUpdateRequest(BaseModel):
    owner: str | None = None
    phone: str | None = None
    email: str | None = None
    vehicle_type: str | None = Field(None, pattern=r"^(CAR|MOTORCYCLE|AUTO|BUS|TRUCK|VAN|OTHER)$")
    color: str | None = None
    make: str | None = None
    year: int | None = Field(None, ge=1900, le=2100)
    state: str | None = None
    registration_state_code: str | None = None
    status: str | None = Field(None, pattern=r"^(ACTIVE|SUSPENDED|BLACKLISTED)$")


class PUCCRequest(BaseModel):
    valid_until: str = Field(..., min_length=1)
    status: str = Field("VALID", pattern=r"^(VALID|EXPIRED)$")


class InsuranceRequest(BaseModel):
    valid_until: str = Field(..., min_length=1)
    type: str = Field("COMPREHENSIVE", pattern=r"^(COMPREHENSIVE|THIRD_PARTY)$")
    status: str = Field("VALID", pattern=r"^(VALID|EXPIRED)$")


class StolenRequest(BaseModel):
    stolen: bool = Field(...)
