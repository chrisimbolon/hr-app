import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

/**
 * Middleware — route protection.
 *
 * Your route group structure:
 *   app/(auth)/login/page.tsx     → URL: /login
 *   app/(dashboard)/page.tsx      → URL: /          (dashboard home)
 *
 * Route groups (parentheses) are invisible to the URL router.
 * So the dashboard lives at / and login lives at /login.
 *
 * Auth state is bridged from localStorage → cookie:
 *   LoginForm sets  'hadir-auth-token=1' on successful login
 *   Sidebar clears  'hadir-auth-token='  on logout
 */

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const authCookie = request.cookies.get('hadir-auth-token')
  const isAuthenticated = !!authCookie?.value

  const isLoginPage = pathname === '/login' || pathname.startsWith('/login/')
  const isRootOrApp  = pathname === '/' || pathname.startsWith('/attendance') ||
                       pathname.startsWith('/employees') || pathname.startsWith('/leave') ||
                       pathname.startsWith('/payroll')

  // Unauthenticated user trying to access the app → send to login
  if (isRootOrApp && !isAuthenticated) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Already authenticated user on login page → send to app home
  if (isLoginPage && isAuthenticated) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|api/).*)',
  ],
}
