"""payroll/presentation/api/v1/routes.py — Payroll API routes."""
from datetime import date
from uuid import UUID

from app.core.dependencies import get_current_employee, get_db, require_roles
from app.modules.payroll.application.use_cases.run_payroll import \
    RunPayrollUseCase
from app.modules.payroll.infrastructure.models import (PayrollPeriodModel,
                                                       PayrollResultModel,
                                                       ThrRecordModel)
from app.shared.schemas.base import ApiResponse
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class CreatePeriodRequest(BaseModel):
    start_date: date
    end_date: date
    cutoff_date: date


class RunPayrollRequest(BaseModel):
    payroll_period_id: UUID


@router.post("/periods", response_model=ApiResponse[dict], status_code=201)
async def create_payroll_period(
    body: CreatePeriodRequest,
    employee=Depends(require_roles("hr_admin", "company_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new payroll period (open status)."""
    import uuid
    period = PayrollPeriodModel(
        id=uuid.uuid4(),
        company_id=employee.company_id,
        start_date=body.start_date,
        end_date=body.end_date,
        cutoff_date=body.cutoff_date,
        status="open",
    )
    db.add(period)
    await db.flush()
    return ApiResponse(
        data={"id": str(period.id), "status": "open"},
        message="Periode payroll berhasil dibuat.",
    )


@router.post("/run", response_model=ApiResponse[dict])
async def run_payroll(
    body: RunPayrollRequest,
    employee=Depends(require_roles("hr_admin", "company_admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Run payroll calculation for all employees in the period.
    Locks the period after calculation. Triggers payslip generation.
    """
    use_case = RunPayrollUseCase(db)
    result = await use_case.execute(
        payroll_period_id=body.payroll_period_id,
        company_id=employee.company_id,
        triggered_by=employee.id,
    )
    return ApiResponse(
        data=result,
        message=f"Payroll diproses untuk {result['employees_processed']} karyawan.",
    )


@router.get("/results/{period_id}", response_model=ApiResponse[list[dict]])
async def get_payroll_results(
    period_id: UUID,
    employee=Depends(require_roles("hr_admin", "company_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Full payroll results for a period — for HR rekap and Finance."""
    rows = await db.execute(
        text("""
            SELECT pr.*, e.full_name, e.employee_code
            FROM payroll_results pr
            JOIN employees e ON e.id = pr.employee_id
            WHERE pr.payroll_period_id = :pid
            ORDER BY e.full_name
        """),
        {"pid": str(period_id)},
    )
    return ApiResponse(
        data=[
            {
                "employee_code": r.employee_code,
                "full_name": r.full_name,
                "base_salary": float(r.base_salary),
                "total_allowances": float(r.total_allowances),
                "overtime_pay": float(r.overtime_pay),
                "bpjs_kesehatan": float(r.bpjs_kesehatan),
                "bpjs_tk": float(r.bpjs_tk),
                "pph21_tax": float(r.pph21_tax),
                "total_deductions": float(r.total_deductions),
                "net_salary": float(r.net_salary),
                "days_present": r.total_present_days,
                "days_alpha": r.total_absent_days,
            }
            for r in rows.fetchall()
        ]
    )


@router.get("/my-payslip/{period_id}", response_model=ApiResponse[dict])
async def get_my_payslip(
    period_id: UUID,
    employee=Depends(get_current_employee),
    db: AsyncSession = Depends(get_db),
):
    """Employee views their own payslip URL for a given period."""
    row = await db.execute(
        text("""
            SELECT ps.file_url, pr.net_salary, pr.generated_at
            FROM payslips ps
            JOIN payroll_results pr ON pr.id = ps.payroll_result_id
            WHERE pr.payroll_period_id = :pid AND pr.employee_id = :emp_id
            LIMIT 1
        """),
        {"pid": str(period_id), "emp_id": str(employee.id)},
    )
    result = row.fetchone()
    if not result:
        raise HTTPException(404, "Payslip not found for this period.")
    return ApiResponse(
        data={
            "file_url": result.file_url,
            "net_salary": float(result.net_salary),
            "generated_at": result.generated_at.isoformat(),
        }
    )
