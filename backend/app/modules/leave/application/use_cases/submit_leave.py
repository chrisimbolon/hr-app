"""
leave/application/use_cases/submit_leave.py
─────────────────────────────────────────────
SubmitLeaveUseCase: validates quota, creates leave_request +
approval record, fires async notifications.
"""
import uuid
from datetime import datetime, timezone

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.leave.infrastructure.models import (ApprovalModel,
                                                     LeaveBalanceModel,
                                                     LeaveDocumentModel,
                                                     LeaveRequestModel,
                                                     LeaveTypeModel)
from app.shared.utils.date_utils import working_days_in_period
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession


class SubmitLeaveUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(
        self,
        employee_id: uuid.UUID,
        company_id: uuid.UUID,
        leave_type_id: uuid.UUID,
        start_date: object,
        end_date: object,
        reason: str,
        half_day_type: str | None = None,
        document_url: str | None = None,
        document_name: str | None = None,
    ) -> LeaveRequestModel:

        # ── 1. Validate leave type exists for this company ───────
        leave_type = await self.db.scalar(
            select(LeaveTypeModel).where(
                LeaveTypeModel.id == leave_type_id,
                LeaveTypeModel.company_id == company_id,
            )
        )
        if not leave_type:
            raise NotFoundError("Leave type")

        # ── 2. Calculate total days (working days only) ──────────
        total_days = working_days_in_period(start_date, end_date)
        if half_day_type:
            total_days = 0.5
        if total_days <= 0:
            raise BusinessRuleError("No working days in selected date range.")

        # ── 3. Document required check ───────────────────────────
        if leave_type.requires_document and total_days > leave_type.document_required_after_days:
            if not document_url:
                raise BusinessRuleError(
                    f"Document required for {leave_type.name} "
                    f"exceeding {leave_type.document_required_after_days} days."
                )

        # ── 4. Balance / quota check ─────────────────────────────
        year = start_date.year
        balance = await self.db.scalar(
            select(LeaveBalanceModel).where(
                and_(
                    LeaveBalanceModel.employee_id == employee_id,
                    LeaveBalanceModel.leave_type_id == leave_type_id,
                    LeaveBalanceModel.year == year,
                )
            )
        )
        if not balance:
            raise BusinessRuleError(f"No leave balance found for {leave_type.name} in {year}.")

        available = balance.total_entitlement + balance.carried_forward - balance.used_days - balance.pending_days
        if available < total_days:
            raise BusinessRuleError(
                f"Insufficient {leave_type.name} balance. "
                f"Available: {available} days, Requested: {total_days} days."
            )

        # ── 5. No overlapping approved/pending leave ─────────────
        overlap = await self.db.scalar(
            select(LeaveRequestModel).where(
                and_(
                    LeaveRequestModel.employee_id == employee_id,
                    LeaveRequestModel.status.in_(["pending", "approved"]),
                    LeaveRequestModel.start_date <= end_date,
                    LeaveRequestModel.end_date >= start_date,
                )
            )
        )
        if overlap:
            raise BusinessRuleError("You already have a leave request overlapping this date range.")

        # ── 6. Create leave request ──────────────────────────────
        leave_request = LeaveRequestModel(
            id=uuid.uuid4(),
            employee_id=employee_id,
            company_id=company_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            total_days=int(total_days),
            half_day_type=half_day_type,
            reason=reason,
            status="pending",
        )
        self.db.add(leave_request)
        await self.db.flush()

        # ── 7. Create generic approval record ────────────────────
        approval = ApprovalModel(
            id=uuid.uuid4(),
            company_id=company_id,
            entity_type="leave",
            entity_id=leave_request.id,
            requester_id=employee_id,
            status="pending",
        )
        self.db.add(approval)

        # ── 8. Attach document if provided ───────────────────────
        if document_url:
            doc = LeaveDocumentModel(
                id=uuid.uuid4(),
                leave_request_id=leave_request.id,
                file_url=document_url,
                file_name=document_name or "document",
            )
            self.db.add(doc)

        # ── 9. Update pending balance ─────────────────────────────
        balance.pending_days += int(total_days)
        await self.db.flush()

        # ── 10. Fire async notifications ─────────────────────────
        from app.modules.leave.tasks.leave_jobs import notify_manager_new_leave
        notify_manager_new_leave.delay(
            employee_id=str(employee_id),
            leave_request_id=str(leave_request.id),
            leave_type_name=leave_type.name,
            total_days=int(total_days),
            start_date=str(start_date),
        )

        return leave_request
