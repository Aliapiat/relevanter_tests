import allure
from pages.base_page import BasePage


class InterviewsPage(BasePage):
    """Вкладка «Собеседования» на странице вакансии.

    URL: /recruiter/interviews

    На тестовой вакансии обычно пустая: показывается заголовок
    «Собеседования» + заголовок секции «AI скрининг». Когда
    появятся реальные собеседования, здесь добавятся селекторы
    на карточки/статусы.
    """

    PATH_PATTERN = "/recruiter/interviews"

    PAGE_TITLE         = "h2:has-text('Собеседования')"
    AI_SCREENING_TITLE = "p:has-text('AI скрининг')"

    # ═══════════════════════════════════════
    # ПРОВЕРКИ
    # ═══════════════════════════════════════

    @allure.step("Ждём, пока прогрузится вкладка «Собеседования»")
    def should_be_loaded(self, timeout: int = 30_000):
        self.page.wait_for_url(
            lambda u: self.PATH_PATTERN in u, timeout=timeout
        )
        self.page.locator(self.PAGE_TITLE).first.wait_for(
            state="visible", timeout=timeout
        )
        return self
