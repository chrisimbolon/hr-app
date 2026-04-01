"""
attendance/application/use_cases/check_out.py
───────────────────────────────────────────────
CheckOutUseCase: validates checkout, computes work hours,
detects early leave and overtime, fires async notifications.
"""
import uuid
from datetime import datetime, timezone

from app.core.exceptions import BusinessRuleError
from app.modules.attendance.application.schemas import (CheckOutRequest,
                                                        CheckOutResponse)
from app.modules.attendance.domain.entities import AttendanceSummary
from app.modules.attendance.domain.policies import AttendancePolicyEngine
from app.modules.attendance.infrastructure.repository import \
    AttendanceRepository
from app.shared.enums.attendance import AttendanceStatus, CheckType
from sqlalchemy.ext.asyncio import AsyncSession


class CheckOutUseCase:
    def __init__(self, db: AsyncSession):
        self.repo = AttendanceRepository(db)

    async def execute(
        self,
        employee_id: uuid.UUID,
        company_id: uuid.UUID,
        request: CheckOutRequest,
        photo_bytes: bytes | None = None,
    ) -> CheckOutResponse:

        server_time = datetime.now(timezone.utc)
        today = server_time.date()

        # ── 1. Must have checked in first ────────────────────────
        checkin_log = await self.repo.get_today_log(employee_id, CheckType.CHECK_IN)
        if not checkin_log:
            raise BusinessRuleError("Cannot check out — no check-in recorded today.")

        # ── 2. Guard: already checked out ────────────────────────
        existing_checkout = await self.repo.get_today_log(employee_id, CheckType.CHECK_OUT)
        if existing_checkout:
            raise BusinessRuleError("You have already checked out today.")

        # ── 3. Load policy + shift ────────────────────────────────
        policy = await self.repo.get_policy(company_id)
        if not policy:
            from app.modules.attendance.domain.entities import AttendancePolicy
            policy = AttendancePolicy(company_id=company_id)

        shift = await self.repo.get_active_shift(employee_id, today)
        if not shift:
            raise BusinessRuleError("No shift assigned. Contact HR.")

        from app.modules.attendance.domain.entities import ShiftPolicy
        shift = ShiftPolicy(
            shift_id=shift.shift_id,
            start_time=shift.start_time,
            end_time=shift.end_time,
            break_minutes=shift.break_minutes,
            is_overnight=shift.is_overnight,
            late_tolerance_minutes=policy.late_tolerance_minutes,
            early_leave_tolerance_minutes=policy.early_leave_tolerance_minutes,
            overtime_threshold_minutes=policy.overtime_threshold_minutes,
            max_work_minutes=policy.max_work_minutes_per_day,
        )

        engine = AttendancePolicyEngine(policy)

        # ── 4. Domain computations (pure Python) ─────────────────
        check_in_time = checkin_log.timestamp_utc
        work_mins = engine.work_minutes(check_in_time, server_time, shift)
        is_early = engine.is_early_leave(server_time, shift)
        early_mins = engine.early_leave_minutes(server_time, shift) if is_early else 0
        ot_mins = engine.overtime_minutes(server_time, shift)

        # ── 5. Persist checkout log ───────────────────────────────
        from app.modules.attendance.domain.entities import AttendanceLog
        from app.shared.enums.attendance import AttendanceSource
        log = AttendanceLog(
            id=uuid.uuid4(),
            employee_id=employee_id,
            company_id=company_id,
            timestamp_utc=server_time,
            type=CheckType.CHECK_OUT,
            latitude=request.latitude,
            longitude=request.longitude,
            accuracy_meters=request.accuracy_meters,
            device_id=request.device_id,
            source=AttendanceSource.MOBILE,
        )
        saved_log = await self.repo.save_log(log)

        # ── 6. Update daily summary ───────────────────────────────
        existing_summary = await self.repo.get_summary(employee_id, today)
        if existing_summary:
            from app.modules.attendance.domain.entities import \
                AttendanceSummary as AS
            updated = AS(
                employee_id=employee_id,
                company_id=company_id,
                date=today,
                shift_id=shift.shift_id,
                check_in_time=check_in_time,
                check_out_time=server_time,
                work_minutes=work_mins,
                late_minutes=existing_summary.late_minutes,
                early_leave_minutes=early_mins,
                overtime_minutes=ot_mins,
                is_late=existing_summary.is_late,
                is_early_leave=is_early,
                status=AttendanceStatus.PRESENT,
            )
            await self.repo.upsert_summary(updated)

        # ── 7. Async tasks ────────────────────────────────────────
        if photo_bytes:
            from app.modules.attendance.tasks.attendance_jobs import \
                upload_selfie_to_r2
            upload_selfie_to_r2.delay(
                log_id=str(saved_log.id),
                photo_bytes=photo_bytes,
                check_type="check_out",
            )

        # ── 8. Format response ────────────────────────────────────
        hours = work_mins // 60
        minutes = work_mins % 60

        return CheckOutResponse(
            log_id=saved_log.id,
            check_out_at=server_time,
            work_minutes=work_mins,
            work_hours_display=f"{hours}j {minutes}m",
            is_early_leave=is_early,
            early_leave_minutes=early_mins,
            overtime_minutes=ot_mins,
            overtime_detected=ot_mins > 0,
        )
