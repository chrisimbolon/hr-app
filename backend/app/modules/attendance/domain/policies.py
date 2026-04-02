"""
attendance/domain/policies.py
──────────────────────────────
Pure Python business rules for attendance.
Zero external dependencies. 100% unit-testable without a DB.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.modules.attendance.domain.entities import (AttendancePolicy,
                                                    ShiftPolicy)


class AttendancePolicyEngine:
    """
    Evaluates attendance rules against raw check-in/out events.
    Reads policy config from AttendancePolicy value object (loaded from DB).
    Completely stateless — pass in values, get back results.
    """

    def __init__(self, policy: AttendancePolicy, shift: ShiftPolicy):
        self.policy = policy
        self.shift = shift

    # ── Late detection ───────────────────────────────────────────

    def is_late(self, check_in_utc: datetime) -> bool:
        """Returns True if check-in is after shift start + tolerance."""
        deadline = self._shift_start_utc(check_in_utc) + timedelta(
            minutes=self.shift.late_tolerance_minutes
        )
        return check_in_utc > deadline

    def late_minutes(self, check_in_utc: datetime) -> int:
        """Minutes late relative to shift start. 0 if on time."""
        shift_start = self._shift_start_utc(check_in_utc)
        delta = (check_in_utc - shift_start).total_seconds()
        return max(0, int(delta / 60))

    # ── Early leave detection ─────────────────────────────────────

    def is_early_leave(self, check_out_utc: datetime) -> bool:
        """Returns True if check-out is before shift end - tolerance."""
        cutoff = self._shift_end_utc(check_out_utc) - timedelta(
            minutes=self.shift.early_leave_tolerance_minutes
        )
        return check_out_utc < cutoff

    def early_leave_minutes(self, check_out_utc: datetime) -> int:
        """Minutes left early relative to shift end. 0 if on time."""
        shift_end = self._shift_end_utc(check_out_utc)
        delta = (shift_end - check_out_utc).total_seconds()
        return max(0, int(delta / 60))

    # ── Work hours ────────────────────────────────────────────────

    def work_minutes(self, check_in_utc: datetime, check_out_utc: datetime) -> int:
        """Effective work minutes excluding break time."""
        raw_minutes = int((check_out_utc - check_in_utc).total_seconds() / 60)
        return max(0, raw_minutes - self.shift.break_minutes)

    def overtime_minutes(self, check_in_utc: datetime, check_out_utc: datetime) -> int:
        """Overtime minutes beyond shift end + threshold."""
        shift_end = self._shift_end_utc(check_out_utc)
        threshold = shift_end + timedelta(minutes=self.shift.overtime_threshold_minutes)
        if check_out_utc <= threshold:
            return 0
        return int((check_out_utc - shift_end).total_seconds() / 60)

    # ── Check-in window ───────────────────────────────────────────

    def is_within_checkin_window(self, check_in_utc: datetime) -> bool:
        """
        Returns True if check-in is within allowed window.
        Window: shift_start - checkin_window_before_minutes → shift_start + 4 hours
        """
        shift_start = self._shift_start_utc(check_in_utc)
        earliest = shift_start - timedelta(minutes=self.policy.checkin_window_before_minutes)
        latest = shift_start + timedelta(hours=4)
        return earliest <= check_in_utc <= latest

    # ── Helpers ───────────────────────────────────────────────────

    def _shift_start_utc(self, reference_utc: datetime) -> datetime:
        """Construct shift start as UTC datetime on the same calendar date."""
        # Work in local time to handle DST correctly
        tz = ZoneInfo("Asia/Jakarta")
        local_date = reference_utc.astimezone(tz).date()
        local_start = datetime.combine(local_date, self.shift.start_time, tzinfo=tz)
        return local_start.astimezone(timezone.utc)

    def _shift_end_utc(self, reference_utc: datetime) -> datetime:
        """Construct shift end as UTC datetime. Handles overnight shifts."""
        tz = ZoneInfo("Asia/Jakarta")
        local_date = reference_utc.astimezone(tz).date()
        local_end = datetime.combine(local_date, self.shift.end_time, tzinfo=tz)
        if self.shift.is_overnight:
            local_end += timedelta(days=1)
        return local_end.astimezone(timezone.utc)
