"""
attendance/infrastructure/repository.py
─────────────────────────────────────────
Concrete implementation of IAttendanceRepository.
ALL SQLAlchemy lives here. Domain layer never touches this directly.
"""
from datetime import date, datetime, timezone
from uuid import UUID

from app.modules.attendance.domain.entities import (AttendanceLog,
                                                    AttendancePolicy,
                                                    AttendanceSummary,
                                                    ShiftPolicy)
from app.modules.attendance.infrastructure.models import (
    AttendanceLogModel, AttendancePolicyModel, AttendanceSummaryModel,
    ShiftAssignmentModel, ShiftModel)
from app.shared.enums.attendance import AttendanceStatus, CheckType
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class AttendanceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Policy ──────────────────────────────────────────────────

    async def get_policy(self, company_id: UUID) -> AttendancePolicy | None:
        row = await self.db.scalar(
            select(AttendancePolicyModel).where(
                AttendancePolicyModel.company_id == company_id
            )
        )
        if not row:
            return None
        return AttendancePolicy(
            company_id=row.company_id,
            late_tolerance_minutes=row.late_tolerance_minutes,
            early_leave_tolerance_minutes=row.early_leave_tolerance_minutes,
            overtime_threshold_minutes=row.overtime_threshold_minutes,
            max_work_minutes_per_day=row.max_work_minutes_per_day,
            checkin_window_before_minutes=row.checkin_window_before_minutes,
            require_selfie=row.require_selfie,
            require_gps=row.require_gps,
            allow_wfh=row.allow_wfh,
        )

    # ── Shift ────────────────────────────────────────────────────

    async def get_active_shift(self, employee_id: UUID, on_date: date) -> ShiftPolicy | None:
        """Get the shift assigned to an employee on a given date."""
        row = await self.db.scalar(
            select(ShiftModel)
            .join(
                ShiftAssignmentModel,
                and_(
                    ShiftAssignmentModel.shift_id == ShiftModel.id,
                    ShiftAssignmentModel.employee_id == employee_id,
                    ShiftAssignmentModel.start_date <= on_date,
                    (ShiftAssignmentModel.end_date.is_(None)) |
                    (ShiftAssignmentModel.end_date >= on_date),
                )
            )
            .order_by(ShiftAssignmentModel.start_date.desc())
            .limit(1)
        )
        if not row:
            return None

        # Fetch policy for tolerances (policy attached to company, not shift)
        return ShiftPolicy(
            shift_id=row.id,
            start_time=row.start_time,
            end_time=row.end_time,
            break_minutes=row.break_minutes,
            is_overnight=row.is_overnight,
            late_tolerance_minutes=15,         # fallback; overridden by policy in use case
            early_leave_tolerance_minutes=15,
            overtime_threshold_minutes=30,
            max_work_minutes=600,
        )

    # ── Attendance log ───────────────────────────────────────────

    async def get_today_log(self, employee_id: UUID, check_type: CheckType) -> AttendanceLogModel | None:
        today = datetime.now(timezone.utc).date()
        return await self.db.scalar(
            select(AttendanceLogModel).where(
                and_(
                    AttendanceLogModel.employee_id == employee_id,
                    AttendanceLogModel.type == check_type.value,
                    func.date(AttendanceLogModel.timestamp_utc) == today,
                )
            ).order_by(AttendanceLogModel.timestamp_utc.desc()).limit(1)
        )

    async def save_log(self, log: AttendanceLog) -> AttendanceLogModel:
        model = AttendanceLogModel(
            id=log.id,
            employee_id=log.employee_id,
            company_id=log.company_id,
            timestamp_utc=log.timestamp_utc,
            type=log.type.value if hasattr(log.type, 'value') else log.type,
            latitude=log.latitude,
            longitude=log.longitude,
            accuracy_meters=log.accuracy_meters,
            photo_url=log.photo_url,
            device_id=log.device_id,
            source=log.source.value if hasattr(log.source, 'value') else log.source,
        )
        self.db.add(model)
        await self.db.flush()
        return model

    # ── Summary ──────────────────────────────────────────────────

    async def get_summary(self, employee_id: UUID, on_date: date) -> AttendanceSummaryModel | None:
        return await self.db.scalar(
            select(AttendanceSummaryModel).where(
                and_(
                    AttendanceSummaryModel.employee_id == employee_id,
                    AttendanceSummaryModel.date == on_date,
                )
            )
        )

    async def upsert_summary(self, summary: AttendanceSummary) -> AttendanceSummaryModel:
        existing = await self.get_summary(summary.employee_id, summary.date)
        if existing:
            existing.check_in_time = summary.check_in_time
            existing.check_out_time = summary.check_out_time
            existing.work_minutes = summary.work_minutes
            existing.late_minutes = summary.late_minutes
            existing.early_leave_minutes = summary.early_leave_minutes
            existing.overtime_minutes = summary.overtime_minutes
            existing.is_late = summary.is_late
            existing.is_early_leave = summary.is_early_leave
            existing.is_alpha = summary.is_alpha
            existing.is_leave = summary.is_leave
            existing.status = summary.status
            existing.processed_at = datetime.now(timezone.utc)
            await self.db.flush()
            return existing
        else:
            model = AttendanceSummaryModel(
                employee_id=summary.employee_id,
                company_id=summary.company_id,
                date=summary.date,
                shift_id=summary.shift_id,
                check_in_time=summary.check_in_time,
                check_out_time=summary.check_out_time,
                work_minutes=summary.work_minutes,
                late_minutes=summary.late_minutes,
                early_leave_minutes=summary.early_leave_minutes,
                overtime_minutes=summary.overtime_minutes,
                is_late=summary.is_late,
                is_early_leave=summary.is_early_leave,
                is_alpha=summary.is_alpha,
                is_leave=summary.is_leave,
                status=summary.status,
                processed_at=datetime.now(timezone.utc),
            )
            self.db.add(model)
            await self.db.flush()
            return model

    async def get_monthly_summaries(
        self, employee_id: UUID, year: int, month: int
    ) -> list[AttendanceSummaryModel]:
        from sqlalchemy import extract
        rows = await self.db.execute(
            select(AttendanceSummaryModel).where(
                and_(
                    AttendanceSummaryModel.employee_id == employee_id,
                    extract("year", AttendanceSummaryModel.date) == year,
                    extract("month", AttendanceSummaryModel.date) == month,
                )
            ).order_by(AttendanceSummaryModel.date)
        )
        return list(rows.scalars().all())
