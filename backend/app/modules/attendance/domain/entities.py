"""
attendance/domain/entities.py
──────────────────────────────
Pure Python dataclasses. No SQLAlchemy. No FastAPI. No imports from infrastructure.
These represent the TRUTH about what an attendance event IS.
"""
from dataclasses import dataclass, field
from datetime import datetime, time
from uuid import UUID

from app.shared.enums.attendance import (AttendanceSource, AttendanceStatus,
                                         CheckType)


@dataclass(frozen=True)
class ShiftPolicy:
    """Value object: the rules for a specific shift."""
    shift_id: UUID
    start_time: time
    end_time: time
    break_minutes: int
    is_overnight: bool
    late_tolerance_minutes: int
    early_leave_tolerance_minutes: int
    overtime_threshold_minutes: int
    max_work_minutes: int


@dataclass(frozen=True)
class AttendancePolicy:
    """Value object: company-level attendance configuration."""
    company_id: UUID
    late_tolerance_minutes: int = 15
    early_leave_tolerance_minutes: int = 15
    overtime_threshold_minutes: int = 30
    max_work_minutes_per_day: int = 600
    checkin_window_before_minutes: int = 60
    require_selfie: bool = True
    require_gps: bool = True
    allow_wfh: bool = False
    gps_radius_meters: float = 100.0


@dataclass
class AttendanceLog:
    """
    An immutable event record of a single check-in or check-out action.
    Stored in attendance_logs table. Never updated after creation.
    """
    employee_id: UUID
    company_id: UUID
    timestamp_utc: datetime
    type: CheckType
    latitude: float | None = None
    longitude: float | None = None
    accuracy_meters: float | None = None
    photo_url: str | None = None
    device_id: str | None = None
    source: AttendanceSource = AttendanceSource.MOBILE
    id: UUID | None = None


@dataclass
class AttendanceSummary:
    """
    The computed daily attendance result for one employee.
    Derived from AttendanceLogs. Stored in attendance_summaries.
    Can be safely re-computed from raw logs.
    """
    employee_id: UUID
    company_id: UUID
    date: object  # datetime.date
    shift_id: UUID | None = None
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    work_minutes: int = 0
    late_minutes: int = 0
    early_leave_minutes: int = 0
    overtime_minutes: int = 0
    is_late: bool = False
    is_early_leave: bool = False
    is_alpha: bool = False
    is_leave: bool = False
    status: AttendanceStatus = AttendanceStatus.INCOMPLETE
    id: UUID | None = None
