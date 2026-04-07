// ── API Response envelope ─────────────────────────────────────────
export interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
}

export interface ApiError {
  success: false
  error: {
    code: string
    message: string
    field: string | null
  }
}

// ── Auth ──────────────────────────────────────────────────────────
export interface EmployeeProfile {
  id: string
  employee_code: string
  full_name: string
  email: string
  role: EmployeeRole
  company_id: string
  employment_type: string
}

export type EmployeeRole = 'employee' | 'manager' | 'hr_admin' | 'company_admin'

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  employee: EmployeeProfile
}

export interface AuthState {
  employee: EmployeeProfile | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

// ── Employee ──────────────────────────────────────────────────────
export interface Employee {
  id: string
  employee_code: string
  full_name: string
  email: string
  phone: string | null
  role: EmployeeRole
  department_id: string | null
  status: 'active' | 'inactive' | 'terminated'
  employment_type: 'permanent' | 'contract' | 'intern'
  join_date: string
}

// ── Attendance ────────────────────────────────────────────────────
export type AttendanceStatus = 'present' | 'late' | 'alpha' | 'leave' | 'holiday' | 'incomplete'

export interface TodayStatus {
  date: string
  shift: {
    name: string
    start_time: string
    end_time: string
    break_minutes: number
  } | null
  check_in_at: string | null
  check_out_at: string | null
  status: AttendanceStatus
  can_check_in: boolean
  can_check_out: boolean
  is_late: boolean
  late_minutes: number
  work_minutes: number
}

export interface DailyLog {
  date: string
  status: AttendanceStatus
  check_in_at: string | null
  check_out_at: string | null
  work_minutes: number
  late_minutes: number
  overtime_minutes: number
  is_late: boolean
  is_alpha: boolean
}

export interface AttendanceSummary {
  employee_id: string
  period: string
  working_days_scheduled: number
  days_present: number
  days_alpha: number
  days_leave: number
  late_count: number
  total_late_minutes: number
  early_leave_count: number
  total_overtime_minutes: number
  attendance_rate: number
  payroll_impact: {
    alpha_deduction_days: number
    late_deduction_minutes: number
    overtime_hours: number
  }
  daily_logs: DailyLog[]
}

// ── Leave ─────────────────────────────────────────────────────────
export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'

export interface LeaveType {
  id: string
  name: string
  code: string
  is_paid: boolean
  requires_document: boolean
  max_days_per_year: number
  balance: {
    total_entitlement: number
    used_days: number
    pending_days: number
    carried_forward: number
    remaining_days: number
  } | null
}

export interface LeaveRequest {
  id: string
  leave_type: string
  start_date: string
  end_date: string
  total_days: number
  status: LeaveStatus
  reason: string
  reviewed_at: string | null
}

// ── Pagination ────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  success: boolean
  data: T[]
  total: number
  page: number
  pages: number
  page_size: number
}
