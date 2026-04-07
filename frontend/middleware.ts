import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_ROUTES = ['/auth/login']
const AUTH_ROUTES = ['/auth']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Check for stored auth (Zustand persists to localStorage, not cookies)
  // So we use a cookie we set on login for SSR route protection
  const authCookie = request.cookies.get('hadir-auth-token')
  const isAuthenticated = !!authCookie?.value

  const isPublicRoute = PUBLIC_ROUTES.some((r) => pathname.startsWith(r))
  const isDashboardRoute = pathname.startsWith('/dashboard')

  // Unauthenticated user trying to access dashboard → login
  if (isDashboardRoute && !isAuthenticated) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  // Authenticated user trying to access login → dashboard
  if (isPublicRoute && isAuthenticated) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
