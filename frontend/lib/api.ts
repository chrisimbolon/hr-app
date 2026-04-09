/**
 * lib/api.ts
 * ──────────
 * Axios instance with automatic JWT refresh.
 *
 * How it works:
 *   1. Every request gets Authorization: Bearer <access_token> from Zustand
 *   2. If response is 401 → try to refresh silently using refresh_token
 *   3. If refresh succeeds → retry original request with new access_token
 *   4. If refresh fails → clear auth state → redirect to /auth/login
 *
 * This means every component just calls api.get/post/patch without
 * ever thinking about token expiry. It just works.
 */
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${BASE_URL}/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
})

// Attach access token to every request
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== 'undefined') {
    // Import lazily to avoid circular deps
    const { useAuthStore } = require('@/stores/auth')
    const token = useAuthStore.getState().accessToken
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// 401 → attempt silent refresh
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
}> = []

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      }).then((token) => {
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${token}`
        }
        return api(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      const { useAuthStore } = require('@/stores/auth')
      const refreshToken = useAuthStore.getState().refreshToken

      if (!refreshToken) throw new Error('No refresh token')

      const { data } = await axios.post(`${BASE_URL}/v1/auth/refresh`, {
        refresh_token: refreshToken,
      })

      const newAccessToken  = data.data.access_token
      const newRefreshToken = data.data.refresh_token  // rotation: MUST update stored token
      useAuthStore.getState().setAuth({
        ...useAuthStore.getState(),
        employee: useAuthStore.getState().employee!,
        accessToken: newAccessToken,
        refreshToken: newRefreshToken,
      })

      processQueue(null, newAccessToken)

      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
      }
      return api(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError as Error, null)
      const { useAuthStore } = require('@/stores/auth')
      useAuthStore.getState().logout()
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)

export default api
