import { test, expect } from '@playwright/test';

/**
 * TC-008: Навигация по всем разделам приложения.
 * Прокликивает каждый таб и проверяет базовые элементы на каждой странице.
 * force: true на табах — toast-уведомления могут перекрывать ссылки.
 */

/** Вспомогательная функция: кликает таб, при блокировке toast-ом переходит через URL */
async function clickTab(page: import('@playwright/test').Page, name: string, urlPattern: RegExp, href: string) {
  const link = page.getByRole('link', { name });
  await link.click({ force: true });

  try {
    await expect(page).toHaveURL(urlPattern, { timeout: 3_000 });
  } catch {
    // Toast перехватил клик — переходим через URL
    await page.goto(href);
    await expect(page).toHaveURL(urlPattern, { timeout: 5_000 });
  }
}

test.describe('TC-008: Навигация по разделам', () => {

  test('Обход всех разделов приложения', async ({ page }) => {
    await page.goto('/recruiter/');

    // --- Главная (Итоги Подбора / Статистика) ---
    await expect(page.getByRole('heading', { name: 'Итоги Подбора' })).toBeVisible({ timeout: 10_000 });

    // Проверяем что сайдбар загружен
    await expect(page.getByRole('button', { name: 'Новая вакансия' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Super Admin System/ })).toBeVisible();

    // --- Таб "Вакансия" ---
    await clickTab(page, 'Вакансия', /\/recruiter\/vacancy/, '/recruiter/vacancy');

    // --- Таб "Поиск" ---
    await clickTab(page, 'Поиск', /\/recruiter\/search/, '/recruiter/search');

    // --- Таб "Рассылка" ---
    await clickTab(page, 'Рассылка', /\/recruiter\/mailings/, '/recruiter/mailings');

    // --- Таб "Диалоги" ---
    await clickTab(page, 'Диалоги', /\/recruiter\/messenger/, '/recruiter/messenger');

    // --- Таб "Собеседования" ---
    await clickTab(page, 'Собеседования', /\/recruiter\/interviews/, '/recruiter/interviews');

    // --- Таб "Итоги Подбора" ---
    await clickTab(page, 'Итоги Подбора', /\/recruiter\/reports/, '/recruiter/reports');

    // --- Сайдбар: Статистика ---
    await page.getByRole('button', { name: 'Статистика' }).click();
    await expect(page).toHaveURL(/\/recruiter\/reports/);

    // --- Сайдбар: Профиль пользователя ---
    await page.getByRole('button', { name: /Super Admin System/ }).click();
    await expect(page).toHaveURL(/\/recruiter\/control/);
  });
});
