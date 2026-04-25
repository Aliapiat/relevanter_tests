import { test, expect } from '@playwright/test';

/**
 * TC-012: Валидация API при создании/сохранении вакансии.
 *
 * ⚠️ ВАЖНО: Тесты проверяют ТОЛЬКО валидацию business-back API.
 * Реальной публикации на HH.ru НЕ происходит — каждая публикация тратит
 * платные кредиты работодателя. Не добавлять тесты с реальным экспортом на HH!
 *
 * Проверяет, что business-back возвращает русские сообщения об ошибках валидации:
 * 1. API: пустой title → 400 с русским сообщением "Название вакансии"
 * 2. API: слишком длинный title → 400 с сообщением о длине
 * 3. API: отрицательная зарплата → 400 с сообщением "Зарплата от"
 * 4. API: возраст > 100 → 400 с сообщением "Возраст от"
 * 5. API: несколько ошибок одновременно → массив errors[]
 * 6. API: описание компании > 10000 символов → 400
 * 7. API: валидные данные → 200 OK
 */

async function getAuthToken(request: any): Promise<string> {
  // Ретрай при 503 от nginx
  for (let i = 0; i < 3; i++) {
    const resp = await request.post('/api/v1/auth/login', {
      data: { email: 'admin@example.com', password: 'admin' },
    });
    if (resp.ok()) {
      const { token } = await resp.json();
      return token;
    }
    if (resp.status() === 503 && i < 2) {
      await new Promise((r) => setTimeout(r, 500));
      continue;
    }
    throw new Error(`Login failed: ${resp.status()}`);
  }
  throw new Error('Login failed after retries');
}

/**
 * POST с ретраем при 503 (nginx upstream timeout).
 * Локальный nginx может кратковременно отвечать 503 при нагрузке от серии тестов.
 */
async function postWithRetry(
  request: any,
  url: string,
  options: Record<string, any>,
  retries = 2,
): Promise<any> {
  let resp = await request.post(url, options);
  for (let i = 0; i < retries && resp.status() === 503; i++) {
    await new Promise((r) => setTimeout(r, 500));
    resp = await request.post(url, options);
  }
  return resp;
}

async function deleteVacancy(request: any, id: number) {
  try {
    const token = await getAuthToken(request);
    await request.delete(`/api/v1/positions/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {}
}

// Базовые валидные данные для создания вакансии
function validVacancyData(overrides: Record<string, any> = {}) {
  return {
    title: `E2E Validation API ${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    description: '<p>Тестовое описание вакансии для проверки API валидации</p>',
    companyDescription: '<p>Тестовая компания</p>',
    salaryTo: 100000,
    topics: ['e2e-validation'],
    answerTime: 60,
    level: 'MIDDLE',
    status: 'ACTIVE',
    questionsCount: 5,
    ...overrides,
  };
}

test.describe('TC-012: API валидация при создании вакансии', () => {
  const createdIds: number[] = [];

  test.afterAll(async ({ request }) => {
    for (const id of createdIds) {
      await deleteVacancy(request, id);
    }
  });

  test('Пустой title → 400 с русским сообщением "Название вакансии"', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ title: '' }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.message).toContain('Название вакансии');
    expect(body.errors).toBeDefined();
    expect(body.errors.some((e: string) => e.includes('Название вакансии'))).toBe(true);
  });

  test('Title > 200 символов → 400 с сообщением о длине', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ title: 'А'.repeat(250) }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.some((e: string) => e.includes('Название вакансии') && e.includes('200'))).toBe(true);
  });

  test('Отрицательная зарплата → 400 с сообщением "Зарплата от"', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ salaryFrom: -100 }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.some((e: string) => e.includes('Зарплата от'))).toBe(true);
  });

  test('Возраст > 100 → 400 с сообщением "Возраст от"', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ ageFrom: 150 }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.some((e: string) => e.includes('Возраст от'))).toBe(true);
  });

  test('Несколько ошибок → массив errors содержит все', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({
        title: '',
        salaryFrom: -100,
        ageFrom: 150,
      }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.length).toBeGreaterThanOrEqual(3);
    expect(body.errors.some((e: string) => e.includes('Название вакансии'))).toBe(true);
    expect(body.errors.some((e: string) => e.includes('Зарплата от'))).toBe(true);
    expect(body.errors.some((e: string) => e.includes('Возраст от'))).toBe(true);
  });

  test('Описание компании > 10000 символов → 400', async ({ request }) => {
    const token = await getAuthToken(request);
    // 10001 символ — минимально превышает лимит, чтобы не нагружать nginx большим payload
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ companyDescription: 'Б'.repeat(10001) }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.some((e: string) => e.includes('Описание компании'))).toBe(true);
  });

  test('Описание вакансии > 10000 символов → 400 "Описание вакансии"', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ description: 'В'.repeat(10001) }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.some((e: string) => e.includes('Описание вакансии'))).toBe(true);
  });

  test('Соц. пакет > 10000 символов → 400 "Соц. пакет"', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ socialPackageText: 'Г'.repeat(10001) }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.some((e: string) => e.includes('Соц. пакет'))).toBe(true);
  });

  test('Помощь при релокации > 5000 символов → 400 "Помощь при релокации"', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ relocationAssistance: 'Д'.repeat(5001) }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.some((e: string) => e.includes('Помощь при релокации'))).toBe(true);
  });

  test('Отрицательная зарплата "до" → 400 "Зарплата до"', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ salaryTo: -50 }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.some((e: string) => e.includes('Зарплата до'))).toBe(true);
  });

  test('Возраст "до" > 100 → 400 "Возраст до"', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData({ ageTo: 200 }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.some((e: string) => e.includes('Возраст до'))).toBe(true);
  });

  test('Все текстовые поля превышают лимиты одновременно → все ошибки в массиве', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      // Минимально превышаем лимит каждого поля, чтобы не нагружать nginx большим payload
      data: validVacancyData({
        title: 'А'.repeat(201),
        description: 'Б'.repeat(10001),
        companyDescription: 'В'.repeat(10001),
        socialPackageText: 'Г'.repeat(10001),
        relocationAssistance: 'Д'.repeat(5001),
      }),
    });

    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.errors.length).toBeGreaterThanOrEqual(5);
    expect(body.errors.some((e: string) => e.includes('Название вакансии'))).toBe(true);
    expect(body.errors.some((e: string) => e.includes('Описание вакансии'))).toBe(true);
    expect(body.errors.some((e: string) => e.includes('Описание компании'))).toBe(true);
    expect(body.errors.some((e: string) => e.includes('Соц. пакет'))).toBe(true);
    expect(body.errors.some((e: string) => e.includes('Помощь при релокации'))).toBe(true);
  });

  test('Валидные данные → 200 OK', async ({ request }) => {
    const token = await getAuthToken(request);
    const resp = await postWithRetry(request, '/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: validVacancyData(),
    });

    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.id).toBeDefined();
    createdIds.push(body.id);
  });
});

// =============================================================================
// UI-тест: ошибки валидации отображаются в toast при сохранении через форму
// ⚠️ Реальной публикации на HH.ru НЕ происходит.
// =============================================================================

test.describe('TC-012: UI — toast с ошибками валидации при сохранении', () => {

  test('Пустое название → toast с ошибкой "Название вакансии"', async ({ page }) => {
    test.setTimeout(60_000);

    await page.goto('/recruiter/');
    await expect(page.getByRole('button', { name: 'Новая вакансия' })).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: 'Новая вакансия' }).click();

    // Ждём форму создания — кнопка "Создать вакансию"
    const createBtn = page.getByRole('button', { name: 'Создать вакансию' });
    await expect(createBtn).toBeVisible({ timeout: 10_000 });

    // Очищаем название (предзаполнено placeholder "Frontend Разработчик")
    const titleInput = page.getByRole('textbox', { name: /Frontend/i });
    await titleInput.fill('');

    // Пытаемся создать
    await createBtn.scrollIntoViewIfNeeded();
    await createBtn.click();

    // Ожидаем toast с ошибкой валидации на русском
    await expect(page.getByText(/Название вакансии/)).toBeVisible({ timeout: 5_000 });

    // Отменяем создание, чтобы не оставлять мусор
    await page.getByRole('button', { name: 'Отмена' }).click();
  });
});
