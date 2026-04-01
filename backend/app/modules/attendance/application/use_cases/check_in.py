"""
attendance/application/use_cases/check_in.py
─────────────────────────────────────────────
CheckInUseCase orchestrates the full check-in flow:
  1. Load company policy from DB
  2. Validate domain rules (GPS, device, duplicate, window)
  3. Compute late status using pure domain policy engine
  4. Write attendance log to DB
  5. Upsert daily summary
  6. Fire async Celery tasks (selfie upload, late notification)
  7. Return response — all in < 200ms
"""
import uuid
from datetime import datetime, timezone

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.attendance.application.schemas import (CheckInRequest,
                                                        CheckInResponse)
from app.modules.attendance.domain.entities import (AttendanceLog,
                                                    AttendanceSummary)
from app.modules.attendance.domain.policies import AttendancePolicyEngine
from app.modules.attendance.infrastructure.repository import \
    AttendanceRepository
from app.shared.enums.attendance import (AttendanceSource, AttendanceStatus,
                                         CheckType)
from app.shared.utils.haversine import haversine
from sqlalchemy.ext.asyncio import AsyncSession


class CheckInUseCase:
    def __init__(self, db: AsyncSession):
        self.repo = AttendanceRepository(db)

    async def execute(
        self,
        employee_id: uuid.UUID,
        company_id: uuid.UUID,
        office_lat: float,
        office_lng: float,
        office_radius: float,
        request: CheckInRequest,
        photo_bytes: bytes | None = None,
    ) -> CheckInResponse:

        server_time = datetime.now(timezone.utc)
        today = server_time.date()

        # ── 1. Load company attendance policy ────────────────────
        policy = await self.repo.get_policy(company_id)
        if not policy:
            # Use sensible defaults if company hasn't configured policy
            from app.modules.attendance.domain.entities import AttendancePolicy
            policy = AttendancePolicy(company_id=company_id)

        # ── 2. Load employee's shift for today ───────────────────
        shift = await self.repo.get_active_shift(employee_id, today)
        if not shift:
            raise BusinessRuleError("No shift assigned for today. Contact HR.")

        # Re-build ShiftPolicy with actual policy tolerances
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

        # ── 3. Domain rule: duplicate check-in guard ─────────────
        existing_checkin = await self.repo.get_today_log(employee_id, CheckType.CHECK_IN)
        if existing_checkin:
            raise BusinessRuleError("You have already checked in today.")

        # ── 4. Domain rule: GPS location validation ──────────────
        distance_m = 0.0
        location_valid = True

        if policy.require_gps and request.latitude and request.longitude:
            distance_m = haversine(
                office_lat, office_lng,
                request.latitude, request.longitude,
            )
            location_valid = distance_m <= office_radius
            # WFH exception: if company allows WFH, location check is advisory only
            if not location_valid and not policy.allow_wfh:
                raise BusinessRuleError(
                    f"Location too far from office ({int(distance_m)}m). "
                    f"Must be within {int(office_radius)}m."
                )

        # ── 5. Domain rule: check-in window ──────────────────────
        if not engine.is_within_checkin_window(server_time, shift):
            raise BusinessRuleError(
                "Check-in outside allowed window. "
                f"Allowed from {policy.checkin_window_before_minutes} minutes before shift start."
            )

        # ── 6. Compute late status (pure domain) ─────────────────
        is_late = engine.is_late(server_time, shift)
        late_mins = engine.late_minutes(server_time, shift) if is_late else 0

        # ── 7. Persist attendance log (append-only) ──────────────
        log = AttendanceLog(
            id=uuid.uuid4(),
            employee_id=employee_id,
            company_id=company_id,
            timestamp_utc=server_time,
            type=CheckType.CHECK_IN,
            latitude=request.latitude,
            longitude=request.longitude,
            accuracy_meters=request.accuracy_meters,
            device_id=request.device_id,
            source=AttendanceSource.MOBILE,
        )
        saved_log = await self.repo.save_log(log)

        # ── 8. Upsert daily summary ──────────────────────────────
        summary = AttendanceSummary(
            employee_id=employee_id,
            company_id=company_id,
            date=today,
            shift_id=shift.shift_id,
            check_in_time=server_time,
            is_late=is_late,
            late_minutes=late_mins,
            status=AttendanceStatus.LATE if is_late else AttendanceStatus.PRESENT,
        )
        await self.repo.upsert_summary(summary)

        # ── 9. Fire async Celery tasks (non-blocking) ────────────
        if photo_bytes:
            from app.modules.attendance.tasks.attendance_jobs import \
                upload_selfie_to_r2
            upload_selfie_to_r2.delay(
                log_id=str(saved_log.id),
                photo_bytes=photo_bytes,
                check_type="check_in",
            )

        if is_late:
            from app.modules.attendance.tasks.attendance_jobs import \
                notify_late_checkin
            notify_late_checkin.delay(
                employee_id=str(employee_id),
                late_minutes=late_mins,
            )

        # ── 10. Build response ───────────────────────────────────
        return CheckInResponse(
            log_id=saved_log.id,
            status="present",
            check_in_at=server_time,
            is_late=is_late,
            late_minutes=late_mins,
            location_valid=location_valid,
            distance_meters=int(distance_m),
            message=(
                f"Terlambat {late_mins} menit" if is_late
                else "Berhasil check-in. Selamat bekerja!"
            ),
        )
