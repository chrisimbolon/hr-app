'use client'

import { useEffect, useState } from 'react'
import { Plus, Calendar, CheckCircle, XCircle, Clock } from 'lucide-react'
import { api } from '@/lib/api'
import { cn, formatDate } from '@/lib/utils'
import type { LeaveType, LeaveRequest } from '@/types'

function LeaveCard({ req }: { req: LeaveRequest }) {
  const statusStyles: Record<string, string> = {
    pending:   'bg-amber-500/10 text-amber-400 border-amber-500/20',
    approved:  'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    rejected:  'bg-red-500/10 text-red-400 border-red-500/20',
    cancelled: 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20',
  }
  const statusLabel: Record<string, string> = { pending: 'Menunggu', approved: 'Disetujui', rejected: 'Ditolak', cancelled: 'Dibatalkan' }
  return (
    <div className="card p-4 hover:border-zinc-700 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <p className="text-sm font-medium text-white">{req.leave_type}</p>
          <p className="text-xs text-zinc-500 mt-0.5">{formatDate(req.start_date)} – {formatDate(req.end_date)} · {req.total_days} hari</p>
        </div>
        <span className={cn('status-badge border text-[11px]', statusStyles[req.status])}>{statusLabel[req.status]}</span>
      </div>
      <p className="text-xs text-zinc-600 line-clamp-2">{req.reason}</p>
    </div>
  )
}

function BalanceCard({ lt }: { lt: LeaveType }) {
  const remaining = lt.balance?.remaining_days ?? 0
  const total = lt.balance?.total_entitlement ?? 0
  const pct = total > 0 ? (remaining / total) * 100 : 0
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-sm font-medium text-white">{lt.name}</p>
          <p className="text-xs text-zinc-500 mt-0.5">{lt.code} · {lt.is_paid ? 'Berbayar' : 'Tidak berbayar'}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-white">{remaining}</p>
          <p className="text-xs text-zinc-600">dari {total}</p>
        </div>
      </div>
      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div className="h-full bg-brand-500 rounded-full transition-all duration-700" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function LeavePage() {
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([])
  const [requests, setRequests] = useState<LeaveRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'requests' | 'balance'>('requests')

  useEffect(() => {
    Promise.all([
      api.get('/leave/types').catch(() => null),
      api.get('/leave/requests').catch(() => null),
    ]).then(([typesRes, reqRes]) => {
      if (typesRes?.data?.data) setLeaveTypes(typesRes.data.data)
      if (reqRes?.data?.data) setRequests(reqRes.data.data)
    }).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Izin & Cuti</h1>
          <p className="text-zinc-500 text-sm mt-1">Kelola permohonan izin dan saldo cuti kamu</p>
        </div>
        <button className="btn-primary"><Plus className="w-4 h-4" />Ajukan Izin</button>
      </div>
      <div className="flex gap-1 p-1 bg-zinc-900 border border-zinc-800 rounded-xl w-fit">
        {(['requests', 'balance'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={cn('px-4 py-2 text-sm font-medium rounded-lg transition-all', tab === t ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300')}>
            {t === 'requests' ? 'Permohonan' : 'Saldo Cuti'}
          </button>
        ))}
      </div>
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="card p-4 skeleton h-24" />)}</div>
      ) : tab === 'requests' ? (
        requests.length > 0
          ? <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">{requests.map((req) => <LeaveCard key={req.id} req={req} />)}</div>
          : <div className="card p-16 text-center"><Calendar className="w-10 h-10 text-zinc-700 mx-auto mb-3" /><p className="text-zinc-600 text-sm">Belum ada permohonan izin</p></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{leaveTypes.map((lt) => <BalanceCard key={lt.id} lt={lt} />)}</div>
      )}
    </div>
  )
}
