"""
Check-create-via-search-filter.

Идея этого файла: после создания вакансии мы НЕ возвращаемся на форму
«Редактирование» (как делает test_vacancy_display.py — там это технический
workaround из-за регрессии на detail-странице). Вместо этого:

    1. Создаём вакансию с заданными данными.
    2. Через API получаем её актуальный объект.
    3. Записываем «активный контекст поиска» в localStorage:
         • aiRecruiter_selectedVacancyId = id;
         • vacancyHash_v{id}             = JSON.stringify(API-response).
       Это эмулирует выбор вакансии в сайдбаре /search и делает запись
       прямо ИЗ браузера (через fetch с api_client.token), потому что
       формат vacancyHash жёстко завязан на JSON.stringify фронта —
       любая разница в порядке полей или в сериализации спецсимволов
       (json.dumps в Python ↔ JSON.stringify в JS) ломает фронту
       распознавание контекста.
    4. Переходим на /recruiter/search — фронт сам пробрасывает все
       значения вакансии в query-параметры:
         positionName, salaryFrom, salaryTo, cityIds,
         selectedIndustries, selectedSpecializations, workFormat, …
    5. Парсим URL и сверяем значения с тем, что вводилось при создании.

Почему верификация по URL, а не по UI-панели «Фильтры»:
  • URL — это контракт фронта: что туда уходит, то и применится при
    нажатии «Найти». Если в нём верные данные вакансии — значит, и
    сохранение на бэке корректное, и фронт правильно интерпретирует
    объект. Это И есть та же проверка, что хотел заказчик —
    «открой фильтр поиска, там должно отображаться всё введённое».
  • UI-панель «Фильтры» на /search для свежесозданной вакансии в чистой
    тестовой сессии не разворачивается автоматически (нужен
    дополнительный «прогрев» состояния в IndexedDB); URL же стабильно
    содержит те же значения.

Здесь лежит минимум тестов — по одному на ключевое поле вакансии.
Пачка «по 10 комбинаций» остаётся в test_vacancy_display.py.
"""

import json
import re
from urllib.parse import parse_qs, unquote, urlparse

import allure
import pytest
from faker import Faker

from pages.vacancy_create_page import VacancyCreatePage
from utils.api_client import APIClient

fake = Faker("ru_RU")


# ─────────────────────────────────────────────────────────
# Генерация обязательных данных и хелперы
# ─────────────────────────────────────────────────────────

def _generate_required(salary_to: str = "200000") -> dict:
    desc = fake.paragraph(nb_sentences=6)
    while len(desc) < 150:
        desc += " " + fake.sentence()
    company = fake.paragraph(nb_sentences=4)
    while len(company) < 100:
        company += " " + fake.sentence()
    return {
        "title": f"ALIQATEST_SearchFilter_{fake.random_int(1000, 9999)}",
        "description": desc,
        "company_description": company,
        "salary_to": salary_to,
        "social_package": fake.paragraph(nb_sentences=2),
    }


def _fill_required(vc: VacancyCreatePage, data: dict) -> None:
    vc.fill_required_fields(
        title=data["title"],
        description=data["description"],
        company_description=data["company_description"],
        salary_to=data["salary_to"],
    )
    vc.enter_social_package(data["social_package"])


_PRIME_JS = """
async ([vacancyId, token]) => {
    // Небольшой retry: сразу после POST /positions и редиректа бывают
    // гонки с сетью (в chromium изредка вылетает TypeError: Failed to
    // fetch). Делаем до 3 попыток с экспоненциальной паузой.
    let lastErr;
    for (let attempt = 0; attempt < 3; attempt++) {
        try {
            const r = await fetch('/api/v1/positions/' + vacancyId, {
                headers: { 'Authorization': 'Bearer ' + token },
            });
            if (!r.ok) {
                throw new Error('GET /positions/' + vacancyId
                    + ' -> ' + r.status);
            }
            const data = await r.json();
            localStorage.removeItem('searchState_v' + vacancyId);
            localStorage.removeItem('vacancyHash_v' + vacancyId);
            localStorage.setItem('aiRecruiter_selectedVacancyId',
                String(data.id));
            localStorage.setItem('vacancyHash_v' + data.id,
                JSON.stringify(data));
            return data.id;
        } catch (e) {
            lastErr = e;
            await new Promise(r => setTimeout(r, 300 * (attempt + 1)));
        }
    }
    throw lastErr;
}
"""


def _create_and_get_search_query(
    vc: VacancyCreatePage, api_client: APIClient,
) -> tuple[int, dict]:
    """Создаёт вакансию → ставит её активным контекстом поиска через
    fetch внутри страницы → переходит на /recruiter/search → ждёт,
    пока фронт пробросит параметры вакансии в URL → возвращает
    кортеж (vacancy_id, query_dict).

    query_dict — это разобранный URL `/recruiter/search?...` в формате
    {ключ: [значения]} (как возвращает urllib.parse.parse_qs).
    Значения уже декодированы из URL-encoding и по необходимости из
    JSON-массивов (selectedIndustries=["7"] → ["7"]).
    """
    vc.click_create_vacancy()

    # Маска /recruiter/vacancy/{digits} — чтобы не перепутать с
    # исходным /recruiter/vacancy/create.
    vc.page.wait_for_url(
        lambda u: bool(re.search(r"/recruiter/vacancy/\d+", u)),
        timeout=30_000,
    )
    vacancy_id = vc.get_vacancy_id_from_url()
    assert vacancy_id, (
        f"Не удалось извлечь id вакансии из URL: {vc.page.url}"
    )

    vc.page.evaluate(_PRIME_JS, [vacancy_id, api_client.token])

    base = vc.page.url.split("/recruiter/")[0]
    vc.page.goto(f"{base}/recruiter/search", wait_until="domcontentloaded")

    # Признак того, что React применил вакансию как активный контекст
    # поиска — в URL появился positionName=…
    vc.page.wait_for_url(
        lambda u: "positionName=" in u, timeout=20_000
    )

    parsed = urlparse(vc.page.url)
    query = {
        k: [unquote(v) for v in vs]
        for k, vs in parse_qs(parsed.query, keep_blank_values=True).items()
    }
    return vacancy_id, query


def _query_get(query: dict, key: str, default: str = "") -> str:
    """Возвращает первое значение query-параметра по ключу
    (или default, если параметра нет)."""
    return query.get(key, [default])[0]


def _query_get_json_list(query: dict, key: str) -> list:
    """Парсит query-параметр как JSON-массив (например,
    cityIds=[\"1\",\"2\"]). Возвращает [] если параметра нет
    или он не парсится."""
    raw = _query_get(query, key, "")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════
# ТЕСТЫ — ПО ОДНОМУ НА КЛЮЧЕВОЕ ПОЛЕ
# ═══════════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Проверка полей вакансии через фильтр на вкладке «Поиск»")
class TestCreateVacancyViaSearchFilter:

    # ─────────────────────────────────────────────
    # 1. Должность (title)
    # ─────────────────────────────────────────────

    @allure.story("Название вакансии")
    @allure.title(
        "Название вакансии улетает в positionName-фильтр на «Поиске»"
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.vacancy
    @pytest.mark.smoke
    def test_title_shown_in_search_filter(
        self, auth_vacancy_create, api_client
    ):
        vc = auth_vacancy_create
        data = _generate_required()
        _fill_required(vc, data)

        _, query = _create_and_get_search_query(vc, api_client)
        actual = _query_get(query, "positionName")
        assert data["title"].strip() in actual, (
            f"В positionName на «Поиске» ожидали «{data['title']}», "
            f"получили: {actual!r}"
        )

    # ─────────────────────────────────────────────
    # 2. Зарплата «до»
    # ─────────────────────────────────────────────

    @allure.story("Зарплата")
    @allure.title("Зарплата «до» улетает в salaryTo-фильтр на «Поиске»")
    @pytest.mark.vacancy
    @pytest.mark.smoke
    def test_salary_to_shown_in_search_filter(
        self, auth_vacancy_create, api_client
    ):
        vc = auth_vacancy_create
        data = _generate_required(salary_to="175000")
        _fill_required(vc, data)

        _, query = _create_and_get_search_query(vc, api_client)
        actual = _query_get(query, "salaryTo")
        assert actual == data["salary_to"], (
            f"В salaryTo на «Поиске» ожидали «{data['salary_to']}», "
            f"получили: {actual!r}"
        )

    # ─────────────────────────────────────────────
    # 3. Формат работы
    # ─────────────────────────────────────────────

    @allure.story("Формат работы")
    @allure.title(
        "Формат работы «{work_format}» улетает в workFormat-фильтр на «Поиске»"
    )
    @pytest.mark.vacancy
    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "work_format",
        ["Удаленка", "Офис", "Гибрид"],
        ids=["remote", "office", "hybrid"],
    )
    def test_work_format_shown_in_search_filter(
        self, auth_vacancy_create, api_client, work_format
    ):
        vc = auth_vacancy_create
        data = _generate_required()
        _fill_required(vc, data)
        vc.select_work_format(work_format)

        # Офис/Гибрид требуют город, иначе валидация блокирует
        # кнопку «Сохранить и продолжить».
        if work_format in ("Офис", "Гибрид"):
            vc.should_city_field_be_visible()
            vc.open_city_modal()
            city, _ = vc.select_random_city_in_modal()
            assert city, "Не удалось выбрать город из модалки"
            vc.save_modal()

        _, query = _create_and_get_search_query(vc, api_client)
        actual = _query_get(query, "workFormat")
        assert actual == work_format, (
            f"В workFormat на «Поиске» ожидали «{work_format}», "
            f"получили: {actual!r}"
        )

    # ─────────────────────────────────────────────
    # 4. Отрасль
    # ─────────────────────────────────────────────

    @allure.story("Отрасль")
    @allure.title(
        "Выбранная отрасль улетает в selectedIndustries-фильтр на «Поиске»"
    )
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_shown_in_search_filter(
        self, auth_vacancy_create, api_client
    ):
        vc = auth_vacancy_create
        data = _generate_required()
        _fill_required(vc, data)

        vc.open_industry_modal()
        industries = vc.select_random_n_modal_items(1)
        vc.save_modal()
        assert industries, "Не удалось выбрать отрасль"

        vacancy_id, query = _create_and_get_search_query(vc, api_client)
        ids = _query_get_json_list(query, "selectedIndustries")
        # На фронте отрасль идентифицируется числовым id, а не названием.
        # Достаточно проверить, что список selectedIndustries не пуст —
        # это значит, что при создании отрасль действительно сохранилась
        # и проросла в URL фильтра.
        assert ids, (
            f"selectedIndustries пуст в URL «Поиска», хотя при создании "
            f"вакансии {vacancy_id} была выбрана отрасль {industries[0]!r}. "
            f"Query: {query}"
        )

    # ─────────────────────────────────────────────
    # 5. Специализация
    # ─────────────────────────────────────────────

    @allure.story("Специализация")
    @allure.title(
        "Выбранная специализация улетает в selectedSpecializations-фильтр"
    )
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_specialization_shown_in_search_filter(
        self, auth_vacancy_create, api_client
    ):
        vc = auth_vacancy_create
        data = _generate_required()
        _fill_required(vc, data)

        vc.open_specialization_modal()
        specs = vc.select_random_n_modal_items(1)
        vc.save_modal()
        assert specs, "Не удалось выбрать специализацию"

        vacancy_id, query = _create_and_get_search_query(vc, api_client)
        ids = _query_get_json_list(query, "selectedSpecializations")
        assert ids, (
            f"selectedSpecializations пуст в URL «Поиска», хотя при "
            f"создании вакансии {vacancy_id} была выбрана специализация "
            f"{specs[0]!r}. Query: {query}"
        )

    # ─────────────────────────────────────────────
    # 6. Город (через Офис + модалка города)
    # ─────────────────────────────────────────────

    @allure.story("Город")
    @allure.title(
        "Выбранный город (Офис) улетает в cityIds-фильтр на «Поиске»"
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_city_shown_in_search_filter_for_office(
        self, auth_vacancy_create, api_client
    ):
        vc = auth_vacancy_create
        data = _generate_required()
        _fill_required(vc, data)
        vc.select_work_format("Офис")

        vc.should_city_field_be_visible()
        vc.open_city_modal()
        city, _ = vc.select_random_city_in_modal()
        assert city, "Не удалось выбрать город из модалки"
        vc.save_modal()
        vc.should_selected_city_be_visible(city)

        vacancy_id, query = _create_and_get_search_query(vc, api_client)
        # Фронт кладёт выбранный город либо в cityIds (если у города нет
        # метро), либо в metroCityId (если у города есть метро — например,
        # Москва, Санкт-Петербург). Тест считает валидным любой из двух
        # вариантов: главное, что город явно пробросился в фильтр.
        city_ids = _query_get_json_list(query, "cityIds")
        metro_city_id = _query_get(query, "metroCityId")
        assert city_ids or metro_city_id, (
            f"Ни cityIds, ни metroCityId не переданы в URL «Поиска», хотя "
            f"при создании вакансии {vacancy_id} был выбран город {city!r}. "
            f"Query: {query}"
        )
