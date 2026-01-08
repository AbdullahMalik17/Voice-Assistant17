import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Futuristic cyber theme colors
        cyber: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        neon: {
          blue: '#00f5ff',
          purple: '#bf00ff',
          pink: '#ff00aa',
          green: '#00ff88',
          yellow: '#ffea00',
        },
        dark: {
          bg: '#0a0e1a',
          card: '#111827',
          border: '#1f2937',
          hover: '#1e293b',
        },
      },
      animation: {
        'pulse-ring': 'pulse-ring 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow-pulse': 'glow-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-up': 'slide-up 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-down': 'slide-down 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-in': 'fade-in 0.3s ease-out',
        'shimmer': 'shimmer 2s linear infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        'pulse-ring': {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.1)', opacity: '0.5' },
        },
        'glow-pulse': {
          '0%, 100%': {
            boxShadow: '0 0 20px rgba(0, 245, 255, 0.5), 0 0 40px rgba(0, 245, 255, 0.3)',
          },
          '50%': {
            boxShadow: '0 0 30px rgba(0, 245, 255, 0.8), 0 0 60px rgba(0, 245, 255, 0.5)',
          },
        },
        'slide-up': {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'cyber-grid': 'linear-gradient(rgba(0, 245, 255, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 245, 255, 0.1) 1px, transparent 1px)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
export default config
