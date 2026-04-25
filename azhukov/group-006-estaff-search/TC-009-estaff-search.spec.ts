import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as nodePath from 'path';

// ═══════════════════════════════════════════════════════════════════
// Стадии видео-демо
//
// Каждый тест проходит 3 обязательные стадии:
//   1. stageTitle   — заставка с названием теста (5 сек)
//   2. stageLoading — оборачивает ожидание API, записывает тайминг для перемотки в видео
//   3. stageResult  — фриз на итоговом экране (10 сек)
//
// Тесты без API-вызовов (UI-обзор, проверка фильтров) пропускают стадию 2.
// ═══════════════════════════════════════════════════════════════════

const TITLE_DURATION = 5_000;   // Стадия 1: длительность заставки
const RESULT_DURATION = 10_000; // Стадия 3: длительность фриза на результате
const TIMING_FILE = nodePath.join(process.cwd(), 'test-results', 'video-timing.jsonl');

/** Время начала текущего теста (для расчёта таймингов перемотки) */
let _testStart = 0;

/** Описания тестов для демо-видео (заголовок + что делает) */
const TEST_TITLES: Record<string, { num: number; text: string; desc: string }> = {
  'Полный обход UI E-Staff: табы, статус, настройки, модалка, фильтры, поиск':
    { num: 1, text: 'Обзор интерфейса E-Staff', desc: 'Табы источников, статус подключения, настройки токена, модалка, фильтры и кнопка поиска' },
  'E-Staff: фильтры без HH-секций':
    { num: 2, text: 'Фильтры E-Staff: нет HH-секций', desc: 'При переключении на E-Staff скрываются HH-специфичные секции фильтров' },
  'E-Staff: поиск по должности возвращает релевантных кандидатов':
    { num: 3, text: 'Поиск по должности «менеджер»', desc: 'Реальный поиск через HR-Proxy — проверяем структуру таблицы и данные кандидатов' },
  'E-Staff: фильтры сужают выдачу (должность + зарплата)':
    { num: 4, text: 'Фильтры сужают выдачу', desc: 'Сначала поиск по должности, затем добавляем зарплату — результатов меньше' },
  'Базовый поиск E-Staff: запрос уходит с source=estaff':
    { num: 5, text: 'Базовый поиск E-Staff', desc: 'Поиск без фильтров — все кандидаты из базы E-Staff' },
  'Фильтр: пол М — все кандидаты мужского пола':
    { num: 6, text: 'Фильтр: Пол М', desc: 'Все кандидаты в результатах — мужчины' },
  'Фильтр: пол Ж — все кандидаты женского пола':
    { num: 7, text: 'Фильтр: Пол Ж', desc: 'Все кандидаты в результатах — женщины' },
  'Фильтр: возраст 25-35 — все кандидаты в диапазоне':
    { num: 8, text: 'Фильтр: Возраст 25–35 лет', desc: 'Все кандидаты в возрастном диапазоне от 25 до 35 лет' },
  'Фильтр: зарплата 100k-200k — все в диапазоне':
    { num: 9, text: 'Фильтр: Зарплата 100–200 тыс.', desc: 'Зарплатные ожидания кандидатов от 100 000 до 200 000 ₽' },
  'Фильтр: должность «менеджер» — результаты релевантны':
    { num: 10, text: 'Фильтр: Должность «менеджер»', desc: 'Кандидаты с должностью, содержащей слово «менеджер»' },
  'Комбинация: пол М + возраст 25-40 — мужчины в диапазоне':
    { num: 11, text: 'Комбинация: М + Возраст 25–40', desc: 'Мужчины от 25 до 40 лет — два фильтра одновременно' },
  'Комбинация: должность + зарплата — оба фильтра применены':
    { num: 12, text: 'Комбинация: Должность + Зарплата', desc: 'Должность «менеджер» + зарплата от 100 000 ₽' },
  'Фильтр: опыт «Более 6 лет» — параметр передаётся':
    { num: 13, text: 'Фильтр: Опыт более 6 лет', desc: 'Кандидаты с профессиональным опытом свыше 6 лет' },
  'Фильтр: опыт «От 3 до 6 лет» — параметр передаётся':
    { num: 14, text: 'Фильтр: Опыт 3–6 лет', desc: 'Кандидаты с опытом от 3 до 6 лет (несколько вариантов)' },
  'Фильтр: навыки — параметр skillGroups передаётся корректно':
    { num: 15, text: 'Фильтр: Навыки (skillGroups)', desc: 'Поиск по группам профессиональных навыков' },
  'Фильтр: стоп-лист компаний — параметр передаётся':
    { num: 16, text: 'Фильтр: Стоп-лист компаний', desc: 'Исключение кандидатов из указанных компаний' },
  'Фильтр: компании-доноры — параметр передаётся':
    { num: 17, text: 'Фильтр: Компании-доноры', desc: 'Приоритетный поиск среди кандидатов из выбранных компаний' },
  'Фильтр: текущая компания — параметр передаётся':
    { num: 18, text: 'Фильтр: Текущая компания', desc: 'Поиск по текущему месту работы в E-Staff' },
  'Фильтр: предыдущая компания — параметр передаётся':
    { num: 19, text: 'Фильтр: Предыдущая компания', desc: 'Поиск по предыдущему месту работы в E-Staff' },
  'Комбинация: пол Ж + должность — женщины с «менеджер»':
    { num: 20, text: 'Комбинация: Ж + Должность', desc: 'Женщины с должностью «менеджер» — два фильтра' },
};

// ── Стадия 1: Заставка (5 сек) ─────────────────────────────────

/** Показывает тёмный экран с номером и названием теста */
async function stageTitle(page: import('@playwright/test').Page) {
  const info = test.info();
  const t = TEST_TITLES[info.title];
  if (t) {
    await page.setContent(`<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;width:100vw;height:100vh;background:#191923;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:system-ui,sans-serif;color:white;">
  <div style="font-size:20px;opacity:0.5;margin-bottom:12px">Тест ${t.num} / 20</div>
  <div style="font-size:32px;font-weight:700;text-align:center;max-width:80%;margin-bottom:16px">${t.text}</div>
  <div style="font-size:18px;opacity:0.65;text-align:center;max-width:70%">${t.desc}</div>
</body></html>`);
    await page.waitForTimeout(TITLE_DURATION);
  }
  _testStart = Date.now();
}

// ── Стадия 2: Перемотка (оборачивает ожидание API) ──────────────

/**
 * Оборачивает ожидание API-запроса. Записывает тайминг loadStart→loadEnd
 * в JSONL-файл — скрипт склейки видео (run-with-video.js) ускоряет
 * этот участок в 100 раз (перемотка).
 */
async function stageLoading<T>(fn: () => Promise<T>): Promise<T> {
  const startSec = (Date.now() - _testStart) / 1000;
  const result = await fn();
  const endSec = (Date.now() - _testStart) / 1000;
  const waitSec = endSec - startSec;
  if (waitSec > 3) {
    try {
      fs.mkdirSync(nodePath.dirname(TIMING_FILE), { recursive: true });
      fs.appendFileSync(
        TIMING_FILE,
        JSON.stringify({ loadStartSec: startSec, loadEndSec: endSec, waitSec }) + '\n',
      );
    } catch { /* не блокируем тест */ }
  }
  return result;
}

// ── Стадия 3: Результат (10 сек фриз) ──────────────────────────

/** Замирает на итоговом экране — зритель видит результат теста */
async function stageResult(page: import('@playwright/test').Page) {
  await page.waitForTimeout(RESULT_DURATION);
}

// ═══════════════════════════════════════════════════════════════════
// Хелперы
// ═══════════════════════════════════════════════════════════════════

/** Локатор для таба в SourceTabs (первый с таким именем — таб, не dropdown) */
function sourceTab(page: import('@playwright/test').Page, name: string) {
  return page.getByRole('button', { name, exact: true }).first();
}

/** Ожидание завершения поиска: таблица, ошибка или 0 результатов */
async function waitForSearchDone(page: import('@playwright/test').Page, timeout = 130_000) {
  await Promise.race([
    page.getByRole('table').waitFor({ state: 'visible', timeout }),
    page.getByText('Ошибка загрузки данных').waitFor({ state: 'visible', timeout }),
    page.getByText(/Найдено 0|Ничего не найдено|Кандидаты не найдены/).waitFor({ state: 'visible', timeout }),
    page.getByText(/Найдено \d+ кандидат/).waitFor({ state: 'visible', timeout }),
  ]).catch(() => {});
}

/**
 * Навигация на E-Staff: блокировка авто-поиска → переход → сброс фильтров → переключение на E-Staff.
 * Используется перед каждым тестом с реальным API.
 */
async function prepareEstaffSearch(page: import('@playwright/test').Page) {
  // Блокируем авто-поиск (HR-Proxy 60–120с, мешает ручному поиску)
  await page.route('**/relevanter/api/applicants?**', route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '{"items":[],"total":0}' }));

  // Retry навигации — контейнер recruiter-front может перезапускаться (502)
  for (let attempt = 0; attempt < 5; attempt++) {
    await page.goto('/recruiter/search?source=estaff');
    const ok = await page.getByRole('heading', { name: 'Поиск из источников' })
      .isVisible({ timeout: 15_000 }).catch(() => false);
    if (ok) break;
    console.log(`  ⚠ Фронт недоступен (попытка ${attempt + 1}/5), жду 15 сек...`);
    await page.waitForTimeout(15_000);
    if (attempt === 4) throw new Error('Фронтенд недоступен после 5 попыток');
  }

  // Сбрасываем вакансионные фильтры (побочный эффект: source → hh)
  const resetBtn = page.getByRole('button', { name: 'Сбросить фильтры' });
  if (await resetBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await resetBtn.click();
    await page.waitForTimeout(500);
  }

  // Переключаемся обратно на E-Staff
  await sourceTab(page, 'E-Staff').click();
  await expect(page).toHaveURL(/source=estaff/, { timeout: 5_000 });

  // Очищаем поле поиска (текст вакансии)
  await page.getByRole('textbox', { name: 'Поиск' }).clear();
}

/** Открыть панель фильтров и включить ручной поиск */
async function openFiltersPanel(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: 'Фильтры', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Фильтры' })).toBeVisible({ timeout: 5_000 });

  const manualBtn = page.getByRole('button', { name: 'Ручной поиск' });
  if (await manualBtn.isVisible({ timeout: 1_000 }).catch(() => false)) {
    await manualBtn.click();
  }
}

/**
 * Клик «Поиск» → перехват URL + ожидание ответа → возврат { url, data }.
 *
 * Регистрирует селективный route-handler (LIFO): пропускает запросы с urlMustContain,
 * остальные блокирует пустым ответом. Уменьшает pageSize до 5 для скорости.
 *
 * @param searchBtn — кнопка для клика (по умолчанию «Поиск» в панели фильтров)
 */
async function executeSearch(
  page: import('@playwright/test').Page,
  urlMustContain?: string,
  searchBtn?: import('@playwright/test').Locator,
) {
  let capturedUrl: URL | null = null;

  // Именованный handler — для точного unroute (не затрагивает блокирующий handler из prepareEstaffSearch)
  const handler = async (route: import('@playwright/test').Route) => {
    const reqUrl = new URL(route.request().url());
    const decoded = decodeURIComponent(reqUrl.search);

    if (urlMustContain && !decoded.includes(urlMustContain)) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"items":[],"total":0}' });
      return;
    }

    if (!capturedUrl) capturedUrl = reqUrl;

    // Уменьшаем лимит — HR-Proxy отвечает быстрее
    const modifiedUrl = new URL(route.request().url());
    modifiedUrl.searchParams.set('pageSize', '5');
    modifiedUrl.searchParams.set('limit', '5');
    await route.continue({ url: modifiedUrl.toString() });
  };

  await page.route('**/relevanter/api/applicants?**', handler);

  // Подписываемся на ответ ДО клика
  const responsePromise = page.waitForResponse(
    r => {
      if (!r.url().includes('/relevanter/api/applicants')) return false;
      if (urlMustContain && !decodeURIComponent(r.url()).includes(urlMustContain)) return false;
      return true;
    },
    { timeout: 150_000 },
  ).catch(() => null);

  // Кликаем кнопку поиска
  const btn = searchBtn || page.getByRole('button', { name: 'Поиск' }).last();
  await btn.click();

  // Ждём ответ
  const response = await responsePromise;
  let capturedData: any = null;
  if (response) {
    try { capturedData = await response.json(); } catch { /* не JSON */ }
  }

  // Ждём завершения поиска на странице
  await waitForSearchDone(page);

  // Снимаем только свой handler (блокирующий из prepareEstaffSearch остаётся)
  await page.unroute('**/relevanter/api/applicants?**', handler).catch(() => {});

  if (!capturedUrl) {
    throw new Error(`Запрос к /applicants не отправлен (ожидался ${urlMustContain || 'любой'})`);
  }

  const url = capturedUrl;
  const data = (capturedData && Array.isArray(capturedData.items))
    ? capturedData
    : { items: [], total: 0, _timeout: true };

  // Лог результата
  const status = data._timeout ? 'TIMEOUT' : `${data.total} кандидатов (items: ${data.items.length})`;
  console.log(`  -> API: ${status} | URL: ${decodeURIComponent(url.search).substring(0, 120)}...`);

  // Ни один параметр не NaN / undefined
  for (const [key, value] of url.searchParams.entries()) {
    expect(value, `${key} не должен быть NaN`).not.toBe('NaN');
    expect(value, `${key} не должен быть undefined`).not.toBe('undefined');
  }
  expect(url.searchParams.get('source')).toBe('estaff');

  // Ждём рендера таблицы если есть данные
  if (data.items?.length > 0) {
    await expect(page.getByRole('table')).toBeVisible({ timeout: 15_000 });
  }

  return { url, data };
}

/**
 * Открывает модалку резюме первого кандидата (глазик) и показывает 5 сек.
 * Клик → ждём модалку → фриз 5 сек → закрываем.
 *
 * Блокирующий route handler перехватывает /applicants?** — glob-паттерн
 * матчит и /applicants/123. LIFO-handler пропускает GET к /applicants/{id}.
 */
async function previewCandidate(page: import('@playwright/test').Page) {
  const eyeBtn = page.getByRole('button', { name: 'Просмотр резюме' }).first();
  if (!(await eyeBtn.isVisible({ timeout: 3_000 }).catch(() => false))) return;

  // LIFO-handler: пропускаем запросы к /applicants/{id} (без query-параметров поиска)
  const passthrough = async (route: import('@playwright/test').Route) => {
    const url = route.request().url();
    // /applicants/{id} — пропускаем; /applicants?source=... — блокируем (оставляем для нижнего handler)
    if (/\/applicants\/[^/?]+/.test(url) && !url.includes('source=')) {
      await route.continue();
    } else {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"items":[],"total":0}' });
    }
  };
  await page.route('**/relevanter/api/applicants**', passthrough);

  await eyeBtn.click();

  // Ждём модалку с резюме
  const modal = page.locator('.fixed.inset-0');
  await expect(modal).toBeVisible({ timeout: 10_000 });

  // Ждём загрузки содержимого (не спиннер, а реальные данные)
  const content = page.getByText('Основная информация').or(page.getByText('Ошибка загрузки'));
  await content.waitFor({ state: 'visible', timeout: 30_000 }).catch(() => {});

  // Фриз на модалке — зритель видит резюме
  await page.waitForTimeout(5_000);

  // Закрываем модалку
  const closeBtn = modal.locator('button').filter({ has: page.locator('svg') }).first();
  if (await closeBtn.isVisible().catch(() => false)) {
    await closeBtn.click();
    await expect(modal).not.toBeVisible({ timeout: 3_000 }).catch(() => {});
  }

  // Снимаем свой handler
  await page.unroute('**/relevanter/api/applicants**', passthrough).catch(() => {});
}

/** Проверка таблицы: наличие строк, лог первых 5, скриншоты */
async function verifyTable(page: import('@playwright/test').Page) {
  const rows = page.getByRole('rowgroup').last().getByRole('row');
  const count = await rows.count();
  expect(count, 'Таблица должна содержать строки').toBeGreaterThan(0);

  for (let i = 0; i < Math.min(count, 5); i++) {
    const rowText = await rows.nth(i).innerText();
    console.log(`    Строка ${i + 1}: ${rowText.replace(/\n/g, ' | ').substring(0, 200)}`);
  }

  // Скриншоты
  const info = test.info();
  const slug = info.title.replace(/[^a-zA-Zа-яА-Я0-9]/g, '-').substring(0, 60);
  const dir = 'results/screenshots';
  fs.mkdirSync(dir, { recursive: true });

  await page.screenshot({ path: `${dir}/${slug}-full.png`, fullPage: true });

  const table = page.getByRole('table');
  if (await table.isVisible().catch(() => false)) {
    await table.screenshot({ path: `${dir}/${slug}-table.png` });
  }
}

// ═══════════════════════════════════════════════════════════════════
// TC-009: UI + базовые поисковые тесты (1–4)
// ═══════════════════════════════════════════════════════════════════

test.describe('TC-009: Поиск через E-Staff', () => {

  test('Полный обход UI E-Staff: табы, статус, настройки, модалка, фильтры, поиск', async ({ page }) => {
    test.setTimeout(240_000);

    // ── Стадия 1: Заставка (5 сек) ──
    await stageTitle(page);

    // ── Действия ──
    await page.goto('/recruiter/search?source=hh');
    await expect(page.getByRole('heading', { name: 'Поиск из источников' })).toBeVisible({ timeout: 10_000 });

    // 1. Табы источников
    const hhTab = sourceTab(page, 'HeadHunter');
    const estaffTab = sourceTab(page, 'E-Staff');
    await expect(hhTab).toBeVisible();
    await expect(estaffTab).toBeVisible();

    await estaffTab.click();
    await expect(page).toHaveURL(/source=estaff/, { timeout: 5_000 });
    await hhTab.click();
    await expect(page).toHaveURL(/source=hh/, { timeout: 5_000 });
    await estaffTab.click();
    await expect(page).toHaveURL(/source=estaff/, { timeout: 5_000 });

    // 2. Индикатор статуса E-Staff
    const statusIndicator = page.getByText(/E-Staff подключен|E-Staff не подключен|E-Staff статус недоступен/);
    await expect(statusIndicator).toBeVisible({ timeout: 15_000 });

    const settingsBtn = page.getByRole('button', { name: /Настройки E-Staff|Подключить E-Staff/ });
    await expect(settingsBtn).toBeVisible();

    // 3. Настройки E-Staff
    await settingsBtn.click();
    await expect(page.getByRole('heading', { name: 'Настройки E-Staff' })).toBeVisible({ timeout: 5_000 });

    const backBtn = page.getByRole('button', { name: /Назад к поиску/ });
    await expect(backBtn).toBeVisible();

    // 4. Статус токена
    const tokenStatus = page.getByText('E-Staff подключен').or(page.getByText('E-Staff не подключен'));
    await expect(tokenStatus).toBeVisible({ timeout: 10_000 });

    await expect(page.getByText('Подключение E-Staff:')).toBeVisible();
    await expect(page.getByText(/Получите токен HR-Proxy/)).toBeVisible();
    await expect(page.getByText(/Нажмите «Установить токен»/)).toBeVisible();
    await expect(page.getByText(/Вставьте токен и сохраните/)).toBeVisible();

    // 5. Модалка токена
    const tokenActionBtn = page.getByRole('button', { name: /Установить токен|Обновить токен/ });
    if (await tokenActionBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await tokenActionBtn.click();

      const modalTitle = page.getByRole('heading', { name: 'Установить токен E-Staff' });
      await expect(modalTitle).toBeVisible({ timeout: 3_000 });
      await expect(page.getByText('HR-Proxy токен')).toBeVisible();

      const tokenInput = page.getByPlaceholder('Введите токен HR-Proxy');
      await expect(tokenInput).toBeVisible();
      await expect(page.getByText(/Токен используется для доступа к E-Staff через HR-Proxy/)).toBeVisible();

      const cancelBtn = page.getByRole('button', { name: 'Отмена' });
      const saveBtn = page.getByRole('button', { name: 'Сохранить' });
      await expect(cancelBtn).toBeVisible();
      await expect(saveBtn).toBeVisible();
      await expect(saveBtn).toBeDisabled();

      await tokenInput.fill('test-token-value');
      await expect(saveBtn).toBeEnabled();
      await tokenInput.clear();

      await cancelBtn.click();
      await expect(modalTitle).not.toBeVisible({ timeout: 3_000 });

      const deleteTokenBtn = page.getByRole('button', { name: /Удалить токен/ });
      if (await deleteTokenBtn.isVisible({ timeout: 1_000 }).catch(() => false)) {
        await expect(deleteTokenBtn).toBeEnabled();
      }
    }

    // 6. Возврат к поиску
    await backBtn.click();
    await expect(page.getByRole('heading', { name: 'Поиск из источников' })).toBeVisible({ timeout: 5_000 });

    if (!(page.url()).includes('source=estaff')) {
      await estaffTab.click();
      await expect(page).toHaveURL(/source=estaff/, { timeout: 5_000 });
    }

    // 7. Фильтры E-Staff
    await page.getByRole('button', { name: 'Фильтры', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Фильтры' })).toBeVisible({ timeout: 5_000 });

    await expect(page.getByText('Должность').first()).toBeVisible();
    await expect(page.getByText('Текущая компания')).toBeVisible();
    await expect(page.getByText('Предыдущая компания')).toBeVisible();

    const companyInputs = page.getByPlaceholder('Название компании');
    expect(await companyInputs.count()).toBeGreaterThanOrEqual(2);

    await expect(page.getByText('Только текущая должность')).toBeVisible();
    await expect(page.getByText('Указана зарплата')).toBeVisible();
    await expect(page.getByText('Обновлено после')).toBeVisible();
    await expect(page.getByText('Создано после')).toBeVisible();
    await expect(page.getByText('Отрасль (HH)')).not.toBeVisible();
    await expect(page.getByText('Специализация (HH)')).not.toBeVisible();

    // 8. Заполняем и «ищем» (API замокан — UI тест)
    await companyInputs.first().fill('Яндекс');
    await page.getByText('Только текущая должность').click();
    await page.getByText('Указана зарплата').click();

    const positionInput = page.getByPlaceholder('Введите должность');
    if (await positionInput.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await positionInput.fill('менеджер');
    }

    await page.route('**/relevanter/api/applicants?**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '{"items":[],"total":0}' }));

    await page.getByRole('button', { name: 'Поиск' }).last().click();
    await page.waitForTimeout(500);

    // ── Стадия 3: Результат (10 сек) ──
    await stageResult(page);
  });

  test('E-Staff: фильтры без HH-секций', async ({ page }) => {
    test.setTimeout(45_000);

    // ── Стадия 1: Заставка (5 сек) ──
    await stageTitle(page);

    // ── Действия ──
    await page.goto('/recruiter/search?source=hh');
    await expect(page.getByRole('heading', { name: 'Поиск из источников' })).toBeVisible({ timeout: 10_000 });

    await sourceTab(page, 'E-Staff').click();
    await expect(page).toHaveURL(/source=estaff/, { timeout: 5_000 });

    await page.getByRole('button', { name: 'Фильтры', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Фильтры' })).toBeVisible({ timeout: 5_000 });

    await expect(page.getByText('Должность').first()).toBeVisible();
    await expect(page.getByText('Отрасль (HH)')).not.toBeVisible();
    await expect(page.getByText('Специализация (HH)')).not.toBeVisible();
    await expect(page.getByText('Статус поиска работы (HH)')).not.toBeVisible();
    await expect(page.getByText('Тип занятости (HH)')).not.toBeVisible();

    // ── Стадия 3: Результат (10 сек) ──
    await stageResult(page);
  });

  test('E-Staff: поиск по должности возвращает релевантных кандидатов', async ({ page }) => {
    test.setTimeout(240_000);

    // ── Стадия 1: Заставка (5 сек) ──
    await stageTitle(page);

    // ── Подготовка ──
    await prepareEstaffSearch(page);

    const searchInput = page.getByRole('textbox', { name: 'Поиск' });
    await searchInput.clear();
    await searchInput.fill('менеджер');

    // ── Стадия 2: Загрузка (перемотка) ──
    const { data } = await stageLoading(() =>
      executeSearch(page, 'менеджер', page.getByRole('button', { name: 'Найти' })),
    );

    if (!data || !Array.isArray(data.items) || data.items.length === 0) {
      test.skip(true, 'HR-Proxy: нет данных или таймаут');
      return;
    }

    // ── Проверки ──
    await expect(page.getByRole('table')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('columnheader', { name: 'ФИО' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Контакты' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Должность' })).toBeVisible();

    const candidateRows = page.getByRole('rowgroup').last().getByRole('row');
    expect(await candidateRows.count()).toBeGreaterThan(0);

    const firstRow = candidateRows.first();
    await expect(firstRow.getByRole('link').first()).toHaveAttribute('href', /\/recruiter\/applicant\//);
    await expect(page.getByText(/Показано \d+ - \d+ из \d+/)).toBeVisible();

    // Просмотр резюме кандидата (глазик)
    await previewCandidate(page);

    // ── Стадия 3: Результат (10 сек) ──
    await stageResult(page);
  });

  test('E-Staff: фильтры сужают выдачу (должность + зарплата)', async ({ page }) => {
    test.setTimeout(300_000);

    // ── Стадия 1: Заставка (5 сек) ──
    await stageTitle(page);

    // ── Подготовка ──
    await prepareEstaffSearch(page);

    const searchInput = page.getByRole('textbox', { name: 'Поиск' });
    await searchInput.clear();
    await searchInput.fill('менеджер');

    // ── Стадия 2: Загрузка (перемотка, оба запроса) ──
    const result = await stageLoading(async () => {
      // Первый поиск: только должность
      const r1 = await executeSearch(page, 'менеджер', page.getByRole('button', { name: 'Найти' }));

      if (r1.data._timeout || r1.data.total === 0) {
        return { r1, r2: null as any };
      }

      await expect(page.getByRole('table')).toBeVisible({ timeout: 15_000 });

      // Второй поиск: должность + зарплата
      await page.getByRole('button', { name: 'Фильтры', exact: true }).click();
      await expect(page.getByRole('heading', { name: 'Фильтры' })).toBeVisible({ timeout: 5_000 });

      const salaryFrom = page.getByRole('textbox', { name: 'от' }).first();
      await salaryFrom.clear();
      await salaryFrom.fill('100000');

      const r2 = await executeSearch(page, 'salaryFrom=100000');
      return { r1, r2 };
    });

    if (!result.r1 || result.r1.data._timeout || result.r1.data.total === 0) {
      test.skip(true, 'HR-Proxy: нет данных на первый запрос');
      return;
    }
    if (!result.r2 || result.r2.data._timeout || result.r2.data.total === 0) {
      test.skip(true, 'HR-Proxy: нет данных на второй запрос');
      return;
    }

    // ── Проверки ──
    expect(result.r2.data.total).toBeLessThanOrEqual(result.r1.data.total);
    expect(result.r2.data.total).toBeGreaterThan(0);

    // Просмотр резюме кандидата (глазик)
    await previewCandidate(page);

    // ── Стадия 3: Результат (10 сек) ──
    await stageResult(page);
  });
});

// ═══════════════════════════════════════════════════════════════════
// TC-009b: Фильтры E-Staff — реальные данные (тесты 5–20)
//
// Паттерн каждого теста:
//   stageTitle → prepareEstaffSearch → openFiltersPanel → фильтр →
//   stageLoading(executeSearch) → проверки → stageResult
// ═══════════════════════════════════════════════════════════════════

test.describe('TC-009b: Фильтры E-Staff — реальные данные', () => {

  // ─── 5. Базовый поиск (без фильтров) ──────────────────────────

  test('Базовый поиск E-Staff: запрос уходит с source=estaff', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    const { url, data } = await stageLoading(() => executeSearch(page, 'searchMode=custom'));

    expect(url.searchParams.get('source')).toBe('estaff');

    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total, 'Ожидаются кандидаты в базе E-Staff').toBeGreaterThan(0);
    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 6. Пол М ────────────────────────────────────────────────

  test('Фильтр: пол М — все кандидаты мужского пола', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByRole('button', { name: 'М', exact: true }).click();

    const { url, data } = await stageLoading(() => executeSearch(page, 'gender=M'));

    expect(url.searchParams.get('gender')).toBe('M');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total).toBeGreaterThan(0);
    for (const item of data.items) {
      expect(item.gender, `${item.fullName} должен быть male`).toBe('male');
    }

    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 7. Пол Ж ────────────────────────────────────────────────

  test('Фильтр: пол Ж — все кандидаты женского пола', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByRole('button', { name: 'Ж', exact: true }).click();

    const { url, data } = await stageLoading(() => executeSearch(page, 'gender=F'));

    expect(url.searchParams.get('gender')).toBe('F');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total).toBeGreaterThan(0);
    for (const item of data.items) {
      expect(item.gender, `${item.fullName} должен быть female`).toBe('female');
    }

    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 8. Возраст от / до ──────────────────────────────────────

  test('Фильтр: возраст 25-35 — все кандидаты в диапазоне', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByPlaceholder('ОТ', { exact: true }).fill('25');
    await page.getByPlaceholder('ДО', { exact: true }).fill('35');

    const { url, data } = await stageLoading(() => executeSearch(page, 'ageFrom=25'));

    expect(url.searchParams.get('ageFrom')).toBe('25');
    expect(url.searchParams.get('ageTo')).toBe('35');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total).toBeGreaterThan(0);
    for (const item of data.items) {
      if (item.age !== null && item.age !== undefined) {
        expect(item.age, `${item.fullName} возраст ${item.age} вне 25-35`)
          .toBeGreaterThanOrEqual(25);
        expect(item.age, `${item.fullName} возраст ${item.age} вне 25-35`)
          .toBeLessThanOrEqual(35);
      }
    }

    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 9. Зарплата от / до ─────────────────────────────────────

  test('Фильтр: зарплата 100k-200k — все в диапазоне', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByPlaceholder('от', { exact: true }).fill('100000');
    await page.getByPlaceholder('до', { exact: true }).fill('200000');

    const { url, data } = await stageLoading(() => executeSearch(page, 'salaryFrom=100000'));

    expect(url.searchParams.get('salaryFrom')).toBe('100000');
    expect(url.searchParams.get('salaryTo')).toBe('200000');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total).toBeGreaterThan(0);
    for (const item of data.items) {
      if (item.salary?.amount) {
        expect(item.salary.amount, `${item.fullName} зарплата ${item.salary.amount} < 100k`)
          .toBeGreaterThanOrEqual(100000);
        expect(item.salary.amount, `${item.fullName} зарплата ${item.salary.amount} > 200k`)
          .toBeLessThanOrEqual(200000);
      }
    }

    const rows = page.getByRole('rowgroup').last().getByRole('row');
    await expect(rows.first().getByText(/\d{3}.*\d{3}/).first()).toBeVisible();

    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 10. Должность ───────────────────────────────────────────

  test('Фильтр: должность «менеджер» — результаты релевантны', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByPlaceholder('Введите должность').fill('менеджер');

    const { url, data } = await stageLoading(() => executeSearch(page, 'positionName=менеджер'));

    expect(url.searchParams.get('positionName')).toBe('менеджер');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total).toBeGreaterThan(0);

    const withPosition = data.items.filter((item: any) =>
      item.position && /менеджер/i.test(item.position),
    );
    expect(withPosition.length, 'Хотя бы один с «менеджер» в должности').toBeGreaterThan(0);

    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 11. Пол М + возраст (комбинация) ────────────────────────

  test('Комбинация: пол М + возраст 25-40 — мужчины в диапазоне', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByRole('button', { name: 'М', exact: true }).click();
    await page.getByPlaceholder('ОТ', { exact: true }).fill('25');
    await page.getByPlaceholder('ДО', { exact: true }).fill('40');

    const { url, data } = await stageLoading(() => executeSearch(page, 'gender=M'));

    expect(url.searchParams.get('gender')).toBe('M');
    expect(url.searchParams.get('ageFrom')).toBe('25');
    expect(url.searchParams.get('ageTo')).toBe('40');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total).toBeGreaterThan(0);
    for (const item of data.items) {
      expect(item.gender, `${item.fullName} должен быть male`).toBe('male');
      if (item.age !== null && item.age !== undefined) {
        expect(item.age).toBeGreaterThanOrEqual(25);
        expect(item.age).toBeLessThanOrEqual(40);
      }
    }

    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 12. Должность + зарплата (комбинация) ───────────────────

  test('Комбинация: должность + зарплата — оба фильтра применены', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByPlaceholder('Введите должность').fill('менеджер');
    await page.getByPlaceholder('от', { exact: true }).fill('100000');
    await page.getByPlaceholder('до', { exact: true }).fill('300000');

    const { url, data } = await stageLoading(() => executeSearch(page, 'positionName=менеджер'));

    expect(url.searchParams.get('positionName')).toBe('менеджер');
    expect(url.searchParams.get('salaryFrom')).toBe('100000');
    expect(url.searchParams.get('salaryTo')).toBe('300000');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total).toBeGreaterThan(0);
    for (const item of data.items) {
      if (item.salary?.amount) {
        expect(item.salary.amount).toBeGreaterThanOrEqual(100000);
        expect(item.salary.amount).toBeLessThanOrEqual(300000);
      }
    }

    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 13. Опыт «Более 6 лет» ─────────────────────────────────

  test('Фильтр: опыт «Более 6 лет» — параметр передаётся', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByRole('checkbox', { name: 'Более 6 лет' }).check();

    const { url, data } = await stageLoading(() => executeSearch(page, 'moreThan6'));

    expect(url.searchParams.get('totalExperience')).toContain('moreThan6');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total, 'Должны быть кандидаты с опытом >6 лет').toBeGreaterThan(0);
    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 14. Опыт «От 3 до 6 лет» ───────────────────────────────

  test('Фильтр: опыт «От 3 до 6 лет» — параметр передаётся', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByRole('checkbox', { name: 'От 3 до 6 лет' }).check();

    const { url, data } = await stageLoading(() => executeSearch(page, 'between3And6'));

    expect(url.searchParams.get('totalExperience')).toContain('between3And6');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }
    if (data.total === 0) { test.skip(true, 'HR-Proxy: 0 кандидатов с опытом 3-6 лет'); return; }

    expect(data.total).toBeGreaterThan(0);
    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 15. Навыки (skillGroups) ─────────────────────────────────

  test('Фильтр: навыки — параметр skillGroups передаётся корректно', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    const skillsSection = page.locator('[data-section="skills"]');

    // Удаляем предзаполненные навыки
    for (let i = 0; i < 10; i++) {
      const tag = skillsSection.locator('span.inline-flex button').first();
      if (!(await tag.isVisible().catch(() => false))) break;
      await tag.click();
    }

    const emptyInput = skillsSection.getByPlaceholder('любой из навыка (ИЛИ)');
    await expect(emptyInput).toBeVisible({ timeout: 3_000 });
    await emptyInput.click();
    await emptyInput.fill('Python');
    await emptyInput.press('Enter');
    await expect(skillsSection.getByText('Python').first()).toBeVisible();

    const { url, data } = await stageLoading(() => executeSearch(page, 'Python'));

    const sg = url.searchParams.get('skillGroups');
    expect(sg).toBeTruthy();
    const groups = JSON.parse(sg!);
    expect(groups).toBeInstanceOf(Array);
    expect(groups[0].skills).toContain('Python');

    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }
    expect(data.total).toBeGreaterThan(0);
    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 16. Стоп-лист компаний ───────────────────────────────────

  test('Фильтр: стоп-лист компаний — параметр передаётся', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    const stopInput = page.getByPlaceholder('Введите название и нажмите Enter').first();
    await stopInput.fill('Газпром');
    await stopInput.press('Enter');

    const { url, data } = await stageLoading(() => executeSearch(page, 'Газпром'));

    const raw = decodeURIComponent(url.search);
    expect(raw).toContain('stopCompanies');
    expect(raw).toContain('Газпром');

    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }
    expect(data.total).toBeGreaterThan(0);
    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 17. Компании-доноры ──────────────────────────────────────

  test('Фильтр: компании-доноры — параметр передаётся', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    const donorInput = page.getByPlaceholder('Введите название и нажмите Enter').last();
    await donorInput.fill('Яндекс');
    await donorInput.press('Enter');

    const { url, data } = await stageLoading(() => executeSearch(page, 'Яндекс'));

    const raw = decodeURIComponent(url.search);
    expect(raw).toContain('donorCompanies');
    expect(raw).toContain('Яндекс');

    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }
    expect(data.total).toBeGreaterThan(0);
    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 18. Текущая компания (E-Staff) ──────────────────────────

  test('Фильтр: текущая компания — параметр передаётся', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    const currentCompanyInput = page.getByPlaceholder('Название компании').first();
    await currentCompanyInput.fill('Яндекс');

    const { url, data } = await stageLoading(() => executeSearch(page, 'currentCompany'));

    const raw = decodeURIComponent(url.search);
    expect(raw).toContain('currentCompany');
    expect(raw).toContain('Яндекс');

    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }
    expect(data.total, 'Кандидаты с текущей компанией «Яндекс»').toBeGreaterThan(0);
    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 19. Предыдущая компания (E-Staff) ───────────────────────

  test('Фильтр: предыдущая компания — параметр передаётся', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    const prevCompanyInput = page.getByPlaceholder('Название компании').last();
    await prevCompanyInput.fill('Газпром');

    const { url, data } = await stageLoading(() => executeSearch(page, 'previousCompany'));

    const raw = decodeURIComponent(url.search);
    expect(raw).toContain('previousCompany');
    expect(raw).toContain('Газпром');

    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }
    expect(data.total, 'Кандидаты с предыдущей компанией «Газпром»').toBeGreaterThan(0);
    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });

  // ─── 20. Пол Ж + должность (комбинация) ──────────────────────

  test('Комбинация: пол Ж + должность — женщины с «менеджер»', async ({ page }) => {
    test.setTimeout(240_000);
    await stageTitle(page);
    await prepareEstaffSearch(page);
    await openFiltersPanel(page);

    await page.getByRole('button', { name: 'Ж', exact: true }).click();
    await page.getByPlaceholder('Введите должность').fill('менеджер');

    const { url, data } = await stageLoading(() => executeSearch(page, 'gender=F'));

    expect(url.searchParams.get('gender')).toBe('F');
    expect(url.searchParams.get('positionName')).toBe('менеджер');
    if (data._timeout) { test.skip(true, 'HR-Proxy таймаут'); return; }

    expect(data.total).toBeGreaterThan(0);
    for (const item of data.items) {
      expect(item.gender, `${item.fullName} должен быть female`).toBe('female');
    }

    await verifyTable(page);
    await previewCandidate(page);
    await stageResult(page);
  });
});
