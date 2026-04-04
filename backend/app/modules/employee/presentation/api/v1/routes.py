"""employee/presentation/api/v1/routes.py — Employee management API."""
from uuid import UUID

from app.core.dependencies import get_current_employee, get_db, require_roles
from app.core.security import hash_password
from app.modules.employee.infrastructure.models import (DepartmentModel,
                                                        EmployeeModel)
from app.shared.schemas.base import ApiResponse, PaginatedResponse
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class CreateEmployeeRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = None
    department_id: UUID | None = None
    direct_manager_id: UUID | None = None
    employment_type: str = "permanent"
    join_date: str
    role: str = "employee"
    default_pin: str = Field("1234", min_length=4, max_length=8)


class UpdateEmployeeRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    department_id: UUID | None = None
    direct_manager_id: UUID | None = None
    role: str | None = None
    status: str | None = None


@router.get("/me", response_model=ApiResponse[dict])
async def get_my_profile(employee=Depends(get_current_employee)):
    """Current employee's own profile."""
    return ApiResponse(data={
        "id": str(employee.id),
        "employee_code": employee.employee_code,
        "full_name": employee.full_name,
        "email": employee.email,
        "phone": employee.phone,
        "role": employee.role,
        "employment_type": employee.employment_type,
        "join_date": employee.join_date.isoformat(),
        "status": employee.status,
        "company_id": str(employee.company_id),
    })


@router.get("/", response_model=ApiResponse[list[dict]])
async def list_employees(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    department_id: UUID | None = None,
    status: str = "active",
    employee=Depends(require_roles("hr_admin", "company_admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Paginated employee list with filters. HR admin / manager only."""
    from sqlalchemy import func

    conditions = [
        EmployeeModel.company_id == employee.company_id,
        EmployeeModel.status == status,
    ]
    if search:
        conditions.append(
            EmployeeModel.full_name.ilike(f"%{search}%") |
            EmployeeModel.employee_code.ilike(f"%{search}%")
        )
    if department_id:
        conditions.append(EmployeeModel.department_id == department_id)

    offset = (page - 1) * page_size
    rows = await db.execute(
        select(EmployeeModel).where(and_(*conditions))
        .order_by(EmployeeModel.full_name)
        .limit(page_size).offset(offset)
    )
    employees = rows.scalars().all()

    total = await db.scalar(
        select(func.count()).select_from(EmployeeModel).where(and_(*conditions))
    )

    return ApiResponse(data=[
        {
            "id": str(e.id),
            "employee_code": e.employee_code,
            "full_name": e.full_name,
            "email": e.email,
            "role": e.role,
            "department_id": str(e.department_id) if e.department_id else None,
            "status": e.status,
            "join_date": e.join_date.isoformat(),
        }
        for e in employees
    ])


@router.post("/", response_model=ApiResponse[dict], status_code=201)
async def create_employee(
    body: CreateEmployeeRequest,
    hr=Depends(require_roles("hr_admin", "company_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create new employee. Auto-generates employee code and sets default PIN."""
    import uuid
    from datetime import date

    # Generate employee code: EMP-XXXXX
    count = await db.scalar(
        text("SELECT COUNT(*) FROM employees WHERE company_id = :cid"),
        {"cid": str(hr.company_id)},
    )
    emp_code = f"EMP-{(count or 0) + 1:05d}"

    employee = EmployeeModel(
        id=uuid.uuid4(),
        company_id=hr.company_id,
        employee_code=emp_code,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        department_id=body.department_id,
        direct_manager_id=body.direct_manager_id,
        employment_type=body.employment_type,
        join_date=date.fromisoformat(body.join_date),
        role=body.role,
        status="active",
        hashed_pin=hash_password(body.default_pin),
    )
    db.add(employee)
    await db.flush()

    # Initialise leave balances for this year
    from app.modules.leave.infrastructure.models import (LeaveBalanceModel,
                                                         LeaveTypeModel)
    current_year = date.today().year
    leave_types = await db.execute(
        select(LeaveTypeModel).where(LeaveTypeModel.company_id == hr.company_id)
    )
    for lt in leave_types.scalars().all():
        balance = LeaveBalanceModel(
            id=uuid.uuid4(),
            employee_id=employee.id,
            leave_type_id=lt.id,
            year=current_year,
            total_entitlement=lt.max_days_per_year,
        )
        db.add(balance)

    await db.flush()

    # Welcome email async
    from app.modules.notification.tasks.notification_jobs import \
        send_welcome_email
    send_welcome_email.delay(
        employee_id=str(employee.id),
        email=body.email,
        full_name=body.full_name,
        employee_code=emp_code,
        default_pin=body.default_pin,
    )

    return ApiResponse(
        data={"id": str(employee.id), "employee_code": emp_code},
        message=f"Karyawan {body.full_name} berhasil dibuat. Email selamat datang dikirim.",
    )


@router.patch("/{employee_id}", response_model=ApiResponse[dict])
async def update_employee(
    employee_id: UUID,
    body: UpdateEmployeeRequest,
    hr=Depends(require_roles("hr_admin", "company_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update employee details. Partial update — only send changed fields."""
    employee = await db.scalar(
        select(EmployeeModel).where(
            EmployeeModel.id == employee_id,
            EmployeeModel.company_id == hr.company_id,
        )
    )
    if not employee:
        raise HTTPException(404, "Employee not found")

    updates = body.model_dump(exclude_none=True)
    for key, val in updates.items():
        setattr(employee, key, val)

    await db.flush()
    return ApiResponse(
        data={"id": str(employee.id), "updated_fields": list(updates.keys())},
        message="Data karyawan berhasil diperbarui.",
    )
