'use client'

import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Clock, AlertCircle, CheckCircle2, XCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { cn, formatTime, minutesToHoursDisplay, getAttendanceStatusLabel, getAttendanceStatusColor } from '@/lib/utils'
import type { AttendanceSummary, DailyLog } from '@/types'

function MonthNav({ period, onPrev, onNext }: { period: string; onPrev: () => void; onNext: () => void }) {
  const [year, month] = period.split('-').map(Number)
  const label = new Date(year, month - 1).toLocaleDateString('id-ID', { month: 'long', year: 'numeric' })
  const isCurrentMonth = period === `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
  return (
    <div className="flex items-center gap-3">
      <button onClick={onPrev} className="btn-ghost p-2"><ChevronLeft className="w-4 h-4" /></button>
      <span className="text-sm font-medium text-white min-w-36 text-center capitalize">{label}</span>
      <button onClick={onNext} disabled={isCurrentMonth} className="btn-ghost p-2 disabled:opacity-30 disabled:pointer-events-none">
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  )
}

function DayRow({ log }: { log: DailyLog }) {
  const date = new Date(log.date + 'T00:00:00')
  const dayName = date.toLocaleDateString('id-ID', { weekday: 'short' })
  const dayNum = date.getDate()
  const isToday = log.date === new Date().toISOString().split('T')[0]
  return (
    <div className={cn('flex items-center gap-4 py-3 px-4 rounded-xl transition-colors', isToday ? 'bg-brand-500/5 border border-brand-500/20' : 'hover:bg-zinc-800/30')}>
      <div className={cn('text-center w-10 flex-shrink-0', isToday ? 'text-brand-400' : 'text-zinc-500')}>
        <p className="text-[10px] uppercase font-medium">{dayName}</p>
        <p className={cn('text-lg font-semibold leading-tight', isToday ? 'text-brand-400' : 'text-zinc-300')}>{dayNum}</p>
      </div>
      <div className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', { 'bg-emerald-500': log.status === 'present', 'bg-amber-500': log.status === 'late', 'bg-red-500': log.status === 'alpha', 'bg-blue-500': log.status === 'leave', 'bg-purple-500': log.status === 'holiday', 'bg-zinc-600': log.status === 'incomplete' })} />
      <div className="flex-1 flex items-center gap-4">
        <div className="text-sm">
          <span className="text-zinc-400">{log.check_in_at ? formatTime(log.check_in_at) : '—'}</span>
          <span className="text-zinc-700 mx-2">→</span>
          <span className="text-zinc-400">{log.check_out_at ? formatTime(log.check_out_at) : '—'}</span>
        </div>
        {log.work_minutes > 0 && <span className="text-xs text-zinc-600">{minutesToHoursDisplay(log.work_minutes)}</span>}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {log.is_late && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">+{log.late_minutes}m</span>}
        {log.overtime_minutes > 0 && <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">OT {minutesToHoursDisplay(log.overtime_minutes)}</span>}
        <span className={cn('status-badge text-[10px]', getAttendanceStatusColor(log.status))}>{getAttendanceStatusLabel(log.status)}</span>
      </div>
    </div>
  )
}

export default function AttendancePage() {
  const now = new Date()
  const [period, setPeriod] = useState(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
  const [summary, setSummary] = useState<AttendanceSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.get(`/attendance/summary/${period}`).then((r) => setSummary(r.data.data)).catch(() => setSummary(null)).finally(() => setLoading(false))
  }, [period])

  const navigate = (dir: 1 | -1) => {
    const [y, m] = period.split('-').map(Number)
    const d = new Date(y, m - 1 + dir, 1)
    setPeriod(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Rekap Kehadiran</h1>
          <p className="text-zinc-500 text-sm mt-1">Riwayat kehadiran dan jam kerja kamu</p>
        </div>
        <MonthNav period={period} onPrev={() => navigate(-1)} onNext={() => navigate(1)} />
      </div>
      {loading ? (
        <div className="space-y-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton h-14 rounded-xl" />)}</div>
      ) : summary ? (
        <>
          <div className="card p-5">
            <div className="grid grid-cols-3 lg:grid-cols-6 gap-4">
              {[
                { label: 'Hadir',      value: summary.days_present,      color: 'text-emerald-400' },
                { label: 'Alpha',      value: summary.days_alpha,         color: 'text-red-400' },
                { label: 'Izin',       value: summary.days_leave,         color: 'text-blue-400' },
                { label: 'Terlambat',  value: summary.late_count,         color: 'text-amber-400' },
                { label: 'Lembur',     value: `${summary.payroll_impact.overtime_hours}j`, color: 'text-purple-400' },
                { label: 'Kehadiran',  value: `${summary.attendance_rate.toFixed(0)}%`, color: 'text-brand-400' },
              ].map((s) => (
                <div key={s.label} className="text-center">
                  <p className={cn('text-2xl font-bold', s.color)}>{s.value}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">{s.label}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-zinc-800">
              <p className="text-sm font-medium text-zinc-300">{summary.working_days_scheduled} hari kerja</p>
            </div>
            <div className="p-2 space-y-0.5">
              {summary.daily_logs.length > 0
                ? [...summary.daily_logs].reverse().map((log) => <DayRow key={log.date} log={log} />)
                : <p className="text-zinc-600 text-sm text-center py-12">Belum ada data kehadiran</p>}
            </div>
          </div>
        </>
      ) : (
        <div className="card p-16 text-center"><p className="text-zinc-600">Gagal memuat data.</p></div>
      )}
    </div>
  )
}
