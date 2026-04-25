import { test, expect } from '@playwright/test';

/**
 * TC-013: Сброс городов (без гео) при редактировании вакансии.
 *
 * Проверяет что:
 * 1. Можно открыть модалку географии и выбрать город
 * 2. Можно сбросить выбор города (кнопка "Сбросить")
 * 3. Кнопка "Сохранить" в модалке доступна после сброса
 * 4. Вакансия сохраняется без городов (без гео)
 */

const TS = Date.now();
const VACANCY_TITLE = `E2E Без гео ${TS}`;
const VACANCY_DESCRIPTION = 'Тестовая вакансия для проверки сброса городов';
const VACANCY_COMPANY = 'Тестовая компания';

let createdVacancyId: string | null = null;

test.describe('TC-013: Сброс городов (без гео)', () => {

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

  test('Создать вакансию с городом, затем сбросить город на "без гео"', async ({ page, request }) => {
    test.setTimeout(120_000);

    // === Шаг 1: Создаём вакансию через API ===
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
        cities: ['1'],  // Москва
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

    // === Шаг 3: Прокручиваем до секции "География и профиль" ===
    const geoHeading = page.getByRole('heading', { name: 'География и профиль' });
    await geoHeading.scrollIntoViewIfNeeded();
    await expect(geoHeading).toBeVisible();

    // === Шаг 4: Открываем модалку географии ===
    // Кнопка выбора городов — содержит текст города или placeholder
    const geoButton = page.getByRole('button', { name: /Москва|Выберите город/i }).first();
    await geoButton.scrollIntoViewIfNeeded();
    await geoButton.click();

    // Ждём появления модалки (заголовок "География" exact, не "География и профиль")
    const modalTitle = page.getByRole('heading', { name: 'География', exact: true });
    await expect(modalTitle).toBeVisible({ timeout: 10_000 });

    // === Шаг 5: Нажимаем "Сбросить" ===
    const resetButton = page.getByRole('button', { name: 'Сбросить' });
    await expect(resetButton).toBeVisible();
    await resetButton.click();

    // === Шаг 6: Проверяем что кнопка "Сохранить" в модалке НЕ заблокирована ===
    const modalSaveButton = page.locator('.modal-container button', { hasText: 'Сохранить' });
    await expect(modalSaveButton).toBeVisible();
    await expect(modalSaveButton).toBeEnabled();

    // === Шаг 7: Нажимаем "Сохранить" в модалке ===
    await modalSaveButton.click();

    // Модалка должна закрыться
    await expect(modalTitle).not.toBeVisible({ timeout: 5_000 });

    // Кнопка географии должна показывать "Выберите города..."
    await expect(page.getByText('Выберите города...')).toBeVisible();

    // === Шаг 8: Сохраняем вакансию ===
    const saveButton = page.getByRole('button', { name: 'Сохранить', exact: true });
    await saveButton.scrollIntoViewIfNeeded();
    await saveButton.click();

    // Ждём перехода (сохранение успешно)
    await expect(page).not.toHaveURL(/\/edit-data\//, { timeout: 15_000 });

    // === Шаг 9: Проверяем что города сброшены через API ===
    const getResp = await request.get(`/api/v1/positions/${createdVacancyId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(getResp.ok()).toBeTruthy();
    const updatedVacancy = await getResp.json();
    expect(updatedVacancy.cities || []).toHaveLength(0);
  });
});
