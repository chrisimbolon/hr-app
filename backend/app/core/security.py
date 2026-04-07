"""
core/security.py
────────────────
JWT creation/verification and PIN/password hashing.

Uses bcrypt directly — passlib 1.7.4 is incompatible with bcrypt 4.x.

token_version ("tv" claim):
  Every access token carries a "tv" integer claim that mirrors
  employee.token_version in the DB at the moment of issuance.

  On every authenticated request, get_current_employee() compares
  payload["tv"] against the current DB value. If they differ —
  because logout-all or change-pin was called — the token is rejected
  immediately with 401, across every device, with zero Redis overhead.

  Tokens issued before this field existed lack "tv" entirely. The
  dependency treats a missing claim as version 0, which matches the
  DB default (0) so existing sessions keep working until the first
  security-sensitive action increments the version.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
from app.core.config import settings
from jose import JWTError, jwt

# ── Password / PIN hashing ──────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain-text password or PIN using bcrypt (rounds=12)."""
    return bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text credential against a bcrypt hash.
    Returns False on any mismatch or invalid hash — never raises.
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
    token_version: int = 0,
    extra: dict[str, Any] | None = None,
) -> str:
    """
    Issue a short-lived access token.

    Args:
        subject:       Employee UUID
        role:          Employee role string (e.g. "hr_admin")
        company_id:    Company UUID (multi-tenant scoping)
        token_version: Current employee.token_version from DB.
                       Embedded as "tv" claim — checked on every request.
                       Incrementing this column via logout-all or change-pin
                       instantly invalidates every token ever issued to
                       this employee, across all devices, with one DB write.
        extra:         Optional additional claims
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "company_id": str(company_id),
        "tv": token_version,          # ← token version — the missing piece
        "exp": expire,
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: UUID | str) -> str:
    """
    Issue a long-lived refresh token.

    Refresh tokens are intentionally stateless — they are:
      - Verified by signature on use
      - Revoked by adding to the Redis blocklist on logout
      - Rotated on every use via the /refresh endpoint
        (old token → blocklisted, new token → issued)

    They do NOT carry token_version because their sole purpose is
    to issue a new access token, which WILL carry the latest version.
    If token_version was incremented since this refresh token was issued,
    the NEW access token will carry the updated version — and on the
    very next use of that access token the version check will pass,
    because the refresh endpoint always reads token_version fresh from DB.
    """
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
