// app/(auth)/login/page.tsx
import LoginForm from '@/components/auth/LoginForm'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Masuk',
}

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      {/* Background texture */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, white 1px, transparent 0)`,
          backgroundSize: '32px 32px',
        }}
      />

      {/* Warm glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-sm animate-fade-in">
        <LoginForm />
      </div>
    </main>
  )
}
