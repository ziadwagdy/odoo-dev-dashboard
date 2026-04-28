import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeChoice = 'system' | 'light' | 'dark'

const mq = window.matchMedia('(prefers-color-scheme: dark)')

function resolvedTheme(choice: ThemeChoice): 'dark' | 'light' {
  if (choice === 'system') return mq.matches ? 'dark' : 'light'
  return choice
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<ThemeChoice>(
    (localStorage.getItem('theme') as ThemeChoice) ?? 'system'
  )

  const isDark = ref(resolvedTheme(theme.value) === 'dark')

  function applyTheme(choice: ThemeChoice) {
    const resolved = resolvedTheme(choice)
    document.documentElement.setAttribute('data-theme', resolved)
    document.documentElement.style.colorScheme = resolved
    isDark.value = resolved === 'dark'
  }

  // Cycle: system → light → dark → system
  function toggle() {
    const next: Record<ThemeChoice, ThemeChoice> = { system: 'light', light: 'dark', dark: 'system' }
    theme.value = next[theme.value]
  }

  // Re-apply when OS preference changes (only matters when theme = 'system')
  mq.addEventListener('change', () => {
    if (theme.value === 'system') applyTheme('system')
  })

  watch(theme, (t) => {
    applyTheme(t)
    localStorage.setItem('theme', t)
  }, { immediate: true })

  return { theme, isDark, toggle }
})
