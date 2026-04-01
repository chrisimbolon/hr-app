"""
attendance/presentation/api/v1/routes.py
──────────────────────────────────────────
Attendance API routes. Thin as possible.
Routes receive HTTP, call use cases, return responses.
Zero business logic here.
"""
from app.core.dependencies import get_current_employee, get_db
from app.modules.attendance.application.schemas import (
    AttendanceSummaryResponse, CheckInResponse, CheckOutResponse,
    TodayStatusResponse)
from app.modules.attendance.application.use_cases.check_in import \
    CheckInUseCase
from app.modules.attendance.application.use_cases.check_out import \
    CheckOutUseCase
from app.shared.schemas.base import ApiResponse
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/check-in", response_model=ApiResponse[CheckInResponse], status_code=201)
async def check_in(
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy_meters: float = Form(...),
    device_id: str = Form(...),
    client_timestamp: str = Form(...),
    location_type: str = Form(default="wfo"),
    selfie_photo: UploadFile = File(...),
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """
    Record employee check-in with GPS coordinates and selfie photo.
    Multipart/form-data — photo uploaded alongside form fields.
    """
    if selfie_photo.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(422, "Selfie must be JPEG, PNG, or WebP")

    photo_bytes = await selfie_photo.read()
    if len(photo_bytes) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(422, "Photo too large. Maximum 5MB.")

    from datetime import datetime
    try:
        ts = datetime.fromisoformat(client_timestamp)
    except ValueError:
        raise HTTPException(422, "Invalid client_timestamp format. Use ISO 8601.")

    # Load office location for GPS validation
    from app.core.database import AsyncSession as AS
    from sqlalchemy import select, text
    office = await db.execute(
        text("""
            SELECT ol.latitude, ol.longitude, ol.radius_meters
            FROM office_locations ol
            WHERE ol.company_id = :cid AND ol.is_primary = true
            LIMIT 1
        """),
        {"cid": str(employee.company_id)},
    )
    office_row = office.fetchone()
    if not office_row:
        raise HTTPException(400, "No office location configured. Contact your HR admin.")

    from app.modules.attendance.application.schemas import CheckInRequest
    req = CheckInRequest(
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
        device_id=device_id,
        client_timestamp=ts,
        location_type=location_type,
    )

    use_case = CheckInUseCase(db)
    result = await use_case.execute(
        employee_id=employee.id,
        company_id=employee.company_id,
        office_lat=office_row.latitude,
        office_lng=office_row.longitude,
        office_radius=office_row.radius_meters,
        request=req,
        photo_bytes=photo_bytes,
    )

    return ApiResponse(data=result, message=result.message)


@router.post("/check-out", response_model=ApiResponse[CheckOutResponse])
async def check_out(
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy_meters: float = Form(...),
    device_id: str = Form(...),
    client_timestamp: str = Form(...),
    selfie_photo: UploadFile = File(...),
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """Record employee check-out with GPS and selfie."""
    if selfie_photo.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(422, "Selfie must be JPEG, PNG, or WebP")

    photo_bytes = await selfie_photo.read()

    from datetime import datetime
    ts = datetime.fromisoformat(client_timestamp)

    from app.modules.attendance.application.schemas import CheckOutRequest
    req = CheckOutRequest(
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
        device_id=device_id,
        client_timestamp=ts,
    )

    use_case = CheckOutUseCase(db)
    result = await use_case.execute(
        employee_id=employee.id,
        company_id=employee.company_id,
        request=req,
        photo_bytes=photo_bytes,
    )
    return ApiResponse(data=result, message="Berhasil check-out. Selamat istirahat!")


@router.get("/today", response_model=ApiResponse[TodayStatusResponse])
async def today_status(
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """Get today's attendance status for the current employee."""
    from datetime import date, datetime, timezone

    from app.modules.attendance.infrastructure.repository import \
        AttendanceRepository
    from app.shared.enums.attendance import AttendanceStatus, CheckType

    repo = AttendanceRepository(db)
    today = datetime.now(timezone.utc).date()

    checkin = await repo.get_today_log(employee.id, CheckType.CHECK_IN)
    checkout = await repo.get_today_log(employee.id, CheckType.CHECK_OUT)
    summary = await repo.get_summary(employee.id, today)
    shift = await repo.get_active_shift(employee.id, today)

    shift_info = None
    if shift:
        shift_info = {
            "name": "Reguler",
            "start_time": shift.start_time.strftime("%H:%M"),
            "end_time": shift.end_time.strftime("%H:%M"),
            "break_minutes": shift.break_minutes,
        }

    return ApiResponse(
        data=TodayStatusResponse(
            date=today.isoformat(),
            shift=shift_info,
            check_in_at=checkin.timestamp_utc if checkin else None,
            check_out_at=checkout.timestamp_utc if checkout else None,
            status=summary.status if summary else AttendanceStatus.INCOMPLETE,
            can_check_in=checkin is None,
            can_check_out=checkin is not None and checkout is None,
            is_late=summary.is_late if summary else False,
            late_minutes=summary.late_minutes if summary else 0,
            work_minutes=summary.work_minutes if summary else 0,
        )
    )


@router.get("/summary/{month}", response_model=ApiResponse[AttendanceSummaryResponse])
async def monthly_summary(
    month: str,  # format: 2026-03
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """
    Monthly attendance summary for the current employee.
    Feeds the Rekap Absensi screen and payroll engine.
    """
    try:
        year, mon = int(month.split("-")[0]), int(month.split("-")[1])
    except (ValueError, IndexError):
        raise HTTPException(400, "Invalid month format. Use YYYY-MM (e.g. 2026-03)")

    from app.modules.attendance.infrastructure.queries import get_monthly_rekap
    from app.modules.attendance.infrastructure.repository import \
        AttendanceRepository

    repo = AttendanceRepository(db)
    summaries = await repo.get_monthly_summaries(employee.id, year, mon)

    days_present = sum(1 for s in summaries if s.status.value in ("present", "late"))
    days_alpha = sum(1 for s in summaries if s.is_alpha)
    days_leave = sum(1 for s in summaries if s.is_leave)
    late_count = sum(1 for s in summaries if s.is_late)
    total_late_min = sum(s.late_minutes for s in summaries)
    early_leave_count = sum(1 for s in summaries if s.is_early_leave)
    total_ot_min = sum(s.overtime_minutes for s in summaries)
    working_days = len(summaries)
    rate = round((days_present / working_days * 100), 1) if working_days > 0 else 0.0

    from app.modules.attendance.application.schemas import (DailyLogEntry,
                                                            PayrollImpact)
    daily = [
        DailyLogEntry(
            date=s.date.isoformat(),
            status=s.status,
            check_in_at=s.check_in_time,
            check_out_at=s.check_out_time,
            work_minutes=s.work_minutes,
            late_minutes=s.late_minutes,
            overtime_minutes=s.overtime_minutes,
            is_late=s.is_late,
            is_alpha=s.is_alpha,
        )
        for s in summaries
    ]

    return ApiResponse(
        data=AttendanceSummaryResponse(
            employee_id=employee.id,
            period=f"{year}-{mon:02d}",
            working_days_scheduled=working_days,
            days_present=days_present,
            days_alpha=days_alpha,
            days_leave=days_leave,
            late_count=late_count,
            total_late_minutes=total_late_min,
            early_leave_count=early_leave_count,
            total_overtime_minutes=total_ot_min,
            attendance_rate=rate,
            payroll_impact=PayrollImpact(
                alpha_deduction_days=days_alpha,
                late_deduction_minutes=total_late_min,
                overtime_hours=round(total_ot_min / 60, 1),
            ),
            daily_logs=daily,
        )
    )
