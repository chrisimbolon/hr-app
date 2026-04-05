"""
payroll/infrastructure/models.py
──────────────────────────────────
All payroll-related SQLAlchemy models.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.core.database import Base, TimestampMixin
from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Index, Integer,
                        Numeric, String, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class PayrollPeriodModel(Base, TimestampMixin):
    __tablename__ = "payroll_periods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open/locked/processed


class EmployeeSalaryModel(Base, TimestampMixin):
    __tablename__ = "employee_salaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)


class SalaryComponentModel(Base, TimestampMixin):
    __tablename__ = "salary_components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)   # allowance/deduction
    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=True)


class EmployeeSalaryComponentModel(Base, TimestampMixin):
    __tablename__ = "employee_salary_components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("salary_components.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)


class BpjsConfigModel(Base, TimestampMixin):
    __tablename__ = "bpjs_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), unique=True, nullable=False)
    kesehatan_employee_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"))
    kesehatan_company_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("4.00"))
    tk_jht_employee_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.00"))
    tk_jht_company_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("3.70"))
    tk_jp_employee_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"))
    tk_jp_company_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.00"))
    tk_jkk_company_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.24"))
    tk_jkm_company_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.30"))


class TaxProfileModel(Base, TimestampMixin):
    __tablename__ = "tax_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), unique=True, nullable=False)
    npwp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    marital_status: Mapped[str] = mapped_column(String(5), default="TK0")  # TK0/K0/K1/K2/K3
    dependents: Mapped[int] = mapped_column(Integer, default=0)
    tax_method: Mapped[str] = mapped_column(String(20), default="progressive")  # progressive/ter


class PayrollResultModel(Base, TimestampMixin):
    __tablename__ = "payroll_results"
    __table_args__ = (UniqueConstraint("payroll_period_id", "employee_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payroll_period_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payroll_periods.id"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)

    total_present_days: Mapped[int] = mapped_column(Integer, default=0)
    total_absent_days: Mapped[int] = mapped_column(Integer, default=0)
    total_late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    total_overtime_minutes: Mapped[int] = mapped_column(Integer, default=0)

    base_salary: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_allowances: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    overtime_pay: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    bpjs_kesehatan: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    bpjs_tk: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    pph21_tax: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    net_salary: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ThrRecordModel(Base, TimestampMixin):
    __tablename__ = "thr_records"
    __table_args__ = (UniqueConstraint("employee_id", "year"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    religion: Mapped[str] = mapped_column(String(20), default="Islam")
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    months_worked: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PayslipModel(Base, TimestampMixin):
    __tablename__ = "payslips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payroll_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payroll_results.id"), unique=True, nullable=False)
    file_url: Mapped[str] = mapped_column(String, nullable=False)  # R2 presigned URL
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
