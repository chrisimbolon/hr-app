"""
auth/application/use_cases/change_pin.py
──────────────────────────────────────────
ChangePinUseCase: authenticated PIN change with automatic session reset.

Security behaviour:
  Changing your PIN is a credential change event. Any attacker who had
  obtained your old PIN and issued themselves a token (before you knew
  they had it) should be locked out the moment you change credentials.

  This use case increments token_version after a successful PIN change,
  which invalidates every JWT ever issued to this employee — on every
  device — immediately. The changing employee must re-login with the new
  PIN to get a fresh token.

  This is the correct behaviour: a credential change = a session reset.
"""
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.exceptions import AuthorizationError, BusinessRuleError
from app.core.security import hash_password, verify_password
from app.modules.employee.infrastructure.models import EmployeeModel

log = structlog.get_logger()


class ChangePinUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(
        self,
        employee_id: UUID,
        current_pin: str,
        new_pin: str,
    ) -> None:
        employee = await self.db.scalar(
            select(EmployeeModel).where(
                EmployeeModel.id == employee_id,
                EmployeeModel.status == "active",
            )
        )
        if not employee:
            raise AuthorizationError("Employee not found")

        # ── 1. Verify current PIN ────────────────────────────────
        if not employee.hashed_pin or not verify_password(current_pin, employee.hashed_pin):
            raise AuthorizationError("PIN saat ini tidak sesuai")

        # ── 2. Prevent reuse ─────────────────────────────────────
        if verify_password(new_pin, employee.hashed_pin):
            raise BusinessRuleError("PIN baru tidak boleh sama dengan PIN sekarang")

        # ── 3. Update PIN ─────────────────────────────────────────
        employee.hashed_pin = hash_password(new_pin)

        # ── 4. Increment token_version → invalidates ALL sessions ─
        # Every JWT ever issued to this employee carries the old tv value.
        # After this increment, every existing token fails the tv check
        # in get_current_employee → 401 on next request.
        # Employee must re-login with new PIN to get a valid token.
        old_version = employee.token_version
        employee.token_version += 1

        await self.db.flush()

        log.info(
            "auth.pin_changed",
            employee_id=str(employee_id),
            token_version_old=old_version,
            token_version_new=employee.token_version,
            sessions_invalidated="all",
        )
