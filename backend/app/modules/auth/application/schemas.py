"""auth/application/schemas.py"""
from app.shared.schemas.base import BaseSchema
from pydantic import Field


class LoginRequest(BaseSchema):
    employee_code: str = Field(..., min_length=3, max_length=20)
    pin: str | None = Field(None, min_length=4, max_length=8)
    password: str | None = Field(None, min_length=6)
    device_id: str | None = None
    platform: str | None = None
    fcm_token: str | None = None


class RefreshRequest(BaseSchema):
    refresh_token: str


class LogoutRequest(BaseSchema):
    refresh_token: str
