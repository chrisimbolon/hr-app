'use client'

import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import type { ApiResponse, LoginResponse } from '@/types'
import { Trash2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'

// ── Helpers ───────────────────────────────────────────────────────
function formatEmployeeCode(value: string) {
  const cleaned = value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase()

  if (cleaned.startsWith('EMP') && cleaned.length > 3) {
    return `EMP-${cleaned.slice(3)}`
  }

  return cleaned
}

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

  // Auto-submit PIN
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

  // ── Step 1 submit ───────────────────────────────────────────────
  const handleCodeSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (isLoading) return

    if (!employeeCode.trim()) {
      setError('Masukkan kode karyawan')
      triggerShake()
      return
    }

    setIsLoading(true)
    setError('')

    // Small UX delay (feels smoother)
    setTimeout(() => {
      setStep('pin')
      setIsLoading(false)
    }, 300)
  }

  // ── Login ───────────────────────────────────────────────────────
  const handleLogin = async () => {
    if (isLoading) return

    setIsLoading(true)
    setError('')

    try {
      const { data } = await api.post<ApiResponse<LoginResponse>>(
        '/auth/login',
        {
          employee_code: employeeCode.replace('-', '').toUpperCase().trim(),
          pin,
        },
      )

      setAuth({
        employee: data.data.employee,
        accessToken: data.data.access_token,
        refreshToken: data.data.refresh_token,
      })

      toast.success(
        `Selamat datang, ${
          data.data.employee.full_name.split(' ')[0]
        }! 👋`,
      )

      router.push('/dashboard')
    } catch (err: unknown) {
      const message =
        (err as {
          response?: { data?: { error?: { message?: string } } }
        })?.response?.data?.error?.message ??
        'Login gagal. Coba lagi.'

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
          <p className="text-xs text-zinc-500 mt-0.5">
            HR & Attendance Management
          </p>
        </div>
      </div>

      {/* Card */}
      <div
        className={cn(
          'w-full bg-zinc-900 border border-zinc-800 rounded-2xl p-6',
          shake && 'animate-[shake_0.5s_ease-in-out]',
        )}
      >
        {step === 'code' ? (
          <form onSubmit={handleCodeSubmit} className="flex flex-col gap-5">
            <div>
              <p className="text-sm font-medium text-zinc-400 mb-4 text-center">
                Masukkan kode karyawan
              </p>

              <input
                type="text"
                value={employeeCode}
                onChange={(e) => {
                  setEmployeeCode(formatEmployeeCode(e.target.value))
                  setError('')
                }}
                placeholder="EMP-00001"
                autoFocus
                className={cn(
                  'w-full bg-zinc-800 border rounded-xl px-4 py-3.5',
                  'text-white text-center text-lg font-mono tracking-widest',
                  'outline-none transition-all',
                  error
                    ? 'border-red-500/60'
                    : 'border-zinc-700 focus:border-brand-500/60',
                )}
              />

              {error && (
                <p className="text-red-400 text-xs mt-2 text-center">
                  {error}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={!employeeCode.trim() || isLoading}
              className={cn(
                'btn-primary w-full py-3 text-base',
                (!employeeCode.trim() || isLoading) &&
                  'opacity-50 cursor-not-allowed',
              )}
            >
              {isLoading ? 'Memproses...' : 'Lanjut'}
            </button>
          </form>
        ) : (
          <div className="flex flex-col items-center gap-6">
            <p className="text-sm text-zinc-400">
              Halo{' '}
              <span className="text-white font-medium">
                {employeeCode}
              </span>
            </p>

            <PinDots length={PIN_LENGTH} filled={pin.length} />

            {error && (
              <p className="text-red-400 text-xs text-center">{error}</p>
            )}

            <div className="grid grid-cols-3 gap-3">
              {['1','2','3','4','5','6','7','8','9'].map((d) => (
                <PinKey key={d} label={d} onClick={() => handlePinKey(d)} />
              ))}

              <PinKey onClick={() => setStep('code')}>
                ←
              </PinKey>

              <PinKey label="0" onClick={() => handlePinKey('0')} />

              <PinKey onClick={handleDelete}>
                <Trash2 className="w-5 h-5 text-zinc-400" />
              </PinKey>
            </div>

            {isLoading && (
              <p className="text-sm text-brand-400">Memverifikasi...</p>
            )}
          </div>
        )}
      </div>

      <p className="text-zinc-600 text-xs text-center">
        Lupa PIN? Hubungi HR admin perusahaan kamu.
      </p>
    </div>
  )
}