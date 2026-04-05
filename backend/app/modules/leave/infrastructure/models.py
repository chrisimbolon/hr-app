"""leave/infrastructure/models.py"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.core.database import Base, TimestampMixin
from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Index, Integer,
                        Numeric, String, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class LeaveTypeModel(Base, TimestampMixin):
    __tablename__ = "leave_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)        # SICK/ANNUAL/MATERNITY
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_document: Mapped[bool] = mapped_column(Boolean, default=False)
    document_required_after_days: Mapped[int] = mapped_column(Integer, default=2)
    max_days_per_year: Mapped[int] = mapped_column(Integer, default=12)
    allow_carry_forward: Mapped[bool] = mapped_column(Boolean, default=False)
    gender_restriction: Mapped[str | None] = mapped_column(String(10), nullable=True)  # M/F/None


class LeaveBalanceModel(Base, TimestampMixin):
    __tablename__ = "leave_balances"
    __table_args__ = (UniqueConstraint("employee_id", "leave_type_id", "year"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    leave_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_entitlement: Mapped[int] = mapped_column(Integer, nullable=False)
    used_days: Mapped[int] = mapped_column(Integer, default=0)
    pending_days: Mapped[int] = mapped_column(Integer, default=0)
    carried_forward: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def remaining_days(self) -> int:
        return self.total_entitlement + self.carried_forward - self.used_days - self.pending_days


class LeaveRequestModel(Base, TimestampMixin):
    __tablename__ = "leave_requests"
    __table_args__ = (
        Index("idx_lr_employee_status", "employee_id", "status"),
        Index("idx_lr_company_status", "company_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    leave_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[int] = mapped_column(Integer, nullable=False)
    half_day_type: Mapped[str | None] = mapped_column(String(2), nullable=True)  # am/pm
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class LeaveDocumentModel(Base, TimestampMixin):
    __tablename__ = "leave_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    leave_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leave_requests.id"), nullable=False)
    file_url: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApprovalModel(Base, TimestampMixin):
    """
    Generic approval engine. One table covers all approvable entities.
    entity_type = 'leave' | 'overtime' | 'attendance_adjustment'
    entity_id = UUID of the specific record being approved.
    """
    __tablename__ = "approvals"
    __table_args__ = (
        Index("idx_approvals_pending", "company_id", "status", "entity_type"),
        Index("idx_approvals_reviewer", "reviewer_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
