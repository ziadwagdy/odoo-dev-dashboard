import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // All theme colors reference CSS variables (RGB triplets) so opacity
        // modifiers like bg-surface/80 continue to work correctly.
        bg:               'rgb(var(--c-bg)         / <alpha-value>)',
        'bg-secondary':   'rgb(var(--c-bg2)        / <alpha-value>)',
        surface:          'rgb(var(--c-surface)    / <alpha-value>)',
        'surface-hover':  'rgb(var(--c-surface-hv) / <alpha-value>)',
        border:           'rgb(var(--c-border)     / <alpha-value>)',
        'border-hover':   'rgb(var(--c-border-hv)  / <alpha-value>)',
        accent:           'rgb(var(--c-accent)     / <alpha-value>)',
        'accent-hover':   'rgb(var(--c-accent-hv)  / <alpha-value>)',
        'accent-light':   'rgb(var(--c-accent-lt)  / <alpha-value>)',
        primary:          'rgb(var(--c-primary)    / <alpha-value>)',
        'primary-dark':   'rgb(var(--c-primary-dk) / <alpha-value>)',
        success:          '#10b981',
        warning:          '#f59e0b',
        danger:           '#ef4444',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
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
        'glow':    '0 0 20px rgba(162, 70, 137, 0.4)',
        'glow-lg': '0 0 30px rgba(162, 70, 137, 0.5)',
        'inner-glow': 'inset 0 0 20px rgba(162, 70, 137, 0.1)',
      }
    }
  },
  plugins: []
} satisfies Config
