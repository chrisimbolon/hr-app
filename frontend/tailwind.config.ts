import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-geist-mono)', 'monospace'],
      },
      colors: {
        brand: {
          500: '#F97F0A',
          600: '#EA6305',
        },
      },
      borderRadius: {
        lg: '12px',
        md: '8px',
        sm: '6px',
      },
    },
  },
  plugins: [],
}

export default config