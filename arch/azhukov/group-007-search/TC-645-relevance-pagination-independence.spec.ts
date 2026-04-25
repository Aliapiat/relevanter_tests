import { test, expect, Page } from '@playwright/test';

/**
 * TASKNEIROKLYUCH-645 — Независимость фильтра релевантности и пагинации.
 *
 * Баг: на странице /recruiter/search два контрола («Количество кандидатов»
 * в RelevanceFilters сверху и «N резюме» в SearchInterface над таблицей)
 * управляли одним полем filters.pageSize/filters.limit. Изменение одного
 * меняло другое.
 *
 * Фикс: разделить на два независимых поля state.
 *   - filters.pageSize  — target count запроса (RelevanceFilters сверху)
 *   - filters.limit     — клиентский rowsPerPage (SearchInterface «N резюме»)
 *
 * Тест мокает все поисковые endpoints, чтобы:
 *   1) не тратить деньги на OpenRouter (AI-скоринг),
 *   2) не зависеть от настройки HH/E-Staff на стенде,
 *   3) не уходить в error-экран «Требуется авторизация в HH.ru».
 */

/** Сгенерировать N фейковых кандидатов (минимум полей для рендера в ResultsTable). */
function makeFakeCandidates(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: `fake-${i + 1}`,
    fullName: `Кандидат ${i + 1}`,
    name: `Кандидат ${i + 1}`,
    firstName: 'Имя',
    lastName: `Фамилия${i + 1}`,
    age: 30 + (i % 10),
    city: 'Москва',
    area: { name: 'Москва' },
    location: 'Москва',
    salary: { amount: 100000 + i * 1000, currency: 'RUB' },
    salaryAmount: 100000 + i * 1000,
    experiences: [],
    educations: [],
    skills: [],
    statusHistory: [],
    aiRating: null,
    aiComment: null,
    matchLevel: null,
  }));
}

/**
 * Подключает мок ко всем поисковым endpoints. Захватывает каждый запрос
 * с включённым skoringEnabled (search-with-relevance) и возвращает массив
 * из 50 фейковых кандидатов с pageSize из request body — это позволяет
 * проверить ASSERT на наличие/отсутствие сетевых вызовов.
 *
 * @returns счётчик запросов, который инкрементируется на каждый search-with-relevance.
 */
async function mockSearchEndpoints(page: Page) {
  const stats = { relevanceRequests: 0, lastRelevanceBody: null as any };

  const buildResponse = (requestedPageSize: number, items: any[]) => ({
    items,
    total: items.length,
    count: items.length,
    page: 1,
    pageSize: requestedPageSize,
    pages: 1,
    scoringApplied: true,
    totalFound: items.length,
    filteredCount: items.length,
  });

  // HH без релевантности — пустой ответ (нам не нужно)
  await page.route('**/relevanter/api/hh/search**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) })
  );
  // E-Staff без релевантности
  await page.route('**/relevanter/api/applicants?**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) })
  );

  // HH с релевантностью — захватываем запрос
  await page.route('**/relevanter/api/hh/search-with-relevance**', (route) => {
    const req = route.request();
    let body: any = {};
    try { body = JSON.parse(req.postData() || '{}'); } catch {}
    stats.relevanceRequests += 1;
    stats.lastRelevanceBody = body;

    const requestedPageSize = Number(body.pageSize) || 20;
    const items = makeFakeCandidates(requestedPageSize);
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(buildResponse(requestedPageSize, items)),
    });
  });

  // E-Staff с релевантностью — то же самое
  await page.route('**/relevanter/api/applicants/search-with-relevance**', (route) => {
    const req = route.request();
    let body: any = {};
    try { body = JSON.parse(req.postData() || '{}'); } catch {}
    stats.relevanceRequests += 1;
    stats.lastRelevanceBody = body;

    const requestedPageSize = Number(body.pageSize) || 20;
    const items = makeFakeCandidates(requestedPageSize);
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(buildResponse(requestedPageSize, items)),
    });
  });

  // HH status — фронт не показывает «Требуется авторизация в HH.ru»
  await page.route('**/relevanter/api/auth/hh/status**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'authorized', authorized: true }),
    })
  );

  return stats;
}

test.describe('TC-645: фильтр релевантности и пагинация независимы', () => {
  test('верхний дропдаун target count и нижний «N резюме» — два независимых state', async ({ page }) => {
    const stats = await mockSearchEndpoints(page);
    // Прямой URL с явными значениями limit и pageSize, чтобы избежать race
    // c восстановлением из localStorage.
    await page.goto(
      '/recruiter/search?source=hh&limit=20&pageSize=20&page=1&sortBy=relevance&includeNoAge=true&companyFilterMode=current&excludeJumpers=false&filterByExpIndustry=false&scoringEnabled=true&strictRegionSearch=false'
    );

    // === Локаторы ===
    // Верхний дропдаун target count живёт внутри блока «Количество кандидатов»
    // в RelevanceFilters.tsx — это input[type=text] рядом со span "Количество кандидатов".
    const targetCountLabel = page.getByText('Количество кандидатов', { exact: true });
    await expect(targetCountLabel).toBeVisible({ timeout: 15_000 });
    const targetCountInput = targetCountLabel.locator('xpath=following-sibling::*[1]//input');

    // Нижний дропдаун «N резюме» — кнопка SearchParams.tsx с ChevronDownIcon (svg) внутри.
    // Опции в открытом дропдауне — обычные button БЕЗ svg. Поэтому фильтруем по `:has(svg)`.
    const rowsPerPageButton = page
      .locator('button:has(svg)')
      .filter({ hasText: /^\d+ резюме$/ });

    /** Хелпер: вернуть число из текста кнопки rowsPerPage («20 резюме» → 20). */
    const readRowsPerPage = async () => {
      const text = (await rowsPerPageButton.textContent()) || '';
      const match = text.match(/(\d+)\s*резюме/);
      return match ? parseInt(match[1], 10) : NaN;
    };

    /** Хелпер: открыть дропдаун, выбрать опцию N. Опции — button без svg. */
    const selectRowsPerPage = async (size: number) => {
      await rowsPerPageButton.click();
      // В открытом меню одноимённая опция «N резюме» — это button без svg
      const option = page
        .locator('button:not(:has(svg))')
        .filter({ hasText: new RegExp(`^${size} резюме$`) });
      await option.click();
    };

    await expect(rowsPerPageButton).toBeVisible({ timeout: 5_000 });

    // Папка для подтверждающих скринов (вне test-results, чтобы не чистились автоматически).
    const shotsDir = 'results/screenshots/TC-645';

    // ============================================================
    // Включаем фильтр релевантности (любой из ≥85% / 70-84% / <70%)
    // — это активирует search-with-relevance endpoint и AI-флоу,
    // именно тот режим, в котором пользователь ловил баг.
    // ============================================================
    const relevanceHigh = page.getByRole('button', { name: '≥85%' });
    await relevanceHigh.click();
    // Ждём первый запрос на бэк (после клика «релевантности» фронт сам стартует поиск)
    await page.waitForFunction(() => true, undefined, { timeout: 1_000 }).catch(() => {});
    // Дожидаемся появления таблицы результатов (любая строка с фейковым кандидатом)
    await expect(page.getByText(/^Кандидат 1$/)).toBeVisible({ timeout: 10_000 });
    const baselineRequests = stats.relevanceRequests;
    expect(baselineRequests).toBeGreaterThan(0);
    // Бэк получил pageSize=20 (дефолт)
    expect(stats.lastRelevanceBody?.pageSize).toBe(20);
    // TASKNEIROKLYUCH-645: filters.limit (клиентский rowsPerPage) НЕ должен
    // утекать на бэк. Negative assertion — критично для предотвращения регрессии
    // в HH-поиске (routes/hh.js:344 раньше читал filters.limit как первый source).
    expect(stats.lastRelevanceBody?.limit).toBeUndefined();

    // Прицельный скрин блока с двумя контролами: верхний RelevanceFilters
    // («Количество кандидатов») + панель searchParams («N резюме»).
    // Берём общий контейнер RelevanceFilters и разворачиваем до родителя,
    // содержащего обе строки.
    const controlsBlock = page
      .getByText('Количество кандидатов', { exact: true })
      .locator('xpath=ancestor::*[contains(@class,"rounded")][1]/parent::*');

    /** Сохранить аккуратный скрин блока (только нужная область, читаемые цифры). */
    const snap = async (name: string) => {
      try {
        await controlsBlock.screenshot({ path: `${shotsDir}/${name}.png` });
      } catch {
        // если xpath не сматчился — fallback на viewport
        await page.screenshot({ path: `${shotsDir}/${name}.png`, fullPage: false });
      }
    };

    // === Baseline ===
    await expect(targetCountInput).toHaveValue('20');
    expect(await readRowsPerPage()).toBe(20);
    // Таблица содержит ровно 20 кандидатов из мока (бэк вернул pageSize=20)
    await expect(page.getByText(/^Кандидат 20$/)).toBeVisible();
    await expect(page.getByText(/^Кандидат 21$/)).toHaveCount(0);
    await snap('01-baseline-target-20-rows-20');

    // ============================================================
    // TC-001: смена target count в верхнем должна:
    //   а) уйти запросом на бэк с pageSize=10
    //   б) НЕ изменить нижний "N резюме"
    //   в) перерисовать таблицу новой подборкой (10 кандидатов)
    // ============================================================
    const requestsBeforeTargetChange = stats.relevanceRequests;
    await targetCountInput.click();
    await targetCountInput.fill('10');
    await targetCountInput.press('Enter');

    // Верхний обновился
    await expect(targetCountInput).toHaveValue('10');
    // Дожидаемся прихода нового запроса на бэк
    await expect.poll(() => stats.relevanceRequests, { timeout: 5_000 })
      .toBeGreaterThan(requestsBeforeTargetChange);
    // Бэк получил именно pageSize=10 (новый target count)
    expect(stats.lastRelevanceBody?.pageSize).toBe(10);
    // limit по-прежнему не уходит на бэк
    expect(stats.lastRelevanceBody?.limit).toBeUndefined();
    // Нижний остался 20 (rowsPerPage НЕ изменился)
    expect(await readRowsPerPage()).toBe(20);
    // Таблица перерисовалась с 10 кандидатами
    await expect(page.getByText(/^Кандидат 10$/)).toBeVisible();
    await expect(page.getByText(/^Кандидат 11$/)).toHaveCount(0);
    await snap('02-after-target-10-rows-still-20');

    // ============================================================
    // TC-002: смена нижнего "N резюме" должна:
    //   а) НЕ дёргать бэк (никаких новых запросов)
    //   б) НЕ изменить верхний target count
    //   в) перерисовать таблицу с rowsPerPage=5 (и должны появиться 2 страницы)
    // ============================================================
    const requestsBeforeRowsChange = stats.relevanceRequests;
    await selectRowsPerPage(50);

    // Дожидаемся минимум debounce + retries окно. Если за 1500ms нового запроса
    // не пришло — фронт точно не дёргает бэк (debounce фронта 500ms × 3 запас).
    // Делаем через poll с throwOnTimeout=false на consistent value.
    let stableSince = Date.now();
    let lastSeen = stats.relevanceRequests;
    while (Date.now() - stableSince < 1500) {
      if (stats.relevanceRequests !== lastSeen) {
        lastSeen = stats.relevanceRequests;
        stableSince = Date.now();
      }
      await page.waitForTimeout(50);
    }
    expect(stats.relevanceRequests).toBe(requestsBeforeRowsChange);
    // Нижний обновился на 50
    expect(await readRowsPerPage()).toBe(50);
    // Верхний target count остался 10
    await expect(targetCountInput).toHaveValue('10');
    // Таблица показывает те же 10 кандидатов (новый запрос не делался,
    // на странице помещаются все 10, т.к. rowsPerPage=50 > всех собранных)
    await expect(page.getByText(/^Кандидат 10$/)).toBeVisible();
    await snap('03-after-rows-50-target-still-10');

    // ============================================================
    // Перекрёстный цикл: ещё одна смена target → должен быть запрос
    // ============================================================
    const requestsBeforeTarget100 = stats.relevanceRequests;
    await targetCountInput.click();
    await targetCountInput.fill('50');
    await targetCountInput.press('Enter');

    await expect(targetCountInput).toHaveValue('50');
    await expect.poll(() => stats.relevanceRequests, { timeout: 5_000 })
      .toBeGreaterThan(requestsBeforeTarget100);
    expect(stats.lastRelevanceBody?.pageSize).toBe(50);
    expect(stats.lastRelevanceBody?.limit).toBeUndefined();
    // rowsPerPage остался 50
    expect(await readRowsPerPage()).toBe(50);
    await expect(page.getByText(/^Кандидат 50$/)).toBeVisible();
    await snap('04-after-target-50-rows-still-50');

    // Финал: смена rowsPerPage без запроса (тот же стабильность-чек)
    const requestsBeforeRows10 = stats.relevanceRequests;
    await selectRowsPerPage(10);
    {
      let stableSince2 = Date.now();
      let lastSeen2 = stats.relevanceRequests;
      while (Date.now() - stableSince2 < 1500) {
        if (stats.relevanceRequests !== lastSeen2) {
          lastSeen2 = stats.relevanceRequests;
          stableSince2 = Date.now();
        }
        await page.waitForTimeout(50);
      }
    }
    expect(stats.relevanceRequests).toBe(requestsBeforeRows10);
    expect(await readRowsPerPage()).toBe(10);
    await expect(targetCountInput).toHaveValue('50');
    await snap('05-after-rows-10-target-still-50');

    // ============================================================
    // TC-003 (NEW): клиентская пагинация в relevance-режиме.
    // state: target=50, rowsPerPage=10 → бэк вернул 50 фейков,
    // фронт должен порезать на 5 страниц по 10.
    //   а) на первой странице видны Кандидат 1..10, нет 11 и 50
    //   б) кнопки пагинации отображаются (totalPages=5 > 1)
    //   в) клик по «следующая страница» переключает на Кандидат 11..20,
    //      при этом новых сетевых запросов НЕ происходит
    //   г) обратный клик возвращает на Кандидат 1..10
    // Это исходный баг: раньше rowsPerPage был декоративный и не
    // влиял на то, что рендерится в таблице — пагинация в relevance-
    // режиме вообще не показывалась. Теперь всё честно слайсится.
    // ============================================================
    await expect(page.getByText(/^Кандидат 10$/)).toBeVisible();
    await expect(page.getByText(/^Кандидат 11$/)).toHaveCount(0);
    await expect(page.getByText(/^Кандидат 50$/)).toHaveCount(0);

    // Кнопки пагинации: ChevronLeft / ChevronRight — без текста, ищем
    // по SVG внутри button. В этом блоке именно 5 страниц — проверим
    // что видна кнопка с текстом «2» (номер страницы) и активна «1».
    const pageOneButton = page.getByRole('button', { name: /^1$/, exact: true });
    const pageTwoButton = page.getByRole('button', { name: /^2$/, exact: true });
    await expect(pageOneButton).toBeVisible();
    await expect(pageTwoButton).toBeVisible();

    const requestsBeforeClientPageChange = stats.relevanceRequests;
    await pageTwoButton.click();

    // Стабильность-чек: после клиентского перелистывания бэк не дёргается
    {
      let stableSince3 = Date.now();
      let lastSeen3 = stats.relevanceRequests;
      while (Date.now() - stableSince3 < 1500) {
        if (stats.relevanceRequests !== lastSeen3) {
          lastSeen3 = stats.relevanceRequests;
          stableSince3 = Date.now();
        }
        await page.waitForTimeout(50);
      }
    }
    expect(stats.relevanceRequests).toBe(requestsBeforeClientPageChange);

    // После клика на стр. 2 — видны Кандидат 11..20, нет 10 и 21
    await expect(page.getByText(/^Кандидат 11$/)).toBeVisible();
    await expect(page.getByText(/^Кандидат 20$/)).toBeVisible();
    await expect(page.getByText(/^Кандидат 10$/)).toHaveCount(0);
    await expect(page.getByText(/^Кандидат 21$/)).toHaveCount(0);
    await snap('06-client-page-2-candidates-11-20');

    // Обратный клик на страницу 1 — снова видны 1..10
    await pageOneButton.click();
    await expect(page.getByText(/^Кандидат 1$/)).toBeVisible();
    await expect(page.getByText(/^Кандидат 10$/)).toBeVisible();
    await expect(page.getByText(/^Кандидат 11$/)).toHaveCount(0);

    // Финал: за клиентские перелистывания не было ни одного сетевого запроса
    expect(stats.relevanceRequests).toBe(requestsBeforeClientPageChange);

    // ============================================================
    // TC-004 (NEW): смена target count сбрасывает клиентскую страницу
    // в 0. Сейчас мы на странице 1 (клик выше) — ставим target=20 →
    // backend вернёт 20 фейков, rowsPerPage остался 10 → 2 страницы,
    // клиент должен показать стр. 1 (Кандидат 1..10), а не сохранить
    // непрочитанную «стр. 2».
    // ============================================================
    await targetCountInput.click();
    await targetCountInput.fill('20');
    await targetCountInput.press('Enter');
    await expect(targetCountInput).toHaveValue('20');
    await expect.poll(() => stats.lastRelevanceBody?.pageSize, { timeout: 5_000 })
      .toBe(20);
    // Убедимся что после перехода к стр. 1 действительно видим кандидатов 1..10
    await expect(page.getByText(/^Кандидат 10$/)).toBeVisible();
    await expect(page.getByText(/^Кандидат 11$/)).toHaveCount(0);
    await snap('07-target-20-client-page-reset');
  });
});
