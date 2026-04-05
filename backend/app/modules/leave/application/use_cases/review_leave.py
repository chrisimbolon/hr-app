"""
leave/application/use_cases/review_leave.py
─────────────────────────────────────────────
ReviewLeaveUseCase: manager approves or rejects a leave request.
Updates both leave_requests, approvals, and leave_balances atomically.
"""
import uuid
from datetime import datetime, timezone

from app.core.exceptions import (AuthorizationError, BusinessRuleError,
                                 NotFoundError)
from app.modules.leave.infrastructure.models import (ApprovalModel,
                                                     LeaveBalanceModel,
                                                     LeaveRequestModel)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ReviewLeaveUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(
        self,
        leave_request_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        action: str,          # "approved" or "rejected"
        notes: str | None = None,
    ) -> LeaveRequestModel:

        if action not in ("approved", "rejected"):
            raise BusinessRuleError("Action must be 'approved' or 'rejected'")

        # ── 1. Load leave request ─────────────────────────────────
        leave_req = await self.db.scalar(
            select(LeaveRequestModel).where(
                LeaveRequestModel.id == leave_request_id
            )
        )
        if not leave_req:
            raise NotFoundError("LeaveRequest", str(leave_request_id))

        if leave_req.status != "pending":
            raise BusinessRuleError(
                f"Cannot review a leave request with status '{leave_req.status}'"
            )

        now = datetime.now(timezone.utc)

        # ── 2. Update leave request ───────────────────────────────
        leave_req.status = action
        leave_req.reviewed_by = reviewer_id
        leave_req.reviewed_at = now
        if action == "rejected":
            leave_req.rejection_reason = notes

        # ── 3. Update generic approval record ────────────────────
        approval = await self.db.scalar(
            select(ApprovalModel).where(
                ApprovalModel.entity_type == "leave",
                ApprovalModel.entity_id == leave_request_id,
            )
        )
        if approval:
            approval.status = action
            approval.reviewer_id = reviewer_id
            approval.notes = notes
            approval.approved_at = now if action == "approved" else None

        # ── 4. Update leave balance ───────────────────────────────
        balance = await self.db.scalar(
            select(LeaveBalanceModel).where(
                LeaveBalanceModel.employee_id == leave_req.employee_id,
                LeaveBalanceModel.leave_type_id == leave_req.leave_type_id,
                LeaveBalanceModel.year == leave_req.start_date.year,
            )
        )
        if balance:
            # Remove from pending regardless
            balance.pending_days = max(0, balance.pending_days - leave_req.total_days)
            if action == "approved":
                balance.used_days += leave_req.total_days

        await self.db.flush()

        # ── 5. Notify employee async ──────────────────────────────
        from app.modules.leave.tasks.leave_jobs import \
            notify_employee_leave_decision
        notify_employee_leave_decision.delay(
            employee_id=str(leave_req.employee_id),
            leave_request_id=str(leave_request_id),
            action=action,
            notes=notes,
        )

        return leave_req
