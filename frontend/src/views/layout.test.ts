import { describe, it, expect } from 'vitest'

// Every page except login must sit inside the sidebar layout and show a breadcrumb,
// otherwise users get stuck on it with no way back (this happened to the Security page).
const files = import.meta.glob('./*.vue', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const EXEMPT = ['./LoginView.vue']

describe('page layout', () => {
  for (const [path, source] of Object.entries(files)) {
    if (EXEMPT.includes(path)) continue
    it(`${path} uses the sidebar layout with a breadcrumb`, () => {
      expect(source).toContain('<SidebarLayout')
      expect(source).toContain('<Breadcrumb')
    })
  }
})
