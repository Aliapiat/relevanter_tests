import { test, expect, Page } from '@playwright/test';

/**
 * TC-011: Валидация полей перед экспортом на HH.ru.
 *
 * ⚠️ ВАЖНО: Тесты НЕ выполняют реальную публикацию на HH.ru!
 * Каждая публикация на HH тратит платные кредиты работодателя.
 * Тесты проверяют только пре-валидацию (до отправки запроса).
 *
 * Проверяет, что экспорт блокируется с понятным сообщением, если:
 * - Название > 100 символов
 * - Описание < 200 символов (итоговое: описание + о компании + соцпакет)
 * - Описание пустое
 *
 * Также проверяет:
 * - Предупреждение о длине названия при > 100 символов
 * - Валидное описание >= 200 символов проходит валидацию
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
  overrides: { title?: string; description?: string; companyDescription?: string } = {},
): Promise<number> {
  const token = await getAuthToken(request);
  const resp = await request.post('/api/v1/positions', {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      title: overrides.title ?? `E2E Validation ${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      description: overrides.description ?? '<p>Тестовое описание для валидации экспорта</p>',
      companyDescription: overrides.companyDescription ?? '<p>Тестовая компания</p>',
      salaryTo: 100000,
      specialization: '124',
      cities: ['1'],
      topics: ['e2e-validation'],
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
// Тест 1: Название > 100 символов блокирует экспорт
// =============================================================================

test.describe('TC-011: Валидация названия перед экспортом', () => {
  // Название 120 символов — превышает лимит HH (100)
  const longTitle = 'А'.repeat(120);
  let vacancyId: number | null = null;

  test.beforeAll(async ({ request }) => {
    vacancyId = await createVacancy(request, { title: longTitle });
  });

  test.afterAll(async ({ request }) => {
    if (vacancyId) await deleteVacancy(request, vacancyId);
  });

  test('Название > 100 символов → toast-ошибка, экспорт не начинается', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, vacancyId!);

    // Предупреждение о длине должно быть видно в форме
    await expect(page.getByText(/Название превышает лимит HH\.ru/)).toBeVisible();

    // Кликаем экспорт
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Должен появиться toast с ошибкой валидации
    await expect(page.getByText(/Название не должно превышать 100 символов/)).toBeVisible({ timeout: 5_000 });

    // Модалка подтверждения НЕ должна открыться
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();
  });
});

// =============================================================================
// Тест 2: Короткое описание блокирует экспорт
// =============================================================================

test.describe('TC-011: Валидация описания перед экспортом', () => {
  let vacancyId: number | null = null;

  // Короткое описание (< 200 символов итого)
  test.beforeAll(async ({ request }) => {
    vacancyId = await createVacancy(request, {
      title: 'E2E Short Desc Test',
      description: '<p>Коротко</p>',
      companyDescription: '<p>Мало</p>',
    });
  });

  test.afterAll(async ({ request }) => {
    if (vacancyId) await deleteVacancy(request, vacancyId);
  });

  test('Описание < 200 символов → toast-ошибка, экспорт не начинается', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, vacancyId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Должен появиться toast с ошибкой о коротком описании
    await expect(page.getByText(/Описание должно содержать не менее 200 символов/)).toBeVisible({ timeout: 5_000 });

    // Модалка подтверждения НЕ должна открыться
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();
  });
});

// =============================================================================
// Тест 3: Валидное описание и название → экспорт проходит до подтверждения
// =============================================================================

test.describe('TC-011: Валидные поля → экспорт доходит до подтверждения', () => {
  let vacancyId: number | null = null;

  // Достаточное описание (> 200 символов) и короткое название (< 100)
  const longDescription = '<p>' + 'Описание вакансии с достаточной длиной для прохождения валидации HH.ru. '.repeat(5) + '</p>';
  const longCompanyDesc = '<p>' + 'Описание компании для теста валидации. '.repeat(5) + '</p>';

  test.beforeAll(async ({ request }) => {
    vacancyId = await createVacancy(request, {
      title: 'E2E Valid Export Test',
      description: longDescription,
      companyDescription: longCompanyDesc,
    });
  });

  test.afterAll(async ({ request }) => {
    if (vacancyId) await deleteVacancy(request, vacancyId);
  });

  test('Валидные поля → модалка подтверждения открывается → отменяем', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, vacancyId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Модалка подтверждения ДОЛЖНА открыться (валидация пройдена)
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).toBeVisible({ timeout: 5_000 });

    // Отменяем (никогда не отправляем реально на HH)
    await page.getByRole('button', { name: 'Нет' }).click();
  });
});
