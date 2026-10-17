import { test, expect } from '@playwright/test'
import { THEMES, PROJECT, signIn, shot, bgLuminance, textLuminance, contrast, expectThemedSurface, openProject, ready } from './helpers'

for (const theme of THEMES) {
  test.describe(`${theme} theme`, () => {

    test('every main page renders in the theme without console errors', async ({ page }) => {
      await signIn(page, 'admin', theme)
      const errors: string[] = []
      page.on('pageerror', (e) => errors.push(String(e)))
      for (const path of ['/', '/health', '/users', '/security', '/help', `/project/${PROJECT}`]) {
        await page.goto(path)
        await ready(page)
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
        expectThemedSurface(await bgLuminance(page.locator('body')), theme, `page background of ${path}`)
        const main = page.locator('main').first()
        if (await main.count()) {
          const c = contrast(await bgLuminance(main), await textLuminance(page.locator('main h1, main h2, main h3, main p').first()))
          expect(c, `readable text on ${path}`).toBeGreaterThan(3)
        }
      }
      await shot(page, 'security-page', theme)
      expect(errors, errors.join('\n')).toEqual([])
    })

    test('Security page has the sidebar and a working way back', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await page.goto('/security')
      await expect(page.locator('aside')).toBeVisible()
      const crumb = page.locator('nav').filter({ hasText: 'Dashboard' }).filter({ hasText: 'Security' }).first()
      await expect(crumb).toBeVisible()
      await crumb.getByText('Dashboard').click()
      await expect(page).toHaveURL(/\/$/)
    })

    test('user menu opens above the page content and can be reached', async ({ page }) => {
      await signIn(page, 'admin', theme)
      await openProject(page)
      await page.locator('header').getByText('zz-ui-admin').first().click()
      const menu = page.getByText('Sign out').locator('xpath=ancestor::div[contains(@class,"absolute")][1]')
      await expect(menu).toBeVisible()
      const box = (await menu.boundingBox())!
      const topElement = await page.evaluate(([x, y]) => {
        const el = document.elementFromPoint(x, y)
        return !!el && !!el.closest('.absolute')?.textContent?.includes('Sign out')
      }, [box.x + box.width / 2, box.y + box.height - 8])
      expect(topElement, 'nothing from the page covers the user menu').toBe(true)
      expectThemedSurface(await bgLuminance(menu), theme, 'user menu')
      await shot(page, 'user-menu', theme)
    })
  })
}
