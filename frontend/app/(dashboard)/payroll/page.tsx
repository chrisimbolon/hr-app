'use client'

import { CreditCard, FileText, Lock } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'

export default function PayrollPage() {
  const employee = useAuthStore((s) => s.employee)
  const isHR = employee?.role === 'hr_admin' || employee?.role === 'company_admin'
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Penggajian</h1>
        <p className="text-zinc-500 text-sm mt-1">{isHR ? 'Kelola periode penggajian dan slip gaji karyawan' : 'Lihat slip gaji dan riwayat penggajian kamu'}</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { icon: CreditCard, label: 'Gaji Bersih Terakhir', value: '—', sub: 'Belum ada data', color: 'bg-emerald-600' },
          { icon: FileText,   label: 'Slip Gaji Tersedia',   value: '0', sub: 'Dokumen',          color: 'bg-blue-600' },
          { icon: Lock,       label: 'Status Periode',       value: '—', sub: 'Belum diproses',    color: 'bg-zinc-700' },
        ].map((card) => (
          <div key={card.label} className="card p-5 flex items-start gap-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${card.color}`}>
              <card.icon className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-xs text-zinc-500 mb-1">{card.label}</p>
              <p className="text-2xl font-semibold text-white">{card.value}</p>
              <p className="text-xs text-zinc-600 mt-0.5">{card.sub}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="card p-16 text-center">
        <CreditCard className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
        <p className="text-zinc-500 text-sm font-medium">Modul Penggajian</p>
        <p className="text-zinc-700 text-xs mt-1 max-w-xs mx-auto">Data penggajian akan tersedia setelah HR admin memproses periode pertama.</p>
      </div>
    </div>
  )
}
