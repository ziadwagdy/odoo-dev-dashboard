import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',
  timeout: 90_000,
  retries: 0,
  workers: 2,
  reporter: [['list']],
  outputDir: '/artifacts/results',
  use: {
    baseURL: process.env.UI_BASE_URL || 'http://127.0.0.1:8892',
    headless: true,
    viewport: { width: 1366, height: 820 },
    ignoreHTTPSErrors: true,
  },
})
