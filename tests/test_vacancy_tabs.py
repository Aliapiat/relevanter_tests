"""
Тесты навигационных вкладок на странице вакансии.

Под «вкладками» понимается верхнее меню на карточке вакансии:
    Вакансия • Поиск • Диалоги • Собеседования • Итоги Подбора

Технически это пять <a href="/recruiter/..."> — атрибутов data-testid
у них нет, поэтому якоримся по href (см. VacancyDetailPage.NAV_TABS).

Стратегия тестов:
  1. test_all_vacancy_tabs_are_reachable — один сценарий, в котором
     последовательно кликаем каждую вкладку, ждём URL + якорь контента
     и проверяем что нужная POM успешно «загружается». Это даёт
     быстрый smoke на всю навигацию за одну созданную вакансию.
  2. test_reports_tab_has_filters — точечная проверка, что на вкладке
     «Итоги Подбора» действительно видны кнопки фильтров (All / AI /
     Live) и кнопка «Скачать отчет PDF». Это тест не столько на
     навигацию, сколько на базовое наполнение вкладки.
"""

import allure
import pytest
from faker import Faker

from pages.vacancy_create_page import VacancyCreatePage
from pages.vacancy_detail_page import VacancyDetailPage
from pages.search_page import SearchPage
from pages.dialogs_page import DialogsPage
from pages.interviews_page import InterviewsPage
from pages.reports_page import ReportsPage

fake = Faker("ru_RU")


# ─────────────────────────────────────────────────────────
# Мини-хелперы (скопированы из test_vacancy_links для
# единообразия; если однажды решим унифицировать — вынесем
# в tests/_helpers.py).
# ─────────────────────────────────────────────────────────

def _generate_required() -> dict:
    desc = fake.paragraph(nb_sentences=6)
    while len(desc) < 150:
        desc += " " + fake.sentence()
    company = fake.paragraph(nb_sentences=4)
    while len(company) < 100:
        company += " " + fake.sentence()
    return {
        "title": f"ALIQATEST_Tabs_{fake.random_int(1000, 9999)}",
        "description": desc,
        "company_description": company,
        "salary_to": "200000",
        "social_package": fake.paragraph(nb_sentences=2),
    }


def _fill_required(vc: VacancyCreatePage) -> None:
    data = _generate_required()
    vc.fill_required_fields(
        title=data["title"],
        description=data["description"],
        company_description=data["company_description"],
        salary_to=data["salary_to"],
    )
    vc.enter_social_package(data["social_package"])


def _create_and_open_detail(vc: VacancyCreatePage) -> VacancyDetailPage:
    _fill_required(vc)
    vc.click_create_vacancy()
    detail = VacancyDetailPage(vc.page)
    detail.should_be_loaded()
    return detail


# ═══════════════════════════════════════════════════════════
# ТЕСТЫ
# ═══════════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Навигационные вкладки на странице вакансии")
class TestVacancyNavigationTabs:

    @allure.story("Все вкладки кликаются и загружаются")
    @allure.title(
        "Переключение по всем 5 вкладкам: Вакансия → Поиск → Диалоги → "
        "Собеседования → Итоги Подбора"
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.vacancy
    @pytest.mark.smoke
    def test_all_vacancy_tabs_are_reachable(self, auth_vacancy_create):
        """Последовательно переключаем все пять табов и по каждому
        валидируем, что соответствующая POM-страница действительно
        загрузилась (URL + якорь контента).
        """
        detail = _create_and_open_detail(auth_vacancy_create)
        page = detail.page

        # ─── 1. Поиск ───
        with allure.step("Переход на «Поиск»"):
            detail.switch_nav_tab("search")
            SearchPage(page).should_be_loaded()

        # ─── 2. Диалоги ───
        with allure.step("Переход на «Диалоги»"):
            detail.switch_nav_tab("dialogs")
            DialogsPage(page).should_be_loaded()

        # ─── 3. Собеседования ───
        with allure.step("Переход на «Собеседования»"):
            detail.switch_nav_tab("interviews")
            InterviewsPage(page).should_be_loaded()

        # ─── 4. Итоги Подбора ───
        with allure.step("Переход на «Итоги Подбора»"):
            detail.switch_nav_tab("reports")
            ReportsPage(page).should_be_loaded()

        # ─── 5. Возврат на «Вакансия» ───
        with allure.step("Возврат на вкладку «Вакансия»"):
            detail.switch_nav_tab("vacancy")
            # Дополнительно убеждаемся что заголовок детальной
            # карточки снова видим.
            detail.should_be_loaded()

    # ─────────────────────────────────────────────
    # Точечная проверка содержимого вкладки «Итоги Подбора»:
    # здесь у нас сразу 4 видимых контрола (3 фильтра + PDF),
    # которые удобно пощупать через POM.
    # ─────────────────────────────────────────────

    @allure.story("Вкладка «Итоги Подбора»")
    @allure.title(
        "На вкладке «Итоги Подбора» видны фильтры All/AI/Live и кнопка PDF"
    )
    @pytest.mark.vacancy
    @pytest.mark.regression
    def test_reports_tab_has_filters(self, auth_vacancy_create):
        detail = _create_and_open_detail(auth_vacancy_create)
        detail.switch_nav_tab("reports")

        reports = ReportsPage(detail.page)
        reports.should_be_loaded()

        reports.should_be_visible(reports.FILTER_ALL)
        reports.should_be_visible(reports.FILTER_AI)
        reports.should_be_visible(reports.FILTER_LIVE)
        reports.should_be_visible(reports.DOWNLOAD_PDF_BUTTON)

    # ─────────────────────────────────────────────
    # Вкладка «Диалоги» — проверяем, что видны трёхколоночные
    # маркеры: поиск диалогов, заголовок пустого чата и блок
    # «Информация о кандидате».
    # ─────────────────────────────────────────────

    @allure.story("Вкладка «Диалоги»")
    @allure.title(
        "На вкладке «Диалоги» виден поиск, пустой чат и блок о кандидате"
    )
    @pytest.mark.vacancy
    @pytest.mark.regression
    def test_dialogs_tab_has_three_columns(self, auth_vacancy_create):
        detail = _create_and_open_detail(auth_vacancy_create)
        detail.switch_nav_tab("dialogs")

        dialogs = DialogsPage(detail.page)
        dialogs.should_be_loaded()

        dialogs.should_be_visible(dialogs.CONVERSATIONS_SEARCH_INPUT)
        dialogs.should_be_visible(dialogs.EMPTY_CHAT_TITLE)
        dialogs.should_be_visible(dialogs.CANDIDATE_INFO_TITLE)
