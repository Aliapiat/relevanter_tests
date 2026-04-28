"""
Личный кабинет / страница «Управление» (`/recruiter/control`).

Что проверяем
-------------
1. Переход в личный кабинет с кнопки профиля внизу сайдбара (SidebarUserProfile).
   Кнопка вызывает `navigate('/recruiter/control?tab=personal')` —
   ожидаем активный таб «Личная информация» и форму с полями
   Email / Имя / Фамилия.

2. Ролевая видимость табов в левой панели страницы. Источник правды —
   `recruiter-front/src/components/TeamManagementPage.tsx`:
       canManageAccounts = SUPER_ADMIN | OWNER | ADMIN
       isSuperAdmin      = SUPER_ADMIN
   На основе этих условий собираются `managementItems`. Рекрутёр НЕ
   должен видеть «Управление аккаунтами», «Компании», «Жалобы».
   Админ должен видеть «Управление аккаунтами» (и не должен — пунктов
   уровня SUPER_ADMIN, если только этот конкретный аккаунт в .env
   действительно ADMIN, а не SUPER_ADMIN).

Чего сознательно НЕ проверяем
-----------------------------
- Контент чужих разделов («Управление аккаунтами», «Компании», «Жалобы») —
  это отдельные фичи со своими тест-кейсами; здесь только видимость
  пункта в левой панели.
- «Моя команда»: пункт всегда отрисован, но раздел отключён (toast
  «В разработке» — `TEAM_SECTION_DISABLED=true`). Проверка ограничена
  фактом наличия пункта.
"""

import allure
import pytest
from playwright.sync_api import Page, expect

from pages.sidebar_page import SidebarPage
from pages.control_panel_page import ControlPanelPage
from config.settings import settings


# Ярлыки, видимые любой ролью (RECRUITER и выше).
COMMON_TAB_LABELS = (
    "Процесс интервью",
    "Брендирование",
    "Моя команда",
    "Настройки интеграций",
    "Личная информация",
)

# Доступно ADMIN / OWNER / SUPER_ADMIN.
ADMIN_ONLY_TAB_LABELS = ("Управление аккаунтами",)

# Доступно ТОЛЬКО SUPER_ADMIN.
SUPER_ADMIN_ONLY_TAB_LABELS = ("Компании", "Жалобы")


@allure.epic("Личный кабинет")
@allure.feature("Переход с кнопки профиля в сайдбаре")
@pytest.mark.smoke
class TestPersonalCabinetEntry:
    """Кнопка профиля в нижней части сайдбара (SidebarUserProfile)
    ведёт на `/recruiter/control?tab=personal` — это «личный кабинет»
    в терминах продукта."""

    @allure.title(
        "Рекрутёр: клик по кнопке профиля → /recruiter/control?tab=personal "
        "+ форма «Личная информация» отрисована"
    )
    def test_recruiter_open_personal_cabinet(self, authenticated_page: Page):
        sidebar = SidebarPage(authenticated_page)
        sidebar.should_be_loaded()

        # Sanity check: в сайдбаре отображается тот же email, под
        # которым мы залогинились. Если плашка показывает чужого
        # пользователя — что-то упало в авторизации, дальше тест
        # провалится с малопонятной ошибкой.
        sidebar_email = sidebar.get_user_profile_email()
        assert sidebar_email.lower() == settings.RECRUITER_EMAIL.lower(), (
            f"Sidebar показывает email='{sidebar_email}', "
            f"ждали RECRUITER_EMAIL='{settings.RECRUITER_EMAIL}'"
        )

        with allure.step("Клик по кнопке профиля"):
            sidebar.click_user_profile()

        with allure.step("URL перешёл на /recruiter/control?tab=personal"):
            authenticated_page.wait_for_url(
                "**/recruiter/control?tab=personal", timeout=10_000
            )

        control = ControlPanelPage(authenticated_page)
        control.should_be_loaded()
        control.should_show_personal_section()


@allure.epic("Личный кабинет")
@allure.feature("Ролевая видимость табов в /recruiter/control")
@pytest.mark.vacancy  # тест влияет на UI вокруг профиля
class TestControlPanelTabsByRole:
    """Левая панель «Управление» содержит разный набор табов в
    зависимости от роли (см. TeamManagementPage.tsx → managementItems)."""

    @allure.title(
        "Рекрутёр: видит общие 5 табов и НЕ видит admin/super-admin пункты"
    )
    @pytest.mark.smoke
    def test_recruiter_tabs_set(self, authenticated_page: Page):
        control = ControlPanelPage(authenticated_page).open(tab="personal")

        visible = control.get_visible_tab_labels()

        with allure.step("Все общие табы видимы"):
            for label in COMMON_TAB_LABELS:
                assert label in visible, (
                    f"У рекрутёра в левой панели должен быть таб "
                    f"'{label}', а его нет. Видим: {visible}"
                )

        with allure.step("Admin/super-admin табы НЕ видимы рекрутёру"):
            for label in ADMIN_ONLY_TAB_LABELS + SUPER_ADMIN_ONLY_TAB_LABELS:
                assert label not in visible, (
                    f"Рекрутёр НЕ должен видеть таб '{label}', "
                    f"но он отрисован. Полный список: {visible}"
                )

        # Ровно 5 пунктов — это контракт. Если фронт добавит/уберёт
        # пункт, тест упадёт и заставит синхронизировать ожидания.
        assert len(visible) == len(COMMON_TAB_LABELS), (
            f"Ожидали ровно {len(COMMON_TAB_LABELS)} табов "
            f"{list(COMMON_TAB_LABELS)} для рекрутёра, "
            f"увидели {len(visible)}: {visible}"
        )

    @allure.title(
        "Админ: дополнительно видит «Управление аккаунтами»"
    )
    def test_admin_sees_account_management(
        self, authenticated_admin_page: Page
    ):
        control = ControlPanelPage(authenticated_admin_page).open(tab="personal")

        visible = control.get_visible_tab_labels()

        with allure.step("Все общие табы видимы и админу"):
            for label in COMMON_TAB_LABELS:
                assert label in visible, (
                    f"У админа в левой панели должен быть таб "
                    f"'{label}', а его нет. Видим: {visible}"
                )

        with allure.step("Виден admin-only таб «Управление аккаунтами»"):
            assert "Управление аккаунтами" in visible, (
                f"Админ должен видеть «Управление аккаунтами», "
                f"но пункта нет. Видим: {visible}. Если ADMIN_EMAIL "
                f"в .env назначен на роль ниже ADMIN — этот тест "
                f"неприменим, и нужно поправить тестовый аккаунт "
                f"на стенде, а не локатор."
            )
