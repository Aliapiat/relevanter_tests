import { test, expect } from '@playwright/test';

/**
 * TC-006: Авторизация — проверка пустых полей, неверного пароля и успешного входа.
 * storageState сброшен — тест начинается неавторизованным.
 */

test.use({ storageState: { cookies: [], origins: [] } });

test.describe('TC-006: Авторизация', () => {

  test('Проверка формы логина: пустые поля, неверный пароль, успешный вход', async ({ page }) => {
    await page.goto('/recruiter/');

    const emailInput = page.getByRole('textbox', { name: 'Email' });
    const passwordInput = page.getByRole('textbox', { name: 'Пароль' });
    const loginButton = page.getByRole('button', { name: 'Войти' });

    // Проверяем что форма логина отображается
    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(loginButton).toBeVisible();

    // --- Шаг 1: Пустые поля → "Войти" → остаёмся на логине ---
    await loginButton.click();
    await expect(emailInput).toBeVisible();

    // --- Шаг 2: Неверный пароль → "Войти" → остаёмся на логине ---
    await emailInput.fill('admin@example.com');
    await passwordInput.fill('wrong_password');
    await loginButton.click();
    // Ждём реакцию сервера, проверяем что не ушли с логина
    await expect(emailInput).toBeVisible({ timeout: 5_000 });

    // --- Шаг 3: Верные данные → "Войти" → успешный вход ---
    await emailInput.clear();
    await emailInput.fill('admin@example.com');
    await passwordInput.clear();
    await passwordInput.fill('admin');
    await loginButton.click();

    // Редирект на приложение
    await expect(page).toHaveURL(/\/recruiter\//, { timeout: 10_000 });
    // Форма логина исчезла
    await expect(emailInput).not.toBeVisible();
  });
});
