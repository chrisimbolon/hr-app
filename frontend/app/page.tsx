// app/page.tsx
//
// IMPORTANT: app/(dashboard)/page.tsx already serves the / route.
// This file must NOT redirect anywhere — the (dashboard) route group
// and its layout.tsx handle all auth checks for the / route.
// If you're getting redirect loops, this file's redirect() was the cause.
export default function RootPage() {
  // return null
  return <h1>ROOT WORKS</h1>
}
