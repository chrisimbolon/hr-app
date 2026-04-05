"""
leave/presentation/api/v1/routes.py
────────────────────────────────────
Leave management API. Thin routes, all logic in use cases.
"""
from uuid import UUID

from app.core.dependencies import get_current_employee, get_db, require_roles
from app.modules.leave.application.schemas import (LeaveRequestResponse,
                                                   LeaveTypeResponse,
                                                   ReviewLeaveRequest,
                                                   SubmitLeaveRequest)
from app.modules.leave.application.use_cases.review_leave import \
    ReviewLeaveUseCase
from app.modules.leave.application.use_cases.submit_leave import \
    SubmitLeaveUseCase
from app.modules.leave.infrastructure.models import (ApprovalModel,
                                                     LeaveBalanceModel,
                                                     LeaveRequestModel,
                                                     LeaveTypeModel)
from app.shared.schemas.base import ApiResponse, PaginatedResponse
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/types", response_model=ApiResponse[list[LeaveTypeResponse]])
async def list_leave_types(
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """All leave types for the company with employee's current balance."""
    from datetime import date
    year = date.today().year

    types = await db.execute(
        select(LeaveTypeModel).where(LeaveTypeModel.company_id == employee.company_id)
    )
    leave_types = types.scalars().all()

    result = []
    for lt in leave_types:
        balance = await db.scalar(
            select(LeaveBalanceModel).where(
                LeaveBalanceModel.employee_id == employee.id,
                LeaveBalanceModel.leave_type_id == lt.id,
                LeaveBalanceModel.year == year,
            )
        )
        from app.modules.leave.application.schemas import BalanceSummary
        result.append(LeaveTypeResponse(
            id=lt.id,
            name=lt.name,
            code=lt.code,
            is_paid=lt.is_paid,
            requires_document=lt.requires_document,
            max_days_per_year=lt.max_days_per_year,
            balance=BalanceSummary(
                total_entitlement=balance.total_entitlement if balance else 0,
                used_days=balance.used_days if balance else 0,
                pending_days=balance.pending_days if balance else 0,
                carried_forward=balance.carried_forward if balance else 0,
                remaining_days=balance.remaining_days if balance else 0,
            ) if balance else None,
        ))
    return ApiResponse(data=result)


@router.post("/requests", response_model=ApiResponse[dict], status_code=201)
async def submit_leave(
    leave_type_id: UUID = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    reason: str = Form(...),
    half_day_type: str | None = Form(default=None),
    document: UploadFile | None = File(default=None),
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """Submit a leave request. Document upload optional (required for some types)."""
    from datetime import date
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(422, "Invalid date format. Use YYYY-MM-DD.")

    doc_bytes = None
    doc_name = None
    if document and document.filename:
        doc_bytes = await document.read()
        doc_name = document.filename
        if len(doc_bytes) > 5 * 1024 * 1024:
            raise HTTPException(422, "Document too large. Maximum 5MB.")

    use_case = SubmitLeaveUseCase(db)
    leave_req = await use_case.execute(
        employee_id=employee.id,
        company_id=employee.company_id,
        leave_type_id=leave_type_id,
        start_date=start,
        end_date=end,
        reason=reason,
        half_day_type=half_day_type,
        document_bytes=doc_bytes,
        document_filename=doc_name,
    )

    return ApiResponse(
        data={"id": str(leave_req.id), "status": leave_req.status},
        message="Permohonan izin berhasil dikirim. Menunggu persetujuan atasan.",
    )


@router.get("/requests", response_model=ApiResponse[list[dict]])
async def list_leave_requests(
    status: str | None = None,
    year: int | None = None,
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """Employee's own leave request history."""
    from datetime import date

    from sqlalchemy import and_, extract

    conditions = [LeaveRequestModel.employee_id == employee.id]
    if status:
        conditions.append(LeaveRequestModel.status == status)
    if year:
        conditions.append(extract("year", LeaveRequestModel.start_date) == year)

    rows = await db.execute(
        select(LeaveRequestModel, LeaveTypeModel)
        .join(LeaveTypeModel, LeaveTypeModel.id == LeaveRequestModel.leave_type_id)
        .where(and_(*conditions))
        .order_by(LeaveRequestModel.created_at.desc())
    )

    result = [
        {
            "id": str(req.id),
            "leave_type": lt.name,
            "start_date": req.start_date.isoformat(),
            "end_date": req.end_date.isoformat(),
            "total_days": req.total_days,
            "status": req.status,
            "reason": req.reason,
            "reviewed_at": req.reviewed_at.isoformat() if req.reviewed_at else None,
        }
        for req, lt in rows.all()
    ]
    return ApiResponse(data=result)


@router.patch("/requests/{request_id}/review", response_model=ApiResponse[dict])
async def review_leave(
    request_id: UUID,
    body: ReviewLeaveRequest,
    employee=Depends(require_roles("manager", "hr_admin", "company_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Manager approves or rejects a leave request."""
    use_case = ReviewLeaveUseCase(db)
    leave_req = await use_case.execute(
        leave_request_id=request_id,
        reviewer_id=employee.id,
        action=body.action,
        notes=body.notes,
    )
    action_msg = "disetujui" if body.action == "approved" else "ditolak"
    return ApiResponse(
        data={"id": str(leave_req.id), "status": leave_req.status},
        message=f"Permohonan izin berhasil {action_msg}.",
    )


@router.get("/team-pending", response_model=ApiResponse[list[dict]])
async def team_pending_approvals(
    employee=Depends(require_roles("manager", "hr_admin", "company_admin")),
    db: AsyncSession = Depends(get_db),
):
    """All pending approvals for the manager's team — leave, overtime, adjustments."""
    rows = await db.execute(
        select(ApprovalModel).where(
            ApprovalModel.company_id == employee.company_id,
            ApprovalModel.status == "pending",
        ).order_by(ApprovalModel.created_at.asc())
    )
    approvals = rows.scalars().all()
    return ApiResponse(
        data=[
            {
                "id": str(a.id),
                "entity_type": a.entity_type,
                "entity_id": str(a.entity_id),
                "requester_id": str(a.requester_id),
                "created_at": a.created_at.isoformat(),
            }
            for a in approvals
        ]
    )
