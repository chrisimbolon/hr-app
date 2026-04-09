'use client'

import { api } from '@/lib/api'
import {
    cn, formatTime,
    getAttendanceStatusColor,
    getAttendanceStatusLabel,
    minutesToHoursDisplay,
} from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import type { AttendanceSummary, TodayStatus } from '@/types'
import { AlertCircle, Calendar, Clock, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'

// ── Stat card ─────────────────────────────────────────────────────
function StatCard({
  label, value, sub, icon: Icon, accent,
}: {
  label: string
  value: string | number
  sub?: string
  icon: React.ElementType
  accent?: string
}) {
  return (
    <div className="card p-5 flex items-start gap-4">
      <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', accent ?? 'bg-zinc-800')}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-zinc-500 mb-1">{label}</p>
        <p className="text-2xl font-semibold text-white leading-none">{value}</p>
        {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
      </div>
    </div>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────
function CardSkeleton() {
  return (
    <div className="card p-5">
      <div className="skeleton h-4 w-24 rounded mb-3" />
      <div className="skeleton h-8 w-16 rounded" />
    </div>
  )
}

// ── Today check-in card ───────────────────────────────────────────
function TodayCard({ status }: { status: TodayStatus | null }) {
  if (!status) return <CardSkeleton />

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm font-medium text-zinc-300">Kehadiran Hari Ini</p>
        <span className={cn('status-badge', getAttendanceStatusColor(status.status))}>
          {getAttendanceStatusLabel(status.status)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-zinc-500 mb-1">Masuk</p>
          <p className="text-xl font-semibold text-white">
            {status.check_in_at ? formatTime(status.check_in_at) : '—'}
          </p>
          {status.is_late && (
            <p className="text-xs text-amber-500 mt-0.5 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              Terlambat {status.late_minutes}m
            </p>
          )}
        </div>
        <div>
          <p className="text-xs text-zinc-500 mb-1">Keluar</p>
          <p className="text-xl font-semibold text-white">
            {status.check_out_at ? formatTime(status.check_out_at) : '—'}
          </p>
        </div>
        {status.shift && (
          <div className="col-span-2 pt-3 border-t border-zinc-800">
            <p className="text-xs text-zinc-500">
              Shift {status.shift.name} · {status.shift.start_time} – {status.shift.end_time}
            </p>
          </div>
        )}
        {status.work_minutes > 0 && (
          <div className="col-span-2">
            <p className="text-xs text-zinc-500 mb-1">Jam Kerja</p>
            <p className="text-lg font-semibold text-white">
              {minutesToHoursDisplay(status.work_minutes)}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Monthly mini summary ──────────────────────────────────────────
function MonthlyMini({ summary }: { summary: AttendanceSummary | null }) {
  if (!summary) return <CardSkeleton />

  const bars = [
    { label: 'Hadir', value: summary.days_present, max: summary.working_days_scheduled, color: 'bg-emerald-500' },
    { label: 'Alpha', value: summary.days_alpha, max: summary.working_days_scheduled, color: 'bg-red-500' },
    { label: 'Izin',  value: summary.days_leave,  max: summary.working_days_scheduled, color: 'bg-blue-500' },
  ]

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm font-medium text-zinc-300">Rekap Bulan Ini</p>
        <span className="text-xs text-zinc-500">{summary.period}</span>
      </div>

      <div className="text-center mb-4">
        <p className="text-3xl font-bold text-white">{summary.attendance_rate.toFixed(0)}%</p>
        <p className="text-xs text-zinc-500 mt-1">Tingkat Kehadiran</p>
      </div>

      <div className="space-y-3">
        {bars.map((bar) => (
          <div key={bar.label}>
            <div className="flex justify-between text-xs text-zinc-500 mb-1">
              <span>{bar.label}</span>
              <span>{bar.value} hari</span>
            </div>
            <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all duration-700', bar.color)}
                style={{ width: `${bar.max > 0 ? (bar.value / bar.max) * 100 : 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main dashboard ────────────────────────────────────────────────
export default function DashboardPage() {
  const employee = useAuthStore((s) => s.employee)
  const [todayStatus, setTodayStatus] = useState<TodayStatus | null>(null)
  const [summary, setSummary] = useState<AttendanceSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const now = new Date()
    const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`

    Promise.all([
      api.get('/attendance/today').catch(() => null),
      api.get(`/attendance/summary/${month}`).catch(() => null),
    ]).then(([todayRes, summaryRes]) => {
      if (todayRes?.data?.data) setTodayStatus(todayRes.data.data)
      if (summaryRes?.data?.data) setSummary(summaryRes.data.data)
    }).finally(() => setLoading(false))
  }, [])

  const hour = new Date().getHours()
  const greeting = hour < 11 ? 'Selamat pagi' : hour < 15 ? 'Selamat siang' : hour < 18 ? 'Selamat sore' : 'Selamat malam'
  const firstName = employee?.full_name.split(' ')[0] ?? ''

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white">
          {greeting}, {firstName} 👋
        </h1>
        <p className="text-zinc-500 text-sm mt-1">
          {new Date().toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
        ) : (
          <>
            <StatCard label="Hadir Bulan Ini" value={summary?.days_present ?? '—'} sub="dari jadwal kerja" icon={Clock} accent="bg-emerald-600" />
            <StatCard label="Tingkat Kehadiran" value={summary ? `${summary.attendance_rate.toFixed(0)}%` : '—'} sub="bulan ini" icon={TrendingUp} accent="bg-brand-500" />
            <StatCard label="Total Lembur" value={summary ? minutesToHoursDisplay(summary.total_overtime_minutes) : '—'} sub="bulan ini" icon={Clock} accent="bg-purple-600" />
            <StatCard label="Sisa Cuti" value="—" sub="hari tersisa" icon={Calendar} accent="bg-blue-600" />
          </>
        )}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <TodayCard status={todayStatus} />

          {/* Recent activity */}
          <div className="card p-5">
            <p className="text-sm font-medium text-zinc-300 mb-4">Aktivitas Terbaru</p>
            {summary && summary.daily_logs.length > 0 ? (
              <div className="space-y-3">
                {summary.daily_logs.slice(-5).reverse().map((log) => (
                  <div key={log.date} className="flex items-center gap-3 py-2 border-b border-zinc-800/50 last:border-0">
                    <div className={cn('w-2 h-2 rounded-full flex-shrink-0', {
                      'bg-emerald-500': log.status === 'present',
                      'bg-amber-500': log.status === 'late',
                      'bg-red-500': log.status === 'alpha',
                      'bg-blue-500': log.status === 'leave',
                      'bg-zinc-600': !['present','late','alpha','leave'].includes(log.status),
                    })} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-zinc-300">
                        {new Date(log.date).toLocaleDateString('id-ID', { weekday: 'short', day: 'numeric', month: 'short' })}
                      </p>
                      <p className="text-xs text-zinc-600">
                        {log.check_in_at ? formatTime(log.check_in_at) : '—'} – {log.check_out_at ? formatTime(log.check_out_at) : '—'}
                      </p>
                    </div>
                    <span className={cn('status-badge text-[11px]', getAttendanceStatusColor(log.status))}>
                      {getAttendanceStatusLabel(log.status)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-zinc-600 text-sm text-center py-6">Belum ada data kehadiran bulan ini</p>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <MonthlyMini summary={summary} />

          {/* Quick actions */}
          <div className="card p-5">
            <p className="text-sm font-medium text-zinc-300 mb-4">Aksi Cepat</p>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Ajukan Izin', href: '/dashboard/leave', color: 'bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border-blue-500/20' },
                { label: 'Rekap Absen', href: '/dashboard/attendance', color: 'bg-brand-500/10 text-brand-400 hover:bg-brand-500/20 border-brand-500/20' },
                { label: 'Profil Saya', href: '/dashboard/employees', color: 'bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 border-purple-500/20' },
                { label: 'Slip Gaji', href: '/dashboard/payroll', color: 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border-emerald-500/20' },
              ].map((action) => (
                <a
                  key={action.label}
                  href={action.href}
                  className={cn(
                    'flex items-center justify-center p-3 rounded-xl text-xs font-medium border transition-all duration-150',
                    action.color,
                  )}
                >
                  {action.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
