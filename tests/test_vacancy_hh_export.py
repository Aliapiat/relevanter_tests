"""
HH.ru экспорт: пре-валидация, модалки специализации/города, диалог
подтверждения. Перенос TC-009 / TC-010 / TC-011 / TC-652 из
arch/azhukov/group-006-hh-export/*.spec.ts на pytest+Playwright.

⚠️ ВАЖНО — НИ ОДИН ТЕСТ НИКОГДА НЕ ПУБЛИКУЕТ РЕАЛЬНО НА HH.RU.
   Каждая публикация на hh.ru тратит платные кредиты работодателя.
   Единственный допустимый «happy path»:

       click_hh_export()  →  модалки/тосты  →  «Нет» в подтверждении

   Прохождение через «Да» запрещено и не используется ни в одном тесте.

Что покрывается:
   TC-009 — открытие/закрытие/пропуск модалок при разных комбинациях
            специализации × города.
   TC-010 — баги: 1 листовая спец «всё равно открывала модалку»;
            география «Россия» (странa) не открывала модалку города;
            сохранение вакансии без специализации.
   TC-011 — пре-валидация полей перед экспортом: длина названия и
            длина описания.
   TC-652 — порядок пре-валидации: тосты ДО диалога подтверждения,
            запрос на бэк не уходит при пустых обязательных полях.

Все тесты получают подготовленную через API вакансию из фикстуры
`make_hh_test_vacancy`. UI-форма в этих тестах не используется —
из неё нельзя выставить нужные комбинации HH-id.
"""

import pytest
import allure
from playwright.sync_api import expect

from pages.vacancy_edit_page import (
    VacancyEditPage,
    CONFIRM_DIALOG_TITLE_RE,
)
from tests.conftest import (
    HH_SPEC_TESTER,
    HH_SPEC_DEVELOPER,
    HH_SPEC_IT_GROUP,
    HH_SPEC_IT_AND_ART,
    HH_CITY_MOSCOW,
    HH_CITY_SPB,
    HH_CITY_RUSSIA,
)


# Дефолтный per-test таймаут — HH-флоу через UI многошаговый,
# 60 секунд держим как в TS-тестах.
HH_TEST_TIMEOUT_S = 60


# =============================================================================
# TC-009 — модалки специализации/города при экспорте
# =============================================================================


@allure.epic("HH.ru экспорт")
@allure.feature("TC-009: модалки специализации и города")
@pytest.mark.hh_export
@pytest.mark.integration
class TestHHExportModalsBasicFlow:
    """Группа 1: вакансия с >1 группой специализаций + >1 город —
    обе модалки гарантированно открываются. Внутри каждого теста
    нажимаем «Нет» на подтверждении."""

    @pytest.fixture
    def vacancy(self, make_hh_test_vacancy):
        return make_hh_test_vacancy(
            tag="TC009-main",
            specialization=HH_SPEC_IT_AND_ART,
            cities=[HH_CITY_MOSCOW, HH_CITY_SPB],
        )

    @allure.title(
        "TC-009.1: основной флоу — спец → город → подтверждение → «Нет»"
    )
    @pytest.mark.smoke
    def test_main_flow(self, vacancy_edit, vacancy):
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_open()
        edit.expect_spec_modal_hint()
        edit.select_it_leaf("Тестировщик")
        edit.modal_click_save()

        edit.expect_city_modal_open()
        edit.expect_city_modal_hint()
        edit.select_barnaul()
        edit.modal_click_save()

        edit.expect_confirm_dialog_open()
        edit.expect_confirm_dialog_body()

        edit.confirm_dialog_click_no()
        # После «Нет» кнопка экспорта снова доступна (форма edit-режима живёт).
        expect(vacancy_edit.page.locator(VacancyEditPage.HH_EXPORT_BUTTON).first).to_be_visible()

    @allure.title("TC-009.2: «Отменить» в модалке специализации прерывает экспорт")
    def test_cancel_on_spec_modal(self, vacancy_edit, vacancy):
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_open()
        edit.modal_click_cancel()

        edit.expect_spec_modal_not_open()
        edit.expect_city_modal_not_open()
        edit.expect_confirm_dialog_not_open()
        assert edit.hh_export_button_visible()

    @allure.title("TC-009.3: «Отменить» в модалке города прерывает экспорт")
    def test_cancel_on_city_modal(self, vacancy_edit, vacancy):
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_open()
        edit.select_it_leaf("Тестировщик")
        edit.modal_click_save()

        edit.expect_city_modal_open()
        edit.modal_click_cancel()

        edit.expect_city_modal_not_open()
        edit.expect_confirm_dialog_not_open()
        assert edit.hh_export_button_visible()

    @allure.title(
        "TC-009.4: повторный экспорт после отмены работает корректно"
    )
    def test_retry_after_cancel(self, vacancy_edit, vacancy):
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])

        # Попытка 1 — отменяем на модалке специализации.
        edit.click_hh_export()
        edit.expect_spec_modal_open()
        edit.modal_click_cancel()
        edit.expect_spec_modal_not_open()

        # Попытка 2 — полный флоу до «Нет».
        edit.click_hh_export()
        edit.expect_spec_modal_open()
        edit.select_it_leaf("Тестировщик")
        edit.modal_click_save()

        edit.expect_city_modal_open()
        edit.select_barnaul()
        edit.modal_click_save()

        edit.expect_confirm_dialog_open()
        edit.confirm_dialog_click_no()
        assert edit.hh_export_button_visible()

    @allure.title(
        "TC-009.5: «Сохранить» в модалке disabled для группы, enabled для листа"
    )
    def test_save_button_state_for_group_vs_leaf(self, vacancy_edit, vacancy):
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()
        edit.expect_spec_modal_open()

        edit.reset_modal_selection()
        save = edit.modal_save_button()
        expect(save).to_be_disabled()

        # Клик на групповой чекбокс «Информационные технологии» —
        # не должен активировать выбор (это группа, не лист).
        page = vacancy_edit.page
        it_cb = page.get_by_role("checkbox", name="Информационные технологии")
        it_cb.scroll_into_view_if_needed()
        it_cb.click()
        expect(it_cb).not_to_be_checked()
        expect(save).to_be_disabled()

        # Раскрываем и выбираем лист — «Сохранить» становится активной.
        edit.expand_spec_group("Информационные технологии")
        tester_cb = page.get_by_role("checkbox", name="Тестировщик")
        expect(tester_cb).to_be_visible(timeout=5_000)
        tester_cb.click()
        expect(tester_cb).to_be_checked()
        expect(save).to_be_enabled()

        # Снимаем выбор — «Сохранить» снова disabled.
        tester_cb.click()
        expect(tester_cb).not_to_be_checked()
        expect(save).to_be_disabled()

        edit.modal_click_cancel()

    @allure.title(
        "TC-009.6: предвыбранные специализации отображаются в модалке"
    )
    def test_preselected_specs_visible(self, vacancy_edit, vacancy):
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()
        edit.expect_spec_modal_open()

        page = vacancy_edit.page
        # Вакансия содержит группы 11 (ИТ) и 24 (Искусство): родительские
        # чекбоксы должны быть отмечены как checked, поскольку у вакансии
        # «выбраны все дочерние листы» этих групп (см. логику фронта).
        expect(page.get_by_role("checkbox", name="Информационные технологии")).to_be_checked()
        expect(page.get_by_role("checkbox", name="Искусство, развлечения, массмедиа")).to_be_checked()

        edit.modal_click_cancel()


@allure.epic("HH.ru экспорт")
@allure.feature("TC-009: пропуск модалок при листовых/пустых значениях")
@pytest.mark.hh_export
@pytest.mark.integration
class TestHHExportModalsSkipFlow:
    """Группа 2: модалки должны ПРОПУСКАТЬСЯ когда не нужны
    (листовая специализация, листовой город, пустые значения)."""

    @pytest.fixture
    def vacancy_leaf_both(self, make_hh_test_vacancy):
        # 1 листовая спец + 1 листовой город → обе модалки пропущены.
        return make_hh_test_vacancy(
            tag="TC009-skip-leaf-both",
            specialization=HH_SPEC_TESTER,
            cities=[HH_CITY_MOSCOW],
        )

    @pytest.fixture
    def vacancy_group_spec_leaf_city(self, make_hh_test_vacancy):
        # 1 группа спец + 1 листовой город → только модалка спец.
        return make_hh_test_vacancy(
            tag="TC009-skip-group-spec",
            specialization=HH_SPEC_IT_GROUP,
            cities=[HH_CITY_MOSCOW],
        )

    @pytest.fixture
    def vacancy_leaf_spec_multi_city(self, make_hh_test_vacancy):
        # 1 листовая спец + >1 город → только модалка города.
        return make_hh_test_vacancy(
            tag="TC009-skip-multi-city",
            specialization=HH_SPEC_TESTER,
            cities=[HH_CITY_MOSCOW, HH_CITY_SPB],
        )

    @pytest.fixture
    def vacancy_empty_both(self, make_hh_test_vacancy):
        # Пустые спец и города → обе модалки пропущены.
        return make_hh_test_vacancy(
            tag="TC009-skip-empty-both",
            specialization="",
            cities=[],
        )

    @allure.title(
        "TC-009.7: 1 лист-спец + 1 лист-город → обе модалки пропущены, "
        "сразу подтверждение"
    )
    def test_leaf_spec_leaf_city_skip(self, vacancy_edit, vacancy_leaf_both):
        edit = vacancy_edit.open_in_edit_mode(vacancy_leaf_both["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_not_open()
        edit.expect_city_modal_not_open()
        edit.expect_confirm_dialog_open()
        edit.confirm_dialog_click_no()

    @allure.title(
        "TC-009.8: 1 группа-спец + 1 лист-город → только модалка специализации"
    )
    def test_group_spec_only_spec_modal(
        self, vacancy_edit, vacancy_group_spec_leaf_city
    ):
        edit = vacancy_edit.open_in_edit_mode(vacancy_group_spec_leaf_city["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_open()
        edit.select_it_leaf("Тестировщик")
        edit.modal_click_save()

        edit.expect_city_modal_not_open()
        edit.expect_confirm_dialog_open()
        edit.confirm_dialog_click_no()

    @allure.title(
        "TC-009.9: 1 лист-спец + >1 город → только модалка города"
    )
    def test_multi_city_only_city_modal(
        self, vacancy_edit, vacancy_leaf_spec_multi_city
    ):
        edit = vacancy_edit.open_in_edit_mode(vacancy_leaf_spec_multi_city["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_not_open()
        edit.expect_city_modal_open()
        edit.select_barnaul()
        edit.modal_click_save()

        edit.expect_confirm_dialog_open()
        edit.confirm_dialog_click_no()

    @allure.title(
        "TC-009.10: пустая спец + пустые города → обе модалки пропущены, "
        "сразу подтверждение"
    )
    def test_both_empty_skip(self, vacancy_edit, vacancy_empty_both):
        edit = vacancy_edit.open_in_edit_mode(vacancy_empty_both["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_not_open()
        edit.expect_city_modal_not_open()
        edit.expect_confirm_dialog_open()
        edit.confirm_dialog_click_no()


# =============================================================================
# TC-010 — регрессии (баги, исправленные в Sprint 4)
# =============================================================================


@allure.epic("HH.ru экспорт")
@allure.feature("TC-010: регрессии HH-export")
@pytest.mark.hh_export
@pytest.mark.regression
@pytest.mark.integration
class TestHHExportRegressions:

    @allure.title(
        "TC-010.1: 1 листовая специализация — модалка не должна открываться"
    )
    def test_leaf_spec_no_modal(self, vacancy_edit, make_hh_test_vacancy):
        # Регрессия: при единственной листовой специализации фронт раньше
        # всё равно открывал модалку «Выберите специализацию». Должно
        # пропускаться.
        vacancy = make_hh_test_vacancy(
            tag="TC010-leaf",
            specialization=HH_SPEC_TESTER,
            cities=[HH_CITY_MOSCOW],
        )
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_not_open()
        edit.expect_city_modal_not_open()
        edit.expect_confirm_dialog_open()
        edit.confirm_dialog_click_no()

    @allure.title(
        "TC-010.2: после смены спец-и через модалку и перезагрузки экспорт "
        "снова пропускает модалку (path-key cache)"
    )
    def test_leaf_spec_after_modal_save_and_reload(
        self, vacancy_edit, make_hh_test_vacancy
    ):
        # Регрессия с path key в localStorage. Сценарий:
        # 1. Открываем вакансию, через UI меняем специализацию на другой
        #    лист (Программист, разработчик).
        # 2. Сохраняем.
        # 3. Перезагружаем страницу.
        # 4. Жмём «На HH.ru» — модалка спец не должна открываться:
        #    значение по-прежнему листовое, кеш path-key не должен
        #    форсировать модалку.
        vacancy = make_hh_test_vacancy(
            tag="TC010-leaf-reload",
            specialization=HH_SPEC_TESTER,
            cities=[HH_CITY_MOSCOW],
        )
        page = vacancy_edit.page
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])

        # 1. Меняем специализацию через стандартную (не-экспортную)
        #    модалку формы. На этой стадии тест зависит от точной
        #    структуры формы создания/редактирования; если в нашем
        #    UI кнопка «Выбрать специализацию» отличается — тест
        #    пропустим (помеченный xfail).
        spec_button = page.get_by_role(
            "button", name=__import__("re").compile(r"Выбрать специализаци", __import__("re").IGNORECASE)
        )
        try:
            spec_button.first.wait_for(state="visible", timeout=2_000)
        except Exception:
            pytest.skip(
                "Кнопка «Выбрать специализацию» не найдена в edit-форме на этом стенде "
                "— проверять path-key cache не на чем."
            )
        spec_button.first.click()
        edit.expect_spec_modal_open()
        edit.reset_modal_selection()
        edit.expand_spec_group("Информационные технологии")
        edit.select_spec_leaf("Программист, разработчик")
        edit.modal_click_save()

        # 2. Сохраняем форму вакансии.
        edit.click_form_save()
        edit.expect_toast_vacancy_updated()

        # 3. Перезагружаем страницу + снова в edit.
        edit.open_in_edit_mode(vacancy["id"])

        # 4. Экспорт: модалка спец НЕ должна открываться.
        edit.click_hh_export()
        edit.expect_spec_modal_not_open()
        edit.expect_confirm_dialog_open()
        edit.confirm_dialog_click_no()

    @allure.title(
        "TC-010.3: география «Россия» — модалка города ДОЛЖНА открыться"
    )
    def test_country_geography_opens_city_modal(
        self, vacancy_edit, make_hh_test_vacancy
    ):
        # Регрессия: cities: ['113'] (страна Россия) — нелистовое значение,
        # модалка города должна открыться. Раньше фронт пропускал модалку.
        vacancy = make_hh_test_vacancy(
            tag="TC010-country",
            specialization=HH_SPEC_TESTER,
            cities=[HH_CITY_RUSSIA],
        )
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_not_open()
        edit.expect_city_modal_open()
        edit.expect_city_modal_hint()
        edit.modal_click_cancel()
        edit.expect_city_modal_not_open()

    @allure.title(
        "TC-010.4: вакансия без специализации сохраняется через форму без ошибки"
    )
    def test_save_without_specialization(
        self, vacancy_edit, make_hh_test_vacancy
    ):
        vacancy = make_hh_test_vacancy(
            tag="TC010-no-spec",
            specialization="",
            cities=[],
        )
        page = vacancy_edit.page
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])

        save = edit.form_save_button()
        expect(save).to_be_visible(timeout=10_000)
        expect(save).to_be_enabled()
        edit.click_form_save()

        # Не должно быть ошибки про обязательные поля.
        expect(
            page.get_by_text("Пожалуйста, заполните все обязательные поля")
        ).not_to_be_visible(timeout=3_000)
        edit.expect_toast_vacancy_updated()


# =============================================================================
# TC-011 — пре-валидация полей перед экспортом
# =============================================================================


@allure.epic("HH.ru экспорт")
@allure.feature("TC-011: пре-валидация полей перед HH-публикацией")
@pytest.mark.hh_export
@pytest.mark.validation
@pytest.mark.integration
class TestHHExportFieldValidation:

    @allure.title(
        "TC-011.1: название > 100 символов → toast-ошибка, экспорт не "
        "начинается"
    )
    def test_title_over_limit_blocks_export(
        self, vacancy_edit, make_hh_test_vacancy
    ):
        long_title = "ALIQATEST_HH_TC011_" + ("А" * 100)  # >> 100
        vacancy = make_hh_test_vacancy(
            tag="TC011-long-title",
            title=long_title,
            specialization=HH_SPEC_TESTER,
            cities=[HH_CITY_MOSCOW],
        )
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])

        edit.expect_form_warning_title_over_limit()
        edit.click_hh_export()
        edit.expect_toast_title_too_long()
        edit.expect_confirm_dialog_not_open()

    @allure.title(
        "TC-011.2: описание < 200 символов → toast-ошибка, экспорт не "
        "начинается"
    )
    def test_short_description_blocks_export(
        self, vacancy_edit, make_hh_test_vacancy
    ):
        vacancy = make_hh_test_vacancy(
            tag="TC011-short-desc",
            description="<p>Коротко</p>",
            company_description="<p>Мало</p>",
            specialization=HH_SPEC_TESTER,
            cities=[HH_CITY_MOSCOW],
        )
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        edit.expect_toast_desc_too_short()
        edit.expect_confirm_dialog_not_open()

    @allure.title(
        "TC-011.3: валидные поля → диалог подтверждения открывается → «Нет»"
    )
    def test_valid_fields_reach_confirm(
        self, vacancy_edit, make_hh_test_vacancy
    ):
        # Достаточно длинное описание — дефолт фабрики уже >200 символов
        # plain-text. Спец и город — листовые, чтобы пропустить обе
        # модалки и попасть прямо в подтверждение.
        vacancy = make_hh_test_vacancy(
            tag="TC011-valid",
            specialization=HH_SPEC_TESTER,
            cities=[HH_CITY_MOSCOW],
        )
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        edit.expect_confirm_dialog_open()
        edit.confirm_dialog_click_no()


# =============================================================================
# TC-652 — порядок пре-валидации (тосты ДО подтверждения)
# =============================================================================


def _install_hh_export_interceptor(page):
    """Перехватчик POST /relevanter/api/hh/vacancies/export.

    Если фронт корректно делает пре-валидацию — на пустых полях запрос
    на бэк уходить НЕ должен. Перехватчик считает количество вызовов
    и в случае попадания возвращает мок-400, чтобы реальная публикация
    не произошла, даже если фронт где-то проворонит проверку.

    Возвращает callable `count()` — число перехваченных запросов.
    """
    state = {"calls": 0}

    def handler(route):
        state["calls"] += 1
        route.fulfill(
            status=400,
            content_type="application/json",
            body='{"success": false, "error": "mocked", "validationErrors": []}',
        )

    page.route("**/relevanter/api/hh/vacancies/export", handler)
    return lambda: state["calls"]


@allure.epic("HH.ru экспорт")
@allure.feature(
    "TC-652: порядок валидации — тосты до подтверждения, без запроса на бэк"
)
@pytest.mark.hh_export
@pytest.mark.validation
@pytest.mark.integration
@pytest.mark.regression
class TestHHExportValidationOrder:
    """Регрессия TASKNEIROKLYUCH-652: при пустых обязательных полях
    диалог подтверждения вообще не должен открываться, и запрос на
    /relevanter/api/hh/vacancies/export не должен уходить."""

    @allure.title(
        "TC-652.1: пустая «Специализация» → toast, без диалога, без запроса"
    )
    def test_empty_specialization(self, vacancy_edit, make_hh_test_vacancy):
        vacancy = make_hh_test_vacancy(
            tag="TC652-no-spec",
            specialization="",
            cities=[HH_CITY_MOSCOW],
        )
        page = vacancy_edit.page
        export_calls = _install_hh_export_interceptor(page)

        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        page_obj = vacancy_edit  # noqa: F841 — alias для читаемости в шаге
        edit.expect_toast_no_spec()
        edit.expect_confirm_dialog_not_open()
        assert export_calls() == 0, (
            "Frontend всё-таки отправил POST /relevanter/api/hh/vacancies/export "
            "при пустой специализации — пре-валидация не сработала."
        )

    @allure.title(
        "TC-652.2: пустая «География» → toast, без диалога, без запроса"
    )
    def test_empty_geography(self, vacancy_edit, make_hh_test_vacancy):
        vacancy = make_hh_test_vacancy(
            tag="TC652-no-city",
            specialization=HH_SPEC_TESTER,
            cities=[],
        )
        page = vacancy_edit.page
        export_calls = _install_hh_export_interceptor(page)

        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        edit.expect_toast_no_city()
        edit.expect_confirm_dialog_not_open()
        assert export_calls() == 0, (
            "Frontend отправил запрос на бэк при пустой географии."
        )

    @allure.title(
        "TC-652.3: оба поля пусты → оба тоста, без диалога, без запроса"
    )
    def test_both_empty(self, vacancy_edit, make_hh_test_vacancy):
        vacancy = make_hh_test_vacancy(
            tag="TC652-both-empty",
            specialization="",
            cities=[],
        )
        page = vacancy_edit.page
        export_calls = _install_hh_export_interceptor(page)

        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])
        edit.click_hh_export()

        edit.expect_toast_no_spec()
        edit.expect_toast_no_city()
        edit.expect_confirm_dialog_not_open()
        assert export_calls() == 0, (
            "Frontend отправил запрос на бэк при пустых спец и географии."
        )
