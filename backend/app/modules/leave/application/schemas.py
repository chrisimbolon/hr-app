"""leave/application/schemas.py"""
from datetime import date
from uuid import UUID

from app.shared.schemas.base import BaseSchema
from pydantic import Field


class LeaveTypeResponse(BaseSchema):
    id: UUID
    name: str
    code: str
    is_paid: bool
    requires_document: bool
    max_days_per_year: int
    balance: "BalanceSummary | None" = None


class BalanceSummary(BaseSchema):
    total_entitlement: int
    used_days: int
    pending_days: int
    carried_forward: int
    remaining_days: int


class SubmitLeaveRequest(BaseSchema):
    leave_type_id: UUID
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=10, max_length=1000)
    half_day_type: str | None = None  # "am" or "pm"


class ReviewLeaveRequest(BaseSchema):
    action: str = Field(..., pattern="^(approved|rejected)$")
    notes: str | None = Field(None, max_length=500)


class LeaveRequestResponse(BaseSchema):
    id: UUID
    leave_type_name: str
    start_date: date
    end_date: date
    total_days: int
    reason: str
    status: str
    created_at: object
