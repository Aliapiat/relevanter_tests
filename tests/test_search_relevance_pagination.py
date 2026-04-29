"""
TC-645 (TASKNEIROKLYUCH-645): независимость фильтра релевантности и
пагинации в поиске кандидатов. Перенос
arch/azhukov/group-007-search/TC-645-relevance-pagination-independence.spec.ts.

Контекст бага:
    На странице /recruiter/search два контрола управляли одним полем
    state'а:
        1. «Количество кандидатов» в RelevanceFilters сверху —
           target-count для запроса на бэк.
        2. Дропдаун «N резюме» над таблицей — клиентский rowsPerPage.
    Изменение одного меняло другое; пагинация в режиме релевантности
    не работала.

Фикс:
    state.filters.pageSize  — target-count (на бэк).
    state.filters.limit     — клиентский rowsPerPage (только UI).

Тест мокает все поисковые эндпоинты, поэтому:
   а) не тратит OpenRouter-кредиты,
   б) не зависит от настройки HH/E-Staff на стенде,
   в) не уходит в error-экран «Требуется авторизация в HH.ru».

Архитектурно тест содержит несколько проверок (baseline → смена target →
смена rows → перекрёстная смена → клиентская пагинация → reset страницы),
каждая в своём pytest-тесте: TS-исходник был один большой test, у нас
разнесено по pytest-кейсам ради отчётности и -k фильтрации.
"""

import json
import re
from typing import Any

import pytest
import allure
from playwright.sync_api import Page, expect

from config.settings import settings


# ─── Хелперы мока ───────────────────────────────────────────────────────


def _make_fake_candidates(n: int) -> list[dict]:
    """N фейковых кандидатов с минимумом полей для рендера в ResultsTable."""
    return [
        {
            "id": f"fake-{i + 1}",
            "fullName": f"Кандидат {i + 1}",
            "name": f"Кандидат {i + 1}",
            "firstName": "Имя",
            "lastName": f"Фамилия{i + 1}",
            "age": 30 + (i % 10),
            "city": "Москва",
            "area": {"name": "Москва"},
            "location": "Москва",
            "salary": {"amount": 100_000 + i * 1000, "currency": "RUB"},
            "salaryAmount": 100_000 + i * 1000,
            "experiences": [],
            "educations": [],
            "skills": [],
            "statusHistory": [],
            "aiRating": None,
            "aiComment": None,
            "matchLevel": None,
        }
        for i in range(n)
    ]


def _build_response(requested_page_size: int, items: list[dict]) -> dict:
    return {
        "items": items,
        "total": len(items),
        "count": len(items),
        "page": 1,
        "pageSize": requested_page_size,
        "pages": 1,
        "scoringApplied": True,
        "totalFound": len(items),
        "filteredCount": len(items),
    }


class _SearchMockStats:
    """Состояние моков: счётчик запросов и тело последнего запроса.

    Используется тестом для проверки, был ли запрос на бэк (пагинация
    клиентская не должна дёргать сеть) и какие параметры в нём пришли
    (pageSize / limit).
    """

    def __init__(self) -> None:
        self.relevance_requests: int = 0
        self.last_relevance_body: dict[str, Any] | None = None
        self.bodies_history: list[dict[str, Any]] = []


def _install_search_mocks(page: Page) -> _SearchMockStats:
    """Подключает моки на все поисковые эндпоинты SearchPage.

    Логика идентична TS-тесту: `search-with-relevance` (HH и E-Staff)
    возвращает N фейков по pageSize из тела запроса; `*hh/search`,
    `applicants?…` без relevance — пустой ответ; auth/hh/status —
    «authorized», чтобы не сорваться на error-экран.

    URL-схема. В TS-исходнике dev-сервер был на localhost с REACT_APP_RELEVANTER_BASE_URL=http://localhost:3001/api,
    поэтому пути выглядели как `/relevanter/api/hh/...`. На нашем
    deploy (env.dev/qa/hr/prod) `REACT_APP_RELEVANTER_BASE_URL`
    указывает на `<host>/relevanter` БЕЗ префикса `/api`, поэтому
    реальные URL — `/relevanter/hh/...`. Чтобы тест работал и в
    локальной разработке (через `npm start`), и на dev/staging
    deploy'е, регистрируем оба варианта паттерна на каждый эндпоинт.
    """
    stats = _SearchMockStats()

    def _empty_response(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"items": [], "total": 0}),
        )

    def _relevance_handler(route):
        try:
            body = json.loads(route.request.post_data or "{}")
        except Exception:
            body = {}
        stats.relevance_requests += 1
        stats.last_relevance_body = body
        stats.bodies_history.append(body)

        requested_page_size = int(body.get("pageSize") or 20)
        items = _make_fake_candidates(requested_page_size)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(_build_response(requested_page_size, items)),
        )

    def _auth_status_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"status": "authorized", "authorized": True}),
        )

    # Deploy-вариант (без /api/), используется на dev/qa/hr/prod.
    page.route("**/relevanter/hh/search**", _empty_response)
    page.route("**/relevanter/applicants?**", _empty_response)
    page.route(
        "**/relevanter/hh/search-with-relevance**", _relevance_handler
    )
    page.route(
        "**/relevanter/applicants/search-with-relevance**",
        _relevance_handler,
    )
    page.route("**/relevanter/auth/hh/status**", _auth_status_handler)

    # Локальная разработка (REACT_APP_RELEVANTER_BASE_URL=…/api),
    # используется при `npm start` и в TS-исходнике из arch/.
    page.route("**/relevanter/api/hh/search**", _empty_response)
    page.route("**/relevanter/api/applicants?**", _empty_response)
    page.route(
        "**/relevanter/api/hh/search-with-relevance**", _relevance_handler
    )
    page.route(
        "**/relevanter/api/applicants/search-with-relevance**",
        _relevance_handler,
    )
    page.route("**/relevanter/api/auth/hh/status**", _auth_status_handler)

    return stats


def _wait_no_new_requests(stats: _SearchMockStats, window_ms: int = 1500) -> int:
    """Ждёт `window_ms` стабильности: счётчик запросов не должен
    меняться. Возвращает финальное значение счётчика.

    Используется чтобы убедиться, что чисто-клиентская смена
    rowsPerPage / переключение страницы пагинации не вызвало запрос
    на бэк (debounce фронта 500ms × 3 запас).
    """
    import time
    stable_since = time.monotonic()
    last_seen = stats.relevance_requests
    deadline = window_ms / 1000
    while time.monotonic() - stable_since < deadline:
        if stats.relevance_requests != last_seen:
            last_seen = stats.relevance_requests
            stable_since = time.monotonic()
        time.sleep(0.05)
    return stats.relevance_requests


# ─── Локаторы для двух контролов и пагинации ────────────────────────────


def _target_count_input(page: Page):
    """Верхний дропдаун «Количество кандидатов» — input в RelevanceFilters."""
    label = page.get_by_text("Количество кандидатов", exact=True)
    expect(label).to_be_visible(timeout=15_000)
    return label.locator("xpath=following-sibling::*[1]//input")


def _rows_per_page_button(page: Page):
    """Нижняя кнопка «N резюме» — button с svg, фильтруем по тексту."""
    return page.locator("button:has(svg)").filter(has_text=re.compile(r"^\d+ резюме$"))


def _read_rows_per_page(page: Page) -> int:
    text = _rows_per_page_button(page).text_content() or ""
    m = re.search(r"(\d+)\s*резюме", text)
    return int(m.group(1)) if m else -1


def _select_rows_per_page(page: Page, size: int):
    _rows_per_page_button(page).click()
    # Опции в открытом меню — button БЕЗ svg.
    option = page.locator("button:not(:has(svg))").filter(
        has_text=re.compile(rf"^{size} резюме$")
    )
    option.click()


# ─── Общие фикстуры для класса ──────────────────────────────────────────


@pytest.fixture
def search_page_with_mocks(authenticated_page: Page):
    """Открывает /recruiter/search с явными limit/pageSize и установленными
    моками. Возвращает (page, stats, baseline_requests).

    Прямой URL с query вместо клика «Поиск из источников» — чтобы
    избежать гонки восстановления state из localStorage.
    """
    stats = _install_search_mocks(authenticated_page)
    base = settings.BASE_URL.rstrip("/")

    # Сначала зайдём на корневой /recruiter, чтобы получить same-origin
    # доступ к localStorage. Без navigate() сюда `evaluate` упадёт на
    # about:blank.
    authenticated_page.goto(base + "/recruiter")

    # Чистим persisted-фильтры поиска. Recruiter-front сохраняет state
    # фильтров /recruiter/search в localStorage, поэтому при повторном
    # заходе query из URL может быть перекрыт восстановленным state'ом
    # с прошлых поисков (включая ручные «QA auto Specialist» того же
    # юзера на dev-стенде). Чистим всё, что начинается с relevant-
    # префиксов: relevanter*, search*, recruiterSearch*.
    authenticated_page.evaluate(
        """
        () => {
          const prefixes = ['relevanter', 'search', 'recruiterSearch', 'relevance'];
          const keys = Object.keys(localStorage);
          for (const k of keys) {
            if (prefixes.some(p => k.toLowerCase().startsWith(p.toLowerCase()))) {
              localStorage.removeItem(k);
            }
          }
        }
        """
    )

    authenticated_page.goto(
        base
        + "/recruiter/search?source=hh&limit=20&pageSize=20&page=1"
        + "&sortBy=relevance&includeNoAge=true&companyFilterMode=current"
        + "&excludeJumpers=false&filterByExpIndustry=false"
        + "&scoringEnabled=true&strictRegionSearch=false"
    )

    # Дожидаемся готовности RelevanceFilters — это сигнал, что страница
    # смонтирована и кнопка «≥85%» уже кликабельна. Без этого ожидания на
    # CI бывает гонка: goto завершился, но React ещё не отрисовал контролы,
    # и клик по «≥85%» уходит «в воздух» → запрос на бэк не уходит →
    # «Кандидат 1» не появляется → падает фикстура.
    expect(
        authenticated_page.get_by_text("Количество кандидатов", exact=True)
    ).to_be_visible(timeout=20_000)

    relevance_button = authenticated_page.get_by_role(
        "button", name="≥85%"
    )
    expect(relevance_button).to_be_visible(timeout=20_000)
    expect(relevance_button).to_be_enabled(timeout=20_000)
    relevance_button.click()

    # Дожидаемся появления первой строки таблицы — фейковый «Кандидат 1».
    # Таймаут увеличен с 10s до 30s: на CI цепочка
    # «click → WebSocket connect → POST search-with-relevance → render»
    # стабильно укладывается в 10s на dev, но бывает пограничной на CI.
    expect(
        authenticated_page.get_by_text(re.compile(r"^Кандидат 1$"))
    ).to_be_visible(timeout=30_000)

    return authenticated_page, stats


# ─── Тесты ──────────────────────────────────────────────────────────────


@allure.epic("Поиск кандидатов")
@allure.feature(
    "TC-645: независимость фильтра релевантности и клиентской пагинации"
)
@pytest.mark.relevance
@pytest.mark.search
@pytest.mark.regression
class TestRelevancePaginationIndependence:

    @allure.title(
        "TC-645.1: baseline — target=20, rowsPerPage=20, в таблице ровно 20 кандидатов"
    )
    def test_baseline(self, search_page_with_mocks):
        page, stats = search_page_with_mocks

        # Бэк получил pageSize=20 (дефолт URL).
        assert stats.relevance_requests > 0
        assert stats.last_relevance_body and stats.last_relevance_body.get("pageSize") == 20
        # filters.limit (rowsPerPage) НЕ должен утекать на бэк (TC-645).
        assert (stats.last_relevance_body or {}).get("limit") is None, (
            "filters.limit (клиентский rowsPerPage) утёк на бэк — регрессия TC-645"
        )

        target_input = _target_count_input(page)
        expect(target_input).to_have_value("20")
        assert _read_rows_per_page(page) == 20

        expect(page.get_by_text(re.compile(r"^Кандидат 20$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 21$"))).to_have_count(0)

    @allure.title(
        "TC-645.2: смена target count → запрос на бэк с новым pageSize, "
        "rowsPerPage не меняется"
    )
    def test_target_change_hits_backend_keeps_rows(
        self, search_page_with_mocks
    ):
        # Архитектура (RelevanterPage.tsx:1373-1398, filterUtils.ts:325-338):
        #   target count → setRelevancePageSize → setFilters → setTimeout(50ms)
        #   → handleSearch → POST search-with-relevance c pageSize=relevancePageSize.
        #   filters.limit (rowsPerPage) уходит в createApiQuery как `pageSize`,
        #   но в relevance-branch override'ится локальным relevancePageSize,
        #   поэтому в теле запроса фактически едет только target count, а
        #   `limit` как поле не сериализуется вовсе.
        page, stats = search_page_with_mocks
        target_input = _target_count_input(page)
        before = stats.relevance_requests

        # Клик по опции "10" в дропдауне — надёжнее fill+Enter (см. TC-645.4).
        target_input.click()
        target_label = page.get_by_text("Количество кандидатов", exact=True)
        target_dropdown_10 = target_label.locator(
            "xpath=following-sibling::*[1]"
        ).get_by_role("button", name="10", exact=True)
        expect(target_dropdown_10).to_be_visible(timeout=5_000)
        target_dropdown_10.click()
        expect(target_input).to_have_value("10", timeout=5_000)
        page.wait_for_timeout(300)

        # Дожидаемся нового запроса на бэк с pageSize=10. 15s — с запасом
        # на CI (debounce + WebSocket connect + бэк-ответ).
        import time
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline and (
            (stats.last_relevance_body or {}).get("pageSize") != 10
        ):
            time.sleep(0.05)
        # Стабилизация — гасим возможный поздний debounced auto-search.
        _wait_no_new_requests(stats, window_ms=1500)
        sizes = [b.get("pageSize") for b in stats.bodies_history]

        assert stats.relevance_requests > before, (
            f"После смены target count новый запрос на бэк не пришёл "
            f"(requests {before}->{stats.relevance_requests})"
        )
        assert (stats.last_relevance_body or {}).get("pageSize") == 10, (
            f"После target=10 на бэк не пришёл pageSize=10, "
            f"история pageSize всех {len(sizes)} запросов: {sizes}"
        )
        # filters.limit (rowsPerPage) НЕ должен утекать в тело запроса.
        assert (stats.last_relevance_body or {}).get("limit") is None, (
            "filters.limit утёк на бэк — регрессия TC-645"
        )

        # Нижний rowsPerPage остался 20 — target count и rowsPerPage независимы.
        assert _read_rows_per_page(page) == 20
        # Таблица перерисовалась с 10 кандидатами.
        expect(page.get_by_text(re.compile(r"^Кандидат 10$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 11$"))).to_have_count(0)

    @allure.title(
        "TC-645.3: смена rowsPerPage не меняет target count UI; "
        "если бэк дёргается, body.pageSize остаётся равным target count"
    )
    def test_rows_change_keeps_target_count(self, search_page_with_mocks):
        # Архитектурный контекст (RelevanterPage.tsx:1338-1347, 1400-1445,
        # filterUtils.ts:325-338):
        #   * filters.limit — единый источник rowsPerPage UI и бэкендного
        #     per_page (через createApiQuery → pageSize: filters.limit).
        #   * НО в relevance-branch handleSearch override'ит pageSize
        #     значением relevancePageSize (target count).
        #   * Смена rowsPerPage меняет filters → 500ms debounced
        #     auto-search → бэк дёргается, но body.pageSize всё равно =
        #     relevancePageSize, не новому filters.limit.
        # Поэтому актуальный TC-645.3-инвариант — независимость UI:
        # «N резюме» меняется, «Количество кандидатов» — нет; и если
        # бэк дёрнулся, его pageSize не уехал на rowsPerPage.
        page, stats = search_page_with_mocks

        # Сначала переходим в состояние target=10, чтобы последующая
        # смена rows → 50 не совпала случайно с target (иначе тест ничего
        # не проверяет).
        target_input = _target_count_input(page)
        target_input.click()
        target_label = page.get_by_text("Количество кандидатов", exact=True)
        target_dropdown_10 = target_label.locator(
            "xpath=following-sibling::*[1]"
        ).get_by_role("button", name="10", exact=True)
        expect(target_dropdown_10).to_be_visible(timeout=5_000)
        target_dropdown_10.click()
        expect(target_input).to_have_value("10", timeout=5_000)
        page.wait_for_timeout(300)

        # Ждём, пока пришёл запрос с pageSize=10 (значит relevancePageSize
        # синхронизировался с UI).
        import time
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline and (
            (stats.last_relevance_body or {}).get("pageSize") != 10
        ):
            time.sleep(0.05)
        _wait_no_new_requests(stats, window_ms=1500)
        assert (stats.last_relevance_body or {}).get("pageSize") == 10, (
            f"Перед сменой rows ожидался pageSize=10, "
            f"история: {[b.get('pageSize') for b in stats.bodies_history]}"
        )

        # Меняем rowsPerPage с 20 (URL-дефолт) на 50.
        _select_rows_per_page(page, 50)

        # Стабилизация: даём React'у завершить дебаунс auto-search'а
        # (500ms) + WebSocket + бэк.
        _wait_no_new_requests(stats, window_ms=2000)

        # Главный инвариант независимости: target count UI не меняется.
        expect(target_input).to_have_value("10")
        # Нижний rowsPerPage обновился.
        assert _read_rows_per_page(page) == 50

        # Если в окно 2с прилетел новый запрос (debounced auto-search на
        # filters.limit-смену) — у него body.pageSize должен оставаться
        # равным relevancePageSize=10, потому что в relevance-branch
        # pageSize override'ится локальным target count'ом, а не
        # rowsPerPage. Это и есть ключевой TC-645-инвариант: target
        # count и rowsPerPage не путают свои каналы на бэк.
        sizes = [b.get("pageSize") for b in stats.bodies_history]
        assert (stats.last_relevance_body or {}).get("pageSize") == 10, (
            f"После смены rowsPerPage=50 на бэк уехал pageSize={sizes[-1]} "
            f"вместо target count = 10 — регрессия TC-645 (filters.limit "
            f"перетёк в body.pageSize вместо relevancePageSize). "
            f"История pageSize: {sizes}"
        )
        # Поле `limit` не должно сериализоваться в тело — backend per_page
        # ездит через pageSize, не через limit.
        assert (stats.last_relevance_body or {}).get("limit") is None, (
            "filters.limit утёк на бэк как отдельное поле — регрессия TC-645"
        )

    @allure.title(
        "TC-645.4: клиентская пагинация в relevance-режиме "
        "(target=50, rowsPerPage=10 → 5 страниц)"
    )
    def test_client_side_pagination(self, search_page_with_mocks):
        page, stats = search_page_with_mocks

        # Перейдём в state: target=50, rowsPerPage=10 → 5 страниц.
        # Используем клик по опции "50" в дропдауне «Количество кандидатов»
        # вместо fill("50")+Enter: последний на текущем фронте не всегда
        # триггерит React-handler input'а (handleInputKeyDown), и
        # handleRelevancePageSizeChange не вызывается → запрос на бэк не
        # уходит. Клик по опции напрямую вызывает handlePageSizeSelect.
        target_input = _target_count_input(page)
        target_input.click()
        target_label = page.get_by_text("Количество кандидатов", exact=True)
        target_dropdown_50 = target_label.locator(
            "xpath=following-sibling::*[1]"
        ).get_by_role("button", name="50", exact=True)
        expect(target_dropdown_50).to_be_visible(timeout=5_000)
        target_dropdown_50.click()
        # Подтверждаем, что фронт принял новое значение в input —
        # это проверка, что handlePageSizeSelect действительно отработал
        # (он синхронно вызывает setInputValue("50")).
        expect(target_input).to_have_value("50", timeout=5_000)
        # Даём React'у обработать setRelevancePageSize → setFilters →
        # setTimeout(50ms) → handleSearch. Без этой паузы поллинг ниже
        # иногда стартует до того, как браузер успел дёрнуть бэк, и
        # 15-секундное окно пропадает зря — конкретный механизм гонки
        # внутри React/Playwright не выявлен, но 300ms стабилизирует.
        page.wait_for_timeout(300)
        # Дожидаемся pageSize=50 в последнем запросе. 15s — с запасом на CI
        # (setTimeout 50ms в handleRelevancePageSizeChange + WebSocket
        # connect + бэк-ответ).
        import time
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline and (
            (stats.last_relevance_body or {}).get("pageSize") != 50
        ):
            time.sleep(0.05)
        # Дополнительная стабилизация: ждём, пока перестанут лететь
        # новые запросы — иначе debounced auto-search может прийти после
        # нашего setTimeout и перетереть last_relevance_body.
        _wait_no_new_requests(stats, window_ms=1500)
        sizes = [b.get("pageSize") for b in stats.bodies_history]
        assert (stats.last_relevance_body or {}).get("pageSize") == 50, (
            f"После target=50 на бэк не пришёл pageSize=50, "
            f"история pageSize всех {len(sizes)} запросов: {sizes}, "
            f"последнее тело: {stats.last_relevance_body}"
        )

        _select_rows_per_page(page, 10)
        # Ждём, что таблица содержит ровно 10 кандидатов и не больше.
        expect(page.get_by_text(re.compile(r"^Кандидат 10$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 11$"))).to_have_count(0)
        expect(page.get_by_text(re.compile(r"^Кандидат 50$"))).to_have_count(0)

        # Кнопки пагинации: «1» (активна) и «2» — видимые.
        page_one = page.get_by_role("button", name="1", exact=True)
        page_two = page.get_by_role("button", name="2", exact=True)
        expect(page_one).to_be_visible()
        expect(page_two).to_be_visible()

        before = stats.relevance_requests
        page_two.click()

        # Клиентское переключение страницы НЕ дёргает бэк.
        final = _wait_no_new_requests(stats, window_ms=1500)
        assert final == before, (
            f"Клиентская пагинация дёрнула бэк (было {before}, стало {final})"
        )

        # На стр. 2 видны 11..20, нет 10 и 21.
        expect(page.get_by_text(re.compile(r"^Кандидат 11$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 20$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 10$"))).to_have_count(0)
        expect(page.get_by_text(re.compile(r"^Кандидат 21$"))).to_have_count(0)

        # Возврат на стр. 1.
        page_one.click()
        expect(page.get_by_text(re.compile(r"^Кандидат 1$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 10$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 11$"))).to_have_count(0)

        # За все клиентские перелистывания — ни одного нового сетевого
        # запроса.
        assert stats.relevance_requests == before, (
            "Клиентская пагинация после двух кликов вызвала сетевые запросы — TC-645"
        )

    @allure.title(
        "TC-645.5: смена target count сбрасывает клиентскую страницу в 1"
    )
    def test_target_change_resets_client_page(self, search_page_with_mocks):
        # Архитектурный контекст (RelevanterPage.tsx:1380-1397):
        #   handleRelevancePageSizeChange при смене target count делает
        #   setFilters({...filters, page: 1, pageSize: newSize}) — это
        #   и обеспечивает сброс клиентской страницы на 1. Тест проверяет
        #   именно эту цепочку.
        page, stats = search_page_with_mocks
        target_input = _target_count_input(page)
        target_label = page.get_by_text("Количество кандидатов", exact=True)

        def _click_target_option(value: int) -> None:
            """Клик по опции value в дропдауне «Количество кандидатов».

            Через клик дропдауна, а не fill+Enter, потому что последний
            на текущем фронте не всегда триггерит handleInputKeyDown
            (см. TC-645.4).
            """
            target_input.click()
            opt = target_label.locator(
                "xpath=following-sibling::*[1]"
            ).get_by_role("button", name=str(value), exact=True)
            expect(opt).to_be_visible(timeout=5_000)
            opt.click()
            expect(target_input).to_have_value(str(value), timeout=5_000)
            page.wait_for_timeout(300)

        # Готовим state: target=50, rowsPerPage=10, на странице 2.
        _click_target_option(50)
        import time
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline and (
            (stats.last_relevance_body or {}).get("pageSize") != 50
        ):
            time.sleep(0.05)
        _wait_no_new_requests(stats, window_ms=1500)
        assert (stats.last_relevance_body or {}).get("pageSize") == 50, (
            f"target=50 не доехал: история pageSize: "
            f"{[b.get('pageSize') for b in stats.bodies_history]}"
        )

        _select_rows_per_page(page, 10)
        # Дожидаемся стабилизации возможного debounced auto-search'а от
        # смены filters.limit, чтобы клик «2» не попал в момент ре-рендера.
        _wait_no_new_requests(stats, window_ms=1500)

        page.get_by_role("button", name="2", exact=True).click()
        expect(page.get_by_text(re.compile(r"^Кандидат 11$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 10$"))).to_have_count(0)

        # Меняем target → 20: backend вернёт 20, rowsPerPage=10 →
        # 2 страницы, и клиент должен принудительно перейти на стр. 1.
        _click_target_option(20)

        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline and (
            (stats.last_relevance_body or {}).get("pageSize") != 20
        ):
            time.sleep(0.05)
        _wait_no_new_requests(stats, window_ms=1500)
        sizes = [b.get("pageSize") for b in stats.bodies_history]
        assert (stats.last_relevance_body or {}).get("pageSize") == 20, (
            f"target=20 не доехал на бэк: история pageSize: {sizes}"
        )

        # Главный инвариант TC-645.5: после смены target count клиент
        # сидит на странице 1 — кандидаты 1..10, нет 11.
        expect(page.get_by_text(re.compile(r"^Кандидат 1$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 10$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 11$"))).to_have_count(0)
