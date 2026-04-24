import allure
from pages.base_page import BasePage


class ReportsPage(BasePage):
    """Вкладка «Итоги Подбора» на странице вакансии.

    URL: /recruiter/reports

    Содержит:
      - переключатель типа: «Все» / «AI» / «Live»
      - кнопку «Скачать отчет PDF»
      - список отчётов или empty-state «Нет данных».
    """

    PATH_PATTERN = "/recruiter/reports"

    PAGE_TITLE = "h1:has-text('Итоги Подбора')"

    # ─── Переключатель типа отчёта ───
    # text-is — exact-match, чтобы «Все» не путалось с «все статусы»
    # в сайдбаре, а «AI» — с «AI-скрининг» в других местах.
    FILTER_ALL  = "button:text-is('Все')"
    FILTER_AI   = "button:text-is('AI')"
    FILTER_LIVE = "button:text-is('Live')"

    # ─── Действия ───
    DOWNLOAD_PDF_BUTTON = "button:has-text('Скачать отчет PDF')"

    # ─── Empty-state ───
    EMPTY_STATE_TITLE = "h3:has-text('Нет данных')"

    # ═══════════════════════════════════════
    # ПРОВЕРКИ / ДЕЙСТВИЯ
    # ═══════════════════════════════════════

    @allure.step("Ждём, пока прогрузится вкладка «Итоги Подбора»")
    def should_be_loaded(self, timeout: int = 15_000):
        self.page.wait_for_url(
            lambda u: self.PATH_PATTERN in u, timeout=timeout
        )
        self.page.locator(self.PAGE_TITLE).first.wait_for(
            state="visible", timeout=timeout
        )
        return self

    @allure.step("Переключаемся на фильтр '{filter_label}'")
    def switch_filter(self, filter_label: str):
        """filter_label: 'Все' | 'AI' | 'Live'."""
        self.page.locator(
            f"button:has-text('{filter_label}')"
        ).first.click()
        return self

    def is_empty(self) -> bool:
        return self.page.locator(self.EMPTY_STATE_TITLE).count() > 0
