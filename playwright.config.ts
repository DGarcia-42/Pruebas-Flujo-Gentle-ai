import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for perfil-usuario E2E suite.
 *
 * Boots two servers before running tests:
 *   1. FastAPI backend via uvicorn (port 8000) — healthcheck on /docs
 *   2. Vite dev server (port 5173) — the React SPA
 *
 * All test requests go through Vite's dev proxy (/api → :8000), so
 * there is no CORS configuration needed.
 *
 * reuseExistingServer: true locally so you can keep servers running
 * during development. In CI (!process.env.CI is false) servers always
 * start fresh.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      // Backend: FastAPI via uvicorn
      command: 'python -m uvicorn app.main:app --port 8000',
      cwd: './backend',
      url: 'http://127.0.0.1:8000/docs',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      // Frontend: Vite dev server
      command: 'npm run dev',
      cwd: './frontend',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
