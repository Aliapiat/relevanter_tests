import { test, expect } from '@playwright/test';

/**
 * TC-007: Полный жизненный цикл вакансии.
 * Один тест: валидация → создание (много полей) → редактирование → проверка → удаление.
 */

const TS = Date.now();
const VACANCY_TITLE = `E2E Тест Вакансия ${TS}`;
const VACANCY_DESCRIPTION = 'Описание тестовой вакансии для E2E теста';
const VACANCY_COMPANY = 'Тестовая компания для E2E автотестов';
const VACANCY_SALARY_FROM = '150000';
const VACANCY_SALARY_TO = '200000';
const VACANCY_SOCIAL = 'ДМС, фитнес, обучение за счёт компании';

const EDITED_TITLE = `${VACANCY_TITLE} (ред.)`;
const EDITED_SALARY_TO = '250000';
const EDITED_SOCIAL = 'ДМС, фитнес, обучение, компенсация питания';

let createdVacancyId: string | null = null;

test.describe('TC-007: Жизненный цикл вакансии', () => {

  // Safety net: удаляем вакансию даже если тест упал
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

  test('Валидация, создание, редактирование и удаление вакансии', async ({ page, request }) => {
    // Увеличиваем таймаут — тест длинный
    test.setTimeout(90_000);

    await page.goto('/recruiter/');

    // ==================== СОЗДАНИЕ ====================

    // Открываем форму
    await page.getByRole('button', { name: 'Новая вакансия' }).click();
    await page.waitForURL(/\/recruiter\/vacancy\/create/, { timeout: 10_000 });
    await expect(page.getByRole('heading', { name: 'Новая вакансия' })).toBeVisible();

    const createButton = page.getByRole('button', { name: 'Создать вакансию' });

    // --- Валидация: пустая форма → не создаётся ---
    await createButton.scrollIntoViewIfNeeded();
    await createButton.click();
    await expect(page).toHaveURL(/\/vacancy\/create/);

    // --- Заполняем все поля ---

    // Название
    const titleInput = page.getByRole('textbox', { name: 'Frontend Разработчик' });
    await titleInput.scrollIntoViewIfNeeded();
    await titleInput.click();
    await titleInput.fill(VACANCY_TITLE);

    // Описание (Quill editor)
    const descriptionEditor = page.locator('.ql-editor').first();
    await descriptionEditor.scrollIntoViewIfNeeded();
    await descriptionEditor.click();
    await descriptionEditor.fill(VACANCY_DESCRIPTION);

    // О компании (Quill editor)
    const companyEditor = page.locator('.ql-editor').nth(1);
    await companyEditor.scrollIntoViewIfNeeded();
    await companyEditor.click();
    await companyEditor.fill(VACANCY_COMPANY);

    // Соц. пакет
    const socialPackage = page.getByRole('textbox', { name: /социальный пакет/i });
    await socialPackage.scrollIntoViewIfNeeded();
    await socialPackage.click();
    await socialPackage.fill(VACANCY_SOCIAL);

    // Зарплата "от"
    const salaryFrom = page.getByRole('textbox', { name: 'от', exact: true }).first();
    await salaryFrom.scrollIntoViewIfNeeded();
    await salaryFrom.click();
    await salaryFrom.fill(VACANCY_SALARY_FROM);

    // Зарплата "до" (обязательное)
    const salaryTo = page.getByRole('textbox', { name: 'до *' });
    await salaryTo.scrollIntoViewIfNeeded();
    await salaryTo.click();
    await salaryTo.fill(VACANCY_SALARY_TO);

    // Опыт в должности — "От 1 года до 3 лет"
    const experience = page.getByRole('checkbox', { name: 'От 1 года до 3 лет' }).first();
    await experience.scrollIntoViewIfNeeded();
    await experience.check();

    // Образование — "Высшее"
    const education = page.getByRole('checkbox', { name: 'Высшее', exact: true });
    await education.scrollIntoViewIfNeeded();
    await education.check();

    // Формат работы — "Удаленка"
    const formatSelect = page.locator('select').filter({ has: page.locator('option', { hasText: 'Удаленка' }) });
    await formatSelect.scrollIntoViewIfNeeded();
    await formatSelect.selectOption('Удаленка');

    // График — "Полный день" (опции зависят от формата; при "Удаленка" доступны: Полный день, Гибкий график и т.д.)
    const scheduleSelect = page.locator('select').filter({ has: page.locator('option', { hasText: 'Полный день' }) });
    await scheduleSelect.scrollIntoViewIfNeeded();
    await scheduleSelect.selectOption('Полный день');

    // Рабочие часы — "8 часов"
    const hoursSelect = page.locator('select').filter({ has: page.locator('option', { hasText: '8 часов' }) });
    await hoursSelect.scrollIntoViewIfNeeded();
    await hoursSelect.selectOption('8 часов');

    // Оформление — "По ТК РФ"
    const employment = page.getByRole('checkbox', { name: 'По ТК РФ' });
    await employment.scrollIntoViewIfNeeded();
    await employment.check();

    // --- Создаём ---
    await createButton.scrollIntoViewIfNeeded();
    await createButton.click();
    await page.waitForURL(/\/recruiter\/vacancy\/(\d+)/, { timeout: 15_000 });

    // Сохраняем ID
    const match = page.url().match(/\/vacancy\/(\d+)/);
    if (match) createdVacancyId = match[1];

    // Проверяем на странице просмотра — название в заголовке
    await expect(page.getByText(VACANCY_TITLE).first()).toBeVisible({ timeout: 10_000 });

    // ==================== РЕДАКТИРОВАНИЕ ====================

    await page.goto(`/recruiter/vacancy/edit-data/${createdVacancyId}`);
    await expect(page.getByRole('button', { name: 'Сохранить', exact: true })).toBeVisible({ timeout: 10_000 });

    // Меняем название
    const editTitle = page.getByRole('textbox', { name: 'Frontend Разработчик' });
    await editTitle.scrollIntoViewIfNeeded();
    await editTitle.click();
    await editTitle.clear();
    await editTitle.fill(EDITED_TITLE);

    // Меняем зарплату "до"
    const editSalaryTo = page.getByRole('textbox', { name: 'до *' });
    await editSalaryTo.scrollIntoViewIfNeeded();
    await editSalaryTo.click();
    await editSalaryTo.clear();
    await editSalaryTo.fill(EDITED_SALARY_TO);

    // Меняем соц. пакет
    const editSocial = page.getByRole('textbox', { name: /социальный пакет/i });
    await editSocial.scrollIntoViewIfNeeded();
    await editSocial.click();
    await editSocial.clear();
    await editSocial.fill(EDITED_SOCIAL);

    // Сохраняем
    const saveButton = page.getByRole('button', { name: 'Сохранить', exact: true });
    await saveButton.scrollIntoViewIfNeeded();
    await saveButton.click();
    await expect(page).not.toHaveURL(/\/edit-data\//, { timeout: 10_000 });

    // Проверяем изменения на странице вакансии
    await page.goto(`/recruiter/vacancy/${createdVacancyId}`);
    // Попробуем дождаться загрузки, при ошибке — перезагрузим
    try {
      await expect(page.getByText(EDITED_TITLE).first()).toBeVisible({ timeout: 5_000 });
    } catch {
      await page.reload();
      await expect(page.getByText(EDITED_TITLE).first()).toBeVisible({ timeout: 10_000 });
    }

    // ==================== УДАЛЕНИЕ ====================

    const loginResp = await request.post('/api/v1/auth/login', {
      data: { email: 'admin@example.com', password: 'admin' },
    });
    expect(loginResp.ok()).toBeTruthy();
    const { token } = await loginResp.json();

    // Попытка удаления с ретраем
    let deleteResp = await request.delete(`/api/v1/positions/${createdVacancyId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!deleteResp.ok()) {
      // Повторная попытка через секунду
      await page.waitForTimeout(1_000);
      deleteResp = await request.delete(`/api/v1/positions/${createdVacancyId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    }
    expect(deleteResp.ok()).toBeTruthy();
    createdVacancyId = null;
  });
});
