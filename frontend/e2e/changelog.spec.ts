import { test, expect } from '@playwright/test'
import { THEMES, signIn, shot } from './helpers'

for (const theme of THEMES) {
  test(`Help shows the shared sign-in fix in the changelog (${theme})`, async ({ page }) => {
    await signIn(page, 'admin', theme)
    await page.goto('/help')
    await expect(page.locator('aside')).toContainText('v1.10.6')
    const release = page.locator('.card').filter({ hasText: '1.10.6' }).last()
    await expect(release).toContainText('2026-10-27')
    await expect(release).toContainText('Open as links remain valid for 60 seconds')
    await expect(release).toContainText('verified database neutralization for every role')
    await release.scrollIntoViewIfNeeded()
    await shot(page, 'changelog-1.10.6', theme)
  })
}
