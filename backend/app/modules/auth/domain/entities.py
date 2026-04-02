"""
auth/domain/entities.py — Pure Python auth domain objects
"""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AuthToken:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # seconds


@dataclass
class LoginCommand:
    employee_code: str
    pin: str | None = None
    password: str | None = None
    device_id: str | None = None
    platform: str | None = None
    fcm_token: str | None = None
