import { test, expect } from '@playwright/test'
import { THEMES, PROJECT, signIn, shot, bgLuminance, expectThemedSurface, openProject, ready } from './helpers'

for (const theme of THEMES) {
  test.describe(`${theme} theme`, () => {

    test('header offers "Open as…" and no Deploy/Delete above the tabs', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await openProject(page)
      await expect(page.getByRole('button', { name: /Open as/ })).toBeVisible()
      const aboveTabs = await page.evaluate(() => {
        const bar = document.querySelector('.tab-btn')!.parentElement!
        const top = bar.getBoundingClientRect().top
        return [...document.querySelectorAll('button, a')]
          .filter((e) => e.getBoundingClientRect().bottom <= top && e.getBoundingClientRect().height > 0)
          .map((e) => (e.textContent || '').trim())
      })
      expect(aboveTabs.some((t) => /^Deploy/.test(t)), 'Deploy above the tabs').toBe(false)
      expect(aboveTabs.some((t) => /^Delete/.test(t)), 'Delete above the tabs').toBe(false)
      expect(aboveTabs.some((t) => t === 'Open'), 'plain "Open" link').toBe(false)
    })

    test('Deploy and Delete live inside the admin-only Manage tab', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await openProject(page)
      await page.locator('.tab-btn', { hasText: 'Manage' }).click()
      const tabTop = (await page.locator('.tab-btn').first().boundingBox())!.y
      for (const label of ['Deploy now', 'Delete']) {
        const b = (await page.getByRole('button', { name: label, exact: false }).first().boundingBox())!
        expect(b.y, `${label} is below the tab bar`).toBeGreaterThan(tabTop)
      }
      await shot(page, 'manage-tab', theme)
    })

    test('the overview shows what people use: no ports, no server paths', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await openProject(page)
      const text = await page.locator('main').innerText()
      for (const forbidden of ['Odoo Port', 'DB Port', 'Addons Paths', '/mnt/', '/home/', 'odoo-dev/']) {
        expect(text, `"${forbidden}" must not be shown`).not.toContain(forbidden)
      }
      for (const wanted of ['Odoo version', 'Branch', 'Updates to pull', 'Address']) {
        await expect(page.getByText(wanted, { exact: true }).first()).toBeVisible()
      }
      await shot(page, 'overview', theme)
    })

    test('developers see no Manage tab, no Deploy, no Delete, no Security link', async ({ page }) => {
      await signIn(page, 'developer', theme)
      await openProject(page)
      await expect(page.locator('.tab-btn', { hasText: 'Manage' })).toHaveCount(0)
      await expect(page.getByRole('button', { name: /^Deploy/ })).toHaveCount(0)
      await expect(page.getByRole('button', { name: /^Delete/ })).toHaveCount(0)
      await expect(page.locator('aside').getByText('Security')).toHaveCount(0)
      await expect(page.locator('aside').getByText('Health')).toHaveCount(0)
      const cfg = await page.evaluate(async () => (await fetch('/api/config', { headers: { Authorization: 'Token ' + localStorage.getItem('auth_token') } })).json())
      expect(Object.keys(cfg), 'no internal tool links for developers').toEqual(['dashboard_title'])
    })

    test('Open as… lists the project databases and users, themed', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await openProject(page)
      await page.getByRole('button', { name: /Open as/ }).click()
      const modal = page.locator('div.fixed').filter({ hasText: `Open ${PROJECT} as` }).first()
      await expect(modal).toBeVisible()
      await expect(modal.getByText('no databases yet')).toHaveCount(0)
      const dbSelect = modal.locator('select').first()
      await expect(dbSelect.locator('option').first()).toBeAttached({ timeout: 20000 })
      expect(await dbSelect.locator('option').count()).toBeGreaterThan(0)
      await expect(modal.locator('select').nth(1).locator('option').first()).toBeAttached({ timeout: 30000 })
      expectThemedSurface(await bgLuminance(modal.locator('div').first().locator('> div').first()), theme, 'Open as dialog')
      await shot(page, 'open-as', theme)
      await modal.getByRole('button', { name: 'Cancel' }).click()
      await expect(modal).toHaveCount(0)
    })

    test('Settings tab shows curated runtime settings and never the raw configuration', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await openProject(page)
      await page.locator('.tab-btn', { hasText: 'Settings' }).click()
      await expect(page.getByText('Runtime settings')).toBeVisible()
      await expect(page.getByText('HTTP workers')).toBeVisible()
      const text = await page.locator('body').innerText()
      for (const forbidden of ['db_password', 'admin_passwd', 'addons_path', 'db_host', 'SUPERSECRET']) {
        expect(text, `"${forbidden}" must not appear`).not.toContain(forbidden)
      }
      await shot(page, 'settings', theme)
    })

    test('Branches tab calls the submodule action "Pull"', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await openProject(page)
      await page.locator('.tab-btn', { hasText: 'Branches' }).click()
      const card = page.locator('.card').filter({ hasText: 'Submodules' }).first()
      await expect(card).toBeVisible()
      await expect(card.getByRole('button', { name: 'Pull' })).toBeVisible()
      await expect(card.getByText('Update All')).toHaveCount(0)
    })

    test('Modules tab: pick a database, see its modules, Update All asks for confirmation', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await openProject(page)
      await page.locator('.tab-btn', { hasText: 'Modules' }).click()
      const select = page.locator('select').filter({ has: page.locator('option', { hasText: 'Select database' }) }).first()
      await expect(select.locator('option').nth(1)).toBeAttached({ timeout: 30000 })
      await select.selectOption({ index: 1 })
      await expect(page.getByText('Loading modules')).toHaveCount(0, { timeout: 60000 })
      expect(await page.locator('input[type=checkbox]').count(), 'module rows are listed').toBeGreaterThan(3)
      await page.getByRole('button', { name: /^Update All/ }).click()
      const confirm = page.getByText('Update All Modules?')
      await expect(confirm).toBeVisible()
      expectThemedSurface(await bgLuminance(confirm.locator('xpath=ancestor::div[contains(@class,"rounded")][1]')), theme, 'confirmation dialog')
      await shot(page, 'modules-confirm', theme)
      await page.getByRole('button', { name: 'Cancel', exact: true }).click()      // never starts a real update
      await expect(confirm).toHaveCount(0)
    })

    test('Database tab shows neutralization badges and the new actions', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await openProject(page)
      await page.locator('.tab-btn', { hasText: 'Database' }).click()
      await expect(page.getByText('+ New database')).toBeVisible()
      await expect(page.getByText(/neutralized/i).first()).toBeVisible({ timeout: 30000 })
      await shot(page, 'database', theme)
    })
  })
}

test('narrow phone viewport keeps the user menu reachable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 })
  await signIn(page, 'admin', 'dark')
  await page.goto('/')
  await ready(page)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2)
  expect(overflow, 'no horizontal page scroll on a phone').toBe(false)
})
