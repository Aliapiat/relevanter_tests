import random
import pytest
import allure
from faker import Faker

from config.settings import settings

fake = Faker("ru_RU")


def randomize_case(email: str) -> str:
    """Рандомно меняет регистр букв в строке, гарантируя минимум 1 изменение"""
    chars = list(email)
    alpha_indices = [i for i, c in enumerate(chars) if c.isalpha()]

    if not alpha_indices:
        return email

    # Гарантируем хотя бы одну букву изменённой
    forced = random.choice(alpha_indices)
    for i, char in enumerate(chars):
        if char.isalpha():
            if i == forced:
                chars[i] = char.upper() if char.islower() else char.lower()
            else:
                chars[i] = char.upper() if random.choice([True, False]) else char.lower()

    return ''.join(chars)


# ═══════════════════════════════════════════
# UI / ОТОБРАЖЕНИЕ
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("UI — отображение элементов")
class TestLoginUI:

    @allure.title("Поле email отображается")
    @pytest.mark.smoke_critical
    @pytest.mark.login
    def test_email_field_visible(self, login_page):
        login_page.open()
        login_page.should_be_visible(login_page.EMAIL_INPUT)

    @allure.title("Поле пароля отображается")
    @pytest.mark.login
    def test_password_field_visible(self, login_page):
        login_page.open()
        login_page.should_be_visible(login_page.PASSWORD_INPUT)

    @allure.title("Чекбокс 'Запомнить меня' отображается")
    @pytest.mark.login
    def test_remember_me_visible(self, login_page):
        login_page.open()
        login_page.should_be_visible(login_page.REMEMBER_ME)

    @allure.title("Кнопка 'Войти' отображается")
    @pytest.mark.login
    def test_login_button_visible(self, login_page):
        login_page.open()
        login_page.should_be_visible(login_page.LOGIN_BUTTON)

    @allure.title("Плейсхолдер email корректен")
    @pytest.mark.login
    def test_email_placeholder(self, login_page):
        login_page.open()
        placeholder = login_page.get_email_placeholder()
        assert "email" in placeholder.lower(), f"Неверный плейсхолдер: {placeholder}"

    @allure.title("Плейсхолдер пароля корректен")
    @pytest.mark.login
    def test_password_placeholder(self, login_page):
        login_page.open()
        placeholder = login_page.get_password_placeholder()
        assert "пароль" in placeholder.lower(), f"Неверный плейсхолдер: {placeholder}"

    @allure.title("Пароль скрыт (type=password)")
    @pytest.mark.login
    def test_password_is_masked(self, login_page):
        login_page.open()
        login_page.enter_password("TestPassword")
        input_type = login_page.get_password_input_type()
        assert input_type == "password", f"Пароль не скрыт, type={input_type}"


# ═══════════════════════════════════════════
# ПОЗИТИВНЫЕ СЦЕНАРИИ
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("Позитивные сценарии")
class TestLoginPositive:

    @allure.title("Успешный логин")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke_critical
    @pytest.mark.login
    def test_successful_login(self, login_page, dashboard_page):
        login_page.open()
        login_page.login(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()

    @allure.title("Вход с включённым 'Запомнить меня'")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_login_with_remember_me(self, login_page, dashboard_page):
        login_page.open()
        login_page.toggle_remember_me()
        login_page.login(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()

    @allure.title("Вход с выключенным 'Запомнить меня'")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_login_without_remember_me(self, login_page, dashboard_page):
        login_page.open()
        login_page.should_remember_me_be_unchecked()
        login_page.login(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()

    @allure.title("Enter в поле пароля отправляет форму")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_enter_submits_form(self, login_page, dashboard_page):
        login_page.open()
        login_page.enter_email(settings.ADMIN_EMAIL)
        login_page.enter_password(settings.ADMIN_PASSWORD)
        login_page.press_enter_in_password()
        dashboard_page.should_be_loaded()


# ═══════════════════════════════════════════
# РЕГИСТР EMAIL
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("Регистр email")
class TestLoginEmailCase:

    @allure.title("Email полностью в верхнем регистре")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_email_all_upper(self, login_page, dashboard_page):
        login_page.open()
        upper_email = settings.ADMIN_EMAIL.upper()
        with allure.step(f"Вводим email: {upper_email}"):
            login_page.login(upper_email, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()

    @allure.title("Email полностью в нижнем регистре")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_email_all_lower(self, login_page, dashboard_page):
        login_page.open()
        lower_email = settings.ADMIN_EMAIL.lower()
        with allure.step(f"Вводим email: {lower_email}"):
            login_page.login(lower_email, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()

    @allure.title("Email с рандомным регистром букв")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_email_random_case(self, login_page, dashboard_page):
        login_page.open()
        mixed_email = randomize_case(settings.ADMIN_EMAIL)
        with allure.step(f"Вводим email: {mixed_email}"):
            login_page.login(mixed_email, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()

    @allure.title("Email с рандомным регистром (повтор для стабильности)")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.login
    @pytest.mark.parametrize("attempt", range(3), ids=lambda i: f"attempt-{i + 1}")
    def test_email_random_case_repeated(self, login_page, dashboard_page, attempt):
        login_page.open()
        mixed_email = randomize_case(settings.ADMIN_EMAIL)
        with allure.step(f"Попытка {attempt + 1}: email = {mixed_email}"):
            login_page.login(mixed_email, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()


# ═══════════════════════════════════════════
# ПРОБЕЛЫ В EMAIL
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("Пробелы в email")
class TestLoginEmailSpaces:

    @allure.title("Пробелы перед email")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_email_leading_spaces(self, login_page, dashboard_page):
        login_page.open()
        spaced_email = f"   {settings.ADMIN_EMAIL}"
        with allure.step(f"Вводим email: '{spaced_email}'"):
            login_page.login(spaced_email, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()

    @allure.title("Пробелы после email")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_email_trailing_spaces(self, login_page, dashboard_page):
        login_page.open()
        spaced_email = f"{settings.ADMIN_EMAIL}   "
        with allure.step(f"Вводим email: '{spaced_email}'"):
            login_page.login(spaced_email, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()

    @allure.title("Пробелы с обеих сторон email")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_email_both_sides_spaces(self, login_page, dashboard_page):
        login_page.open()
        spaced_email = f"   {settings.ADMIN_EMAIL}   "
        with allure.step(f"Вводим email: '{spaced_email}'"):
            login_page.login(spaced_email, settings.ADMIN_PASSWORD)
        dashboard_page.should_be_loaded()

    @allure.title("Пробелы перед паролем")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_password_leading_spaces(self, login_page):
        login_page.open()
        spaced_password = f"   {settings.ADMIN_PASSWORD}"
        with allure.step("Вводим пароль с пробелами в начале"):
            login_page.login(settings.ADMIN_EMAIL, spaced_password)
        # Пароль НЕ должен триммиться — ожидаем ошибку
        login_page.should_show_error("Ошибка входа. Проверьте email и пароль.")

    @allure.title("Пробелы после пароля")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.login
    def test_password_trailing_spaces(self, login_page):
        login_page.open()
        spaced_password = f"{settings.ADMIN_PASSWORD}   "
        with allure.step("Вводим пароль с пробелами в конце"):
            login_page.login(settings.ADMIN_EMAIL, spaced_password)
        # Пароль НЕ должен триммиться — ожидаем ошибку
        login_page.should_show_error("Ошибка входа. Проверьте email и пароль.")


# ═══════════════════════════════════════════
# СЕССИЯ — ЗАПОМНИТЬ МЕНЯ (НОВАЯ ВКЛАДКА)
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("Сессия — запомнить меня")
class TestLoginSession:

    @allure.title("'Запомнить меня' ВКЛ → новая вкладка → сессия сохранена")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.login
    def test_remember_me_persists_in_new_tab(self, login_page):
        login_page.open()
        login_page.toggle_remember_me()
        login_page.should_remember_me_be_checked()
        login_page.login(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)

        login_page.page.wait_for_url(
            lambda url: "/login" not in url,
            timeout=15000
        )

        ctx = login_page.page.context

        with allure.step("Открываем новую вкладку"):
            new_page = ctx.new_page()
            new_page.goto(settings.BASE_URL)
            # domcontentloaded вместо networkidle
            new_page.wait_for_load_state("domcontentloaded")

        with allure.step("Проверяем: сессия сохранена"):
            logo = new_page.locator("span:has-text('Релевантер')")
            logo.wait_for(state="visible", timeout=15000)
            assert logo.is_visible(), \
                "Сессия не сохранилась — дашборд не загружен"

        new_page.close()

    @allure.title("'Запомнить меня' ВЫКЛ → новая вкладка → сессия НЕ сохранена")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.login
    def test_no_remember_me_no_session_in_new_tab(self, login_page):
        login_page.open()
        login_page.should_remember_me_be_unchecked()
        login_page.login(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)

        login_page.page.wait_for_url(
            lambda url: "/login" not in url,
            timeout=15000
        )

        ctx = login_page.page.context

        with allure.step("Открываем новую вкладку"):
            new_page = ctx.new_page()
            new_page.goto(settings.BASE_URL)
            # domcontentloaded вместо networkidle
            new_page.wait_for_load_state("domcontentloaded")

        with allure.step("Проверяем: страница логина"):
            login_button = new_page.locator("button[type='submit']")
            login_button.wait_for(state="visible", timeout=15000)
            assert login_button.is_visible(), \
                "Должна быть страница логина"

        new_page.close()


# ═══════════════════════════════════════════
# НЕГАТИВНЫЕ — ПУСТЫЕ ПОЛЯ
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("Негативные — пустые поля")
class TestLoginEmptyFields:

    @allure.title("Пустой email + валидный пароль")
    @pytest.mark.login
    def test_empty_email(self, login_page):
        login_page.open()
        login_page.enter_password(fake.password())
        login_page.click_login()
        login_page.should_email_be_invalid()

    @allure.title("Валидный email + пустой пароль")
    @pytest.mark.login
    def test_empty_password(self, login_page):
        login_page.open()
        login_page.enter_email(settings.ADMIN_EMAIL)
        login_page.click_login()
        login_page.should_password_be_invalid()

    @allure.title("Оба поля пустые")
    @pytest.mark.login
    def test_both_empty(self, login_page):
        login_page.open()
        login_page.click_login()
        login_page.should_email_be_invalid()


# ═══════════════════════════════════════════
# НЕГАТИВНЫЕ — НЕВЕРНЫЕ CREDENTIALS
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("Негативные — неверные credentials")
class TestLoginInvalidCredentials:

    @allure.title("Неверный пароль")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke_critical
    @pytest.mark.login
    def test_wrong_password(self, login_page):
        login_page.open()
        login_page.login(settings.ADMIN_EMAIL, fake.password())
        login_page.should_show_error("Ошибка входа. Проверьте email и пароль.")

    @allure.title("Несуществующий пользователь")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.login
    def test_nonexistent_user(self, login_page):
        login_page.open()
        login_page.login(fake.email(), fake.password())
        login_page.should_show_error("Ошибка входа. Проверьте email и пароль.")

    @allure.title("Пробелы вместо логина")
    @pytest.mark.login
    def test_spaces_as_email(self, login_page):
        login_page.open()
        login_page.enter_email("   ")
        login_page.enter_password(fake.password())
        login_page.click_login()
        login_page.should_email_be_invalid()

    @allure.title("Пробелы вместо пароля")
    @pytest.mark.login
    def test_spaces_as_password(self, login_page):
        login_page.open()
        login_page.enter_email(settings.ADMIN_EMAIL)
        login_page.enter_password("   ")
        login_page.click_login()
        login_page.should_show_error("Ошибка входа. Проверьте email и пароль.")

    @allure.title("Очень длинный email (500+ символов)")
    @pytest.mark.login
    def test_very_long_email(self, login_page):
        login_page.open()
        login_page.login(f"{'a' * 500}@mail.com", fake.password())
        login_page.should_show_error("Ошибка входа. Проверьте email и пароль.")

    @allure.title("Очень длинный пароль (1000+ символов)")
    @pytest.mark.login
    def test_very_long_password(self, login_page):
        login_page.open()
        login_page.login(settings.ADMIN_EMAIL, "a" * 1000)
        login_page.should_show_error("Ошибка входа. Проверьте email и пароль.")


# ═══════════════════════════════════════════
# HTML5 ВАЛИДАЦИЯ EMAIL
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("HTML5 валидация email")
class TestLoginEmailValidation:

    @allure.title("Email без @")
    @pytest.mark.login
    def test_email_without_at(self, login_page):
        login_page.open()
        login_page.enter_email(fake.user_name())
        login_page.enter_password(fake.password())
        login_page.click_login()
        login_page.should_email_have_validation("@")

    @allure.title("Email без домена (user@)")
    @pytest.mark.login
    def test_email_without_domain(self, login_page):
        login_page.open()
        login_page.enter_email(f"{fake.user_name()}@")
        login_page.enter_password(fake.password())
        login_page.click_login()
        login_page.should_email_be_invalid()

    @allure.title("Email с двойной точкой в домене")
    @pytest.mark.login
    def test_email_double_dot(self, login_page):
        login_page.open()
        login_page.enter_email(f"{fake.user_name()}@mail..com")
        login_page.enter_password(fake.password())
        login_page.click_login()
        login_page.should_email_be_invalid()


# ═══════════════════════════════════════════
# ЧЕКБОКС "ЗАПОМНИТЬ МЕНЯ"
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("Чекбокс 'Запомнить меня'")
class TestRememberMe:

    @allure.title("Чекбокс выключен по умолчанию")
    @pytest.mark.login
    def test_default_state_unchecked(self, login_page):
        login_page.open()
        login_page.should_remember_me_be_unchecked()

    @allure.title("Клик включает чекбокс")
    @pytest.mark.login
    def test_check(self, login_page):
        login_page.open()
        login_page.toggle_remember_me()
        login_page.should_remember_me_be_checked()

    @allure.title("Повторный клик выключает чекбокс")
    @pytest.mark.login
    def test_uncheck(self, login_page):
        login_page.open()
        login_page.toggle_remember_me()
        login_page.should_remember_me_be_checked()
        login_page.toggle_remember_me()
        login_page.should_remember_me_be_unchecked()


# ═══════════════════════════════════════════
# КНОПКА "ВОЙТИ"
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("Кнопка 'Войти'")
class TestLoginButton:

    @allure.title("Кнопка активна")
    @pytest.mark.login
    def test_button_enabled(self, login_page):
        login_page.open()
        assert login_page.is_login_button_enabled(), "Кнопка должна быть активна"

    @allure.title("Enter в поле email отправляет форму")
    @pytest.mark.login
    def test_enter_in_email_submits(self, login_page, dashboard_page):
        login_page.open()
        login_page.enter_email(settings.ADMIN_EMAIL)
        login_page.enter_password(settings.ADMIN_PASSWORD)
        login_page.press_enter_in_email()
        dashboard_page.should_be_loaded()

    @allure.title("Двойной клик — кнопка блокируется после отправки")
    @pytest.mark.login
    def test_double_click_no_duplicate(self, login_page):
        login_page.open()
        login_page.enter_email(settings.ADMIN_EMAIL)
        login_page.enter_password(settings.ADMIN_PASSWORD)
        login_page.click_login()

        # Кнопка должна стать disabled после клика
        from playwright.sync_api import expect
        expect(login_page.get_element(login_page.LOGIN_BUTTON)).to_be_disabled()

# ═══════════════════════════════════════════
# БЕЗОПАСНОСТЬ
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("Безопасность")
class TestLoginSecurity:

    @allure.title("SQL инъекция в email")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.login
    def test_sql_injection_email(self, login_page):
        login_page.open()
        login_page.enter_email("' OR 1=1 --")
        login_page.enter_password(fake.password())
        login_page.click_login()
        login_page.should_email_be_invalid()

    @allure.title("XSS в поле email")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.login
    def test_xss_in_email(self, login_page):
        login_page.open()
        login_page.enter_email("<script>alert('xss')</script>@mail.com")
        login_page.enter_password(fake.password())
        login_page.click_login()
        login_page.should_email_be_invalid()

    @allure.title("Спецсимволы в пароле")
    @pytest.mark.login
    def test_special_chars_password(self, login_page):
        login_page.open()
        login_page.login(settings.ADMIN_EMAIL, "!@#$%^&*()_+-=[]{}|;':\",./<>?")
        login_page.should_show_error("Ошибка входа. Проверьте email и пароль.")

    @allure.title("XSS в поле пароля")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.login
    def test_xss_in_password(self, login_page):
        login_page.open()
        login_page.login(settings.ADMIN_EMAIL, "<script>alert('xss')</script>")
        login_page.should_show_error("Ошибка входа. Проверьте email и пароль.")


# ═══════════════════════════════════════════
# UX / ACCESSIBILITY
# ═══════════════════════════════════════════

@allure.epic("Авторизация")
@allure.feature("UX / Accessibility")
class TestLoginAccessibility:

    @allure.title("Tab из email переводит фокус на пароль")
    @pytest.mark.login
    def test_tab_navigation(self, login_page):
        login_page.open()
        login_page.page.locator(login_page.EMAIL_INPUT).focus()
        login_page.tab_from_email_to_password()
        assert login_page.is_password_focused(), "Фокус должен быть на поле пароля"

    @allure.title("Поле email имеет label")
    @pytest.mark.login
    def test_email_has_label(self, login_page):
        login_page.open()
        login_page.should_be_visible(login_page.EMAIL_LABEL)

    @allure.title("Поле пароля имеет label")
    @pytest.mark.login
    def test_password_has_label(self, login_page):
        login_page.open()
        login_page.should_be_visible(login_page.PASSWORD_LABEL)

    @allure.title("Сообщение об ошибке читаемо скрин-ридером (role=status)")
    @pytest.mark.login
    def test_error_has_aria_role(self, login_page):
        login_page.open()
        login_page.login(fake.email(), fake.password())
        aria_live = login_page.page.locator(
            login_page.ERROR_MESSAGE
        ).get_attribute("aria-live")
        assert aria_live == "polite", \
            f"aria-live должен быть 'polite', получили: {aria_live}"