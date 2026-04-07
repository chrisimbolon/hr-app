import type { Metadata } from 'next'
import { Toaster } from 'react-hot-toast'
import './globals.css'

export const metadata: Metadata = {
  title: {
    default: 'HaDir HRMS',
    template: '%s | HaDir',
  },
  description: 'Sistem Manajemen HR & Kehadiran untuk Perusahaan Indonesia',
  icons: {
    icon: '/favicon.ico',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="id" suppressHydrationWarning>
      <body>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              borderRadius: '10px',
              background: '#18181b',
              color: '#fafafa',
              fontSize: '14px',
            },
            success: {
              iconTheme: { primary: '#f97f0a', secondary: '#fff' },
            },
          }}
        />
      </body>
    </html>
  )
}
