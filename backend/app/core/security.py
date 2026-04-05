"""
core/security.py
────────────────
JWT creation/verification and PIN/password hashing.

Uses bcrypt directly (not passlib) — passlib 1.7.4 is incompatible
with bcrypt 4.x which removed the __about__ attribute passlib reads.
Direct bcrypt usage: same security, fewer dependencies, no wrapper bugs.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
from app.core.config import settings
from jose import JWTError, jwt

# ── Password / PIN hashing ──────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain-text password or PIN using bcrypt."""
    password_bytes = plain.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.
    Returns False (never raises) on any mismatch or invalid hash.
    Constant-time comparison — safe against timing attacks.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


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
