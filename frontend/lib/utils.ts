import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, parseISO } from 'date-fns'
import { id as localeId } from 'date-fns/locale'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatRupiah(amount: number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
  }).format(amount)
}

export function formatDate(dateStr: string, fmt = 'd MMM yyyy'): string {
  try {
    return format(parseISO(dateStr), fmt, { locale: localeId })
  } catch {
    return dateStr
  }
}

export function formatDateTime(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'd MMM yyyy, HH:mm', { locale: localeId })
  } catch {
    return dateStr
  }
}

export function formatTime(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'HH:mm', { locale: localeId })
  } catch {
    return dateStr
  }
}

export function minutesToHoursDisplay(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m}m`
  if (m === 0) return `${h}j`
  return `${h}j ${m}m`
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase()
}

export function getRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    employee: 'Karyawan',
    manager: 'Manager',
    hr_admin: 'HR Admin',
    company_admin: 'Admin Perusahaan',
  }
  return labels[role] ?? role
}

export function getAttendanceStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    present: 'Hadir',
    late: 'Terlambat',
    alpha: 'Alpha',
    leave: 'Izin',
    holiday: 'Libur',
    incomplete: 'Belum Checkout',
  }
  return labels[status] ?? status
}

export function getAttendanceStatusColor(status: string): string {
  const colors: Record<string, string> = {
    present: 'text-emerald-700 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950',
    late: 'text-amber-700 bg-amber-50 dark:text-amber-400 dark:bg-amber-950',
    alpha: 'text-red-700 bg-red-50 dark:text-red-400 dark:bg-red-950',
    leave: 'text-blue-700 bg-blue-50 dark:text-blue-400 dark:bg-blue-950',
    holiday: 'text-purple-700 bg-purple-50 dark:text-purple-400 dark:bg-purple-950',
    incomplete: 'text-zinc-600 bg-zinc-100 dark:text-zinc-400 dark:bg-zinc-800',
  }
  return colors[status] ?? colors.incomplete
}
