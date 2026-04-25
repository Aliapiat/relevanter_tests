import { chromium } from '@playwright/test';

const baseURL = process.env.BASE_URL || 'http://localhost:7800';
const authFile = 'automated/.auth/user.json';

/**
 * globalSetup: логин через UI и сохранение storageState.
 * Выполняется один раз перед всеми тестами.
 * НЕ отображается в Playwright UI — пользователь видит только реальные тесты.
 */
async function globalSetup() {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(`${baseURL}/recruiter/`);
  await page.fill('input[type="email"]', 'admin@example.com');
  await page.fill('input[type="password"]', 'admin');
  await page.click('button:has-text("Войти")');
  await page.waitForURL(/\/recruiter\//, { timeout: 10_000 });

  // Копируем auth-данные из sessionStorage в localStorage
  // (storageState не захватывает sessionStorage)
  await page.evaluate(() => {
    const keys = ['crm_auth_token', 'crm_auth_user', 'crm_auth_role', 'crm_auth_rememberMe'];
    keys.forEach(key => {
      const val = sessionStorage.getItem(key);
      if (val) localStorage.setItem(key, val);
    });
  });

  await context.storageState({ path: authFile });
  await browser.close();
}

export default globalSetup;
