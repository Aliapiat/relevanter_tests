import { test, expect, Page } from '@playwright/test';

/**
 * TC-652 (TASKNEIROKLYUCH-652): Порядок валидации перед публикацией на HH.ru.
 *
 * ⚠️ ВАЖНО: Тесты НЕ выполняют реальную публикацию на HH.ru!
 * Запросы к /relevanter/api/hh/vacancies/export перехватываются через page.route()
 * и в случае ошибки теста — отклоняются.
 *
 * Баг: при пустых «Специализация» и/или «География» сначала открывался диалог
 * подтверждения «Вы хотите продолжить?», и только после клика «Да» бэк отвечал 400
 * с тостами «Укажите регион или город…» / «Выберите специализацию…».
 * Пользователь подтверждал заведомо невыполнимое действие.
 *
 * Ожидание: пре-валидация на фронте (handleExportClick) показывает тосты СРАЗУ,
 * без открытия диалога подтверждения, без отправки запроса на бэк.
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
  // Описание ≥ 150 символов plain text, чтобы пре-валидация описания прошла.
  const longDescription =
    '<p>' +
    'Описание вакансии с достаточной длиной для прохождения валидации HH.ru. '.repeat(5) +
    '</p>';
  const resp = await request.post('/api/v1/positions', {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      title: `E2E TC-652 ${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      description: longDescription,
      companyDescription: '<p>Тестовая компания для TC-652</p>',
      salaryTo: 100000,
      // По умолчанию пустые — для тестирования пре-валидации
      specialization: overrides.specialization ?? '',
      cities: overrides.cities ?? [],
      topics: ['e2e-tc-652'],
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

/**
 * Перехватываем запрос на публикацию HH. Если фронт его всё-таки отправит при пустых
 * полях — счётчик увеличится, и тест провалится. Реальный запрос на бэк не уходит.
 */
function installHHExportInterceptor(page: Page): { count: () => number } {
  let calls = 0;
  page.route('**/relevanter/api/hh/vacancies/export', async (route) => {
    calls += 1;
    await route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ success: false, error: 'mocked', validationErrors: [] }),
    });
  });
  return { count: () => calls };
}

// =============================================================================
// TC-001: Пустая специализация → тост сразу, без диалога подтверждения
// =============================================================================

test.describe('TC-652: пустая специализация → тост до подтверждения', () => {
  let vacancyId: number | null = null;

  test.beforeAll(async ({ request }) => {
    // Спец-я пустая, город заполнен (Москва, id=1)
    vacancyId = await createVacancy(request, { specialization: '', cities: ['1'] });
  });

  test.afterAll(async ({ request }) => {
    if (vacancyId) await deleteVacancy(request, vacancyId);
  });

  test('пустая «Специализация» → тост, без диалога подтверждения, без запроса на бэк', async ({
    page,
  }) => {
    test.setTimeout(60_000);
    const interceptor = installHHExportInterceptor(page);

    const exportBtn = await openEditMode(page, vacancyId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Тост с пре-валидацией спец-и
    await expect(
      page.getByText(/Выберите специализацию для публикации на HeadHunter/),
    ).toBeVisible({ timeout: 5_000 });

    // Диалог подтверждения НЕ открывается
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();

    // Запрос на бэк НЕ ушёл
    expect(interceptor.count()).toBe(0);
  });
});

// =============================================================================
// TC-002: Пустая география → тост сразу, без диалога подтверждения
// =============================================================================

test.describe('TC-652: пустая география → тост до подтверждения', () => {
  let vacancyId: number | null = null;

  test.beforeAll(async ({ request }) => {
    // Спец-я заполнена (124 — листовая), города пустые
    vacancyId = await createVacancy(request, { specialization: '124', cities: [] });
  });

  test.afterAll(async ({ request }) => {
    if (vacancyId) await deleteVacancy(request, vacancyId);
  });

  test('пустая «География» → тост, без диалога подтверждения, без запроса на бэк', async ({
    page,
  }) => {
    test.setTimeout(60_000);
    const interceptor = installHHExportInterceptor(page);

    const exportBtn = await openEditMode(page, vacancyId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Тост с пре-валидацией географии
    await expect(
      page.getByText(/Укажите регион или город для публикации на HeadHunter/),
    ).toBeVisible({ timeout: 5_000 });

    // Диалог подтверждения НЕ открывается
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();

    // Запрос на бэк НЕ ушёл
    expect(interceptor.count()).toBe(0);
  });
});

// =============================================================================
// TC-003: Оба поля пусты → оба сообщения, без диалога подтверждения
// =============================================================================

test.describe('TC-652: оба поля пусты → оба сообщения вместе', () => {
  let vacancyId: number | null = null;

  test.beforeAll(async ({ request }) => {
    vacancyId = await createVacancy(request, { specialization: '', cities: [] });
  });

  test.afterAll(async ({ request }) => {
    if (vacancyId) await deleteVacancy(request, vacancyId);
  });

  test('оба пусты → оба тоста, без диалога подтверждения, без запроса на бэк', async ({
    page,
  }) => {
    test.setTimeout(60_000);
    const interceptor = installHHExportInterceptor(page);

    const exportBtn = await openEditMode(page, vacancyId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Оба сообщения — могут быть в одном тосте через '\n' или в двух разных
    await expect(
      page.getByText(/Выберите специализацию для публикации на HeadHunter/),
    ).toBeVisible({ timeout: 5_000 });
    await expect(
      page.getByText(/Укажите регион или город для публикации на HeadHunter/),
    ).toBeVisible();

    // Диалог подтверждения НЕ открывается
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();

    // Запрос на бэк НЕ ушёл
    expect(interceptor.count()).toBe(0);
  });
});
