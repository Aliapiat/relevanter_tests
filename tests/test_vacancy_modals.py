import pytest
import allure

from pages.sidebar_page import SidebarPage
from pages.vacancy_create_page import VacancyCreatePage


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════

def generate_full_data() -> dict:
    return {
        "title": "ALIQATEST Модалки",
        "description": "А" * 150,
        "company_description": "А" * 100,
        "salary_to": "200000",
    }


# ═══════════════════════════════════════════════
# ОТРАСЛИ — UI
# ═══════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Модалка Отрасли")
@allure.story("UI")
class TestIndustryModalUI:

    @allure.title("Модалка отраслей открывается")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_modal_opens(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        assert auth_vacancy_create.is_modal_visible()

    @allure.title("Заголовок 'Отрасли' отображается")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_modal_title(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        title = auth_vacancy_create.page.locator(
            ".modal-container h2:has-text('Отрасли')"
        )
        assert title.is_visible()

    @allure.title("Поле поиска отраслей видно")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_search_visible(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        search = auth_vacancy_create.page.locator(
            ".modal-container input[placeholder='Поиск отраслей']"
        )
        assert search.is_visible()

    @allure.title("Кнопки Сохранить/Отменить/Сбросить видны")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_buttons_visible(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        page = auth_vacancy_create.page
        assert page.locator(
            ".modal-container button:has-text('Сохранить')"
        ).is_visible()
        assert page.locator(
            ".modal-container button:has-text('Отменить')"
        ).is_visible()
        assert page.locator(
            ".modal-container button:has-text('Сбросить')"
        ).is_visible()

    @allure.title("Список отраслей не пустой")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_list_not_empty(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()

        # Ждём появления хотя бы одного элемента списка
        auth_vacancy_create.page.locator(
            ".modal-container label"
        ).first.wait_for(state="visible", timeout=10000)

        items = auth_vacancy_create.page.locator(
            ".modal-container label"
        )
        count = items.count()
        assert count > 0, (
            f"Ожидали непустой список отраслей, получили {count} элементов"
        )

    @allure.title("Закрытие модалки крестиком")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_close_button(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        auth_vacancy_create.close_modal()
        assert not auth_vacancy_create.is_modal_visible()


# ═══════════════════════════════════════════════
# ОТРАСЛИ — ФУНКЦИОНАЛЬНЫЕ
# ═══════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Модалка Отрасли")
@allure.story("Функциональные")
class TestIndustryModalFunctional:

    @allure.title("Поиск фильтрует отрасли")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_search_filters(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        auth_vacancy_create.search_in_modal("Информационные")
        # Проверяем что среди видимых элементов есть нужный
        target = auth_vacancy_create.page.locator(
            ".modal-container label:has-text('Информационные'):visible"
        )
        assert target.count() >= 1
        assert "Информационные" in target.first.inner_text()

    @allure.title("Выбор отрасли — чекбокс отмечается")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_select_checkbox(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        auth_vacancy_create.search_in_modal("Информационные")
        auth_vacancy_create.select_modal_item(
            "Информационные технологии"
        )
        assert auth_vacancy_create.is_modal_item_checked(
            "Информационные технологии"
        )

    @allure.title("Сохранение отрасли — отображается на форме")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_save_shows_on_form(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        auth_vacancy_create.search_in_modal("Информационные")
        auth_vacancy_create.select_modal_item(
            "Информационные технологии"
        )
        auth_vacancy_create.save_modal()

        text = auth_vacancy_create.get_industry_button_text()
        assert "Информационные" in text

    @allure.title("Отмена — выбор не сохраняется")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_cancel_discards(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        auth_vacancy_create.search_in_modal("Информационные")
        auth_vacancy_create.select_modal_item(
            "Информационные технологии"
        )
        auth_vacancy_create.cancel_modal()

        text = auth_vacancy_create.get_industry_button_text()
        assert "Выберите отрасль" in text

    @allure.title("Сброс — снимает выбор")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_reset(self, auth_vacancy_create):
        auth_vacancy_create.open_industry_modal()
        auth_vacancy_create.select_modal_item(
            "Продукты питания"
        )
        auth_vacancy_create.reset_modal()
        assert not auth_vacancy_create.is_modal_item_checked(
            "Продукты питания"
        )


# ═══════════════════════════════════════════════
# СПЕЦИАЛИЗАЦИИ — UI + ФУНКЦИОНАЛЬНЫЕ
# ═══════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Модалка Специализации")
class TestSpecializationModal:

    @allure.title("Модалка специализаций открывается")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_specialization_modal_opens(self, auth_vacancy_create):
        auth_vacancy_create.open_specialization_modal()
        title = auth_vacancy_create.page.locator(
            ".modal-container h2:has-text('Специализации')"
        )
        assert title.is_visible()

    @allure.title("Поиск работает")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_specialization_search(self, auth_vacancy_create):
        auth_vacancy_create.open_specialization_modal()
        search = auth_vacancy_create.page.locator(
            ".modal-container input[placeholder='Поиск']"
        )
        search.fill("Информационные")
        auth_vacancy_create.page.locator(
            ".modal-container label:has-text('Информационные'):visible"
        ).first.wait_for(state="visible", timeout=5000)
        items = auth_vacancy_create.page.locator(
            ".modal-container label:visible"
        )
        assert items.count() >= 1

    @allure.title("Список специализаций не пустой")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_specialization_list_not_empty(
            self, auth_vacancy_create
    ):
        auth_vacancy_create.open_specialization_modal()

        # Ждём появления хотя бы одного элемента списка
        auth_vacancy_create.page.locator(
            ".modal-container label"
        ).first.wait_for(state="visible", timeout=10000)

        items = auth_vacancy_create.page.locator(
            ".modal-container label"
        )
        count = items.count()
        assert count > 10, (
            f"Ожидали более 10 специализаций, получили {count}"
        )

    @allure.title("Кнопки Сохранить/Отменить/Сбросить видны")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_specialization_buttons(self, auth_vacancy_create):
        auth_vacancy_create.open_specialization_modal()
        page = auth_vacancy_create.page
        assert page.locator(
            ".modal-container button:has-text('Сохранить')"
        ).is_visible()
        assert page.locator(
            ".modal-container button:has-text('Отменить')"
        ).is_visible()


# ═══════════════════════════════════════════════
# ГЕОГРАФИЯ — UI + ФУНКЦИОНАЛЬНЫЕ
# ═══════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Модалка География")
class TestGeographyModal:

    @allure.title("Модалка географии открывается")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_geography_modal_opens(self, auth_vacancy_create):
        auth_vacancy_create.open_geography_modal()
        title = auth_vacancy_create.page.locator(
            ".modal-container h2:has-text('География')"
        )
        assert title.is_visible()

    @allure.title("Кнопки стран видны (Россия, Казахстан...)")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_geography_country_buttons(self, auth_vacancy_create):
        auth_vacancy_create.open_geography_modal()
        page = auth_vacancy_create.page
        assert page.locator(
            ".modal-container button:has(span:has-text('Россия'))"
        ).is_visible()
        assert page.locator(
            ".modal-container button:has(span:has-text('Казахстан'))"
        ).is_visible()

    @allure.title("Россия выбрана по умолчанию")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_geography_russia_default(self, auth_vacancy_create):
        auth_vacancy_create.open_geography_modal()
        russia_btn = auth_vacancy_create.page.locator(
            ".modal-container "
            "button:has(span:has-text('Россия'))"
        )
        border = russia_btn.evaluate(
            "el => el.className"
        )
        assert "border-[#f97316]" in border

    @allure.title("Поиск регионов работает")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_geography_search(self, auth_vacancy_create):
        auth_vacancy_create.open_geography_modal()
        auth_vacancy_create.search_in_modal("Московская")
        target = auth_vacancy_create.page.locator(
            ".modal-container label:has-text('Московская область'):visible"
        )
        assert target.count() >= 1

    @allure.title("Выбор региона и сохранение")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_geography_select_and_save(self, auth_vacancy_create):
        auth_vacancy_create.open_geography_modal()
        auth_vacancy_create.page.locator(
            ".modal-container "
            "label:has-text('Московская область')"
        ).click()
        auth_vacancy_create.save_modal()

        btn_text = auth_vacancy_create.page.locator(
            "div[data-field-id='region'] "
            "button:has-text('Московская')"
        )
        assert btn_text.is_visible()

    @allure.title("Чекбокс 'Выбрать все' видим")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_geography_select_all_checkbox(self, auth_vacancy_create):
        auth_vacancy_create.open_geography_modal()
        # Ждём загрузки списка регионов внутри модалки
        auth_vacancy_create.page.locator(
            ".modal-container label"
        ).first.wait_for(state="visible", timeout=5000)
        select_all = auth_vacancy_create.page.locator(
            ".modal-container span:has-text('Выбрать все')"
        )
        select_all.wait_for(state="visible", timeout=5000)
        assert select_all.is_visible()


# ═══════════════════════════════════════════════
# ГРАЖДАНСТВО — UI + ФУНКЦИОНАЛЬНЫЕ
# ═══════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Модалка Гражданство")
class TestCitizenshipModal:

    @allure.title("Модалка гражданства открывается")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_citizenship_modal_opens(self, auth_vacancy_create):
        auth_vacancy_create.open_citizenship_modal()
        title = auth_vacancy_create.page.locator(
            ".bg-white.rounded-\\[24px\\] "
            "h3:has-text('Гражданство')"
        )
        assert title.is_visible()

    @allure.title("Поиск стран работает")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_citizenship_search(self, auth_vacancy_create):
        auth_vacancy_create.open_citizenship_modal()
        auth_vacancy_create.search_citizenship("Россия")
        items = auth_vacancy_create.page.locator(
            ".bg-white.rounded-\\[24px\\] "
            "button:has(span:has-text('Россия')):visible"
        )
        assert items.count() >= 1

    @allure.title("Выбор гражданства и применение")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_citizenship_select_and_apply(
        self, auth_vacancy_create
    ):
        auth_vacancy_create.open_citizenship_modal()
        auth_vacancy_create.select_citizenship("Россия")
        auth_vacancy_create.apply_citizenship()

        text = auth_vacancy_create.get_citizenship_button_text()
        assert "Россия" in text

    @allure.title("Список гражданства не пустой")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_citizenship_list_not_empty(self, auth_vacancy_create):
        auth_vacancy_create.open_citizenship_modal()

        # Ждём появления хотя бы одного элемента списка
        auth_vacancy_create.page.locator(
            ".bg-white.rounded-\\[24px\\] button:has(span)"
        ).first.wait_for(state="visible", timeout=10000)

        items = auth_vacancy_create.page.locator(
            ".bg-white.rounded-\\[24px\\] button:has(span)"
        )
        count = items.count()
        assert count > 0, (
            f"Ожидали непустой список гражданств, получили {count} элементов"
        )

    @allure.title("Кнопка Применить видна")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_citizenship_apply_button(self, auth_vacancy_create):
        auth_vacancy_create.open_citizenship_modal()
        assert auth_vacancy_create.page.locator(
            auth_vacancy_create.CITIZENSHIP_APPLY
        ).is_visible()


# ═══════════════════════════════════════════════
# ФОРМАТ РАБОТЫ — УСЛОВНЫЕ ПОЛЯ
# ═══════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Формат работы — условные поля")
class TestWorkFormatConditionalFields:

    @allure.title("Удаленка — поле 'Город' НЕ появляется")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_remote_no_city(self, auth_vacancy_create):
        auth_vacancy_create.select_work_format("Удаленка")
        auth_vacancy_create.page.locator(
            auth_vacancy_create.CITY_OPEN_BUTTON
        ).wait_for(state="hidden", timeout=5000)
        auth_vacancy_create.should_city_field_not_exist()

    @allure.title("value=Офис — поле 'Город' появляется")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_office_shows_city(self, auth_vacancy_create):
        auth_vacancy_create.select_work_format("value=Офис")
        auth_vacancy_create.should_city_field_be_visible()

    @allure.title("Гибрид — поле 'Город' появляется")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_hybrid_shows_city(self, auth_vacancy_create):
        auth_vacancy_create.select_work_format("Гибрид")
        auth_vacancy_create.should_city_field_be_visible()

    @allure.title(
        "value=Офис → Выбор города → Появляются Адрес и Метро"
    )
    @pytest.mark.vacancy
    @pytest.mark.modals
    # test_office_city_shows_address_metro
    def test_office_city_shows_address_metro(self, auth_vacancy_create):
        auth_vacancy_create.select_work_format("Офис")
        auth_vacancy_create.should_city_field_be_visible()

        auth_vacancy_create.open_city_modal()
        auth_vacancy_create.select_city_in_modal(
            city="Москва",
            region="Московская область"  # сначала раскроет регион
        )
        auth_vacancy_create.save_modal()
        auth_vacancy_create.should_address_field_be_visible()

    @allure.title("Кнопка '+ Добавить адрес или метро' добавляет поля")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_add_address_button(self, auth_vacancy_create):
        auth_vacancy_create.select_work_format("Офис")
        auth_vacancy_create.should_city_field_be_visible()

        auth_vacancy_create.open_city_modal()
        auth_vacancy_create.select_city_in_modal(
            city="Москва",
            region="Московская область"
        )
        auth_vacancy_create.save_modal()

        initial_count = auth_vacancy_create.get_address_count()
        auth_vacancy_create.click_add_address_or_metro()
        auth_vacancy_create.page.locator(
            auth_vacancy_create.ADDRESS_INPUT
        ).nth(initial_count).wait_for(state="visible", timeout=5000)
        new_count = auth_vacancy_create.get_address_count()
        assert new_count > initial_count


    @allure.title("Ввод адреса работает")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_enter_address(self, auth_vacancy_create):
        auth_vacancy_create.select_work_format("Офис")
        auth_vacancy_create.open_city_modal()
        auth_vacancy_create.select_city_in_modal(
            city="Москва",
            region="Московская область"
        )
        auth_vacancy_create.save_modal()

        auth_vacancy_create.enter_address("ул. Ленина, 1")
        value = auth_vacancy_create.page.locator(
            auth_vacancy_create.ADDRESS_INPUT
        ).first.input_value()
        assert value == "ул. Ленина, 1"


# ═══════════════════════════════════════════════
# E2E — СОЗДАНИЕ С МОДАЛКАМИ
# ═══════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("E2E — Создание с модалками")
class TestVacancyCreateWithModals:

    @allure.title(
        "Создание вакансии с отраслью и географией"
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_create_with_industry_and_geography(
        self, auth_vacancy_create
    ):
        data = generate_full_data()

        # Заполняем обязательные поля
        auth_vacancy_create.fill_required_fields(
            title=data["title"],
            description=data["description"],
            company_description=data["company_description"],
            salary_to=data["salary_to"],
        )

        # Выбираем отрасль
        auth_vacancy_create.open_industry_modal()
        auth_vacancy_create.select_modal_item("Продукты питания")
        auth_vacancy_create.save_modal()

        # Выбираем географию
        auth_vacancy_create.open_geography_modal()
        auth_vacancy_create.page.locator(
            ".modal-container "
            "label:has-text('Московская область')"
        ).click()
        auth_vacancy_create.save_modal()

        # Создаём
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar(data["title"])
        titles = sidebar.get_vacancy_titles()
        assert data["title"] in titles

    @allure.title("Создание вакансии с гражданством")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_create_with_citizenship(self, auth_vacancy_create):
        data = generate_full_data()
        data["title"] = "ALIQATEST Гражданство"

        auth_vacancy_create.fill_required_fields(
            title=data["title"],
            description=data["description"],
            company_description=data["company_description"],
            salary_to=data["salary_to"],
        )

        # Выбираем гражданство
        auth_vacancy_create.open_citizenship_modal()
        auth_vacancy_create.select_citizenship("Россия")
        auth_vacancy_create.apply_citizenship()

        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar(data["title"])
        titles = sidebar.get_vacancy_titles()
        assert data["title"] in titles

    @allure.title(
        "Создание вакансии: value=Офис + город + адрес"
    )
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_create_office_with_city_address(
        self, auth_vacancy_create
    ):
        data = generate_full_data()
        data["title"] = "ALIQATEST value=Офис+Город"

        auth_vacancy_create.fill_required_fields(
            title=data["title"],
            description=data["description"],
            company_description=data["company_description"],
            salary_to=data["salary_to"],
        )

        # Формат работы — value=Офис
        auth_vacancy_create.select_work_format("value=Офис")
        auth_vacancy_create.should_city_field_be_visible()

        # Выбираем город
        auth_vacancy_create.open_city_modal()
        auth_vacancy_create.select_city_in_modal(
            city="Москва",
            region="Московская область"
        )
        auth_vacancy_create.save_modal()

        # Вводим адрес
        auth_vacancy_create.enter_address(
            "ул. Тестовая, 42"
        )

        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar(data["title"])
        titles = sidebar.get_vacancy_titles()
        assert data["title"] in titles


# ═══════════════════════════════════════════════
# ОТОБРАЖЕНИЕ ВЫБРАННЫХ ЗНАЧЕНИЙ НА ФОРМЕ
# ═══════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Отображение выбранных значений модалок на форме")
class TestModalDisplayOnForm:
    """
    Проверяет, что значения, выбранные в модалках,
    корректно отображаются на странице создания вакансии.

    Для каждой модалки два сценария:
      • 3 конкретных значения — выбираем через поиск по имени
      • 1 общая категория   — берём первый видимый элемент без поиска
    Для «Город» — проверяем оба формата: Офис и Гибрид.
    """

    # ─── ОТРАСЛЬ ───────────────────────────────────────────────────

    @allure.title("Отрасль: 3 конкретных значения отображаются на форме")
    @allure.story("Отрасль")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_3_items_displayed(self, auth_vacancy_create):
        industries = [
            "Информационные технологии",
            "Продукты питания",
            "Строительство",
        ]
        vc = auth_vacancy_create
        vc.open_industry_modal()
        vc.select_modal_items(industries)
        vc.save_modal()

        field_text = vc.get_industry_field_text()
        for industry in industries:
            assert industry in field_text or industry.split()[0] in field_text, (
                f"'{industry}' не отображается в поле Отрасль. "
                f"Текст поля: {field_text!r}"
            )

    @allure.title(
        "Отрасль: 1 общая категория (без раскрытия) отображается на форме"
    )
    @allure.story("Отрасль")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_industry_1_general_displayed(self, auth_vacancy_create):
        """
        Детерминированный сценарий: открываем модалку отраслей, через
        поиск выбираем конкретную общую категорию и проверяем, что её
        имя появилось в поле формы.
        """
        vc = auth_vacancy_create
        vc.open_industry_modal()
        vc.search_in_modal("Продукты питания")
        vc.select_modal_item("Продукты питания")
        vc.save_modal()

        field_text = vc.get_industry_field_text()
        assert "Продукты" in field_text, (
            f"'Продукты питания' не отображается в поле Отрасль. "
            f"Текст поля: {field_text!r}"
        )

    # ─── СПЕЦИАЛИЗАЦИЯ ──────────────────────────────────────────────

    @allure.title("Специализация: 3 значения отображаются на форме")
    @allure.story("Специализация")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_specialization_3_items_displayed(self, auth_vacancy_create):
        vc = auth_vacancy_create
        vc.open_specialization_modal()
        selected = vc.select_first_n_modal_items(3)
        vc.save_modal()

        assert len(selected) == 3, (
            f"Ожидали выбрать 3 специализации, выбрано: {selected}"
        )
        field_text = vc.get_specialization_field_text()
        for spec in selected:
            first_word = spec.split()[0]
            assert first_word in field_text, (
                f"'{spec}' не отображается в поле Специализация. "
                f"Текст поля: {field_text!r}"
            )

    @allure.title(
        "Специализация: 1 общая (без раскрытия) отображается на форме"
    )
    @allure.story("Специализация")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_specialization_1_general_displayed(self, auth_vacancy_create):
        vc = auth_vacancy_create
        vc.open_specialization_modal()
        selected = vc.select_first_n_modal_items(1)
        vc.save_modal()

        assert selected, "Не удалось выбрать специализацию"
        field_text = vc.get_specialization_field_text()
        first_word = selected[0].split()[0]
        assert first_word in field_text, (
            f"'{selected[0]}' не отображается в поле Специализация. "
            f"Текст поля: {field_text!r}"
        )

    # ─── ГЕОГРАФИЯ ──────────────────────────────────────────────────

    @allure.title("География: 3 региона отображаются на форме")
    @allure.story("География")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_geography_3_items_displayed(self, auth_vacancy_create):
        regions = [
            "Московская область",
            "Свердловская область",
            "Новосибирская область",
        ]
        vc = auth_vacancy_create
        vc.open_geography_modal()
        vc.select_modal_items(regions)
        vc.save_modal()

        field_text = vc.get_geography_field_text()
        for region in regions:
            assert region in field_text or region.split()[0] in field_text, (
                f"'{region}' не отображается в поле География. "
                f"Текст поля: {field_text!r}"
            )

    @allure.title(
        "География: 1 общий регион (без раскрытия) отображается на форме"
    )
    @allure.story("География")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_geography_1_general_displayed(self, auth_vacancy_create):
        vc = auth_vacancy_create
        vc.open_geography_modal()
        selected = vc.select_first_n_modal_items(1)
        vc.save_modal()

        assert selected, "Не удалось выбрать регион в модалке Географии"
        field_text = vc.get_geography_field_text()
        first_word = selected[0].split()[0]
        assert first_word in field_text, (
            f"'{selected[0]}' не отображается в поле География. "
            f"Текст поля: {field_text!r}"
        )

    # ─── ГОРОД — ОФИС ───────────────────────────────────────────────

    @allure.title("Город: отображается на форме при формате 'Офис'")
    @allure.story("Город — Офис")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_city_displayed_when_office(self, auth_vacancy_create):
        vc = auth_vacancy_create
        vc.select_work_format("Офис")
        vc.should_city_field_be_visible()
        vc.open_city_modal()
        vc.select_city_in_modal(city="Москва", region="Московская область")
        vc.save_modal()

        field_text = vc.get_work_format_section_text()
        assert "Москва" in field_text, (
            f"'Москва' не отображается в секции Формат работы (Офис). "
            f"Текст секции: {field_text!r}"
        )

    # ─── ГОРОД — ГИБРИД ─────────────────────────────────────────────

    @allure.title("Город: отображается на форме при формате 'Гибрид'")
    @allure.story("Город — Гибрид")
    @pytest.mark.vacancy
    @pytest.mark.modals
    def test_city_displayed_when_hybrid(self, auth_vacancy_create):
        vc = auth_vacancy_create
        vc.select_work_format("Гибрид")
        vc.should_city_field_be_visible()
        vc.open_city_modal()
        vc.select_city_in_modal(city="Москва", region="Московская область")
        vc.save_modal()

        field_text = vc.get_work_format_section_text()
        assert "Москва" in field_text, (
            f"'Москва' не отображается в секции Формат работы (Гибрид). "
            f"Текст секции: {field_text!r}"
        )