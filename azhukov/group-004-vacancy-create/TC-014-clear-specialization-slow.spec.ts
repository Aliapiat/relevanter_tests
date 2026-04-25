import { test, expect, Page, Locator } from '@playwright/test';

/**
 * TC-014-slow: Сброс специализации при редактировании вакансии (замедленный).
 *
 * Тот же сценарий что TC-014, но с паузами и фокусом на элементах для наглядности.
 */

const TS = Date.now();
const VACANCY_TITLE = `E2E Без спец slow ${TS}`;
const VACANCY_DESCRIPTION = 'Тестовая вакансия для проверки сброса специализации (slow)';
const VACANCY_COMPANY = 'Тестовая компания';
const DELAY = 1_000;

/** Подсветить элемент рамкой, прокрутить к нему и подождать */
async function focus(page: Page, locator: Locator) {
  await locator.scrollIntoViewIfNeeded();
  await locator.evaluate((el) => {
    el.style.outline = '3px solid red';
    el.style.outlineOffset = '2px';
  });
  await page.waitForTimeout(DELAY);
  await locator.evaluate((el) => {
    el.style.outline = '';
    el.style.outlineOffset = '';
  });
}

let createdVacancyId: string | null = null;

test.describe('TC-014-slow: Сброс специализации (замедленный)', () => {

  test.afterAll(async ({ request }) => {
    if (!createdVacancyId) return;
    try {
      const loginResp = await request.post('/api/v1/auth/login', {
        data: { email: 'admin@example.com', password: 'admin' },
      });
      const { token } = await loginResp.json();
      await request.delete(`/api/v1/positions/${createdVacancyId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Уже удалена
    }
  });

  test('Создать вакансию со специализацией, затем сбросить', async ({ page, request }) => {
    test.setTimeout(180_000);

    // === Шаг 1: Создаём вакансию через API со специализацией ===
    const loginResp = await request.post('/api/v1/auth/login', {
      data: { email: 'admin@example.com', password: 'admin' },
    });
    const { token } = await loginResp.json();

    const createResp = await request.post('/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        title: VACANCY_TITLE,
        description: VACANCY_DESCRIPTION,
        companyDescription: VACANCY_COMPANY,
        salaryTo: 200000,
        specialization: '1',
        level: 'JUNIOR',
        status: 'ACTIVE',
        answerTime: 180,
        questionsCount: 5,
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const vacancy = await createResp.json();
    createdVacancyId = String(vacancy.id);

    // === Шаг 2: Открываем редактирование вакансии ===
    await page.goto(`/recruiter/vacancy/edit-data/${createdVacancyId}`);
    await expect(page.getByRole('button', { name: 'Сохранить', exact: true })).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(DELAY);

    // === Шаг 3: Открываем модалку специализации ===
    const specLabel = page.getByText('Специализация', { exact: true }).first();
    const specButton = specLabel.locator('..').getByRole('button').first();
    await focus(page, specButton);
    await specButton.click();

    const modal = page.locator('.modal-container');
    await expect(modal).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(DELAY);

    // === Шаг 4: Нажимаем "Сбросить" ===
    const resetButton = page.getByRole('button', { name: 'Сбросить' });
    await expect(resetButton).toBeVisible();
    await focus(page, resetButton);
    await resetButton.click();
    await page.waitForTimeout(DELAY);

    // === Шаг 5: Проверяем что кнопка "Сохранить" в модалке НЕ заблокирована ===
    const modalSaveButton = page.locator('.modal-container button', { hasText: 'Сохранить' });
    await expect(modalSaveButton).toBeVisible();
    await expect(modalSaveButton).toBeEnabled();
    await focus(page, modalSaveButton);

    // === Шаг 6: Нажимаем "Сохранить" в модалке ===
    await modalSaveButton.click();

    // Модалка должна закрыться
    await expect(modal).not.toBeVisible({ timeout: 5_000 });
    await page.waitForTimeout(DELAY);

    // Кнопка специализации должна показывать placeholder
    const placeholder = page.getByText('Выберите специализацию...');
    await expect(placeholder).toBeVisible();
    await focus(page, placeholder);

    // === Шаг 7: Сохраняем вакансию ===
    const saveButton = page.getByRole('button', { name: 'Сохранить', exact: true });
    await focus(page, saveButton);
    await saveButton.click();

    // Ждём перехода (сохранение успешно)
    await expect(page).not.toHaveURL(/\/edit-data\//, { timeout: 15_000 });
    await page.waitForTimeout(DELAY);

    // === Шаг 8: Проверяем что специализация сброшена через API ===
    const getResp = await request.get(`/api/v1/positions/${createdVacancyId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(getResp.ok()).toBeTruthy();
    const updatedVacancy = await getResp.json();
    const spec = updatedVacancy.specialization || '';
    expect(spec).toBe('');
  });
});
