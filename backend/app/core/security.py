"""
core/security.py
────────────────
JWT creation/verification and PIN/password hashing.
No business logic here — pure cryptographic utilities.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.core.config import settings
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password / PIN hashing ──────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ─────────────────────────────────────────────────────────

def create_access_token(
    subject: UUID | str,
    role: str,
    company_id: UUID | str,
    extra: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "company_id": str(company_id),
        "exp": expire,
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: UUID | str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify JWT. Raises JWTError on failure.
    Caller is responsible for checking token type.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def verify_access_token(token: str) -> dict[str, Any]:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise JWTError("Not an access token")
        return payload
    except JWTError:
        raise


def verify_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise JWTError("Not a refresh token")
        return payload
    except JWTError:
        raise