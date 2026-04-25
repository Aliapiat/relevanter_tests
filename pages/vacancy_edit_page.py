"""
VacancyEditPage — режим редактирования вакансии: /recruiter/vacancy/{id} → «Редактировать».

Покрывает работу с кнопкой «На HH.ru» и связанными модалками /
диалогами: «Выберите специализацию для публикации», «Выберите город
публикации», «Подтверждение публикации/обновления». Используется в
test_vacancy_hh_export (TC-009/010/011/652).

Принципы:
  • Тесты НИКОГДА не нажимают «Да» в диалоге подтверждения — реальная
    публикация на hh.ru тратит платные кредиты работодателя. Хелпер
    `confirm_dialog_click_no()` нажимает «Нет» как единственно
    допустимый сценарий завершения.
  • Все тексты на русском (соответствуют UI recruiter-front).
  • Локаторы текстовые там, где это устойчивее селекторов по DOM —
    UI меняется медленно, тексты держатся.
"""

import re

import allure
from playwright.sync_api import expect

from pages.base_page import BasePage


# ─── Тексты UI (вынесены, чтобы не дублировать в локаторах) ─────────────
SPEC_MODAL_HEADING = "Выберите специализацию для публикации"
CITY_MODAL_HEADING = "Выберите город публикации"
SPEC_MODAL_HINT = "Для публикации на HH.ru необходимо выбрать одну специализацию"
CITY_MODAL_HINT = "Каждый город — это отдельная публикация"

# В UI текст диалога подтверждения варьируется между «Подтверждение
# публикации» (новая) и «Подтверждение обновления» (повторный экспорт),
# поэтому везде ищем по regex.
CONFIRM_DIALOG_TITLE_RE = re.compile(r"Подтверждение (публикации|обновления)")
CONFIRM_DIALOG_BODY_RE = re.compile(
    r"будет (отправлена на публикацию|обновлена) на hh\.ru",
    re.IGNORECASE,
)

# Тексты тостов пре-валидации (TC-011, TC-652)
TOAST_TITLE_TOO_LONG_RE = re.compile(r"Название не должно превышать 100 символов")
TOAST_DESC_TOO_SHORT_RE = re.compile(r"Описание должно содержать не менее 200 символов")
TOAST_NO_SPEC_RE = re.compile(
    r"Выберите специализацию для публикации на HeadHunter"
)
TOAST_NO_CITY_RE = re.compile(
    r"Укажите регион или город для публикации на HeadHunter"
)
WARN_TITLE_OVER_LIMIT_RE = re.compile(r"Название превышает лимит HH\.ru")


class VacancyEditPage(BasePage):
    """Режим редактирования вакансии + взаимодействие с HH-export."""

    PATH_PATTERN = "/recruiter/vacancy/"

    PAGE_HEADING = "h1:has-text('Вакансия'), h2:has-text('Вакансия')"
    EDIT_BUTTON = "button:has-text('Редактировать')"
    HH_EXPORT_BUTTON = "button:has-text('на HH.ru')"
    SAVE_BUTTON = "button:has-text('Сохранить')"

    # ─── Навигация / открытие ────────────────────────────────────────

    @allure.step("Открываем вакансию id={vacancy_id} в режиме редактирования")
    def open(self, vacancy_id: int) -> "VacancyEditPage":
        from config.settings import settings  # local import → нет циклов
        self.page.goto(f"{settings.BASE_URL.rstrip('/')}/recruiter/vacancy/{vacancy_id}")
        # Ждём появления заголовка «Вакансия» (h1 или h2 — зависит от
        # релиза UI, в TS-тестах это h2, в текущем dev уже h1 встречалось).
        self.page.locator(self.PAGE_HEADING).first.wait_for(
            state="visible", timeout=15_000
        )
        return self

    @allure.step("Переходим в режим редактирования (кнопка «Редактировать»)")
    def click_edit(self) -> "VacancyEditPage":
        btn = self.page.locator(self.EDIT_BUTTON).first
        btn.scroll_into_view_if_needed()
        btn.click()
        # После клика должна появиться кнопка «На HH.ru» — это самый
        # надёжный признак, что edit-форма прорисовалась полностью.
        self.page.locator(self.HH_EXPORT_BUTTON).first.wait_for(
            state="visible", timeout=10_000
        )
        return self

    @allure.step("Открываем вакансию и сразу переходим в режим редактирования")
    def open_in_edit_mode(self, vacancy_id: int) -> "VacancyEditPage":
        self.open(vacancy_id)
        self.click_edit()
        return self

    # ─── HH export ──────────────────────────────────────────────────

    @allure.step("Нажимаем кнопку «На HH.ru»")
    def click_hh_export(self) -> "VacancyEditPage":
        btn = self.page.locator(self.HH_EXPORT_BUTTON).first
        btn.scroll_into_view_if_needed()
        btn.click()
        return self

    def hh_export_button_visible(self) -> bool:
        return self.page.locator(self.HH_EXPORT_BUTTON).first.is_visible()

    # ─── Модалка специализации ──────────────────────────────────────

    def spec_modal_heading(self):
        return self.page.get_by_role("heading", name=SPEC_MODAL_HEADING)

    def is_spec_modal_open(self, timeout: int = 5_000) -> bool:
        try:
            self.spec_modal_heading().wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    @allure.step("Ждём, что модалка специализации открыта")
    def expect_spec_modal_open(self, timeout: int = 5_000):
        expect(self.spec_modal_heading()).to_be_visible(timeout=timeout)
        return self

    @allure.step("Ждём, что модалка специализации НЕ открыта")
    def expect_spec_modal_not_open(self, timeout: int = 3_000):
        expect(self.spec_modal_heading()).not_to_be_visible(timeout=timeout)
        return self

    @allure.step("Ждём подсказку «Для публикации необходимо выбрать одну специализацию»")
    def expect_spec_modal_hint(self):
        expect(self.page.get_by_text(SPEC_MODAL_HINT)).to_be_visible()
        return self

    @allure.step("Сбрасываем выбор в модалке (кнопка «Сбросить»)")
    def reset_modal_selection(self):
        self.page.get_by_role("button", name="Сбросить").click()
        return self

    @allure.step("Раскрываем группу «{group_name}» в модалке специализации")
    def expand_spec_group(self, group_name: str):
        # Кнопка раскрытия группы — соседний button рядом с checkbox в
        # tree-узле. Структура: <li><span><label><input checkbox/><span>Имя
        # группы</span></label></span><button>Стрелка</button></li>.
        # Поэтому через xpath '../../button' находим именно стрелку.
        cb = self.page.get_by_role("checkbox", name=group_name)
        cb.scroll_into_view_if_needed()
        cb.locator("xpath=../../button").click()
        return self

    @allure.step("Выбираем листовую специализацию «{leaf_name}» в модалке")
    def select_spec_leaf(self, leaf_name: str):
        cb = self.page.get_by_role("checkbox", name=leaf_name)
        expect(cb).to_be_visible(timeout=5_000)
        cb.scroll_into_view_if_needed()
        cb.click()
        return self

    @allure.step("Хелпер: сбросить → раскрыть «Информационные технологии» → выбрать «{leaf_name}»")
    def select_it_leaf(self, leaf_name: str = "Тестировщик"):
        """Универсальный путь к листовой ИТ-специализации.

        Используется во всех TC-009/010/011, чтобы провести модалку до
        состояния «Сохранить enabled». Дефолт «Тестировщик» совпадает
        с TS-тестами (HH ID 124).
        """
        self.reset_modal_selection()
        self.expand_spec_group("Информационные технологии")
        self.select_spec_leaf(leaf_name)
        cb = self.page.get_by_role("checkbox", name=leaf_name)
        expect(cb).to_be_checked()
        return self

    def modal_save_button(self):
        # «Сохранить» в модалке стоит в одном action-row с «Отменить» —
        # поднимаемся к общему родителю и берём кнопку «Сохранить»
        # уже из него, чтобы не зацепить «Сохранить» с самой формы
        # вакансии (которая всегда висит снизу).
        actions = self.page.get_by_role("button", name="Отменить").locator("..")
        return actions.get_by_role("button", name="Сохранить")

    @allure.step("Нажимаем «Сохранить» в модалке")
    def modal_click_save(self):
        self.modal_save_button().click()
        return self

    @allure.step("Нажимаем «Отменить» в модалке")
    def modal_click_cancel(self):
        self.page.get_by_role("button", name="Отменить").click()
        return self

    # ─── Модалка города ─────────────────────────────────────────────

    def city_modal_heading(self):
        return self.page.get_by_role("heading", name=CITY_MODAL_HEADING)

    def is_city_modal_open(self, timeout: int = 5_000) -> bool:
        try:
            self.city_modal_heading().wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    @allure.step("Ждём, что модалка города открыта")
    def expect_city_modal_open(self, timeout: int = 5_000):
        expect(self.city_modal_heading()).to_be_visible(timeout=timeout)
        return self

    @allure.step("Ждём, что модалка города НЕ открыта")
    def expect_city_modal_not_open(self, timeout: int = 3_000):
        expect(self.city_modal_heading()).not_to_be_visible(timeout=timeout)
        return self

    @allure.step("Ждём подсказку «Каждый город — это отдельная публикация»")
    def expect_city_modal_hint(self):
        expect(self.page.get_by_text(CITY_MODAL_HINT)).to_be_visible()
        return self

    @allure.step("В модалке города ищем «{query}», раскрываем регион «{region}», выбираем город «{city}»")
    def select_city_via_search(self, query: str, region: str, city: str):
        """Универсальный путь выбора одного города в модалке HH-публикации.

        UI: input[placeholder=Поиск...] фильтрует дерево регионов; нужный
        регион раскрывается стрелкой (брат checkbox), внутри — лист-город.
        """
        self.reset_modal_selection()
        self.page.get_by_role("textbox", name=re.compile("Поиск", re.IGNORECASE)).fill(query)

        region_cb = self.page.get_by_role("checkbox", name=region)
        expect(region_cb).to_be_visible(timeout=5_000)
        region_cb.locator("xpath=../../button").click()

        city_cb = self.page.get_by_role("checkbox", name=city)
        expect(city_cb).to_be_visible(timeout=3_000)
        city_cb.click()
        return self

    def select_barnaul(self):
        """Дефолтный «безопасный» город для тестов экспорта (TS-тесты тоже его используют)."""
        return self.select_city_via_search("Барнаул", "Алтайский край", "Барнаул")

    # ─── Диалог подтверждения ───────────────────────────────────────

    def confirm_dialog_title(self):
        return self.page.get_by_text(CONFIRM_DIALOG_TITLE_RE)

    @allure.step("Ждём, что диалог подтверждения открыт")
    def expect_confirm_dialog_open(self, timeout: int = 5_000):
        expect(self.confirm_dialog_title()).to_be_visible(timeout=timeout)
        return self

    @allure.step("Ждём, что диалог подтверждения НЕ открыт")
    def expect_confirm_dialog_not_open(self, timeout: int = 3_000):
        expect(self.confirm_dialog_title()).not_to_be_visible(timeout=timeout)
        return self

    @allure.step("Подтверждение: проверяем тело диалога (вакансия будет отправлена/обновлена)")
    def expect_confirm_dialog_body(self):
        expect(self.page.get_by_text(CONFIRM_DIALOG_BODY_RE)).to_be_visible()
        return self

    @allure.step("Нажимаем «Нет» в диалоге подтверждения (никогда не публикуем реально)")
    def confirm_dialog_click_no(self):
        # Безопасное завершение: тест НИКОГДА не должен нажимать «Да»,
        # иначе спишет реальные кредиты работодателя на hh.ru.
        self.page.get_by_role("button", name="Нет").click()
        self.expect_confirm_dialog_not_open()
        return self

    # ─── Тосты пре-валидации ────────────────────────────────────────

    @allure.step("Ждём toast «Название не должно превышать 100 символов»")
    def expect_toast_title_too_long(self, timeout: int = 5_000):
        expect(self.page.get_by_text(TOAST_TITLE_TOO_LONG_RE)).to_be_visible(timeout=timeout)
        return self

    @allure.step("Ждём toast «Описание должно содержать не менее 200 символов»")
    def expect_toast_desc_too_short(self, timeout: int = 5_000):
        expect(self.page.get_by_text(TOAST_DESC_TOO_SHORT_RE)).to_be_visible(timeout=timeout)
        return self

    @allure.step("Ждём toast «Выберите специализацию для публикации на HeadHunter»")
    def expect_toast_no_spec(self, timeout: int = 5_000):
        expect(self.page.get_by_text(TOAST_NO_SPEC_RE)).to_be_visible(timeout=timeout)
        return self

    @allure.step("Ждём toast «Укажите регион или город для публикации на HeadHunter»")
    def expect_toast_no_city(self, timeout: int = 5_000):
        expect(self.page.get_by_text(TOAST_NO_CITY_RE)).to_be_visible(timeout=timeout)
        return self

    @allure.step("Ждём warning «Название превышает лимит HH.ru» в форме")
    def expect_form_warning_title_over_limit(self):
        expect(self.page.get_by_text(WARN_TITLE_OVER_LIMIT_RE)).to_be_visible()
        return self

    # ─── Сохранение из формы (для TC-010 «без специализации») ────────

    def form_save_button(self):
        # Кнопка «Сохранить» из главной формы (не из модалки): exact=True,
        # без братской «Отменить» рядом — не действует как modal-action.
        return self.page.get_by_role("button", name="Сохранить", exact=True)

    @allure.step("Нажимаем «Сохранить» формы вакансии")
    def click_form_save(self):
        btn = self.form_save_button()
        btn.scroll_into_view_if_needed()
        btn.click()
        return self

    @allure.step("Ждём toast «Вакансия успешно обновлена»")
    def expect_toast_vacancy_updated(self, timeout: int = 10_000):
        expect(self.page.get_by_text("Вакансия успешно обновлена")).to_be_visible(
            timeout=timeout
        )
        return self
