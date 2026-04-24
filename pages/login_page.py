import allure
from pages.base_page import BasePage


class LoginPage(BasePage):
    PATH = "/login"

    EMAIL_INPUT = "#email"
    PASSWORD_INPUT = "#password"
    LOGIN_BUTTON = "button[type='submit']"
    REMEMBER_ME = "input[type='checkbox']"
    FORGOT_PASSWORD = "button:has-text('Забыли пароль?')"
    ERROR_MESSAGE = "div[role='status']"
    EMAIL_LABEL = "label[for='email']"
    PASSWORD_LABEL = "label[for='password']"

    def open(self):
        self.navigate(self.PATH)
        self.wait_for_visible(self.EMAIL_INPUT)
        return self

    def enter_email(self, email: str):
        self.fill(self.EMAIL_INPUT, email)
        return self

    def enter_password(self, password: str):
        self.fill(self.PASSWORD_INPUT, password)
        return self

    def click_login(self):
        self.click(self.LOGIN_BUTTON)
        return self

    def login(self, email: str, password: str):
        self.enter_email(email)
        self.enter_password(password)
        self.click_login()
        return self

    def press_enter_in_password(self):
        self.page.locator(self.PASSWORD_INPUT).press("Enter")
        return self

    def press_enter_in_email(self):
        self.page.locator(self.EMAIL_INPUT).press("Enter")
        return self

    def toggle_remember_me(self):
        self.page.locator(self.REMEMBER_ME).click()
        return self

    def tab_from_email_to_password(self):
        self.page.locator(self.EMAIL_INPUT).press("Tab")
        return self

    def tab_from_password_to_next(self):
        self.page.locator(self.PASSWORD_INPUT).press("Tab")
        return self

    # ─── Проверки ───

    def should_be_opened(self):
        self.should_have_url(f"**{self.PATH}*")
        self.should_be_visible(self.LOGIN_BUTTON)
        return self

    def should_show_error(self, expected_text: str):
        self.should_be_visible(self.ERROR_MESSAGE)
        self.should_contain_text(self.ERROR_MESSAGE, expected_text)
        return self

    def should_email_be_invalid(self):
        self.should_be_invalid(self.EMAIL_INPUT)
        return self

    def should_email_have_validation(self, expected_text: str):
        self.should_have_validation_message(self.EMAIL_INPUT, expected_text)
        return self

    def should_password_be_invalid(self):
        self.should_be_invalid(self.PASSWORD_INPUT)
        return self

    def should_remember_me_be_checked(self):
        from playwright.sync_api import expect
        expect(self.page.locator(self.REMEMBER_ME)).to_be_checked()
        return self

    def should_remember_me_be_unchecked(self):
        from playwright.sync_api import expect
        expect(self.page.locator(self.REMEMBER_ME)).not_to_be_checked()
        return self

    def get_email_placeholder(self) -> str:
        return self.page.locator(self.EMAIL_INPUT).get_attribute("placeholder")

    def get_password_placeholder(self) -> str:
        return self.page.locator(self.PASSWORD_INPUT).get_attribute("placeholder")

    def get_password_input_type(self) -> str:
        return self.page.locator(self.PASSWORD_INPUT).get_attribute("type")

    def is_password_focused(self) -> bool:
        return self.page.locator(self.PASSWORD_INPUT).evaluate(
            "el => document.activeElement === el"
        )

    def is_login_button_enabled(self) -> bool:
        return self.page.locator(self.LOGIN_BUTTON).is_enabled()