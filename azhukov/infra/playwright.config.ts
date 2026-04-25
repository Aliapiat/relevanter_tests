import { defineConfig, devices } from '@playwright/test';

/**
 * Конфигурация Playwright для E2E тестов HR Recruiter.
 *
 * baseURL: по умолчанию http://localhost:7800 (nginx hr).
 * Авторизация: globalSetup логинится один раз и сохраняет storageState.
 * Все тесты стартуют уже авторизованными — без повторного логина.
 */
export default defineConfig({
  testDir: './automated',
  globalSetup: './automated/auth.setup.ts',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'results/report' }],
    ['list'],
  ],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:7800',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: process.env.VIDEO === 'on' ? 'on' : 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
    launchOptions: {
      slowMo: Number(process.env.SLOW_MO) || 0,
    },
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 960 },
        storageState: 'automated/.auth/user.json',
      },
    },
  ],
});
