"""
auth/presentation/api/v1/routes.py
────────────────────────────────────
Auth API: login, refresh, logout.
"""
from app.core.dependencies import get_current_employee, get_db, get_redis
from app.core.security import create_access_token, verify_refresh_token
from app.modules.auth.application.schemas import (LoginRequest, LogoutRequest,
                                                  RefreshRequest)
from app.modules.auth.application.use_cases.login_user import LoginUserUseCase
from app.modules.auth.domain.entities import LoginCommand
from app.shared.schemas.base import ApiResponse
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/login", response_model=ApiResponse[dict])
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Employee login. Accepts PIN (mobile) or password (web).
    Returns access_token (15min) + refresh_token (7 days).
    """
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
    return ApiResponse(data=result, message="Login berhasil")


@router.post("/refresh", response_model=ApiResponse[dict])
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Rotate access token using a valid refresh token."""
    if await redis.exists(f"blocklist:{body.refresh_token}"):
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    try:
        payload = verify_refresh_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    from uuid import UUID

    from app.modules.employee.infrastructure.models import EmployeeModel
    from sqlalchemy import select

    employee = await db.scalar(
        select(EmployeeModel).where(
            EmployeeModel.id == UUID(payload["sub"]),
            EmployeeModel.status == "active",
        )
    )
    if not employee:
        raise HTTPException(status_code=401, detail="Employee not found")

    new_access = create_access_token(
        subject=employee.id,
        role=employee.role,
        company_id=employee.company_id,
    )
    return ApiResponse(
        data={"access_token": new_access, "token_type": "bearer", "expires_in": 900}
    )


@router.post("/logout", response_model=ApiResponse[dict])
async def logout(
    body: LogoutRequest,
    redis: Redis = Depends(get_redis),
    employee=Depends(get_current_employee),
):
    """Revoke refresh token by adding to Redis blocklist."""
    from app.core.config import settings
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.setex(f"blocklist:{body.refresh_token}", ttl, "1")
    return ApiResponse(data={}, message="Logout berhasil. Sampai jumpa!")
