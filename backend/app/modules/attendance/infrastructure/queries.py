"""
attendance/infrastructure/queries.py
──────────────────────────────────────
Read-optimised SQL queries for attendance reporting.

Separate from the repository (which handles single-entity CRUD)
because monthly summaries require aggregation across many rows
and are better expressed as raw SQL than ORM queries.
"""
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_monthly_rekap(
    db: AsyncSession,
    employee_id: UUID,
    year: int,
    month: int,
) -> dict:
    """
    Return a monthly attendance summary for one employee.

    Aggregates attendance_summaries rows for the given month.
    Returns a dict matching the AttendanceSummaryResponse schema.

    If no data exists yet (new employee, no check-ins recorded),
    returns zeroed-out values rather than raising an error.
    """
    # Pull all daily summaries for the month
    result = await db.execute(
        text("""
            SELECT
                COUNT(*)                                            AS total_days,
                COUNT(*) FILTER (WHERE status = 'present')         AS days_present,
                COUNT(*) FILTER (WHERE status = 'late')            AS days_late,
                COUNT(*) FILTER (WHERE status = 'alpha')           AS days_alpha,
                COUNT(*) FILTER (WHERE status = 'leave')           AS days_leave,
                COUNT(*) FILTER (WHERE status = 'holiday')         AS days_holiday,
                COUNT(*) FILTER (WHERE is_late = true)             AS late_count,
                COALESCE(SUM(late_minutes), 0)                     AS total_late_minutes,
                COALESCE(SUM(early_leave_minutes), 0)              AS total_early_leave_minutes,
                COALESCE(SUM(overtime_minutes), 0)                 AS total_overtime_minutes,
                COALESCE(SUM(work_minutes), 0)                     AS total_work_minutes
            FROM attendance_summaries
            WHERE
                employee_id = :employee_id
                AND EXTRACT(YEAR  FROM date) = :year
                AND EXTRACT(MONTH FROM date) = :month
        """),
        {"employee_id": str(employee_id), "year": year, "month": month},
    )
    row = result.mappings().one_or_none()

    # Working days = days the employee was expected to work (not holiday/weekend)
    working_days_result = await db.execute(
        text("""
            SELECT COUNT(*) AS working_days
            FROM attendance_summaries
            WHERE
                employee_id = :employee_id
                AND EXTRACT(YEAR  FROM date) = :year
                AND EXTRACT(MONTH FROM date) = :month
                AND is_alpha = false
                AND status != 'holiday'
        """),
        {"employee_id": str(employee_id), "year": year, "month": month},
    )
    wd_row = working_days_result.mappings().one_or_none()

    if not row or row["total_days"] == 0:
        # No attendance data yet — return zeroed structure
        return {
            "employee_id": str(employee_id),
            "period": f"{year}-{month:02d}",
            "working_days_scheduled": 0,
            "days_present": 0,
            "days_alpha": 0,
            "days_leave": 0,
            "days_holiday": 0,
            "late_count": 0,
            "total_late_minutes": 0,
            "total_overtime_minutes": 0,
            "attendance_rate": 0.0,
            "payroll_impact": {
                "alpha_deduction_days": 0,
                "late_deduction_minutes": 0,
                "overtime_hours": 0,
            },
            "daily_logs": [],
        }

    days_present = int(row["days_present"] or 0)
    days_late    = int(row["days_late"] or 0)
    days_alpha   = int(row["days_alpha"] or 0)
    working_days = int(wd_row["working_days"] or 0) if wd_row else 0
    attendance_rate = (days_present + days_late) / working_days * 100 if working_days > 0 else 0.0
    overtime_minutes = int(row["total_overtime_minutes"] or 0)

    # Pull daily logs for the chart
    logs_result = await db.execute(
        text("""
            SELECT
                date::text                  AS date,
                status,
                check_in_time::text         AS check_in_at,
                check_out_time::text        AS check_out_at,
                work_minutes,
                late_minutes,
                overtime_minutes,
                is_late,
                is_alpha
            FROM attendance_summaries
            WHERE
                employee_id = :employee_id
                AND EXTRACT(YEAR  FROM date) = :year
                AND EXTRACT(MONTH FROM date) = :month
            ORDER BY date ASC
        """),
        {"employee_id": str(employee_id), "year": year, "month": month},
    )
    daily_logs = [dict(r) for r in logs_result.mappings().all()]

    return {
        "employee_id": str(employee_id),
        "period": f"{year}-{month:02d}",
        "working_days_scheduled": working_days,
        "days_present": days_present,
        "days_alpha": days_alpha,
        "days_leave": int(row["days_leave"] or 0),
        "days_holiday": int(row["days_holiday"] or 0),
        "late_count": int(row["late_count"] or 0),
        "total_late_minutes": int(row["total_late_minutes"] or 0),
        "total_overtime_minutes": overtime_minutes,
        "attendance_rate": round(attendance_rate, 1),
        "payroll_impact": {
            "alpha_deduction_days": days_alpha,
            "late_deduction_minutes": int(row["total_late_minutes"] or 0),
            "overtime_hours": round(overtime_minutes / 60, 1),
        },
        "daily_logs": daily_logs,
    }
