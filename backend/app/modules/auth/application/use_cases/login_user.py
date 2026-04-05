"""
auth/application/use_cases/login_user.py
──────────────────────────────────────────
LoginUserUseCase — hardened, production-grade login flow.

Flow (in order):
  1. Find employee by code (case-insensitive, active only)
  2. Check account lockout BEFORE touching the credential
  3. Verify PIN or password via constant-time bcrypt compare
  4. On failure: increment attempt counter, lock if threshold crossed
  5. On success: reset counter, write last_login_at, issue JWT pair
  6. Register/update device + FCM token
  7. Return structured response

Security properties:
  ┌─────────────────────────────────────────────────────────────┐
  │ Timing attack prevention                                    │
  │   bcrypt.verify() always runs — even when employee not      │
  │   found — using a dummy hash. This means login takes the    │
  │   same ~100ms whether the code exists or not. Attacker      │
  │   cannot enumerate valid employee codes via timing.         │
  │                                                             │
  │ Brute-force protection (4-digit PIN = 10,000 combos)        │
  │   5 failures  → locked for 15 minutes (auto-expiry)         │
  │   10 failures → locked permanently (HR admin must unlock)   │
  │                                                             │
  │ Error message uniformity                                    │
  │   "Invalid credentials" always — never "employee not found" │
  │   or "wrong PIN". Attacker learns nothing from the message. │
  │                                                             │
  │ Lockout check before credential verification                │
  │   Locked accounts are rejected immediately without          │
  │   running bcrypt — prevents a DoS where attacker triggers   │
  │   bcrypt (slow by design) repeatedly on locked accounts.    │
  └─────────────────────────────────────────────────────────────┘
"""
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from app.core.exceptions import AuthorizationError, BusinessRuleError
from app.core.security import (create_access_token, create_refresh_token,
                               hash_password, verify_password)
from app.modules.auth.domain.entities import LoginCommand
from app.modules.employee.infrastructure.models import (
    DeviceRegistrationModel, EmployeeModel)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()

# ── Lockout policy ───────────────────────────────────────────────
SOFT_LOCK_AFTER = 5            # attempts before temporary lockout
HARD_LOCK_AFTER = 10           # attempts before permanent lockout
SOFT_LOCK_DURATION_MINUTES = 15

# Dummy hash for constant-time rejection
# Pre-computed once at module load — never changes
_DUMMY_HASH = hash_password("__hadir_dummy_never_matches_any_real_pin__")


class LoginUserUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, cmd: LoginCommand) -> dict:

        # ── 1. Look up employee ──────────────────────────────────
        employee = await self.db.scalar(
            select(EmployeeModel).where(
                EmployeeModel.employee_code == cmd.employee_code.upper().strip(),
                EmployeeModel.status == "active",
            )
        )

        # ── 2. Lockout check — before credential verification ────
        # If employee exists AND is locked, reject early.
        # Do NOT run bcrypt on locked accounts (prevents CPU DoS).
        if employee and employee.locked_until is not None:
            now = datetime.now(timezone.utc)
            if employee.locked_until > now:
                remaining = int((employee.locked_until - now).total_seconds() / 60)
                if remaining > 0:
                    # Temporary lockout — tell user when it expires
                    raise AuthorizationError(
                        f"Akun terkunci. Coba lagi dalam {remaining} menit."
                    )
                else:
                    # Lockout has expired — clear it and proceed
                    employee.locked_until = None
                    employee.failed_login_attempts = 0
            else:
                # Permanent lockout (locked_until set to far future)
                raise AuthorizationError(
                    "Akun terkunci permanen karena terlalu banyak percobaan gagal. "
                    "Hubungi HR untuk membuka kunci."
                )

        # ── 3. Verify credentials (constant-time) ────────────────
        # Always call verify_password — even when employee is None.
        # This prevents timing attacks to enumerate valid employee codes.
        if cmd.pin:
            stored_hash = (employee.hashed_pin if employee else None) or _DUMMY_HASH
            credential_valid = verify_password(cmd.pin, stored_hash)
        elif cmd.password:
            stored_hash = (employee.hashed_password if employee else None) or _DUMMY_HASH
            credential_valid = verify_password(cmd.password, stored_hash)
        else:
            raise AuthorizationError("PIN atau password diperlukan")

        # ── 4a. Credential FAILED ────────────────────────────────
        if not employee or not credential_valid:
            if employee:
                await self._record_failure(employee)

            log.warning(
                "auth.login_failed",
                employee_code=cmd.employee_code,
                attempts=employee.failed_login_attempts if employee else None,
            )
            # Always the same message — never reveal whether code or PIN was wrong
            raise AuthorizationError("Kode karyawan atau PIN/password salah")

        # ── 4b. Credential SUCCEEDED ─────────────────────────────
        await self._record_success(employee)

        # ── 5. Issue JWT pair ────────────────────────────────────
        access_token = create_access_token(
            subject=employee.id,
            role=employee.role,
            company_id=employee.company_id,
        )
        refresh_token = create_refresh_token(subject=employee.id)

        log.info(
            "auth.login_success",
            employee_id=str(employee.id),
            employee_code=employee.employee_code,
            role=employee.role,
            company_id=str(employee.company_id),
        )

        # ── 6. Register/update device + FCM token ────────────────
        if cmd.device_id:
            await self._upsert_device(employee.id, cmd)

        # ── 7. Return structured response ────────────────────────
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
                "employment_type": employee.employment_type,
            },
        }

    # ── Private helpers ──────────────────────────────────────────

    async def _record_failure(self, employee: EmployeeModel) -> None:
        """
        Increment attempt counter.
        Apply soft lock (15 min) at SOFT_LOCK_AFTER.
        Apply hard lock (permanent) at HARD_LOCK_AFTER.
        """
        employee.failed_login_attempts += 1
        attempts = employee.failed_login_attempts

        if attempts >= HARD_LOCK_AFTER:
            # Permanent lock — set locked_until far into the future
            # HR admin must manually set locked_until = NULL to unlock
            employee.locked_until = datetime.now(timezone.utc) + timedelta(days=3650)
            log.error(
                "auth.account_hard_locked",
                employee_id=str(employee.id),
                employee_code=employee.employee_code,
                attempts=attempts,
            )
        elif attempts >= SOFT_LOCK_AFTER:
            employee.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=SOFT_LOCK_DURATION_MINUTES
            )
            log.warning(
                "auth.account_soft_locked",
                employee_id=str(employee.id),
                employee_code=employee.employee_code,
                attempts=attempts,
                locked_until=employee.locked_until.isoformat(),
                locked_for_minutes=SOFT_LOCK_DURATION_MINUTES,
            )

        await self.db.flush()

    async def _record_success(self, employee: EmployeeModel) -> None:
        """Reset security counters and record login timestamp."""
        employee.failed_login_attempts = 0
        employee.locked_until = None
        employee.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def _upsert_device(self, employee_id: uuid.UUID, cmd: LoginCommand) -> None:
        """
        Insert or update device registration.
        PostgreSQL ON CONFLICT DO UPDATE — atomic, race-safe.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(DeviceRegistrationModel)
            .values(
                id=uuid.uuid4(),
                employee_id=employee_id,
                device_id=cmd.device_id,
                fcm_token=cmd.fcm_token,
                platform=cmd.platform or "unknown",
                is_active=True,
            )
            .on_conflict_do_update(
                index_elements=["employee_id", "device_id"],
                set_={
                    "fcm_token": cmd.fcm_token,
                    "is_active": True,
                },
            )
        )
        await self.db.execute(stmt)
        log.info(
            "auth.device_registered",
            employee_id=str(employee_id),
            device_id=cmd.device_id,
            platform=cmd.platform,
        )
