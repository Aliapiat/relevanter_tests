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
from utils.api_client import APIClient


def _assert_vacancy_fields(
    api_client: APIClient,
    vacancy_id: int,
    *,
    specialization,
    cities,
) -> dict:
    """Дёргает `GET /positions/{id}` и проверяет, что бэк сохранил
    переданные значения specialization / cities ровно так, как мы их
    отправили в POST.

    Зачем: фабрика `make_hh_test_vacancy` отправляет нужные поля в
    payload, но это ничего не говорит о том, что бэк не подменил их
    дефолтом / прежним значением / нормализацией. Если хотим тестить
    UI-флоу «обе модалки пропущены при пустых полях», мы обязаны
    убедиться, что поля действительно пусты на стороне backend'а
    ПЕРЕД тем, как открывать UI. Иначе зелёный/красный тест ничего
    не доказывает — мы просто не знаем, что там лежит в БД.
    """
    fresh = api_client.get_vacancy(vacancy_id)

    # Нормализация: бэк может вернуть `null` вместо пустой строки/списка.
    # Для нашей задачи (проверить, что специализация/города пусты или
    # совпадают строго с переданными) это эквивалент.
    actual_spec = fresh.get("specialization") or ""
    expected_spec = specialization or ""
    if actual_spec != expected_spec:
        raise AssertionError(
            f"Backend сохранил specialization={actual_spec!r} вместо "
            f"ожидаемого {expected_spec!r} (vacancy_id={vacancy_id}). "
            f"Тест не может продолжаться: предусловия по полям не выполнены."
        )

    actual_cities = list(fresh.get("cities") or [])
    expected_cities = list(cities or [])
    if actual_cities != expected_cities:
        raise AssertionError(
            f"Backend сохранил cities={actual_cities!r} вместо ожидаемого "
            f"{expected_cities!r} (vacancy_id={vacancy_id}). Тест не может "
            f"продолжаться: предусловия по полям не выполнены."
        )

    return fresh


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
    def vacancy_empty_both(self, make_hh_test_vacancy, api_client):
        """Создаёт через API вакансию с пустыми specialization и cities,
        затем GET'ом проверяет, что бэк действительно сохранил их
        пустыми. Без этой post-verify шага мы не имеем права утверждать,
        что в TC-009.10 «обе модалки пропущены при пустых полях» —
        возможно, бэк сохранил дефолт, и модалки пропущены по другой
        причине (или не пропущены, но мы это пропускаем из-за гонки UI).
        """
        vacancy = make_hh_test_vacancy(
            tag="TC009-skip-empty-both",
            specialization="",
            cities=[],
        )
        with allure.step(
            f"Verify backend state: spec='', cities=[] for id={vacancy['id']}"
        ):
            _assert_vacancy_fields(
                api_client,
                vacancy["id"],
                specialization="",
                cities=[],
            )
        return vacancy

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
        "TC-009.10: пустая спец + пустые города → сначала открывается "
        "модалка спец-и; после её сохранения — модалка города"
    )
    def test_both_empty_open_spec_then_city(
        self, vacancy_edit, vacancy_empty_both
    ):
        # Поведение фронта поменялось: раньше при пустых specialization
        # и cities обе модалки пропускались и пользователь сразу шёл
        # в confirm-диалог. Сейчас правило проще и строже:
        #   • если specialization пустая ИЛИ содержит >1 группы —
        #     spec-модалка открывается;
        #   • если cities пустые ИЛИ содержат >1 значения (и spec уже
        #     выбрана/подтверждена) — city-модалка открывается.
        # Для пустых spec и cities это означает строгую цепочку:
        # click → spec-модалка → save → city-модалка.
        # Сам экспорт по подтверждению мы не вызываем — реальная
        # публикация на hh.ru стоит платных кредитов работодателя
        # (см. предупреждение в шапке файла).
        edit = vacancy_edit.open_in_edit_mode(vacancy_empty_both["id"])
        edit.click_hh_export()

        edit.expect_spec_modal_open()
        edit.select_it_leaf("Тестировщик")
        edit.modal_click_save()

        edit.expect_city_modal_open()
        # Не идём дальше confirm-диалога: нам важен только сам факт
        # появления city-модалки после выбора спец-и.
        edit.modal_click_cancel()
        edit.expect_city_modal_not_open()


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
        "TC-010.2: после выбора leaf-спец-и через form-модалку и reload — "
        "модалка спец-и при экспорте больше не открывается"
    )
    def test_leaf_spec_after_modal_save_and_reload(
        self, vacancy_edit, make_hh_test_vacancy, api_client
    ):
        # Регрессия: если пользователь выбрал leaf-специализацию через
        # form-модалку (кнопка «Специализация» в режиме редактирования)
        # и сохранил вакансию — после reload повторный экспорт должен
        # сразу открывать confirm-диалог, минуя spec-модалку.
        #
        # Архитектурный контекст
        # (recruiter-front/src/components/vacancies/VacancyDataEditForm.tsx):
        #   • строка 3620-3626: `<SpecializationModal selectionMode="multi"
        #     onSelectionChange={handleSpecializationSelectionChange}/>` —
        #     это FORM-модалка спец, привязана к кнопке «Специализация» в
        #     форме редактирования (строка 2824). Её callback РЕАЛЬНО пишет
        #     в form state `specialization` и в localStorage-кэш
        #     `vacancySpecializationPathKeys_<id>` (строки 1027-1034).
        #   • строка 3668-3676: `<SpecializationModal selectionMode="single_category"
        #     onSelectionChange={handleExportSpecSelected}/>` — EXPORT-модалка,
        #     открывается из click «На HH.ru». Её callback пишет ТОЛЬКО
        #     `setExportSpecOverride` (строка 1596-1598) и не трогает form
        #     state. Поэтому save формы после export-модалки НЕ обновит
        #     specialization на бэке — отсюда был неверный xfail в первом
        #     порте теста.
        #   • строки 1886-1888: form save отправляет `specialization.join(',')`
        #     на бэк через PATCH /positions/<id>.
        #   • строки 1157-1173: на mount/reload backend-spec идёт через
        #     extractLastPathSegment в setSpecialization. Когда form spec
        #     state приходит как leaf path "11/124" → save отправляет
        #     "11/124" → reload получает "11/124" → isSpecializationLeafId
        #     находит leaf → spec-modal на экспорте не открывается.
        #
        # Шаги:
        #   1. Создаём вакансию с пустой specialization, leaf-городом
        #      (Москва, id=1). Кнопка «Специализация» показывает
        #      «Выберите специализацию…».
        #   2. Open form spec-modal (клик по кнопке-анchor «Специализация»).
        #   3. Выбираем leaf «Тестировщик» (id=124) в модалке → modal save.
        #      handleSpecializationSelectionChange пишет form state и кэш.
        #   4. click_form_save → бэк апдейтит specialization до leaf path.
        #   5. Reload + edit.
        #   6. click «На HH.ru» → backend имеет leaf → spec-modal НЕ
        #      открывается → сразу confirm-dialog → «Нет».
        vacancy = make_hh_test_vacancy(
            tag="TC010-pathkey",
            specialization="",
            cities=[HH_CITY_MOSCOW],
        )
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])

        # 1-3. Открываем form spec-modal — кнопка-селектор стоит в блоке
        # «Специализация» формы, у пустой вакансии её текст —
        # «Выберите специализацию…». В отличие от export-модалки
        # (heading «Выберите специализацию для публикации»), у form-модалки
        # заголовок по умолчанию — «Специализации». Поэтому проверяем
        # открытие через heading-regex, а не через expect_spec_modal_open().
        import re as _re
        edit.page.get_by_role(
            "button", name="Выберите специализацию..."
        ).click()
        expect(
            edit.page.get_by_role(
                "heading", name=_re.compile(r"Специализаци")
            )
        ).to_be_visible(timeout=15_000)
        edit.select_it_leaf("Тестировщик")
        edit.modal_click_save()
        # Подтверждаем, что form state применился: кнопка-селектор теперь
        # содержит текст выбранной leaf-специализации.
        expect(
            edit.page.get_by_role(
                "button", name=_re.compile(r"Тестировщик")
            ).first
        ).to_be_visible(timeout=5_000)

        # 4. Сохраняем форму — бэк апдейтит specialization до leaf path key
        # ("11/10" или "11/124" в зависимости от справочника HH).
        edit.click_form_save()
        edit.expect_toast_vacancy_updated()
        fresh = api_client.get_vacancy(vacancy["id"])
        # Проверяем, что бэк действительно сохранил leaf, а не пустую/group
        # specialization. extractLastPathSegment в коде фронта смотрит на
        # последний сегмент после '/', поэтому достаточно проверить, что
        # значение содержит "/" (т.е. это полный path, а не просто id).
        assert "/" in (fresh.get("specialization") or ""), (
            f"Бэк сохранил specialization={fresh.get('specialization')!r}, "
            f"ожидался leaf path-key вида '11/<leaf_id>'. "
            f"Регрессия handleSpecializationSelectionChange / form save."
        )

        # 5. Reload + edit.
        edit.open_in_edit_mode(vacancy["id"])

        # 6. Второй экспорт: spec-modal НЕ открывается, сразу confirm.
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
        # Регрессия: раньше форма падала «Пожалуйста, заполните все
        # обязательные поля», если в вакансии не выставлена специализация.
        # Теперь должен сохраняться без ошибки.
        #
        # ВАЖНО про success-toast: react-hot-toast в этом UI живёт ≈2с
        # (toast.success default duration). К моменту 10-секундного
        # ассерта он уже исчезает с DOM. Поэтому проверяем:
        #   1) после click формa осталась на edit-странице (не редиректнула
        #      на список вакансий с ошибкой),
        #   2) НЕ показалась ошибка «Пожалуйста, заполните все обязательные поля»
        #      (regression-инвариант),
        #   3) кнопка «Сохранить» снова active (форма не зависла в loading).
        # Это эквивалентно тому, что сохранение прошло; success-toast
        # ловить нестабильно и не нужен для этой регрессии.
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

        expect(
            page.get_by_text("Пожалуйста, заполните все обязательные поля")
        ).not_to_be_visible(timeout=5_000)
        # Любые красные тосты-ошибки от валидации формы — фейл регрессии.
        expect(
            page.get_by_text("Зарплата «от» не может")
        ).not_to_be_visible(timeout=2_000)
        # Кнопка «Сохранить» снова доступна (запрос завершился, не висит).
        expect(save).to_be_enabled(timeout=15_000)


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
        # ВНИМАНИЕ: backend на нашем dev отвергает POST /positions
        # с title длиннее ~100 символов (HTTP 400). TS-вариант теста
        # создавал вакансию с длинным title напрямую через API; у нас
        # так не получится — нужен UI-флоу:
        #   1) Создаём вакансию с короткой title (фабрика)
        #   2) Открываем edit-режим, перезаписываем title в input >100 chars
        #   3) Кликаем «На HH.ru» → фронт ловит длину перед отправкой
        #      на бэк и показывает toast.
        # Тестируем именно frontend-пре-валидацию, т.е. сам бэк не
        # дёргается (POST /positions с длинным title не уходит).
        vacancy = make_hh_test_vacancy(
            tag="TC011-long-title",
            specialization=HH_SPEC_TESTER,
            cities=[HH_CITY_MOSCOW],
        )
        edit = vacancy_edit.open_in_edit_mode(vacancy["id"])

        long_title = "ALIQATEST_HH_TC011_" + ("А" * 100)  # 119 символов > 100
        edit.set_title_in_form(long_title)
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
    """Перехватчик POST `…/relevanter/hh/vacancies/export`.

    Если фронт корректно делает пре-валидацию — на пустых полях запрос
    на бэк уходить НЕ должен. Перехватчик считает количество вызовов
    и в случае попадания возвращает мок-400, чтобы реальная публикация
    не произошла, даже если фронт где-то проворонит проверку.

    Регистрируем оба варианта префикса (с `/api/` для локального
    dev-сервера и без `/api/` для deploy'а на hr-dev) — см. подробное
    объяснение в test_search_relevance_pagination._install_search_mocks.

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

    page.route("**/relevanter/hh/vacancies/export", handler)
    page.route("**/relevanter/api/hh/vacancies/export", handler)
    return lambda: state["calls"]


@allure.epic("HH.ru экспорт")
@allure.feature(
    "TC-652: пре-валидация — модалки спец/города ДО подтверждения, "
    "без запроса на бэк"
)
@pytest.mark.hh_export
@pytest.mark.validation
@pytest.mark.integration
@pytest.mark.regression
class TestHHExportValidationOrder:
    """Регрессия TASKNEIROKLYUCH-652 (адаптирована под TASKNEIROKLYUCH-678).

    Архитектурный контекст
    (recruiter-front/src/components/vacancies/VacancyDataEditForm.tsx,
    handleExportClick на строках 1525-1593):
        * Старая семантика TASKNEIROKLYUCH-652 — toast при пустых
          specialization/cities — заменена на TASKNEIROKLYUCH-678:
          пустое/non-leaf поле → открывается соответствующая модалка
          (spec-modal или city-modal), а не выводится toast.
        * Шаг 1 (строки 1559-1573): спец-валидация. Пустая, >1, или
          ровно один не-лист → setIsExportSpecModalOpen(true), return.
        * Шаг 2 (строки 1575-1589): город-валидация. Аналогично.
        * Только при обоих заполненных листовых значениях открывается
          confirm-dialog (строка 1591-1592).

    Поэтому актуальный TC-652-инвариант:
        * При пустом обязательном поле открывается соответствующая
          модалка для уточнения (а не сразу confirm-dialog).
        * Confirm-dialog НЕ открывается, пока пользователь не
          уточнит все нелистовые/пустые поля.
        * POST `/relevanter/hh/vacancies/export` НЕ уходит вплоть до
          явного «Да» в confirm-dialog (которое тесты никогда не жмут).
    """

    @allure.title(
        "TC-652.1: пустая «Специализация» → spec-modal, без confirm, без запроса"
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

        # Шаг 1 handleExportClick: спец пустая → spec-modal, return до
        # любого дальнейшего флоу (city-modal / confirm).
        edit.expect_spec_modal_open()
        edit.expect_confirm_dialog_not_open()
        assert export_calls() == 0, (
            "Frontend всё-таки отправил POST /relevanter/hh/vacancies/export "
            "при пустой специализации — пре-валидация не сработала."
        )

    @allure.title(
        "TC-652.2: пустая «География» → city-modal, без confirm, без запроса"
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

        # Спец листовая → шаг 1 handleExportClick проходит. Города пусты
        # → шаг 2 → city-modal, return до confirm-dialog.
        edit.expect_spec_modal_not_open()
        edit.expect_city_modal_open()
        edit.expect_confirm_dialog_not_open()
        assert export_calls() == 0, (
            "Frontend отправил запрос на бэк при пустой географии."
        )

    @allure.title(
        "TC-652.3: оба поля пусты → spec-modal первой, без confirm, без запроса"
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

        # handleExportClick проверяет спец первой (строка 1559). При пустой
        # специализации фронт открывает spec-modal и делает early return
        # ДО city-валидации. Поэтому city-modal на этом этапе не открыт.
        edit.expect_spec_modal_open()
        edit.expect_city_modal_not_open()
        edit.expect_confirm_dialog_not_open()
        assert export_calls() == 0, (
            "Frontend отправил запрос на бэк при двух пустых полях."
        )
        assert export_calls() == 0, (
            "Frontend отправил запрос на бэк при пустых спец и географии."
        )
