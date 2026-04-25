import { type Page } from '@playwright/test';

/** Учётные данные для тестового пользователя */
export const TEST_USER = {
  email: 'admin@example.com',
  password: 'admin',
};

/**
 * Выполняет логин через UI.
 * Используется в auth.setup.ts для первоначальной авторизации.
 * В обычных тестах НЕ нужен — авторизация через storageState.
 */
export async function login(page: Page) {
  await page.goto('/recruiter/');
  await page.fill('input[type="email"]', TEST_USER.email);
  await page.fill('input[type="password"]', TEST_USER.password);
  await page.click('button:has-text("Войти")');
  await page.waitForURL(/\/recruiter\//, { timeout: 10_000 });
}
