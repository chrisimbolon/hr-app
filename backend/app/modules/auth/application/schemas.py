"""
auth/application/schemas.py
─────────────────────────────
Request and response Pydantic models for the auth module.
"""
from uuid import UUID

from app.shared.schemas.base import BaseSchema
from pydantic import Field, field_validator

# ── Request schemas ──────────────────────────────────────────────

class LoginRequest(BaseSchema):
    employee_code: str = Field(..., min_length=3, max_length=20)
    pin: str | None = Field(None, min_length=4, max_length=8)
    password: str | None = Field(None, min_length=6)
    device_id: str | None = Field(None, max_length=200)
    platform: str | None = Field(None)
    fcm_token: str | None = None

    @field_validator("employee_code")
    @classmethod
    def upper_code(cls, v: str) -> str:
        return v.upper().strip()


class RefreshRequest(BaseSchema):
    refresh_token: str = Field(..., min_length=10)


class LogoutRequest(BaseSchema):
    refresh_token: str = Field(..., min_length=10)


class ChangePinRequest(BaseSchema):
    current_pin: str = Field(..., min_length=4, max_length=8)
    new_pin: str = Field(..., min_length=4, max_length=8)

    @field_validator("new_pin")
    @classmethod
    def pin_not_sequential(cls, v: str) -> str:
        weak = ["1234", "0000", "1111", "2222", "3333",
                "4444", "5555", "6666", "7777", "8888", "9999"]
        if v in weak:
            raise ValueError("PIN terlalu lemah. Hindari angka berurutan atau berulang.")
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
    refresh_token: str          # rotation: client MUST replace the stored refresh token
    token_type: str = "bearer"
    expires_in: int = 900
