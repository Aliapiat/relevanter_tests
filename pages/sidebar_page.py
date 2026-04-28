import re

from pages.base_page import BasePage


class SidebarPage(BasePage):
    """Сайдбар — общий для всех авторизованных страниц"""

    # ── Логотип ──
    LOGO = "span:has-text('Релевантер')"

    # ── Навигация ──
    NEW_VACANCY_BUTTON = "button:has-text('Новая вакансия')"
    SEARCH_VACANCIES = "span:has-text('Поиск по вакансиям')"
    STATISTICS = "span:has-text('Статистика')"

    # ── Список вакансий ──
    VACANCY_LIST = ".flex-1.overflow-y-auto .px-5.space-y-0\\.5"
    VACANCY_ITEM = ".flex-1.overflow-y-auto [role='button']"

    # ── Профиль ──
    # Старый общий локатор оставляем для обратной совместимости.
    PROFILE_BUTTON = "button:has(.rounded-full)"
    # Кнопка профиля внизу сайдбара (SidebarUserProfile). Сужаем
    # селектор до конкретной комбинации классов, чтобы не зацепить
    # другие кнопки с круглыми аватарками (например, в шапке
    # списков и в карточках вакансий).
    USER_PROFILE_BUTTON = (
        "button.bg-\\[\\#F5F6F1\\].rounded-xl:has(.rounded-full)"
    )

    def should_be_loaded(self):
        """Проверяет что сайдбар загружен"""
        self.wait_for_visible(self.LOGO)
        self.should_be_visible(self.LOGO)
        return self

    def click_new_vacancy(self):
        """Нажимает кнопку 'Новая вакансия'"""
        self.click(self.NEW_VACANCY_BUTTON)
        return self

    def click_search_vacancies(self):
        """Нажимает 'Поиск по вакансиям'"""
        self.click(self.SEARCH_VACANCIES)
        return self

    def click_statistics(self):
        """Нажимает 'Статистика'"""
        self.click(self.STATISTICS)
        return self

    def get_vacancy_count(self) -> int:
        """Возвращает количество вакансий в списке"""
        self.page.locator(self.VACANCY_ITEM).first.wait_for(
            state="visible", timeout=10000
        )
        return self.page.locator(self.VACANCY_ITEM).count()

    def get_vacancy_titles(self) -> list[str]:
        """Возвращает список названий вакансий"""
        items = self.page.locator(
            f"{self.VACANCY_ITEM} span.text-\\[14px\\].font-medium.truncate"
        )
        return [item.inner_text() for item in items.all()]

    def wait_for_vacancy_in_sidebar(self, title: str, timeout: int = 20000):
        """Ждёт появления вакансии с указанным названием в сайдбаре"""
        self.page.locator(
            f"{self.VACANCY_ITEM} "
            f"span.text-\\[14px\\].font-medium.truncate"
        ).filter(
            has_text=re.compile(f"^{re.escape(title)}$")
        ).first.wait_for(state="visible", timeout=timeout)
        return self

    def click_vacancy_by_title(self, title: str):
        """Кликает по вакансии с указанным названием"""
        self.page.locator(
            f"{self.VACANCY_ITEM}:has(span:has-text('{title}'))"
        ).first.click()
        return self

    def click_user_profile(self):
        """Кликает по кнопке профиля внизу сайдбара (SidebarUserProfile).
        По клику фронт делает navigate('/recruiter/control?tab=personal')
        — попадаем в личный кабинет / страницу «Управление».
        """
        self.page.locator(self.USER_PROFILE_BUTTON).first.click()
        return self

    def get_user_profile_email(self) -> str:
        """Возвращает email, отображаемый в плашке профиля внизу
        сайдбара. Полезно для cross-проверки того, что в этом UI
        авторизован именно тот пользователь, под которым мы
        логинились (рекрутёр vs админ)."""
        return self.page.locator(
            f"{self.USER_PROFILE_BUTTON} div.text-\\[12px\\]"
        ).first.inner_text().strip()
