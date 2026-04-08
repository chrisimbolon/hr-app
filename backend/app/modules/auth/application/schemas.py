"""
auth/application/schemas.py
─────────────────────────────
Request and response Pydantic models for the auth module.

PIN policy (enforced here at the API boundary):
  - Exactly 6 digits — no more, no less
  - Must be numeric only
  - Must not be a weak pattern (sequential or all-same)

This is the single source of truth for PIN format.
The Flutter app and web frontend should also enforce 6 digits
in the UI, but the backend validates regardless.
"""
from uuid import UUID

from app.shared.schemas.base import BaseSchema
from pydantic import Field, field_validator

# ── Request schemas ──────────────────────────────────────────────

class LoginRequest(BaseSchema):
    employee_code: str = Field(..., min_length=3, max_length=20)
    pin: str | None = Field(
        None,
        min_length=6,
        max_length=6,
        description="Exactly 6 numeric digits",
    )
    password: str | None = Field(None, min_length=6)
    device_id: str | None = Field(None, max_length=200)
    platform: str | None = Field(None)
    fcm_token: str | None = None

    @field_validator("employee_code")
    @classmethod
    def upper_code(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("pin")
    @classmethod
    def pin_must_be_numeric(cls, v: str | None) -> str | None:
        if v is not None and not v.isdigit():
            raise ValueError("PIN harus berupa 6 angka")
        return v


class RefreshRequest(BaseSchema):
    refresh_token: str = Field(..., min_length=10)


class LogoutRequest(BaseSchema):
    refresh_token: str = Field(..., min_length=10)


class ChangePinRequest(BaseSchema):
    current_pin: str = Field(..., min_length=6, max_length=6)
    new_pin: str = Field(..., min_length=6, max_length=6)

    @field_validator("current_pin", "new_pin")
    @classmethod
    def pin_must_be_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("PIN harus berupa 6 angka")
        return v

    @field_validator("new_pin")
    @classmethod
    def pin_not_weak(cls, v: str) -> str:
        # All-same digits: 000000, 111111, ..., 999999
        if len(set(v)) == 1:
            raise ValueError("PIN terlalu lemah. Jangan gunakan angka yang sama semua.")
        # Sequential ascending: 123456, 234567, ..., 678901 (wrapping)
        digits = [int(c) for c in v]
        diffs = [digits[i+1] - digits[i] for i in range(len(digits) - 1)]
        if all(d == 1 for d in diffs):
            raise ValueError("PIN terlalu lemah. Jangan gunakan angka berurutan.")
        # Sequential descending: 654321, 987654
        if all(d == -1 for d in diffs):
            raise ValueError("PIN terlalu lemah. Jangan gunakan angka berurutan turun.")
        return v


# ── Response schemas ─────────────────────────────────────────────

class EmployeeProfile(BaseSchema):
    id: UUID
    employee_code: str
    full_name: str
    email: str
    role: str
    company_id: UUID
    employment_type: str


class LoginResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    employee: EmployeeProfile


class TokenRefreshResponse(BaseSchema):
    access_token: str
    refresh_token: str          # rotation: client MUST replace stored token
    token_type: str = "bearer"
    expires_in: int = 900