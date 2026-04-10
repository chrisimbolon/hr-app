import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

/**
 * middleware.ts
 * ─────────────
 * Route protection for the HaDir frontend.
 *
 * URL structure (route groups are invisible to URLs):
 *   app/(auth)/login/page.tsx       → /login
 *   app/(dashboard)/page.tsx        → /           (dashboard home)
 *   app/(dashboard)/attendance/...  → /attendance
 *   app/(dashboard)/employees/...   → /employees
 *   app/(dashboard)/leave/...       → /leave
 *   app/(dashboard)/payroll/...     → /payroll
 *
 * Auth bridge: LoginForm sets 'hadir-auth-token=1' cookie on login.
 *              Sidebar clears it on logout.
 *              Middleware reads it for server-side route protection.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const isAuthenticated = !!request.cookies.get('hadir-auth-token')?.value

  const isLoginPage = pathname === '/login'

  const isProtectedPage =
    pathname === '/' ||
    pathname.startsWith('/attendance') ||
    pathname.startsWith('/employees') ||
    pathname.startsWith('/leave') ||
    pathname.startsWith('/payroll')

  // Not logged in + trying to access protected page → go to login
  if (isProtectedPage && !isAuthenticated) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Already logged in + on login page → go to dashboard home
  if (isLoginPage && isAuthenticated) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api/).*)'],
}
