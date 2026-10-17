import { describe, it, expect } from 'vitest'

// The dashboard shows what people use, not how the server is wired.
const raw = import.meta.glob(['./*.vue', '../components/*.vue', '../stores/*.ts'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const src = (name: string) => Object.entries(raw).find(([k]) => k.endsWith(name))![1]

describe('no operational details in the UI', () => {
  it('the project overview shows no ports and no filesystem paths', () => {
    const detail = src('ProjectDetailView.vue')
    expect(detail).not.toMatch(/Odoo Port|DB Port|odoo_port|db_port/)
    expect(detail).not.toContain('Addons Paths')
    expect(detail).not.toContain('addons_paths')
  })

  it('the project type carries no ports, host folder or config path', () => {
    const store = src('projects.ts')
    expect(store).not.toMatch(/odoo_port|db_port|conf_file|folder/)
    expect(store).toContain('uses_hr_base')
  })

  it('onboarding does not display assigned ports', () => {
    expect(src('OnboardView.vue')).not.toContain('Assigned Ports')
  })

  it('the branches tab decides hr-base handling from a flag, not from a host path', () => {
    const tab = src('BranchTab.vue')
    expect(tab).not.toMatch(/props\.folder/)
    expect(tab).toContain('usesHrBase')
  })

  it('the health page link is only for managers and admins', () => {
    const sidebar = src('Sidebar.vue')
    const link = sidebar.slice(sidebar.indexOf('to="/health"') - 80, sidebar.indexOf('to="/health"') + 40)
    expect(link).toMatch(/v-if="auth\.canOnboard"/)
  })

  it('the config store never sends the token to a different origin and tolerates a stale token', () => {
    const cfg = src('config.ts')
    expect(cfg).toContain("fetch('/api/config'")        // same-origin relative URL only
    expect(cfg).toContain('Authorization')
  })
})
