from pages.base_page import BasePage


class DashboardPage(BasePage):
    PATH = "/dashboard"

    SIDEBAR_LOGO = "span:has-text('Релевантер')"

    def should_be_loaded(self):
        self.wait_for_visible(self.SIDEBAR_LOGO)
        self.should_be_visible(self.SIDEBAR_LOGO)
        return self