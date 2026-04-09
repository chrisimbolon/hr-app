import type { NextRequest } from 'next/server'
import { NextResponse } from 'next/server'

/**
 * Middleware — route protection via cookie.
 *
 * Auth state lives in Zustand → localStorage (client-side only).
 * We bridge this to SSR by setting a presence cookie on login
 * (in LoginForm.tsx) and clearing it on logout (in Sidebar.tsx).
 *
 * The cookie value is NOT a secret — it's just a boolean flag.
 * The real access token lives in localStorage and is sent as
 * Authorization: Bearer on every API call by the axios interceptor.
 */

const PUBLIC_PATHS = ['/auth/login', '/auth/']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const authCookie = request.cookies.get('hadir-auth-token')
  const isAuthenticated = !!authCookie?.value

  const isPublicPath = PUBLIC_PATHS.some((p) => pathname.startsWith(p))
  const isDashboardPath = pathname.startsWith('/dashboard')

  // Unauthenticated → redirect to login
  if (isDashboardPath && !isAuthenticated) {
    const url = new URL('/auth/login', request.url)
    return NextResponse.redirect(url)
  }

  // Already authenticated → redirect away from login to dashboard
  if (isPublicPath && isAuthenticated) {
    const url = new URL('/dashboard', request.url)
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    // Match all paths except static files, api routes, Next internals
    '/((?!_next/static|_next/image|favicon.ico|api/).*)',
  ],
}
