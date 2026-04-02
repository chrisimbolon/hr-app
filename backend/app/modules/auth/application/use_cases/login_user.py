"""
auth/application/use_cases/login_user.py
──────────────────────────────────────────
LoginUserUseCase: validates credentials, issues JWT pair,
registers device + FCM token for push notifications.
"""
from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.security import (create_access_token, create_refresh_token,
                               verify_password)
from app.modules.auth.domain.entities import AuthToken, LoginCommand
from app.modules.employee.infrastructure.models import EmployeeModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class LoginUserUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, cmd: LoginCommand) -> dict:
        # ── 1. Find employee by code ─────────────────────────────
        employee = await self.db.scalar(
            select(EmployeeModel).where(
                EmployeeModel.employee_code == cmd.employee_code.upper(),
                EmployeeModel.status == "active",
            )
        )
        if not employee:
            raise AuthorizationError("Invalid credentials")

        # ── 2. Verify PIN or password ────────────────────────────
        if cmd.pin:
            if not employee.hashed_pin or not verify_password(cmd.pin, employee.hashed_pin):
                raise AuthorizationError("Invalid credentials")
        elif cmd.password:
            if not employee.hashed_password or not verify_password(cmd.password, employee.hashed_password):
                raise AuthorizationError("Invalid credentials")
        else:
            raise AuthorizationError("PIN or password required")

        # ── 3. Issue JWT pair ────────────────────────────────────
        access_token = create_access_token(
            subject=employee.id,
            role=employee.role,
            company_id=employee.company_id,
        )
        refresh_token = create_refresh_token(subject=employee.id)

        # ── 4. Register/update device + FCM ──────────────────────
        if cmd.device_id:
            await self._upsert_device(employee.id, cmd)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 900,
            "employee": {
                "id": str(employee.id),
                "employee_code": employee.employee_code,
                "full_name": employee.full_name,
                "email": employee.email,
                "role": employee.role,
                "company_id": str(employee.company_id),
            },
        }

    async def _upsert_device(self, employee_id, cmd: LoginCommand) -> None:
        import uuid

        from app.modules.employee.infrastructure.models import \
            DeviceRegistrationModel
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(DeviceRegistrationModel).values(
            id=uuid.uuid4(),
            employee_id=employee_id,
            device_id=cmd.device_id,
            fcm_token=cmd.fcm_token,
            platform=cmd.platform or "unknown",
            is_active=True,
        ).on_conflict_do_update(
            index_elements=["employee_id", "device_id"],
            set_={
                "fcm_token": cmd.fcm_token,
                "is_active": True,
            },
        )
        await self.db.execute(stmt)
