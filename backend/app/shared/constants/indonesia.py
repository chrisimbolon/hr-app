"""
shared/constants/indonesia.py
──────────────────────────────
All Indonesia-specific business constants in one place.
Never hardcode these elsewhere.
"""

# ── Payroll ─────────────────────────────────────────────────────
WORKING_DAYS_DIVISOR = 26        # UU Ketenagakerjaan Pasal 77-78
MAX_OVERTIME_HOURS_PER_DAY = 4   # UU No.11/2020 CK
MAX_OVERTIME_HOURS_PER_WEEK = 18 # UU No.11/2020 CK

# ── BPJS Kesehatan default % ─────────────────────────────────────
BPJS_KESEHATAN_EMPLOYEE_PCT = 1.00   # 1% of salary
BPJS_KESEHATAN_COMPANY_PCT = 4.00    # 4% of salary
BPJS_KESEHATAN_MAX_SALARY = 12_000_000  # cap salary for BPJS

# ── BPJS Ketenagakerjaan default % ──────────────────────────────
BPJS_TK_JHT_EMPLOYEE_PCT = 2.00     # Jaminan Hari Tua employee
BPJS_TK_JHT_COMPANY_PCT = 3.70      # Jaminan Hari Tua company
BPJS_TK_JP_EMPLOYEE_PCT = 1.00      # Jaminan Pensiun employee
BPJS_TK_JP_COMPANY_PCT = 2.00       # Jaminan Pensiun company
BPJS_TK_JKK_COMPANY_PCT = 0.24      # Jaminan Kecelakaan Kerja (medium risk)
BPJS_TK_JKM_COMPANY_PCT = 0.30      # Jaminan Kematian
BPJS_TK_MAX_SALARY_JP = 9_077_600   # JP salary ceiling

# ── PTKP (Tax-Free Income) 2024 ─────────────────────────────────
PTKP = {
    "TK0": 54_000_000,    # Single, no dependents
    "TK1": 58_500_000,    # Single, 1 dependent
    "TK2": 63_000_000,    # Single, 2 dependents
    "TK3": 67_500_000,    # Single, 3 dependents
    "K0":  58_500_000,    # Married, no dependents
    "K1":  63_000_000,    # Married, 1 dependent
    "K2":  67_500_000,    # Married, 2 dependents
    "K3":  72_000_000,    # Married, 3 dependents
}

# ── PPh 21 Progressive Brackets 2024 ────────────────────────────
PPH21_BRACKETS = [
    (60_000_000, 0.05),
    (190_000_000, 0.15),
    (250_000_000, 0.25),
    (500_000_000, 0.30),
    (float("inf"), 0.35),
]

# ── Timezones ────────────────────────────────────────────────────
TIMEZONE_WIB = "Asia/Jakarta"
TIMEZONE_WITA = "Asia/Makassar"
TIMEZONE_WIT = "Asia/Jayapura"

# ── THR ──────────────────────────────────────────────────────────
THR_MIN_MONTHS_WORKED = 1       # must work at least 1 month
THR_FULL_MONTHS_FOR_FULL = 12   # 12 months = 1 month salary
