import { test, expect, Page } from '@playwright/test';

/**
 * TC-009: Экспорт вакансии на HH.ru.
 *
 * ⚠️ ВАЖНО: Тесты НЕ выполняют реальную публикацию на HH.ru!
 * Каждая публикация на HH тратит платные кредиты работодателя.
 * Все тесты останавливаются на диалоге подтверждения и нажимают "Нет".
 *
 * Группа 1 (модалки открываются): вакансия с >1 специализацией + >1 город
 *   → обе модалки всегда открываются.
 *
 * Группа 2 (модалки пропускаются): вакансии с разными комбинациями
 *   листовых/групповых/пустых специализаций и городов.
 *   Проверяет что модалки пропускаются когда не нужны.
 *
 * Каждая группа создаёт свои вакансии через API и удаляет после.
 */

// === Данные тестовой вакансии ===

const TS = Date.now();
const VACANCY_TITLE = `E2E HH Export ${TS}`;

// HH API group IDs: 11 = Информационные технологии, 24 = Искусство
// Оба — группы (не листья), >1 → модалка специализации всегда открывается
const SPECIALIZATION_IDS = '11,24';

// HH API city IDs: 1 = Москва, 2 = Санкт-Петербург
// >1 город → модалка города всегда открывается
const CITY_IDS = ['1', '2'];

let testVacancyId: number | null = null;

// === Хелперы ===

/** Логин через API, возвращает токен */
async function getAuthToken(request: any): Promise<string> {
  const loginResp = await request.post('/api/v1/auth/login', {
    data: { email: 'admin@example.com', password: 'admin' },
  });
  const { token } = await loginResp.json();
  return token;
}

/** Открыть вакансию и перейти в режим редактирования */
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

/** Нажать кнопку экспорта и дождаться модалки специализации */
async function clickExportAndWaitSpec(page: Page, exportBtn: ReturnType<Page['getByRole']>) {
  await exportBtn.scrollIntoViewIfNeeded();
  await exportBtn.click();

  const specTitle = page.getByRole('heading', { name: 'Выберите специализацию для публикации' });
  await expect(specTitle).toBeVisible({ timeout: 5_000 });
  return specTitle;
}

/** Выбрать листовую специализацию "Тестировщик" в модалке */
async function selectTesterSpec(page: Page) {
  // Сбрасываем → раскрываем ИТ → выбираем Тестировщик
  await page.getByRole('button', { name: 'Сбросить' }).click();

  const itCheckbox = page.getByRole('checkbox', { name: 'Информационные технологии' });
  await itCheckbox.scrollIntoViewIfNeeded();
  await itCheckbox.locator('xpath=../../button').click();

  const testerCheckbox = page.getByRole('checkbox', { name: 'Тестировщик' });
  await expect(testerCheckbox).toBeVisible({ timeout: 5_000 });
  await testerCheckbox.scrollIntoViewIfNeeded();
  await testerCheckbox.click();
  await expect(testerCheckbox).toBeChecked();
}

/** Нажать "Сохранить" в модалке (рядом с "Отменить") */
async function clickModalSave(page: Page) {
  const actions = page.getByRole('button', { name: 'Отменить' }).locator('..');
  await actions.getByRole('button', { name: 'Сохранить' }).click();
}

/** Выбрать город "Барнаул" в модалке города */
async function selectBarnaul(page: Page) {
  await page.getByRole('button', { name: 'Сбросить' }).click();

  const citySearch = page.getByRole('textbox', { name: /Поиск/i });
  await citySearch.fill('Барнаул');

  const regionCheckbox = page.getByRole('checkbox', { name: 'Алтайский край' });
  await expect(regionCheckbox).toBeVisible({ timeout: 5_000 });
  await regionCheckbox.locator('xpath=../../button').click();

  const cityCheckbox = page.getByRole('checkbox', { name: 'Барнаул' });
  await expect(cityCheckbox).toBeVisible({ timeout: 3_000 });
  await cityCheckbox.click();
}

test.describe('TC-009: Экспорт вакансии на HH.ru', () => {

  // Создаём тестовую вакансию перед всеми тестами
  test.beforeAll(async ({ request }) => {
    const token = await getAuthToken(request);

    const createResp = await request.post('/api/v1/positions', {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        title: VACANCY_TITLE,
        description: '<p>Тестовая вакансия для E2E экспорта на HH. Проверяем корректную работу модалок специализации и городов, валидацию полей перед публикацией.</p>',
        companyDescription: '<p>Тестовая компания для автоматизированного тестирования. Проверка корректности маппинга данных и обработки ошибок при экспорте вакансий.</p>',
        salaryTo: 100000,
        specialization: SPECIALIZATION_IDS,
        cities: CITY_IDS,
        topics: ['e2e-export-test'],
        answerTime: 60,
        level: 'MIDDLE',
        status: 'ACTIVE',
        questionsCount: 5,
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const vacancy = await createResp.json();
    testVacancyId = vacancy.id;
  });

  // Удаляем тестовую вакансию после всех тестов
  test.afterAll(async ({ request }) => {
    if (!testVacancyId) return;
    try {
      const token = await getAuthToken(request);
      await request.delete(`/api/v1/positions/${testVacancyId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Уже удалена
    }
  });

  test('Основной флоу: специализация → город → подтверждение → Нет', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, testVacancyId!);
    await clickExportAndWaitSpec(page, exportBtn);

    // Модалка специализации: подзаголовок
    await expect(page.getByText('Для публикации на HH.ru необходимо выбрать одну специализацию')).toBeVisible();

    // Выбираем листовую специализацию
    await selectTesterSpec(page);
    await clickModalSave(page);

    // Модалка города
    const cityTitle = page.getByRole('heading', { name: 'Выберите город публикации' });
    await expect(cityTitle).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText('Каждый город — это отдельная публикация')).toBeVisible();

    await selectBarnaul(page);
    await clickModalSave(page);

    // Диалог подтверждения
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/будет (отправлена на публикацию|обновлена) на hh\.ru/)).toBeVisible();

    // Всегда "Нет"
    await page.getByRole('button', { name: 'Нет' }).click();
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();
    await expect(page.getByRole('button', { name: /на HH\.ru/ })).toBeVisible();
  });

  test('Отмена модалки специализации прерывает экспорт', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, testVacancyId!);
    await clickExportAndWaitSpec(page, exportBtn);

    // Нажимаем "Отменить" в модалке специализации
    await page.getByRole('button', { name: 'Отменить' }).click();

    // Модалка закрылась, модалка города НЕ появилась
    await expect(page.getByRole('heading', { name: 'Выберите специализацию для публикации' })).not.toBeVisible();
    await expect(page.getByRole('heading', { name: 'Выберите город публикации' })).not.toBeVisible();
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();

    // Кнопка экспорта на месте
    await expect(exportBtn).toBeVisible();
  });

  test('Отмена модалки города прерывает экспорт', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, testVacancyId!);
    await clickExportAndWaitSpec(page, exportBtn);

    // Выбираем спец и сохраняем → должна открыться модалка города
    await selectTesterSpec(page);
    await clickModalSave(page);

    const cityTitle = page.getByRole('heading', { name: 'Выберите город публикации' });
    await expect(cityTitle).toBeVisible({ timeout: 5_000 });

    // Нажимаем "Отменить" в модалке города
    await page.getByRole('button', { name: 'Отменить' }).click();

    // Модалка закрылась, подтверждение НЕ появилось
    await expect(cityTitle).not.toBeVisible();
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();
    await expect(exportBtn).toBeVisible();
  });

  test('Повторный экспорт после отмены работает корректно', async ({ page }) => {
    test.setTimeout(90_000);

    const exportBtn = await openEditMode(page, testVacancyId!);

    // --- Попытка 1: отменяем на модалке специализации ---
    await clickExportAndWaitSpec(page, exportBtn);
    await page.getByRole('button', { name: 'Отменить' }).click();
    await expect(page.getByRole('heading', { name: 'Выберите специализацию для публикации' })).not.toBeVisible();

    // --- Попытка 2: полный флоу → "Нет" ---
    await clickExportAndWaitSpec(page, exportBtn);

    await selectTesterSpec(page);
    await clickModalSave(page);

    await expect(page.getByRole('heading', { name: 'Выберите город публикации' })).toBeVisible({ timeout: 5_000 });
    await selectBarnaul(page);
    await clickModalSave(page);

    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).toBeVisible({ timeout: 5_000 });
    await page.getByRole('button', { name: 'Нет' }).click();
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();
    await expect(exportBtn).toBeVisible();
  });

  test('Кнопка "Сохранить" disabled для группы, enabled для листа', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, testVacancyId!);
    await clickExportAndWaitSpec(page, exportBtn);

    // После сброса — "Сохранить" disabled (ничего не выбрано)
    await page.getByRole('button', { name: 'Сбросить' }).click();
    const saveBtn = page.getByRole('button', { name: 'Отменить' }).locator('..').getByRole('button', { name: 'Сохранить' });
    await expect(saveBtn).toBeDisabled();

    // Кликаем группу "Информационные технологии" — не должна отмечаться, save остаётся disabled
    const itCheckbox = page.getByRole('checkbox', { name: 'Информационные технологии' });
    await itCheckbox.scrollIntoViewIfNeeded();
    await itCheckbox.click();
    await expect(itCheckbox).not.toBeChecked();
    await expect(saveBtn).toBeDisabled();

    // Раскрываем и выбираем лист "Тестировщик" → save enabled
    await itCheckbox.locator('xpath=../../button').click();
    const testerCheckbox = page.getByRole('checkbox', { name: 'Тестировщик' });
    await expect(testerCheckbox).toBeVisible({ timeout: 5_000 });
    await testerCheckbox.click();
    await expect(testerCheckbox).toBeChecked();
    await expect(saveBtn).toBeEnabled();

    // Снимаем выбор — save снова disabled
    await testerCheckbox.click();
    await expect(testerCheckbox).not.toBeChecked();
    await expect(saveBtn).toBeDisabled();

    // Закрываем модалку
    await page.getByRole('button', { name: 'Отменить' }).click();
  });

  test('Предвыбранные специализации отображаются в модалке', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, testVacancyId!);
    await clickExportAndWaitSpec(page, exportBtn);

    // Вакансия содержит ИТ (11) и Искусство (24) — родительские чекбоксы должны быть checked
    // (все дочерние листья выбраны → родитель отображается как checked)
    const itCheckbox = page.getByRole('checkbox', { name: 'Информационные технологии' });
    const artCheckbox = page.getByRole('checkbox', { name: 'Искусство, развлечения, массмедиа' });

    await expect(itCheckbox).toBeChecked();
    await expect(artCheckbox).toBeChecked();

    // Закрываем
    await page.getByRole('button', { name: 'Отменить' }).click();
  });
});

// =============================================================================
// Группа 2: Пропуск модалок при листовых / пустых значениях
// =============================================================================

/** Создать вакансию через API и вернуть её ID */
async function createTestVacancy(
  request: any,
  overrides: { specialization?: string; cities?: string[] } = {},
): Promise<number> {
  const token = await getAuthToken(request);
  const resp = await request.post('/api/v1/positions', {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      title: `E2E HH Skip ${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      description: '<p>Тестовая вакансия для проверки пропуска модалок специализации и городов. Валидация экспорта на HH.ru должна пропускать модалки при листовых значениях.</p>',
      companyDescription: '<p>Тестовая компания для автоматизированного тестирования функционала экспорта. Проверка обработки листовых и нелистовых значений справочников.</p>',
      salaryTo: 100000,
      specialization: overrides.specialization ?? '',
      cities: overrides.cities ?? [],
      topics: ['e2e-skip-test'],
      answerTime: 60,
      level: 'MIDDLE',
      status: 'ACTIVE',
      questionsCount: 5,
    },
  });
  expect(resp.ok()).toBeTruthy();
  const vacancy = await resp.json();
  return vacancy.id;
}

/** Удалить вакансию через API */
async function deleteTestVacancy(request: any, id: number) {
  try {
    const token = await getAuthToken(request);
    await request.delete(`/api/v1/positions/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    // Уже удалена
  }
}

test.describe('TC-009: Пропуск модалок при листовых значениях', () => {

  // ID = 124 (Тестировщик) — листовая специализация
  // ID = 1 (Москва) — листовой город

  let leafBothId: number | null = null;   // 1 лист + 1 лист → обе модалки пропущены
  let groupSpecId: number | null = null;  // 1 группа + 1 лист → только модалка спец
  let multiCityId: number | null = null;  // 1 лист + >1 город → только модалка города
  let emptyBothId: number | null = null;  // пустая спец + пустые города → обе пропущены

  test.beforeAll(async ({ request }) => {
    [leafBothId, groupSpecId, multiCityId, emptyBothId] = await Promise.all([
      createTestVacancy(request, { specialization: '124', cities: ['1'] }),
      createTestVacancy(request, { specialization: '11', cities: ['1'] }),
      createTestVacancy(request, { specialization: '124', cities: ['1', '2'] }),
      createTestVacancy(request, { specialization: '', cities: [] }),
    ]);
  });

  test.afterAll(async ({ request }) => {
    await Promise.all(
      [leafBothId, groupSpecId, multiCityId, emptyBothId]
        .filter((id): id is number => id !== null)
        .map(id => deleteTestVacancy(request, id)),
    );
  });

  test('1 листовая спец + 1 листовой город → обе модалки пропущены, сразу подтверждение', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, leafBothId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Обе модалки НЕ должны появляться
    await expect(page.getByRole('heading', { name: 'Выберите специализацию для публикации' })).not.toBeVisible();
    await expect(page.getByRole('heading', { name: 'Выберите город публикации' })).not.toBeVisible();

    // Сразу диалог подтверждения
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).toBeVisible({ timeout: 5_000 });

    await page.getByRole('button', { name: 'Нет' }).click();
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();
  });

  test('1 группа спец + 1 листовой город → только модалка специализации', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, groupSpecId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Модалка специализации ДОЛЖНА открыться (группа, не лист)
    await expect(page.getByRole('heading', { name: 'Выберите специализацию для публикации' })).toBeVisible({ timeout: 5_000 });

    // Выбираем лист и сохраняем
    await selectTesterSpec(page);
    await clickModalSave(page);

    // Модалка города НЕ должна открыться (1 листовой город)
    await expect(page.getByRole('heading', { name: 'Выберите город публикации' })).not.toBeVisible();

    // Сразу подтверждение
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).toBeVisible({ timeout: 5_000 });
    await page.getByRole('button', { name: 'Нет' }).click();
  });

  test('1 листовая спец + >1 город → только модалка города', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, multiCityId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Модалка специализации НЕ должна открыться (1 лист)
    await expect(page.getByRole('heading', { name: 'Выберите специализацию для публикации' })).not.toBeVisible();

    // Модалка города ДОЛЖНА открыться (>1 город)
    await expect(page.getByRole('heading', { name: 'Выберите город публикации' })).toBeVisible({ timeout: 5_000 });

    await selectBarnaul(page);
    await clickModalSave(page);

    // Подтверждение
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).toBeVisible({ timeout: 5_000 });
    await page.getByRole('button', { name: 'Нет' }).click();
  });

  test('Пустая спец + пустые города → обе модалки пропущены, сразу подтверждение', async ({ page }) => {
    test.setTimeout(60_000);

    const exportBtn = await openEditMode(page, emptyBothId!);
    await exportBtn.scrollIntoViewIfNeeded();
    await exportBtn.click();

    // Обе модалки НЕ должны появляться
    await expect(page.getByRole('heading', { name: 'Выберите специализацию для публикации' })).not.toBeVisible();
    await expect(page.getByRole('heading', { name: 'Выберите город публикации' })).not.toBeVisible();

    // Сразу подтверждение
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).toBeVisible({ timeout: 5_000 });

    await page.getByRole('button', { name: 'Нет' }).click();
    await expect(page.getByText(/Подтверждение (публикации|обновления)/)).not.toBeVisible();
  });
});
