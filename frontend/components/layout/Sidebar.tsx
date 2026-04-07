'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState } from 'react'
import toast from 'react-hot-toast'
import {
  LayoutDashboard, Clock, Users, Calendar, CreditCard,
  LogOut, ChevronRight, Bell, Settings,
} from 'lucide-react'
import { cn, getInitials, getRoleLabel } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api'

const NAV_ITEMS = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    exact: true,
  },
  {
    label: 'Kehadiran',
    href: '/dashboard/attendance',
    icon: Clock,
  },
  {
    label: 'Karyawan',
    href: '/dashboard/employees',
    icon: Users,
    roles: ['hr_admin', 'company_admin', 'manager'],
  },
  {
    label: 'Izin & Cuti',
    href: '/dashboard/leave',
    icon: Calendar,
  },
  {
    label: 'Penggajian',
    href: '/dashboard/payroll',
    icon: CreditCard,
    roles: ['hr_admin', 'company_admin'],
  },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { employee, logout, refreshToken } = useAuthStore()
  const [loggingOut, setLoggingOut] = useState(false)

  const handleLogout = async () => {
    if (loggingOut) return
    setLoggingOut(true)
    try {
      if (refreshToken) {
        await api.post('/auth/logout', { refresh_token: refreshToken })
      }
    } catch {
      // Logout locally regardless of API response
    } finally {
      logout()
      // Clear the auth cookie
      document.cookie = 'hadir-auth-token=; path=/; max-age=0'
      router.push('/auth/login')
      toast.success('Sampai jumpa! 👋')
    }
  }

  const visibleItems = NAV_ITEMS.filter(
    (item) =>
      !item.roles || (employee?.role && item.roles.includes(employee.role)),
  )

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-zinc-950 border-r border-zinc-800/60">

      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-zinc-800/60">
        <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center flex-shrink-0">
          <svg viewBox="0 0 20 20" fill="none" className="w-4.5 h-4.5">
            <path d="M10 2L3 6.5V13.5L10 18L17 13.5V6.5L10 2Z" fill="white" fillOpacity="0.2" stroke="white" strokeWidth="1.2"/>
            <circle cx="10" cy="10" r="3" fill="white"/>
          </svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-white leading-tight">HaDir</p>
          <p className="text-[10px] text-zinc-500 leading-tight">HRMS Platform</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {visibleItems.map((item) => {
          const isActive = item.exact
            ? pathname === item.href
            : pathname.startsWith(item.href)

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm',
                'transition-all duration-150',
                isActive
                  ? 'bg-brand-500/15 text-brand-400 font-medium'
                  : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50',
              )}
            >
              <item.icon
                className={cn(
                  'w-4 h-4 flex-shrink-0 transition-colors',
                  isActive ? 'text-brand-400' : 'text-zinc-600 group-hover:text-zinc-400',
                )}
              />
              <span className="flex-1">{item.label}</span>
              {isActive && (
                <div className="w-1 h-1 rounded-full bg-brand-400" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* User section */}
      <div className="px-3 py-3 border-t border-zinc-800/60 space-y-1">
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50 transition-all text-sm">
          <Bell className="w-4 h-4 flex-shrink-0" />
          <span>Notifikasi</span>
        </button>
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50 transition-all text-sm">
          <Settings className="w-4 h-4 flex-shrink-0" />
          <span>Pengaturan</span>
        </button>

        {/* Employee card */}
        {employee && (
          <div className="mt-2 pt-3 border-t border-zinc-800/60">
            <div className="flex items-center gap-3 px-3 py-2">
              <div className="w-8 h-8 rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-semibold text-brand-400">
                  {getInitials(employee.full_name)}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">
                  {employee.full_name}
                </p>
                <p className="text-[11px] text-zinc-500 truncate">
                  {getRoleLabel(employee.role)}
                </p>
              </div>
            </div>

            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-500/5 transition-all text-sm mt-1 disabled:opacity-50"
            >
              <LogOut className="w-4 h-4 flex-shrink-0" />
              <span>{loggingOut ? 'Keluar...' : 'Keluar'}</span>
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
