import { test, expect } from '@playwright/test';

/**
 * TC-014: Сброс специализации при редактировании вакансии.
 *
 * Проверяет что:
 * 1. Можно открыть модалку специализации и выбрать значение
 * 2. Можно сбросить выбор (кнопка "Сбросить")
 * 3. Кнопка "Сохранить" в модалке доступна после сброса
 * 4. Вакансия сохраняется без специализации
 */

const TS = Date.now();
const VACANCY_TITLE = `E2E Без спец ${TS}`;
const VACANCY_DESCRIPTION = 'Тестовая вакансия для проверки сброса специализации';
const VACANCY_COMPANY = 'Тестовая компания';

let createdVacancyId: string | null = null;

test.describe('TC-014: Сброс специализации', () => {

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
    test.setTimeout(120_000);

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

    // === Шаг 3: Открываем модалку специализации ===
    // Находим label "Специализация" и кнопку после неё
    const specLabel = page.getByText('Специализация', { exact: true }).first();
    await specLabel.scrollIntoViewIfNeeded();
    const specButton = specLabel.locator('..').getByRole('button').first();
    await specButton.click();

    // Ждём появления модалки (заголовок "Специализации")
    const modal = page.locator('.modal-container');
    await expect(modal).toBeVisible({ timeout: 10_000 });

    // === Шаг 4: Нажимаем "Сбросить" ===
    const resetButton = page.getByRole('button', { name: 'Сбросить' });
    await expect(resetButton).toBeVisible();
    await resetButton.click();

    // === Шаг 5: Проверяем что кнопка "Сохранить" в модалке НЕ заблокирована ===
    const modalSaveButton = page.locator('.modal-container button', { hasText: 'Сохранить' });
    await expect(modalSaveButton).toBeVisible();
    await expect(modalSaveButton).toBeEnabled();

    // === Шаг 6: Нажимаем "Сохранить" в модалке ===
    await modalSaveButton.click();

    // Модалка должна закрыться
    await expect(modal).not.toBeVisible({ timeout: 5_000 });

    // Кнопка специализации должна показывать placeholder
    await expect(page.getByText('Выберите специализацию...')).toBeVisible();

    // === Шаг 7: Сохраняем вакансию ===
    const saveButton = page.getByRole('button', { name: 'Сохранить', exact: true });
    await saveButton.scrollIntoViewIfNeeded();
    await saveButton.click();

    // Ждём перехода (сохранение успешно)
    await expect(page).not.toHaveURL(/\/edit-data\//, { timeout: 15_000 });

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
