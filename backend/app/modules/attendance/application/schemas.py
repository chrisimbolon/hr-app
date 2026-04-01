"""
attendance/application/schemas.py
───────────────────────────────────
Pydantic models for attendance API request/response.
These live in application/ — they serve the presentation layer,
not the domain layer (which uses pure dataclasses).
"""
from datetime import datetime
from uuid import UUID

from app.shared.enums.attendance import AttendanceSource, AttendanceStatus
from app.shared.schemas.base import BaseSchema
from pydantic import Field

# ── Check-in ────────────────────────────────────────────────────

class CheckInRequest(BaseSchema):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_meters: float = Field(..., ge=0, le=5000)
    device_id: str = Field(..., min_length=10, max_length=200)
    client_timestamp: datetime
    location_type: str = "wfo"


class CheckInResponse(BaseSchema):
    log_id: UUID
    status: str
    check_in_at: datetime
    is_late: bool
    late_minutes: int
    location_valid: bool
    distance_meters: int
    message: str


# ── Check-out ────────────────────────────────────────────────────

class CheckOutRequest(BaseSchema):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_meters: float = Field(..., ge=0)
    device_id: str = Field(..., min_length=10, max_length=200)
    client_timestamp: datetime


class CheckOutResponse(BaseSchema):
    log_id: UUID
    check_out_at: datetime
    work_minutes: int
    work_hours_display: str
    is_early_leave: bool
    early_leave_minutes: int
    overtime_minutes: int
    overtime_detected: bool


# ── Today status ─────────────────────────────────────────────────

class ShiftInfo(BaseSchema):
    name: str
    start_time: str
    end_time: str
    break_minutes: int


class TodayStatusResponse(BaseSchema):
    date: str
    shift: ShiftInfo | None
    check_in_at: datetime | None
    check_out_at: datetime | None
    status: AttendanceStatus
    can_check_in: bool
    can_check_out: bool
    is_late: bool
    late_minutes: int
    work_minutes: int


# ── Monthly summary ──────────────────────────────────────────────

class DailyLogEntry(BaseSchema):
    date: str
    status: AttendanceStatus
    check_in_at: datetime | None
    check_out_at: datetime | None
    work_minutes: int
    late_minutes: int
    overtime_minutes: int
    is_late: bool
    is_alpha: bool


class PayrollImpact(BaseSchema):
    alpha_deduction_days: int
    late_deduction_minutes: int
    overtime_hours: float


class AttendanceSummaryResponse(BaseSchema):
    employee_id: UUID
    period: str
    working_days_scheduled: int
    days_present: int
    days_alpha: int
    days_leave: int
    late_count: int
    total_late_minutes: int
    early_leave_count: int
    total_overtime_minutes: int
    attendance_rate: float
    payroll_impact: PayrollImpact
    daily_logs: list[DailyLogEntry]
