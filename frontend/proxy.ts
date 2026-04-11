import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

/**
 * proxy.ts — Next.js 16 renamed the file from middleware.ts to proxy.ts
 *
 * IMPORTANT: The filename is proxy.ts but the exported function
 * must still be named "middleware" — Next.js always looks for
 * that export name regardless of what the file is called.
 *
 * URL structure (route groups are invisible to URLs):
 *   app/(auth)/login/page.tsx        → /login
 *   app/(dashboard)/page.tsx         → /
 *   app/(dashboard)/attendance/...   → /attendance
 *   app/(dashboard)/employees/...    → /employees
 *   app/(dashboard)/leave/...        → /leave
 *   app/(dashboard)/payroll/...      → /payroll
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

  if (isProtectedPage && !isAuthenticated) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  if (isLoginPage && isAuthenticated) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api/).*)'],
}
