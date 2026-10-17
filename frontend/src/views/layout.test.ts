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

// The header (user menu dropdown) must stack above the scrolling page content; with
// backdrop-blur it forms its own stacking context, so it needs an explicit z-index.
const layout = import.meta.glob('../layouts/SidebarLayout.vue', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
describe('header stacking', () => {
  it('the header sits above the page content so the user dropdown is not covered', () => {
    const source = Object.values(layout)[0]
    const header = source.split('\n').find(l => l.includes('<header')) || ''
    expect(header).toMatch(/\brelative\b/)
    expect(header).toMatch(/\bz-30\b/)
  })
})

// Tab panels belong below the tab bar. The Manage panel (Deploy / Delete) once sat above it.
const detail = import.meta.glob('./ProjectDetailView.vue', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
describe('project page structure', () => {
  const source = Object.values(detail)[0]
  const tabBar = source.indexOf('<!-- Tabs -->')

  it('every tab panel is rendered after the tab bar', () => {
    expect(tabBar).toBeGreaterThan(0)
    for (const id of ['overview', 'logs', 'database', 'modules', 'branches', 'settings', 'notebook', 'manage']) {
      const at = source.indexOf(`activeTab === '${id}'`)
      expect(at, `panel ${id} exists`).toBeGreaterThan(-1)
      expect(at, `panel ${id} comes after the tab bar`).toBeGreaterThan(tabBar)
    }
  })

  it('Deploy and Delete live only inside the Manage panel', () => {
    const manage = source.indexOf("activeTab === 'manage'")
    const deploy = source.indexOf('@click="deploy"')
    const del = source.indexOf('showDeleteModal = true')
    expect(deploy).toBeGreaterThan(manage)
    expect(del).toBeGreaterThan(manage)
    expect(source.slice(0, source.indexOf('<!-- Tabs -->'))).not.toContain('@click="deploy"')
  })
})
