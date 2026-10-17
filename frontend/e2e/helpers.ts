import { expect, Page, Locator, test } from '@playwright/test'

export type Role = 'admin' | 'developer'
export const THEMES = ['dark', 'light'] as const
export type Theme = (typeof THEMES)[number]
export const PROJECT = process.env.UI_PROJECT || 'omc-holding'

const TOKENS: Record<Role, string> = {
  admin: process.env.UI_TOKEN_ADMIN || '',
  developer: process.env.UI_TOKEN_DEV || '',
}

/** Sign in without the login form (throwaway test users) and force a theme. */
export async function signIn(page: Page, role: Role, theme: Theme) {
  test.skip(!TOKENS[role], `no ${role} token supplied`)
  await page.addInitScript(([token, r, user, th]) => {
    localStorage.setItem('auth_token', token)
    localStorage.setItem('auth_role', r)
    localStorage.setItem('auth_user', user)
    localStorage.setItem('theme', th)
  }, [TOKENS[role], role, `zz-ui-${role}`, theme] as const)
}

export async function shot(page: Page, name: string, theme: Theme) {
  await page.screenshot({ path: `/artifacts/${name}-${theme}.png`, fullPage: false })
}

/** WCAG relative luminance (0 dark … 1 light) of the first opaque background up the DOM tree. */
export async function bgLuminance(locator: Locator): Promise<number> {
  return locator.evaluate((el) => {
    const lin = (v: number) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }
    let n: Element | null = el
    while (n) {
      const m = getComputedStyle(n).backgroundColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/)
      if (m && (m[4] === undefined || parseFloat(m[4]) > 0.6)) {
        return 0.2126 * lin(+m[1]) + 0.7152 * lin(+m[2]) + 0.0722 * lin(+m[3])
      }
      n = n.parentElement
    }
    return 1
  })
}

/** Text colour luminance of an element. */
export async function textLuminance(locator: Locator): Promise<number> {
  return locator.evaluate((el) => {
    const lin = (v: number) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }
    const m = getComputedStyle(el).color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)!
    return 0.2126 * lin(+m[1]) + 0.7152 * lin(+m[2]) + 0.0722 * lin(+m[3])
  })
}

export function contrast(a: number, b: number) {
  const [hi, lo] = a > b ? [a, b] : [b, a]
  return (hi + 0.05) / (lo + 0.05)
}

/** The surface a theme should use for panels/modals: dark theme -> dark, light theme -> light. */
export function expectThemedSurface(lum: number, theme: Theme, what: string) {
  if (theme === 'dark') expect(lum, `${what} should be dark in the dark theme`).toBeLessThan(0.25)
  else expect(lum, `${what} should be light in the light theme`).toBeGreaterThan(0.6)
}

export async function openProject(page: Page, name = PROJECT) {
  await page.goto(`/project/${name}`)
  await page.waitForSelector('.tab-btn')
}

export async function pageErrors(page: Page): Promise<string[]> {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(String(e)))
  return errors
}

/** The app keeps event streams open, so "network idle" never happens: wait for real content instead. */
export async function ready(page: Page) {
  await page.waitForSelector('main', { state: 'visible' })
  await page.waitForTimeout(400)
}
