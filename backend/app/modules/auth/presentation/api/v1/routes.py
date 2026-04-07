"""
auth/presentation/api/v1/routes.py
────────────────────────────────────
Auth API endpoints. Thin routes — all security logic lives in
use cases and get_current_employee. Each route: validate input,
call use case or inline logic, return response. Nothing else.

Endpoints:
  POST /v1/auth/login           — PIN or password login → JWT pair
  POST /v1/auth/refresh         — rotate both tokens (rotation pattern)
  POST /v1/auth/logout          — revoke this session (blocklist refresh token)
  POST /v1/auth/logout-all      — revoke ALL sessions (increment token_version)
  POST /v1/auth/change-pin      — change PIN + invalidate all sessions
  GET  /v1/auth/me              — current employee profile
  POST /v1/auth/unlock/{id}     — HR admin: unlock locked account
"""
from uuid import UUID

import structlog
from app.core.config import settings
from app.core.dependencies import get_current_employee, get_db, get_redis
from app.core.security import (create_access_token, create_refresh_token,
                               verify_refresh_token)
from app.modules.auth.application.schemas import (ChangePinRequest,
                                                  EmployeeProfile,
                                                  LoginRequest, LoginResponse,
                                                  LogoutRequest,
                                                  RefreshRequest,
                                                  TokenRefreshResponse)
from app.modules.auth.application.use_cases.change_pin import ChangePinUseCase
from app.modules.auth.application.use_cases.login_user import LoginUserUseCase
from app.modules.auth.domain.entities import LoginCommand
from app.shared.schemas.base import ApiResponse
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
log = structlog.get_logger()


# ── POST /login ──────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=ApiResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="Employee login",
    description=(
        "PIN login for Flutter mobile app, password login for web dashboard.\n\n"
        "**Security built in:**\n"
        "- Brute-force protection: 5 failures → 15 min lockout, 10 → permanent\n"
        "- Constant-time bcrypt — prevents timing-based enumeration\n"
        "- `tv` (token_version) embedded in JWT for instant global revocation\n"
        "- Device + FCM token registered on every login"
    ),
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    use_case = LoginUserUseCase(db)
    result = await use_case.execute(
        LoginCommand(
            employee_code=body.employee_code,
            pin=body.pin,
            password=body.password,
            device_id=body.device_id,
            platform=body.platform,
            fcm_token=body.fcm_token,
        )
    )
    return ApiResponse(data=LoginResponse(**result), message="Login berhasil. Selamat bekerja!")


# ── POST /refresh ─────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=ApiResponse[TokenRefreshResponse],
    summary="Rotate tokens",
    description=(
        "**Refresh token rotation** — best practice for session security.\n\n"
        "Every call to this endpoint:\n"
        "1. Verifies the incoming refresh token\n"
        "2. Adds the OLD refresh token to the Redis blocklist immediately\n"
        "3. Issues a NEW refresh token (different value, same 7-day TTL)\n"
        "4. Issues a NEW access token with the latest `token_version` from DB\n\n"
        "**Why rotation matters:**\n"
        "If a refresh token is stolen before logout is called, the attacker\n"
        "can use it indefinitely. With rotation, the moment either the\n"
        "attacker OR the legitimate user calls /refresh, the other one gets\n"
        "a 401 on their next request — because the token they hold was already\n"
        "consumed. This turns a 7-day stolen token window into a single-use window."
    ),
)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    # ── 1. Blocklist check ───────────────────────────────────────
    # If this token was already used (rotation) or explicitly logged
    # out, reject before doing any crypto.
    if await redis.exists(f"blocklist:{body.refresh_token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token telah digunakan atau dicabut. Silakan login kembali.",
        )

    # ── 2. Verify signature ──────────────────────────────────────
    try:
        payload = verify_refresh_token(body.refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token tidak valid atau sudah kadaluarsa.",
        )

    # ── 3. Load employee (fresh from DB) ─────────────────────────
    from app.modules.employee.infrastructure.models import EmployeeModel

    employee = await db.scalar(
        select(EmployeeModel).where(
            EmployeeModel.id == UUID(payload["sub"]),
            EmployeeModel.status == "active",
        )
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Karyawan tidak ditemukan atau sudah tidak aktif.",
        )

    # ── 4. ROTATION: blocklist the OLD refresh token immediately ─
    # TTL = remaining lifetime of the old token so the Redis key
    # self-expires at the same time the old token would have expired.
    from datetime import datetime, timezone
    old_exp = payload.get("exp", 0)
    now_ts  = int(datetime.now(timezone.utc).timestamp())
    ttl     = max(old_exp - now_ts, 1)  # never set TTL=0 (would mean no expiry)
    await redis.setex(f"blocklist:{body.refresh_token}", ttl, "revoked:rotated")

    # ── 5. Issue NEW tokens ──────────────────────────────────────
    # Access token always carries the CURRENT token_version from DB.
    # If logout-all was called between when this refresh token was issued
    # and now, the new access token will carry the updated version, and
    # every subsequent API call will pass the version check.
    new_access_token  = create_access_token(
        subject=employee.id,
        role=employee.role,
        company_id=employee.company_id,
        token_version=employee.token_version,   # always fresh from DB
    )
    new_refresh_token = create_refresh_token(subject=employee.id)

    log.info(
        "auth.token_rotated",
        employee_id=str(employee.id),
        token_version=employee.token_version,
    )

    return ApiResponse(
        data=TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,    # ← NEW: client MUST store this
        ),
        message="Token berhasil diperbarui",
    )


# ── POST /logout ──────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=ApiResponse[dict],
    summary="Logout — revoke this session",
    description=(
        "Adds the refresh token to the Redis blocklist.\n\n"
        "The current access token expires naturally in ≤15 minutes.\n"
        "For immediate revocation across ALL devices, use `/logout-all`."
    ),
)
async def logout(
    body: LogoutRequest,
    redis: Redis = Depends(get_redis),
    employee=Depends(get_current_employee),
):
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86_400
    await redis.setex(f"blocklist:{body.refresh_token}", ttl, "revoked:logout")

    log.info("auth.logout", employee_id=str(employee.id))
    return ApiResponse(data={}, message="Logout berhasil. Sampai jumpa!")


# ── POST /logout-all ──────────────────────────────────────────────

@router.post(
    "/logout-all",
    response_model=ApiResponse[dict],
    summary="Logout from ALL devices instantly",
    description=(
        "Increments `token_version` by 1.\n\n"
        "Every access token ever issued to this employee — on every device —\n"
        "immediately fails the `tv` version check and returns 401.\n\n"
        "**One DB write. Zero Redis operations. Instant effect.**\n\n"
        "Use this when a phone is lost or stolen."
    ),
)
async def logout_all(
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    old_version = employee.token_version
    employee.token_version += 1
    await db.flush()

    log.info(
        "auth.logout_all",
        employee_id=str(employee.id),
        token_version_old=old_version,
        token_version_new=employee.token_version,
    )
    return ApiResponse(
        data={
            "token_version": employee.token_version,
            "sessions_invalidated": "all",
        },
        message="Semua sesi berhasil dihapus. Silakan login kembali di semua perangkat.",
    )


# ── POST /change-pin ──────────────────────────────────────────────

@router.post(
    "/change-pin",
    response_model=ApiResponse[dict],
    summary="Change PIN — invalidates all sessions",
    description=(
        "Verifies current PIN, sets new PIN, increments `token_version`.\n\n"
        "The token_version increment means all existing tokens on all devices\n"
        "are immediately invalidated. The employee must log in again with the\n"
        "new PIN. This is intentional — a credential change = full session reset."
    ),
)
async def change_pin(
    body: ChangePinRequest,
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    use_case = ChangePinUseCase(db)
    await use_case.execute(
        employee_id=employee.id,
        current_pin=body.current_pin,
        new_pin=body.new_pin,
    )
    return ApiResponse(
        data={},
        message="PIN berhasil diubah. Semua sesi lama telah dihapus. Silakan login kembali.",
    )


# ── GET /me ───────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=ApiResponse[EmployeeProfile],
    summary="Current employee profile",
    description=(
        "Validates the access token and returns the current employee's profile.\n\n"
        "Flutter calls this on app startup to verify the stored token is still\n"
        "valid and to refresh the local user profile (name, role, company)."
    ),
)
async def me(employee=Depends(get_current_employee)):
    return ApiResponse(
        data=EmployeeProfile(
            id=employee.id,
            employee_code=employee.employee_code,
            full_name=employee.full_name,
            email=employee.email,
            role=employee.role,
            company_id=employee.company_id,
            employment_type=employee.employment_type,
        )
    )


# ── POST /unlock/{employee_id} ────────────────────────────────────

@router.post(
    "/unlock/{employee_id}",
    response_model=ApiResponse[dict],
    summary="HR admin: unlock locked account",
    description=(
        "Clears account lockout after 10 failed PIN attempts.\n\n"
        "HR admin or company admin only. Resets `failed_login_attempts` to 0\n"
        "so the employee gets a fresh 5-attempt window."
    ),
)
async def unlock_account(
    employee_id: UUID,
    hr=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    if hr.role not in ("hr_admin", "company_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya HR admin yang dapat membuka kunci akun.",
        )

    from app.modules.employee.infrastructure.models import EmployeeModel

    employee = await db.scalar(
        select(EmployeeModel).where(
            EmployeeModel.id == employee_id,
            EmployeeModel.company_id == hr.company_id,
        )
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Karyawan tidak ditemukan.")

    was_locked = employee.locked_until is not None
    employee.locked_until = None
    employee.failed_login_attempts = 0
    await db.flush()

    log.info(
        "auth.account_unlocked",
        employee_id=str(employee_id),
        unlocked_by=str(hr.id),
        was_locked=was_locked,
    )
    return ApiResponse(
        data={"employee_id": str(employee_id), "employee_name": employee.full_name, "was_locked": was_locked},
        message=f"Akun {employee.full_name} berhasil dibuka.",
    )
