"""
payroll/domain/salary_rules.py
────────────────────────────────
Pure Python salary calculation rules.
No imports from infrastructure, FastAPI, or SQLAlchemy.
Unit-testable with zero setup — just Python and math.

Indonesia-specific: UU Ketenagakerjaan, BPJS, PPh 21 TER/Progressive.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from app.shared.constants.indonesia import (BPJS_KESEHATAN_EMPLOYEE_PCT,
                                            BPJS_KESEHATAN_MAX_SALARY,
                                            BPJS_TK_JHT_EMPLOYEE_PCT,
                                            BPJS_TK_JP_EMPLOYEE_PCT,
                                            BPJS_TK_MAX_SALARY_JP,
                                            PPH21_BRACKETS, PTKP,
                                            WORKING_DAYS_DIVISOR)


def daily_rate(base_salary: Decimal) -> Decimal:
    """
    Daily rate per UU Ketenagakerjaan.
    Base / 26 working days (not calendar days).
    """
    return (base_salary / WORKING_DAYS_DIVISOR).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def overtime_pay(
    overtime_minutes: int,
    multiplier: Decimal,
    base_salary: Decimal,
) -> Decimal:
    """
    Overtime pay = (salary / 173) × multiplier × overtime_hours
    173 = standard monthly hours per Permenaker No.102/2004
    """
    hourly_rate = base_salary / Decimal("173")
    overtime_hours = Decimal(str(overtime_minutes)) / Decimal("60")
    return (hourly_rate * multiplier * overtime_hours).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def late_deduction(total_late_minutes: int, base_salary: Decimal) -> Decimal:
    """
    Deduct proportionally for late minutes.
    Varies by company policy — this uses a common formula.
    """
    hourly_rate = base_salary / Decimal("173")
    late_hours = Decimal(str(total_late_minutes)) / Decimal("60")
    return (hourly_rate * late_hours).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def alpha_deduction(alpha_days: int, base_salary: Decimal) -> Decimal:
    """Deduct daily rate for each absent-without-reason day."""
    return daily_rate(base_salary) * alpha_days


def prorate_salary(base_salary: Decimal, days_worked: int, total_days: int) -> Decimal:
    """Prorated salary for partial month (new joiners, terminators)."""
    if total_days == 0:
        return Decimal("0")
    return (base_salary * days_worked / total_days).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def thr_amount(base_salary: Decimal, months_worked: float) -> Decimal:
    """
    THR = (months_worked / 12) × base_salary
    Must be at least 1 month worked. Max = 1 month salary.
    Per UU No.6/2016 (Government Regulation on THR).
    """
    if months_worked < 1:
        return Decimal("0")
    ratio = min(Decimal(str(months_worked)) / Decimal("12"), Decimal("1"))
    return (base_salary * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


# ── BPJS Calculations ────────────────────────────────────────────

def bpjs_kesehatan_employee(
    base_salary: Decimal,
    employee_pct: float = BPJS_KESEHATAN_EMPLOYEE_PCT,
    max_salary: Decimal = Decimal(str(BPJS_KESEHATAN_MAX_SALARY)),
) -> Decimal:
    """Employee portion of BPJS Kesehatan (health insurance)."""
    capped = min(base_salary, max_salary)
    return (capped * Decimal(str(employee_pct)) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def bpjs_kesehatan_company(
    base_salary: Decimal,
    company_pct: float,
    max_salary: Decimal = Decimal(str(BPJS_KESEHATAN_MAX_SALARY)),
) -> Decimal:
    """Company portion of BPJS Kesehatan."""
    capped = min(base_salary, max_salary)
    return (capped * Decimal(str(company_pct)) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def bpjs_jht_employee(base_salary: Decimal, pct: float = BPJS_TK_JHT_EMPLOYEE_PCT) -> Decimal:
    """Jaminan Hari Tua — employee portion."""
    return (base_salary * Decimal(str(pct)) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def bpjs_jp_employee(
    base_salary: Decimal,
    pct: float = BPJS_TK_JP_EMPLOYEE_PCT,
    max_salary: Decimal = Decimal(str(BPJS_TK_MAX_SALARY_JP)),
) -> Decimal:
    """Jaminan Pensiun — employee portion (has salary ceiling)."""
    capped = min(base_salary, max_salary)
    return (capped * Decimal(str(pct)) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


# ── PPh 21 (Income Tax) ──────────────────────────────────────────

def pph21_progressive(annual_taxable_income: Decimal, ptkp_key: str = "TK0") -> Decimal:
    """
    PPh 21 annual tax via progressive brackets (pre-TER method).
    Applicable for employees without NPWP or those using old method.
    """
    ptkp = Decimal(str(PTKP.get(ptkp_key, PTKP["TK0"])))
    pkp = max(annual_taxable_income - ptkp, Decimal("0"))  # Penghasilan Kena Pajak

    tax = Decimal("0")
    remaining = pkp
    prev_ceiling = Decimal("0")

    for ceiling, rate in PPH21_BRACKETS:
        ceiling_dec = Decimal(str(ceiling)) if ceiling != float("inf") else remaining + 1
        bracket_size = min(remaining, ceiling_dec - prev_ceiling)
        if bracket_size <= 0:
            break
        tax += bracket_size * Decimal(str(rate))
        remaining -= bracket_size
        prev_ceiling = ceiling_dec
        if remaining <= 0:
            break

    # Monthly PPh21 = annual / 12
    return (tax / 12).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


@dataclass
class SalaryCalculationResult:
    """Full payroll calculation result for one employee for one period."""
    employee_id: str
    period: str

    # Earnings
    base_salary: Decimal
    total_allowances: Decimal
    overtime_pay: Decimal
    gross_salary: Decimal

    # Deductions
    alpha_deduction: Decimal
    late_deduction: Decimal
    bpjs_kesehatan_employee: Decimal
    bpjs_jht_employee: Decimal
    bpjs_jp_employee: Decimal
    pph21_monthly: Decimal
    other_deductions: Decimal
    total_deductions: Decimal

    # Result
    net_salary: Decimal

    # Attendance inputs
    days_present: int
    days_alpha: int
    total_late_minutes: int
    total_overtime_minutes: int
