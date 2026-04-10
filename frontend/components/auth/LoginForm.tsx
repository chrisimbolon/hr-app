'use client'

import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import type { ApiResponse, LoginResponse } from '@/types'
import { Delete } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'

// ── PIN display ───────────────────────────────────────────────────
function PinDots({ length, filled }: { length: number; filled: number }) {
  return (
    <div className="flex items-center justify-center gap-3">
      {Array.from({ length }).map((_, i) => (
        <div
          key={i}
          className={cn(
            'w-3 h-3 rounded-full border-2 transition-all duration-150',
            i < filled
              ? 'bg-brand-500 border-brand-500 scale-110'
              : 'bg-transparent border-zinc-600',
          )}
        />
      ))}
    </div>
  )
}

// ── Keypad key ────────────────────────────────────────────────────
function PinKey({
  label,
  sub,
  onClick,
  className,
  children,
}: {
  label?: string
  sub?: string
  onClick: () => void
  className?: string
  children?: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'pin-key relative flex flex-col items-center justify-center',
        'w-20 h-20 rounded-2xl text-white',
        'bg-zinc-800/80 border border-zinc-700/50',
        'hover:bg-zinc-700/80 hover:border-zinc-600',
        'active:bg-zinc-600/80',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400',
        className,
      )}
    >
      {children ?? (
        <>
          <span className="text-2xl font-light tracking-tight leading-none">
            {label}
          </span>
          {sub && (
            <span className="text-[9px] tracking-[0.2em] text-zinc-500 mt-0.5 uppercase">
              {sub}
            </span>
          )}
        </>
      )}
    </button>
  )
}

// ── Main form ─────────────────────────────────────────────────────
export default function LoginForm() {
  const router = useRouter()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [step, setStep] = useState<'code' | 'pin'>('code')
  const [employeeCode, setEmployeeCode] = useState('')
  const [pin, setPin] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [shake, setShake] = useState(false)

  const PIN_LENGTH = 6

  const triggerShake = useCallback(() => {
    setShake(true)
    setTimeout(() => setShake(false), 500)
  }, [])

  // Keyboard support for PIN
  useEffect(() => {
    if (step !== 'pin') return
    const handler = (e: KeyboardEvent) => {
      if (e.key >= '0' && e.key <= '9') {
        setPin((p) => (p.length < PIN_LENGTH ? p + e.key : p))
      } else if (e.key === 'Backspace') {
        setPin((p) => p.slice(0, -1))
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [step])

  // Auto-submit when PIN is complete
  useEffect(() => {
    if (pin.length === PIN_LENGTH) {
      handleLogin()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pin])

  const handlePinKey = (digit: string) => {
    if (pin.length < PIN_LENGTH) {
      setPin((p) => p + digit)
      setError('')
    }
  }

  const handleDelete = () => {
    setPin((p) => p.slice(0, -1))
    setError('')
  }

  const handleCodeSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!employeeCode.trim()) {
      setError('Masukkan kode karyawan')
      triggerShake()
      return
    }
    setError('')
    setStep('pin')
  }

  const handleLogin = async () => {
    if (isLoading) return
    setIsLoading(true)
    setError('')

    try {
      const { data } = await api.post<ApiResponse<LoginResponse>>(
        '/auth/login',   // ← FIXED: was '/login', needs the /auth/ prefix
        {
          employee_code: employeeCode.toUpperCase().trim(),
          pin,
        },
      )

      setAuth({
        employee: data.data.employee,
        accessToken: data.data.access_token,
        refreshToken: data.data.refresh_token,
      })

      // Bridge localStorage auth state → cookie for middleware route protection.
      // We store a simple presence flag (not the actual token) because:
      //   1. The real token is in localStorage via Zustand — where the axios
      //      interceptor reads it for every API call.
      //   2. The middleware only needs to know "is there a session?" to decide
      //      whether to redirect. It doesn't validate the token.
      //   3. Storing the actual JWT in a cookie would require httpOnly (no JS
      //      access) which would break the Zustand interceptor that reads it.
      // Max-age matches refresh token TTL (7 days).
      const maxAge = 7 * 24 * 60 * 60
      document.cookie = `hadir-auth-token=1; path=/; max-age=${maxAge}; SameSite=Strict`

      toast.success(`Selamat datang, ${data.data.employee.full_name.split(' ')[0]}! 👋`)
      router.push('/')
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: { message?: string } } } })
          ?.response?.data?.error?.message ?? 'Login gagal. Coba lagi.'

      setError(message)
      setPin('')
      triggerShake()

      if (message.toLowerCase().includes('terkunci')) {
        setTimeout(() => setStep('code'), 2000)
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-8">

      {/* Logo */}
      <div className="flex flex-col items-center gap-2">
        <div className="w-14 h-14 rounded-2xl bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/30">
          <svg viewBox="0 0 28 28" fill="none" className="w-8 h-8">
            <path d="M14 3L4 8.5V19.5L14 25L24 19.5V8.5L14 3Z" fill="white" fillOpacity="0.2" stroke="white" strokeWidth="1.5"/>
            <circle cx="14" cy="14" r="4" fill="white"/>
            <path d="M14 10V7M14 21V18M10 14H7M21 14H18" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
        <div className="text-center">
          <h1 className="text-xl font-semibold text-white tracking-tight">HaDir</h1>
          <p className="text-xs text-zinc-500 mt-0.5">HR & Attendance Management</p>
        </div>
      </div>

      {/* Card */}
      <div
        className={cn(
          'w-full bg-zinc-900 border border-zinc-800 rounded-2xl p-6',
        )}
        style={{
          animation: shake ? 'shake 0.5s ease-in-out' : undefined,
        }}
      >
        {step === 'code' ? (
          /* ── Step 1: Employee code ─────────────────────────── */
          <form onSubmit={handleCodeSubmit} className="flex flex-col gap-5">
            <div>
              <p className="text-sm font-medium text-zinc-400 mb-4 text-center">
                Masukkan kode karyawan
              </p>
              <input
                type="text"
                value={employeeCode}
                onChange={(e) => {
                  setEmployeeCode(e.target.value.toUpperCase())
                  setError('')
                }}
                placeholder="ADM001"
                autoFocus
                autoComplete="off"
                autoCapitalize="characters"
                className={cn(
                  'w-full bg-zinc-800 border rounded-xl px-4 py-3.5',
                  'text-white text-center text-lg font-mono tracking-widest',
                  'placeholder:text-zinc-600 placeholder:tracking-normal placeholder:font-sans',
                  'outline-none transition-all duration-150',
                  error
                    ? 'border-red-500/60 focus:ring-2 focus:ring-red-500/30'
                    : 'border-zinc-700 focus:border-brand-500/60 focus:ring-2 focus:ring-brand-500/20',
                )}
              />
              {error && (
                <p className="text-red-400 text-xs mt-2 text-center animate-fade-in">
                  {error}
                </p>
              )}
            </div>
            <button type="submit" className="btn-primary w-full py-3 text-base">
              Lanjut
            </button>
          </form>
        ) : (
          /* ── Step 2: PIN pad ───────────────────────────────── */
          <div className="flex flex-col items-center gap-6">
            <div>
              <p className="text-sm text-zinc-400 text-center mb-1">
                Halo,{' '}
                <span className="text-white font-medium">
                  {employeeCode.toUpperCase()}
                </span>
              </p>
              <p className="text-xs text-zinc-600 text-center">
                Masukkan PIN 6 digit kamu
              </p>
            </div>

            {/* PIN dots */}
            <div className="py-2">
              <PinDots length={PIN_LENGTH} filled={pin.length} />
              {error && (
                <p className="text-red-400 text-xs mt-3 text-center animate-fade-in">
                  {error}
                </p>
              )}
            </div>

            {/* Number pad */}
            <div className="grid grid-cols-3 gap-3">
              {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((d) => (
                <PinKey key={d} label={d} onClick={() => handlePinKey(d)} />
              ))}

              {/* Back button */}
              <PinKey
                onClick={() => {
                  setStep('code')
                  setPin('')
                  setError('')
                }}
                className="text-zinc-500 hover:text-zinc-300 text-xs"
              >
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-zinc-500">
                  <path fillRule="evenodd" d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z" clipRule="evenodd" />
                </svg>
              </PinKey>

              {/* Zero */}
              <PinKey label="0" onClick={() => handlePinKey('0')} />

              {/* Delete */}
              <PinKey
                onClick={handleDelete}
                className={pin.length === 0 ? 'opacity-30 pointer-events-none' : ''}
              >
                <Delete className="w-5 h-5 text-zinc-400" />
              </PinKey>
            </div>

            {/* Loading state */}
            {isLoading && (
              <div className="flex items-center gap-2 text-brand-400 text-sm animate-fade-in">
                <div className="w-4 h-4 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
                <span>Memverifikasi...</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <p className="text-zinc-600 text-xs text-center">
        Lupa PIN? Hubungi HR admin perusahaan kamu.
      </p>
    </div>
  )
}
