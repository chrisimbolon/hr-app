"""
payroll/application/use_cases/run_payroll.py
──────────────────────────────────────────────
RunPayrollUseCase: orchestrates the full monthly payroll calculation.
For each active employee:
  1. Load base salary + salary components
  2. Load attendance summary (days present, alpha, late, overtime)
  3. Load BPJS config + tax profile
  4. Run pure domain salary calculations
  5. Write payroll_result row
  6. Fire payslip generation task
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.payroll.domain.salary_rules import (SalaryCalculationResult,
                                                     alpha_deduction,
                                                     bpjs_jht_employee,
                                                     bpjs_jp_employee,
                                                     bpjs_kesehatan_employee)
from app.modules.payroll.domain.salary_rules import \
    late_deduction as calc_late_deduction
from app.modules.payroll.domain.salary_rules import \
    overtime_pay as calc_overtime_pay
from app.modules.payroll.domain.salary_rules import pph21_progressive
from app.modules.payroll.infrastructure.models import (
    BpjsConfigModel, EmployeeSalaryComponentModel, EmployeeSalaryModel,
    PayrollPeriodModel, PayrollResultModel, SalaryComponentModel,
    TaxProfileModel)
from app.shared.constants.indonesia import PTKP
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession


class RunPayrollUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(
        self,
        payroll_period_id: uuid.UUID,
        company_id: uuid.UUID,
        triggered_by: uuid.UUID,
    ) -> dict:
        """Run payroll for ALL active employees in the company for the given period."""

        # ── 1. Load and validate period ───────────────────────────
        period = await self.db.scalar(
            select(PayrollPeriodModel).where(
                PayrollPeriodModel.id == payroll_period_id,
                PayrollPeriodModel.company_id == company_id,
            )
        )
        if not period:
            raise NotFoundError("PayrollPeriod", str(payroll_period_id))
        if period.status == "locked":
            raise BusinessRuleError("Payroll period is already locked/processed.")

        # ── 2. Load BPJS config ───────────────────────────────────
        bpjs = await self.db.scalar(
            select(BpjsConfigModel).where(BpjsConfigModel.company_id == company_id)
        )
        if not bpjs:
            raise BusinessRuleError("BPJS configuration not set up. Contact super admin.")

        # ── 3. Get all active employees ───────────────────────────
        employees = await self.db.execute(
            text("""
                SELECT id, direct_manager_id
                FROM employees
                WHERE company_id = :cid AND status = 'active'
            """),
            {"cid": str(company_id)},
        )
        emp_rows = employees.fetchall()

        results = []
        errors = []

        for emp_row in emp_rows:
            try:
                result = await self._calculate_for_employee(
                    employee_id=emp_row.id,
                    payroll_period_id=payroll_period_id,
                    period=period,
                    bpjs=bpjs,
                )
                results.append(result)
            except Exception as e:
                errors.append({"employee_id": str(emp_row.id), "error": str(e)})

        # ── 4. Lock period ────────────────────────────────────────
        period.status = "locked"
        await self.db.flush()

        # ── 5. Fire payslip generation for all (Celery batch) ─────
        from app.modules.payroll.tasks.payroll_jobs import \
            generate_all_payslips
        generate_all_payslips.delay(
            payroll_period_id=str(payroll_period_id),
            company_id=str(company_id),
        )

        return {
            "period_id": str(payroll_period_id),
            "employees_processed": len(results),
            "errors": errors,
            "status": "locked",
        }

    async def _calculate_for_employee(
        self,
        employee_id: uuid.UUID,
        payroll_period_id: uuid.UUID,
        period: PayrollPeriodModel,
        bpjs: BpjsConfigModel,
    ) -> PayrollResultModel:

        # ── Load base salary ──────────────────────────────────────
        salary_row = await self.db.scalar(
            select(EmployeeSalaryModel).where(
                EmployeeSalaryModel.employee_id == employee_id,
                EmployeeSalaryModel.effective_date <= period.end_date,
            ).order_by(EmployeeSalaryModel.effective_date.desc()).limit(1)
        )
        if not salary_row:
            raise BusinessRuleError(f"No salary configured for employee {employee_id}")
        base = salary_row.base_salary

        # ── Load salary components ────────────────────────────────
        comp_rows = await self.db.execute(
            select(EmployeeSalaryComponentModel, SalaryComponentModel)
            .join(SalaryComponentModel)
            .where(
                EmployeeSalaryComponentModel.employee_id == employee_id,
                EmployeeSalaryComponentModel.effective_date <= period.end_date,
            )
        )
        allowances = Decimal("0")
        other_deductions = Decimal("0")
        taxable_income_additions = Decimal("0")

        for emp_comp, comp in comp_rows.all():
            if comp.type == "allowance":
                allowances += emp_comp.amount
                if comp.is_taxable:
                    taxable_income_additions += emp_comp.amount
            else:
                other_deductions += emp_comp.amount

        # ── Load attendance summary for period ────────────────────
        att_data = await self.db.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE status IN ('present','late')) AS days_present,
                    COUNT(*) FILTER (WHERE is_alpha = true)              AS days_alpha,
                    SUM(late_minutes)                                    AS total_late_min,
                    SUM(overtime_minutes)                                AS total_ot_min
                FROM attendance_summaries
                WHERE employee_id = :emp_id
                  AND date BETWEEN :start AND :end
            """),
            {
                "emp_id": str(employee_id),
                "start": period.start_date,
                "end": period.cutoff_date,
            },
        )
        att = att_data.fetchone()
        days_present = att.days_present or 0
        days_alpha = att.days_alpha or 0
        total_late_min = att.total_late_min or 0
        total_ot_min = att.total_ot_min or 0

        # ── Load overtime policy for multiplier ───────────────────
        ot_policy = await self.db.execute(
            text("SELECT multiplier_weekday FROM overtime_policies WHERE company_id = :cid LIMIT 1"),
            {"cid": str(period.company_id)},
        )
        ot_policy_row = ot_policy.fetchone()
        ot_multiplier = Decimal(str(ot_policy_row.multiplier_weekday)) if ot_policy_row else Decimal("1.5")

        # ── Load tax profile ──────────────────────────────────────
        tax_profile = await self.db.scalar(
            select(TaxProfileModel).where(TaxProfileModel.employee_id == employee_id)
        )
        ptkp_key = tax_profile.marital_status if tax_profile else "TK0"

        # ── Domain calculations (pure Python) ─────────────────────
        alpha_ded = alpha_deduction(days_alpha, base)
        late_ded = calc_late_deduction(total_late_min, base)
        ot_pay = calc_overtime_pay(total_ot_min, ot_multiplier, base)
        bpjs_kes = bpjs_kesehatan_employee(base, float(bpjs.kesehatan_employee_pct))
        bpjs_jht = bpjs_jht_employee(base, float(bpjs.tk_jht_employee_pct))
        bpjs_jp = bpjs_jp_employee(base, float(bpjs.tk_jp_employee_pct))

        gross = base + allowances + ot_pay
        annual_taxable = (gross + taxable_income_additions) * 12
        pph21 = pph21_progressive(annual_taxable, ptkp_key)

        total_deductions = (
            alpha_ded + late_ded + other_deductions +
            bpjs_kes + bpjs_jht + bpjs_jp + pph21
        )
        net = gross - total_deductions

        # ── Write payroll result ──────────────────────────────────
        result = PayrollResultModel(
            id=uuid.uuid4(),
            payroll_period_id=payroll_period_id,
            employee_id=employee_id,
            total_present_days=days_present,
            total_absent_days=days_alpha,
            total_late_minutes=total_late_min,
            total_overtime_minutes=total_ot_min,
            base_salary=base,
            total_allowances=allowances,
            overtime_pay=ot_pay,
            total_deductions=total_deductions,
            bpjs_kesehatan=bpjs_kes,
            bpjs_tk=bpjs_jht + bpjs_jp,
            pph21_tax=pph21,
            net_salary=max(net, Decimal("0")),
        )
        self.db.add(result)
        await self.db.flush()
        return result
