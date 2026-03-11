import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0f0b14',
        'bg-secondary': '#1a1420',
        surface: '#251b2f',
        'surface-hover': '#2d2138',
        border: '#3d2d4a',
        'border-hover': '#4d3d5a',
        accent: '#a24689',
        'accent-hover': '#875a7b',
        'accent-light': '#c95fb5',
        primary: '#714b67',
        'primary-dark': '#5d3d56',
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-primary': 'linear-gradient(135deg, #714b67 0%, #a24689 100%)',
        'gradient-success': 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
        'gradient-warning': 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(162, 70, 137, 0.3)',
        'glow': '0 0 20px rgba(162, 70, 137, 0.4)',
        'glow-lg': '0 0 30px rgba(162, 70, 137, 0.5)',
        'inner-glow': 'inset 0 0 20px rgba(162, 70, 137, 0.1)',
      }
    }
  },
  plugins: []
} satisfies Config
