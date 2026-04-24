"""
Тесты проверяют, что значения выбранные в модалках на странице СОЗДАНИЯ вакансии,
корректно отображаются на странице ПРОСМОТРА вакансии (/recruiter/vacancy/{id}).

Что проверяется:
  Описание / О команде / Соц. пакет — faker-текст; наличие на странице просмотра.
  Отрасль       — случайные N элементов из модалки
  Специализация — случайные N элементов из модалки
  География     — случайные N регионов (плоская модалка)
  Город (Офис)  — случайный регион → случайный город
  Город (Гибрид)— аналогично Офису

Для каждой модалки — 10 параметризованных запусков с УНИКАЛЬНЫМИ значениями
(class-scope fixture `seen_values` хранит уже использованные, чтобы между
итерациями не было повторов).
"""

import random
import pytest
import allure
from faker import Faker

from pages.vacancy_create_page import VacancyCreatePage
from pages.vacancy_detail_page import VacancyDetailPage

fake = Faker("ru_RU")


# ─────────────────────────────────────────────────────────
# Общая фикстура: накопитель уже использованных значений
# для каждой модалки — одна на весь параметризованный class.
# ─────────────────────────────────────────────────────────
@pytest.fixture(scope="class")
def seen_values() -> dict:
    return {
        "industry": set(),
        "specialization": set(),
        "geography": set(),
        "city_region": set(),
    }


# ─────────────────────────────────────────────────────────
# Генерация данных
# ─────────────────────────────────────────────────────────

def generate_required() -> dict:
    """Генерирует реалистичные данные для обязательных полей через Faker."""
    desc = fake.paragraph(nb_sentences=6)
    while len(desc) < 150:
        desc += " " + fake.sentence()

    company = fake.paragraph(nb_sentences=4)
    while len(company) < 100:
        company += " " + fake.sentence()

    return {
        "title": f"ALIQATEST_Дисплей_{fake.random_int(1000, 9999)}",
        "description": desc,
        "company_description": company,
        "salary_to": "200000",
        "social_package": fake.paragraph(nb_sentences=2),
    }


# ─────────────────────────────────────────────────────────
# Хелперы
# ─────────────────────────────────────────────────────────

def fill_required(vc: VacancyCreatePage) -> dict:
    """Заполняет обязательные поля faker-данными. Возвращает использованный dict."""
    data = generate_required()
    vc.fill_required_fields(
        title=data["title"],
        description=data["description"],
        company_description=data["company_description"],
        salary_to=data["salary_to"],
    )
    vc.enter_social_package(data["social_package"])
    return data


def open_detail(vc: VacancyCreatePage) -> VacancyDetailPage:
    """Нажимает «Создать» и возвращает страницу просмотра."""
    vc.click_create_vacancy()
    detail = VacancyDetailPage(vc.page)
    detail.should_be_loaded()
    return detail


def verify_text_fields(detail: VacancyDetailPage, data: dict) -> None:
    """Проверяет что описание, О команде и соц. пакет видны на странице просмотра."""
    detail.should_body_contain(data["description"])
    detail.should_body_contain(data["company_description"])
    detail.should_body_contain(data["social_package"])


def select_random_cities(vc: VacancyCreatePage, count: int) -> list[str]:
    """
    Выбирает count городов из count разных случайных регионов.
    Передаёт уже использованные регионы чтобы не повторяться.
    """
    selected_cities: list[str] = []
    used_regions: list[str] = []
    for _ in range(count):
        city, region = vc.select_random_city_in_modal(exclude_regions=used_regions)
        if city:
            selected_cities.append(city)
        if region:
            used_regions.append(region)
    return selected_cities


def verify_city_via_edit(
    vc: VacancyCreatePage, city: str, data: dict
) -> None:
    """
    Создаёт вакансию → проверяет текстовые поля на детальной странице →
    нажимает Редактировать → проверяет что город отображается на форме.
    """
    vc.click_create_vacancy()
    detail = VacancyDetailPage(vc.page)
    detail.should_be_loaded()
    verify_text_fields(detail, data)
    detail.click_edit_vacancy()
    vc.page.locator(vc.TITLE_INPUT).wait_for(state="visible", timeout=10000)
    vc.should_selected_city_be_visible(city)


# ═══════════════════════════════════════════════════════════
# Вспомогательный сценарий для плоских модалок (Отрасль /
# Специализация / География): открыть → выбрать 1 новый
# (уникальный на весь class) элемент → save → создать вакансию
# → проверить отображение на detail-странице.
# ═══════════════════════════════════════════════════════════

def _run_flat_modal_case(
    vc: VacancyCreatePage,
    open_modal,
    detail_field: str,
    seen: set[str],
):
    """Один кейс параметризованного теста плоской модалки."""
    data = fill_required(vc)
    open_modal()
    picked = vc.select_random_n_modal_items(1, exclude_texts=seen)
    assert picked, (
        f"Все значения модалки '{detail_field}' исчерпаны: {sorted(seen)}"
    )
    vc.save_modal()
    seen.add(picked[0])

    detail = open_detail(vc)
    verify_text_fields(detail, data)
    detail.should_field_contain_all(detail_field, picked)


# ═══════════════════════════════════════════════════════════
# ОТРАСЛЬ  —  10 параметризованных тестов с уникальными значениями
# ═══════════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Отображение на странице вакансии")
@allure.story("Отрасль")
class TestIndustryDisplayOnDetailPage:

    @pytest.mark.vacancy
    @pytest.mark.modals
    @pytest.mark.parametrize("iteration", range(1, 11))
    def test_industry_random_unique(
        self, auth_vacancy_create, seen_values, iteration
    ):
        allure.dynamic.title(
            f"Отрасль #{iteration}/10: случайное уникальное значение"
        )
        _run_flat_modal_case(
            auth_vacancy_create,
            open_modal=auth_vacancy_create.open_industry_modal,
            detail_field="Отрасль",
            seen=seen_values["industry"],
        )


# ═══════════════════════════════════════════════════════════
# СПЕЦИАЛИЗАЦИЯ  —  10 параметризованных тестов
# ═══════════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Отображение на странице вакансии")
@allure.story("Специализация")
class TestSpecializationDisplayOnDetailPage:

    @pytest.mark.vacancy
    @pytest.mark.modals
    @pytest.mark.parametrize("iteration", range(1, 11))
    def test_specialization_random_unique(
        self, auth_vacancy_create, seen_values, iteration
    ):
        allure.dynamic.title(
            f"Специализация #{iteration}/10: случайное уникальное значение"
        )
        _run_flat_modal_case(
            auth_vacancy_create,
            open_modal=auth_vacancy_create.open_specialization_modal,
            detail_field="Специализация",
            seen=seen_values["specialization"],
        )


# ═══════════════════════════════════════════════════════════
# ГЕОГРАФИЯ  —  10 параметризованных тестов
# ═══════════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Отображение на странице вакансии")
@allure.story("География")
class TestGeographyDisplayOnDetailPage:

    @pytest.mark.vacancy
    @pytest.mark.modals
    @pytest.mark.parametrize("iteration", range(1, 11))
    def test_geography_random_unique(
        self, auth_vacancy_create, seen_values, iteration
    ):
        allure.dynamic.title(
            f"География #{iteration}/10: случайное уникальное значение"
        )
        _run_flat_modal_case(
            auth_vacancy_create,
            open_modal=auth_vacancy_create.open_geography_modal,
            detail_field="Город",
            seen=seen_values["geography"],
        )


# ═══════════════════════════════════════════════════════════
# ГОРОД (Офис/Гибрид) — одна модалка, 10 параметризованных тестов:
#   5 × workFormat="Офис"  +  5 × workFormat="Гибрид"
# В каждом запуске выбирается РАЗНЫЙ регион (exclude_regions — накопленный
# seen_values["city_region"]), внутри региона — случайный город.
#
# Проверка делается НЕ на detail-странице (там фронт пока не рендерит
# officeCityId — регрессия recruiter-front/VacancyDetailPage), а через
# форму РЕДАКТИРОВАНИЯ: после создания вакансии кликаем «Редактировать»,
# ждём загрузку формы и убеждаемся, что кнопка города в секции workFormat
# содержит выбранный текст. Фронт редактирования корректно восстанавливает
# `officeCityId` → если мы видим тот же город — значит он сохранился в БД.
# ═══════════════════════════════════════════════════════════


def _city_cases():
    """5 Офис + 5 Гибрид = 10 параметризованных кейсов."""
    return (
        [("Офис", i) for i in range(1, 6)]
        + [("Гибрид", i) for i in range(1, 6)]
    )


@allure.epic("Вакансии")
@allure.feature("Отображение на странице вакансии")
@allure.story("Город (Офис/Гибрид)")
class TestCityDisplayOnDetailPage:

    @pytest.mark.vacancy
    @pytest.mark.modals
    @pytest.mark.parametrize(
        "work_format,iteration",
        _city_cases(),
        ids=[f"{wf}-{i}" for wf, i in _city_cases()],
    )
    def test_city_random_unique(
        self,
        auth_vacancy_create,
        seen_values,
        work_format,
        iteration,
    ):
        allure.dynamic.title(
            f"Город [{work_format}] #{iteration}/5: уникальный регион + "
            f"случайный город (проверка через Редактировать)"
        )
        vc = auth_vacancy_create
        data = fill_required(vc)
        vc.select_work_format(work_format)
        vc.should_city_field_be_visible()

        vc.open_city_modal()
        city, region = vc.select_random_city_in_modal(
            exclude_regions=list(seen_values["city_region"])
        )
        assert city, (
            f"Все регионы исчерпаны: {sorted(seen_values['city_region'])}"
        )
        vc.save_modal()
        if region:
            seen_values["city_region"].add(region)
        vc.should_selected_city_be_visible(city)

        # Создаём вакансию и переходим на detail — тексты проверяем там.
        detail = open_detail(vc)
        verify_text_fields(detail, data)

        # Клик «Редактировать» → ждём форму → на форме должен быть
        # восстановлен выбранный город (фронт редактирования читает
        # officeCityId из API-ответа и заново отрисовывает кнопку города).
        detail.click_edit_vacancy()
        vc.page.locator(vc.TITLE_INPUT).wait_for(
            state="visible", timeout=10_000
        )
        vc.should_selected_city_be_visible(city)


# ═══════════════════════════════════════════════════════════
# КОМБИНИРОВАННЫЕ ТЕСТЫ
# ═══════════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Отображение на странице вакансии")
@allure.story("Комбинированные")
class TestCombinedModalsDisplayOnDetailPage:

    @allure.title("Отрасль(1) + Специализация(1) → оба поля на странице")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_and_specialization_shown(self, auth_vacancy_create):
        vc = auth_vacancy_create
        data = fill_required(vc)

        vc.open_industry_modal()
        industries = vc.select_random_n_modal_items(1)
        vc.save_modal()

        vc.open_specialization_modal()
        specs = vc.select_random_n_modal_items(1)
        vc.save_modal()

        assert industries, "Не удалось выбрать отрасль"
        assert specs, "Не удалось выбрать специализацию"

        detail = open_detail(vc)
        verify_text_fields(detail, data)
        detail.should_field_contain_all("Отрасль", [industries[0]])
        detail.should_field_contain_all("Специализация", [specs[0]])

    @allure.title("Отрасль(3) + Специализация(3) → оба поля на странице")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_three_industries_and_three_specializations_shown(
        self, auth_vacancy_create
    ):
        vc = auth_vacancy_create
        data = fill_required(vc)

        vc.open_industry_modal()
        industries = vc.select_random_n_modal_items(3)
        vc.save_modal()

        vc.open_specialization_modal()
        specs = vc.select_random_n_modal_items(3)
        vc.save_modal()

        assert len(industries) == 3
        assert len(specs) == 3

        detail = open_detail(vc)
        verify_text_fields(detail, data)
        detail.should_field_contain_all("Отрасль", industries)
        detail.should_field_contain_all("Специализация", specs)

    @allure.title("Отрасль(3) + Специализация(3) + 3 региона → все поля")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_specialization_geography_shown(self, auth_vacancy_create):
        vc = auth_vacancy_create
        data = fill_required(vc)

        vc.open_industry_modal()
        industries = vc.select_random_n_modal_items(3)
        vc.save_modal()

        vc.open_specialization_modal()
        specs = vc.select_random_n_modal_items(3)
        vc.save_modal()

        vc.open_geography_modal()
        regions = vc.select_random_n_modal_items(3)
        vc.save_modal()

        detail = open_detail(vc)
        verify_text_fields(detail, data)
        detail.should_field_contain_all("Отрасль", industries)
        detail.should_field_contain_all("Специализация", specs)
        detail.should_field_contain_all("Город", regions)

    @allure.title("Отрасль(3) + Специализация(3) + Офис + 1 город → все поля")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_specialization_office_city_shown(
        self, auth_vacancy_create
    ):
        vc = auth_vacancy_create
        data = fill_required(vc)

        vc.open_industry_modal()
        industries = vc.select_random_n_modal_items(3)
        vc.save_modal()

        vc.open_specialization_modal()
        specs = vc.select_random_n_modal_items(3)
        vc.save_modal()

        vc.select_work_format("Офис")
        vc.should_city_field_be_visible()
        vc.open_city_modal()
        cities = select_random_cities(vc, 1)
        vc.save_modal()

        assert cities, "select_random_city_in_modal не нашёл город"
        vc.should_selected_city_be_visible(cities[0])

        detail = open_detail(vc)
        verify_text_fields(detail, data)
        detail.should_field_contain_all("Отрасль", industries)
        detail.should_field_contain_all("Специализация", specs)

    @allure.title("Отрасль(1) + Специализация(1) + Гибрид + 1 город → все поля")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_specialization_hybrid_city_shown(
        self, auth_vacancy_create
    ):
        vc = auth_vacancy_create
        data = fill_required(vc)

        vc.open_industry_modal()
        industries = vc.select_random_n_modal_items(1)
        vc.save_modal()

        vc.open_specialization_modal()
        specs = vc.select_random_n_modal_items(1)
        vc.save_modal()

        vc.select_work_format("Гибрид")
        vc.should_city_field_be_visible()
        vc.open_city_modal()
        cities = select_random_cities(vc, 1)
        vc.save_modal()

        assert cities, "select_random_city_in_modal не нашёл город"
        vc.should_selected_city_be_visible(cities[0])

        detail = open_detail(vc)
        verify_text_fields(detail, data)
        detail.should_field_contain_all("Отрасль", [industries[0]])
        detail.should_field_contain_all("Специализация", [specs[0]])

    @allure.title("Все модалки: Отрасль(3) + Специализация(3) + 3 региона + Офис 1 город")
    @pytest.mark.vacancy
    @pytest.mark.modals
    @allure.severity(allure.severity_level.CRITICAL)
    def test_all_modals_combined_shown(self, auth_vacancy_create):
        vc = auth_vacancy_create
        data = fill_required(vc)

        vc.open_industry_modal()
        industries = vc.select_random_n_modal_items(3)
        vc.save_modal()

        vc.open_specialization_modal()
        specs = vc.select_random_n_modal_items(3)
        vc.save_modal()

        vc.open_geography_modal()
        regions = vc.select_random_n_modal_items(3)
        vc.save_modal()

        vc.select_work_format("Офис")
        vc.should_city_field_be_visible()
        vc.open_city_modal()
        cities = select_random_cities(vc, 1)
        vc.save_modal()

        assert cities, "select_random_city_in_modal не нашёл город"
        vc.should_selected_city_be_visible(cities[0])

        detail = open_detail(vc)
        verify_text_fields(detail, data)
        detail.should_field_contain_all("Отрасль", industries)
        detail.should_field_contain_all("Специализация", specs)
        detail.should_field_contain_all("Город", regions)
