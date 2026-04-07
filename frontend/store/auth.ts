/**
 * stores/auth.ts
 * ──────────────
 * Global auth state via Zustand.
 * Persists tokens to localStorage — survives page refresh.
 * The API interceptor reads from this store on every request.
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { EmployeeProfile } from '@/types'

interface AuthStore {
  employee: EmployeeProfile | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean

  // Actions
  setAuth: (payload: {
    employee: EmployeeProfile
    accessToken: string
    refreshToken: string
  }) => void
  setAccessToken: (token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      employee: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setAuth: ({ employee, accessToken, refreshToken }) =>
        set({
          employee,
          accessToken,
          refreshToken,
          isAuthenticated: true,
        }),

      setAccessToken: (accessToken) => set({ accessToken }),

      logout: () =>
        set({
          employee: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'hadir-auth',
      storage: createJSONStorage(() => localStorage),
      // Only persist what's needed — never the loading state
      partialize: (state) => ({
        employee: state.employee,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)
