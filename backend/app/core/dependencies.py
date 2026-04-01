"""
core/dependencies.py
─────────────────────
Global FastAPI dependencies: DB session, Redis, current employee.
Module-specific deps live in modules/<name>/application/dependencies.py
"""
from typing import AsyncGenerator
from uuid import UUID

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import verify_access_token
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

bearer_scheme = HTTPBearer()
_redis_client: Redis | None = None


# ── Database session ────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Redis connection ─────────────────────────────────────────────

async def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
        )
    return _redis_client


# ── Current employee from JWT ────────────────────────────────────

async def get_current_employee(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Validates JWT, checks Redis blocklist, loads employee.
    Returns employee ORM model. Used in all protected routes.
    """
    from app.modules.employee.infrastructure.models import EmployeeModel

    token = credentials.credentials

    # Check blocklist first (O(1) Redis lookup)
    if await redis.exists(f"blocklist:{token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    try:
        payload = verify_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    employee_id = payload.get("sub")
    if not employee_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    employee = await db.scalar(
        select(EmployeeModel).where(
            EmployeeModel.id == UUID(employee_id),
            EmployeeModel.status == "active",
        )
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee not found or inactive",
        )

    return employee


# ── Role / permission guard ──────────────────────────────────────

def require_roles(*roles: str):
    """
    Factory: returns a dep that enforces role membership.

    Usage:
        @router.get("/admin")
        async def admin_route(emp = Depends(require_roles("hr_admin", "company_admin"))):
            ...
    """
    async def _check(employee=Depends(get_current_employee)):
        if employee.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{employee.role}' is not authorized for this action",
            )
        return employee
    return _check


def require_permission(permission_code: str):
    """
    Fine-grained permission check via RBAC.
    Checks employee_roles → role_permissions → permissions.
    """
    async def _check(
        employee=Depends(get_current_employee),
        db: AsyncSession = Depends(get_db),
    ):
        from sqlalchemy import text
        result = await db.execute(
            text("""
                SELECT 1 FROM employee_roles er
                JOIN role_permissions rp ON rp.role_id = er.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE er.employee_id = :emp_id
                  AND p.code = :perm_code
                LIMIT 1
            """),
            {"emp_id": str(employee.id), "perm_code": permission_code},
        )
        if not result.scalar():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_code}",
            )
        return employee
    return _check