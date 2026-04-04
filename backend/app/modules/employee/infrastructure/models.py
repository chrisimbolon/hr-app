"""
employee/infrastructure/models.py
───────────────────────────────────
SQLAlchemy models for employees, organizations, and devices.
Also contains Company and OfficeLocation — referenced across modules.
"""
import uuid
from datetime import date, datetime

from app.core.database import Base, TimestampMixin
from sqlalchemy import (Boolean, Date, DateTime, Enum, ForeignKey, Index,
                        Integer, String, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class TenantModel(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(20), default="starter")   # starter/pro/enterprise
    status: Mapped[str] = mapped_column(String(20), default="trial")   # trial/active/suspended
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CompanyModel(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    npwp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    legal_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Jakarta")
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)


class OfficeLocationModel(Base, TimestampMixin):
    __tablename__ = "office_locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    radius_meters: Mapped[int] = mapped_column(Integer, default=100)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class DepartmentModel(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)


class EmployeeModel(Base, TimestampMixin):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("company_id", "employee_code"),
        Index("idx_emp_company_status", "company_id", "status"),
        Index("idx_emp_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    direct_manager_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)

    employee_code: Mapped[str] = mapped_column(String(20), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    employment_type: Mapped[str] = mapped_column(String(20), default="permanent")  # permanent/contract/intern
    join_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    role: Mapped[str] = mapped_column(String(30), default="employee")  # employee/manager/hr_admin/company_admin
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/inactive/terminated

    hashed_pin: Mapped[str | None] = mapped_column(String, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)


class DeviceRegistrationModel(Base, TimestampMixin):
    __tablename__ = "device_registrations"
    __table_args__ = (
        UniqueConstraint("employee_id", "device_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(200), nullable=False)
    fcm_token: Mapped[str | None] = mapped_column(String, nullable=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # android/ios
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── RBAC ────────────────────────────────────────────────────────

class RoleModel(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)


class PermissionModel(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # e.g. "attendance:view_all"
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False)


class RolePermissionModel(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True)


class EmployeeRoleModel(Base):
    __tablename__ = "employee_roles"
    __table_args__ = (UniqueConstraint("employee_id", "role_id"),)

    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
