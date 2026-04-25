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


def _install_search_mocks(page: Page) -> _SearchMockStats:
    """Подключает моки на все поисковые эндпоинты SearchPage.

    Логика идентична TS-тесту: `search-with-relevance` (HH и E-Staff)
    возвращает N фейков по pageSize из тела запроса; `*hh/search`,
    `applicants?…` без relevance — пустой ответ; auth/hh/status —
    «authorized», чтобы не сорваться на error-экран.
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

    page.route("**/relevanter/api/hh/search**", _empty_response)
    page.route("**/relevanter/api/applicants?**", _empty_response)
    page.route("**/relevanter/api/hh/search-with-relevance**", _relevance_handler)
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
    authenticated_page.goto(
        base
        + "/recruiter/search?source=hh&limit=20&pageSize=20&page=1"
        + "&sortBy=relevance&includeNoAge=true&companyFilterMode=current"
        + "&excludeJumpers=false&filterByExpIndustry=false"
        + "&scoringEnabled=true&strictRegionSearch=false"
    )

    # Включаем фильтр релевантности «≥85%» — активирует search-with-relevance.
    authenticated_page.get_by_role("button", name="≥85%").click()

    # Дожидаемся появления первой строки таблицы — фейковый «Кандидат 1».
    expect(
        authenticated_page.get_by_text(re.compile(r"^Кандидат 1$"))
    ).to_be_visible(timeout=10_000)

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
        page, stats = search_page_with_mocks
        target_input = _target_count_input(page)
        before = stats.relevance_requests

        target_input.click()
        target_input.fill("10")
        target_input.press("Enter")

        expect(target_input).to_have_value("10")
        # Дожидаемся нового запроса на бэк (expect.poll нет в playwright-python,
        # поэтому крутим вручную в окне 5 секунд).
        import time
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and stats.relevance_requests <= before:
            time.sleep(0.05)
        assert stats.relevance_requests > before, (
            "После смены target count новый запрос на бэк не пришёл"
        )

        assert (stats.last_relevance_body or {}).get("pageSize") == 10
        assert (stats.last_relevance_body or {}).get("limit") is None

        # Нижний rowsPerPage остался 20.
        assert _read_rows_per_page(page) == 20
        # Таблица перерисовалась с 10 кандидатами.
        expect(page.get_by_text(re.compile(r"^Кандидат 10$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 11$"))).to_have_count(0)

    @allure.title(
        "TC-645.3: смена rowsPerPage → НЕ дёргает бэк, target count не меняется"
    )
    def test_rows_change_does_not_hit_backend(self, search_page_with_mocks):
        page, stats = search_page_with_mocks

        # Сначала переходим в состояние target=10 (как в TS-тесте), чтобы
        # последующая смена rows → 50 не оказалась случайно равной target.
        target_input = _target_count_input(page)
        target_input.click()
        target_input.fill("10")
        target_input.press("Enter")
        expect(target_input).to_have_value("10")
        # Ждём пока пришёл соответствующий запрос на бэк (pageSize=10).
        import time
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and (
            (stats.last_relevance_body or {}).get("pageSize") != 10
        ):
            time.sleep(0.05)

        before = stats.relevance_requests
        _select_rows_per_page(page, 50)

        # Стабильность 1.5с — бэк за это время не дёрнулся.
        final = _wait_no_new_requests(stats, window_ms=1500)
        assert final == before, (
            f"Клиентская смена rowsPerPage вызвала запрос на бэк "
            f"(было {before}, стало {final}) — регрессия TC-645"
        )

        assert _read_rows_per_page(page) == 50
        expect(target_input).to_have_value("10")

    @allure.title(
        "TC-645.4: клиентская пагинация в relevance-режиме "
        "(target=50, rowsPerPage=10 → 5 страниц)"
    )
    def test_client_side_pagination(self, search_page_with_mocks):
        page, stats = search_page_with_mocks

        # Перейдём в state: target=50, rowsPerPage=10 → 5 страниц.
        target_input = _target_count_input(page)
        target_input.click()
        target_input.fill("50")
        target_input.press("Enter")
        # Дожидаемся pageSize=50 в последнем запросе.
        import time
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and (
            (stats.last_relevance_body or {}).get("pageSize") != 50
        ):
            time.sleep(0.05)

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
        page, stats = search_page_with_mocks

        # Готовим state: target=50, rowsPerPage=10, на странице 2.
        target_input = _target_count_input(page)
        target_input.click()
        target_input.fill("50")
        target_input.press("Enter")
        import time
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and (
            (stats.last_relevance_body or {}).get("pageSize") != 50
        ):
            time.sleep(0.05)

        _select_rows_per_page(page, 10)
        page.get_by_role("button", name="2", exact=True).click()
        expect(page.get_by_text(re.compile(r"^Кандидат 11$"))).to_be_visible()

        # Теперь меняем target → 20: backend вернёт 20, rowsPerPage=10 →
        # 2 страницы, но клиент должен принудительно перейти на стр. 1.
        target_input.click()
        target_input.fill("20")
        target_input.press("Enter")
        expect(target_input).to_have_value("20")

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and (
            (stats.last_relevance_body or {}).get("pageSize") != 20
        ):
            time.sleep(0.05)
        assert (stats.last_relevance_body or {}).get("pageSize") == 20

        # На странице 1: кандидаты 1..10, нет 11.
        expect(page.get_by_text(re.compile(r"^Кандидат 10$"))).to_be_visible()
        expect(page.get_by_text(re.compile(r"^Кандидат 11$"))).to_have_count(0)
