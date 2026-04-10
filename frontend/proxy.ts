import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

/**
 * proxy.ts  (Next.js 16 renamed middleware.ts → proxy.ts)
 * ──────────
 * Route protection for HaDir.
 *
 * URL structure (route groups are invisible to URLs):
 *   app/(auth)/login/page.tsx        → /login
 *   app/(dashboard)/page.tsx         → /            ← dashboard home
 *   app/(dashboard)/attendance/...   → /attendance
 *   app/(dashboard)/employees/...    → /employees
 *   app/(dashboard)/leave/...        → /leave
 *   app/(dashboard)/payroll/...      → /payroll
 *
 * Auth bridge:
 *   LoginForm sets cookie 'hadir-auth-token=1' on successful login
 *   Sidebar clears cookie 'hadir-auth-token=' on logout
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const isAuthenticated = !!request.cookies.get('hadir-auth-token')?.value

  const isLoginPage = pathname === '/login'

  const isProtectedPage =
    pathname === '/' ||
    pathname.startsWith('/attendance') ||
    pathname.startsWith('/employees') ||
    pathname.startsWith('/leave') ||
    pathname.startsWith('/payroll')

  // Unauthenticated + protected page → login
  if (isProtectedPage && !isAuthenticated) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Authenticated + login page → dashboard home
  if (isLoginPage && isAuthenticated) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api/).*)'],
}