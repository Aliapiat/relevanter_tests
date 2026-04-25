import { test, expect, Page } from '@playwright/test';

/**
 * TC-010: Регрессионные тесты экспорта на HH.ru.
 *
 * ⚠️ ВАЖНО: Тесты НЕ выполняют реальную публикацию на HH.ru!
 * Каждая публикация на HH тратит платные кредиты работодателя.
 * Все тесты останавливаются на диалоге подтверждения и нажимают "Нет".
 *
 * Баг 1: При 1 листовой специализации модалка всё равно открывалась.
 *   Ожидание: если 1 валидное листовое значение → модалка НЕ открывается.
 *
 * Баг 2: При географии "Россия" (cities: ["113"]) модалка НЕ открывалась.
 *   Ожидание: страна/регион → модалка ДОЛЖНА открыться.
 *
 * Баг 3: Нельзя сохранить вакансию без специализации.
 *   Ожидание: сохранение работает без специализации.
 */

async function getAuthToken(request: any): Promise<string> {
  const resp = await request.post('/api/v1/auth/login', {
    data: { email: 'admin@example.com', password: 'admin' },
  });
  const { token } = await resp.json();
  return token;
}

async function createVacancy(
  request: any,
  overrides: { specialization?: string; cities?: string[] } = {},
): Promise<number> {
  const token = await getAuthToken(request);
  const resp = await request.post('/api/v1/positions', {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      title: `E2E Regression ${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      description: '<p>Регрессионный тест экспорта вакансий на HH.ru с проверкой модалок специализации и городов. Этот тест проверяет корректную работу валидации при экспорте.</p>',
      companyDescription: '<p>Тестовая компания для автоматизированного тестирования функционала экспорта вакансий. Проверяем корректную обработку листовых и нелистовых значений справочников.</p>',
      salaryTo: 100000,
      specialization: overrides.specialization ?? '',
      cities: overrides.cities ?? [],
      topics: ['e2e-regression'],
      answerTime: 60,
      level: 'MIDDLE',
      status: 'ACTIVE',
      questionsCount: 5,
    },
  });
  expect(resp.ok()).toBeTruthy();
  return (await resp.json()).id;
}

async function deleteVacancy(request: any, id: number) {
  try {
    const token = await getAuthToken(request);
    await request.delete(`/api/v1/positions/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {}
}

async function openEditMode(page: Page, vacancyId: number) {
  await page.goto(`/recruiter/vacancy/${vacancyId}`);
  await expect(page.getByRole('heading', { name: 'Вакансия' })).toBeVisible({ timeout: 10_000 });

  const editBtn = page.getByRole('button', { name: 'Редактировать' });
  await editBtn.scrollIntoViewIfNeeded();
  await editBtn.click();

  const exportBtn = page.getByRole('button', { name: /на HH\.ru/ });
  await expect(exportBtn).toBeVisible({ timeout: 10_000 });
  return exportBtn;
}

// =============================================================================
// Баг 1: 1 листовая специализация → модалка НЕ должна открываться
// =============================================================================

test.describe('TC-010: Баг — модалка спец при 1 листовом значении', () => {
  let vacancyId: number | null = null;

  // Специализация "124" = Тестировщик (листовой элемент под "Информационные технологии")
  test.beforeAll(async ({ request }) => {
    vacancyId = await createVacancy(request, { specialization: '124', cities: ['1'] });
  });

  test.afterAll(async ({ request }) => {
    if (vacancyId) await deleteVacancy(request, vacancyId);
  });

  test('1 листовая специализация → модалка спец НЕ открывается, сразу подтверждение', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, vacancyId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Модалка специализации НЕ должна открываться (1 листовое значение)
    await expect(page.getByRole('heading', { name: 'Выберите специализацию для публикации' })).not.toBeVisible();

    // Город тоже листовой и один → модалка города тоже не открывается
    await expect(page.getByRole('heading', { name: 'Выберите город публикации' })).not.toBeVisible();

    // Сразу подтверждение → "Нет"
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).toBeVisible({ timeout: 5_000 });
    await page.getByRole('button', { name: 'Нет' }).click();
  });

  test('После выбора спец через модалку и перезагрузки — экспорт снова пропускает модалку', async ({ page }) => {
    test.setTimeout(90_000);

    // Шаг 1: Открываем вакансию, меняем специализацию через модалку (создаёт path key в кеше)
    await page.goto(`/recruiter/vacancy/${vacancyId}`);
    await expect(page.getByRole('heading', { name: 'Вакансия' })).toBeVisible({ timeout: 10_000 });

    const editBtn = page.getByRole('button', { name: 'Редактировать' });
    await editBtn.scrollIntoViewIfNeeded();
    await editBtn.click();

    // Ждём полной загрузки формы редактирования
    await expect(page.getByRole('button', { name: 'Сохранить', exact: true })).toBeVisible({ timeout: 10_000 });

    // Открываем модалку специализации (обычную, не экспортную) — находим кнопку
    const specSection = page.getByText('Специализация').first();
    await specSection.scrollIntoViewIfNeeded();

    // Ищем кнопку выбора специализации рядом с полем
    const specButton = page.getByRole('button', { name: /Выбрать специализаци/i });
    if (await specButton.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await specButton.click();

      // Выбираем "Программист, разработчик" (листовой, ID=96)
      await page.getByRole('button', { name: 'Сбросить' }).click();
      const itCheckbox = page.getByRole('checkbox', { name: 'Информационные технологии' });
      await itCheckbox.scrollIntoViewIfNeeded();
      await itCheckbox.locator('xpath=../../button').click();

      const devCheckbox = page.getByRole('checkbox', { name: 'Программист, разработчик' });
      await expect(devCheckbox).toBeVisible({ timeout: 5_000 });
      await devCheckbox.click();

      // Сохраняем модалку
      const actions = page.getByRole('button', { name: 'Отменить' }).locator('..');
      await actions.getByRole('button', { name: 'Сохранить' }).click();

      // Сохраняем вакансию (чтобы path key попал в кеш)
      const saveBtn = page.getByRole('button', { name: 'Сохранить', exact: true });
      await saveBtn.scrollIntoViewIfNeeded();
      await saveBtn.click();
      await expect(page.getByText('Вакансия успешно обновлена')).toBeVisible({ timeout: 10_000 });
    }

    // Шаг 2: Перезагружаем страницу (path key в localStorage)
    await page.goto(`/recruiter/vacancy/${vacancyId}`);
    await expect(page.getByRole('heading', { name: 'Вакансия' })).toBeVisible({ timeout: 10_000 });

    const editBtn2 = page.getByRole('button', { name: 'Редактировать' });
    await editBtn2.scrollIntoViewIfNeeded();
    await editBtn2.click();

    const exportBtn = page.getByRole('button', { name: /на HH\.ru/ });
    await expect(exportBtn).toBeVisible({ timeout: 10_000 });

    // Экспорт: модалка спец НЕ должна открываться (1 листовое, даже с path key в кеше)
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    await expect(page.getByRole('heading', { name: 'Выберите специализацию для публикации' })).not.toBeVisible();

    // Подтверждение → "Нет"
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).toBeVisible({ timeout: 5_000 });
    await page.getByRole('button', { name: 'Нет' }).click();
  });
});

// =============================================================================
// Баг 2: География "Россия" → модалка города ДОЛЖНА открываться
// =============================================================================

test.describe('TC-010: Баг — география Россия, модалка не открывалась', () => {
  let vacancyId: number | null = null;

  // cities: ["113"] — Россия (страна, не листовой город)
  test.beforeAll(async ({ request }) => {
    vacancyId = await createVacancy(request, { specialization: '124', cities: ['113'] });
  });

  test.afterAll(async ({ request }) => {
    if (vacancyId) await deleteVacancy(request, vacancyId);
  });

  test('География "Россия" (113) → модалка города ДОЛЖНА открыться', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, vacancyId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Специализация — 1 лист → модалка спец НЕ открывается
    await expect(page.getByRole('heading', { name: 'Выберите специализацию для публикации' })).not.toBeVisible();

    // Город — "Россия" (не листовой) → модалка города ДОЛЖНА открыться
    await expect(page.getByRole('heading', { name: 'Выберите город публикации' })).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('Каждый город — это отдельная публикация')).toBeVisible();

    // Отменяем
    await page.getByRole('button', { name: 'Отменить' }).click();
    await expect(page.getByRole('heading', { name: 'Выберите город публикации' })).not.toBeVisible();
  });
});

// =============================================================================
// Баг 3: Сохранение вакансии без специализации
// =============================================================================

test.describe('TC-010: Баг — сохранение без специализации', () => {
  let vacancyId: number | null = null;

  test.beforeAll(async ({ request }) => {
    vacancyId = await createVacancy(request, { specialization: '', cities: [] });
  });

  test.afterAll(async ({ request }) => {
    if (vacancyId) await deleteVacancy(request, vacancyId);
  });

  test('Вакансия без специализации сохраняется успешно', async ({ page }) => {
    test.setTimeout(60_000);

    await page.goto(`/recruiter/vacancy/${vacancyId}`);
    await expect(page.getByRole('heading', { name: 'Вакансия' })).toBeVisible({ timeout: 10_000 });

    const editBtn = page.getByRole('button', { name: 'Редактировать' });
    await editBtn.scrollIntoViewIfNeeded();
    await editBtn.click();

    const saveBtn = page.getByRole('button', { name: 'Сохранить', exact: true });
    await expect(saveBtn).toBeVisible({ timeout: 10_000 });
    await expect(saveBtn).toBeEnabled();

    await saveBtn.scrollIntoViewIfNeeded();
    await saveBtn.click();

    // НЕ должно быть ошибки валидации
    await expect(page.getByText('Пожалуйста, заполните все обязательные поля')).not.toBeVisible({ timeout: 3_000 });

    // Должен появиться тост успеха
    await expect(page.getByText('Вакансия успешно обновлена')).toBeVisible({ timeout: 10_000 });
  });
});
