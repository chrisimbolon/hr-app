'use client'

import { useEffect, useState, useCallback } from 'react'
import { Search, Plus, ChevronLeft, ChevronRight, UserCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { cn, formatDate, getInitials, getRoleLabel } from '@/lib/utils'
import type { Employee } from '@/types'

function EmployeeRow({ emp }: { emp: Employee }) {
  const roleColors: Record<string, string> = {
    hr_admin: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    company_admin: 'bg-brand-500/10 text-brand-400 border-brand-500/20',
    manager: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    employee: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  }
  return (
    <tr className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition-colors">
      <td className="px-4 py-3.5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-brand-500/15 border border-brand-500/20 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-semibold text-brand-400">{getInitials(emp.full_name)}</span>
          </div>
          <div>
            <p className="text-sm font-medium text-white">{emp.full_name}</p>
            <p className="text-xs text-zinc-500">{emp.email}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3.5"><span className="text-sm font-mono text-zinc-400">{emp.employee_code}</span></td>
      <td className="px-4 py-3.5"><span className={cn('status-badge border text-[11px]', roleColors[emp.role] ?? roleColors.employee)}>{getRoleLabel(emp.role)}</span></td>
      <td className="px-4 py-3.5"><span className={cn('status-badge text-[11px]', emp.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-zinc-500/10 text-zinc-500')}>{emp.status === 'active' ? 'Aktif' : 'Nonaktif'}</span></td>
      <td className="px-4 py-3.5 text-sm text-zinc-500">{formatDate(emp.join_date)}</td>
    </tr>
  )
}

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const PAGE_SIZE = 20

  useEffect(() => { const t = setTimeout(() => setDebouncedSearch(search), 300); return () => clearTimeout(t) }, [search])
  useEffect(() => { setPage(1) }, [debouncedSearch])

  const fetchEmployees = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), status: 'active' })
      if (debouncedSearch) params.set('search', debouncedSearch)
      const { data } = await api.get(`/employees?${params}`)
      setEmployees(data.data); setTotal(data.total ?? data.data.length)
    } catch { setEmployees([]) } finally { setLoading(false) }
  }, [page, debouncedSearch])

  useEffect(() => { fetchEmployees() }, [fetchEmployees])
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Karyawan</h1>
          <p className="text-zinc-500 text-sm mt-1">{total > 0 ? `${total} karyawan aktif` : 'Manajemen karyawan perusahaan'}</p>
        </div>
        <button className="btn-primary"><Plus className="w-4 h-4" />Tambah Karyawan</button>
      </div>
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
        <input type="search" placeholder="Cari nama atau kode..." value={search} onChange={(e) => setSearch(e.target.value)} className="input-field pl-9" />
      </div>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-800/30">
                {['Karyawan', 'Kode', 'Jabatan', 'Status', 'Bergabung'].map((h) => (
                  <th key={h} className="px-4 py-3 text-xs font-medium text-zinc-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 6 }).map((_, i) => <tr key={i} className="border-b border-zinc-800/50">{Array.from({ length: 5 }).map((_, j) => <td key={j} className="px-4 py-4"><div className="skeleton h-4 rounded w-24" /></td>)}</tr>)
                : employees.length > 0
                  ? employees.map((emp) => <EmployeeRow key={emp.id} emp={emp} />)
                  : <tr><td colSpan={5} className="px-4 py-16 text-center"><UserCircle className="w-10 h-10 text-zinc-700 mx-auto mb-3" /><p className="text-zinc-600 text-sm">{debouncedSearch ? 'Tidak ada karyawan yang cocok' : 'Belum ada karyawan'}</p></td></tr>}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-zinc-800 flex items-center justify-between">
            <p className="text-xs text-zinc-500">Halaman {page} dari {totalPages}</p>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="btn-ghost p-1.5 disabled:opacity-30"><ChevronLeft className="w-4 h-4" /></button>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn-ghost p-1.5 disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
