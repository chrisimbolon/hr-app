"""shared/utils/date_utils.py"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.shared.constants.indonesia import TIMEZONE_WIB


def to_local(dt: datetime, tz: str = TIMEZONE_WIB) -> datetime:
    """Convert UTC datetime to local timezone."""
    return dt.astimezone(ZoneInfo(tz))


def now_wib() -> datetime:
    from datetime import timezone
    return datetime.now(ZoneInfo(TIMEZONE_WIB))


def working_days_in_period(start: date, end: date, holidays: set[date] | None = None) -> int:
    """Count weekdays (Mon-Fri) excluding public holidays between start and end inclusive."""
    holidays = holidays or set()
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            count += 1
        current += timedelta(days=1)
    return count


def format_rupiah(amount: float) -> str:
    """Format number as Indonesian Rupiah string. e.g. 5000000 → 'Rp 5.000.000'"""
    return f"Rp {amount:,.0f}".replace(",", ".")


def months_between(start: date, end: date) -> float:
    """Returns fractional months between two dates. Used for THR proration."""
    years = end.year - start.year
    months = end.month - start.month
    days = end.day - start.day
    total_months = years * 12 + months + days / 30.0
    return max(0.0, total_months)
