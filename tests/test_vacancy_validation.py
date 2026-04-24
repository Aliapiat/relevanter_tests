import pytest
import allure

from pages.sidebar_page import SidebarPage

# ═══════════════════════════════════════════
# ЛИМИТЫ
# ═══════════════════════════════════════════

# Суммарно: Описание + О компании + Соц. пакет
TOTAL_MIN = 122
TOTAL_MAX = 9911 #(Если три поля -- 9911, если два -- 9939)

# Название вакансии — отдельный лимит
TITLE_MIN = 1
TITLE_MAX = 100


def text_of_length(length: int, char: str = "А") -> str:
    return char * length


# ═══════════════════════════════════════════════════
# НАЗВАНИЕ ВАКАНСИИ — ДЛИНА (min 1, max 100)
# ═══════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Валидация — Название вакансии")
@allure.story("Длина текста")
class TestTitleLength:

    @allure.title("Название: 1 символ (граница min)")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_title_min_boundary(self, auth_vacancy_create):
        auth_vacancy_create.fill_all_required_except("title")
        auth_vacancy_create.enter_title(text_of_length(TITLE_MIN))
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar(text_of_length(TITLE_MIN))
        titles = sidebar.get_vacancy_titles()
        assert text_of_length(TITLE_MIN) in titles

    @allure.title("Название: 100 символов (граница max)")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_title_max_boundary(self, auth_vacancy_create):
        title = text_of_length(TITLE_MAX)
        auth_vacancy_create.fill_all_required_except("title")
        auth_vacancy_create.enter_title(title)
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar(title)
        titles = sidebar.get_vacancy_titles()
        assert title in titles

    @allure.title("Название: 101 символ (превышение max)")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_title_exceeds_max(self, auth_vacancy_create):
        title_101 = text_of_length(TITLE_MAX + 1)
        auth_vacancy_create.fill_all_required_except("title")
        auth_vacancy_create.enter_title(title_101)

        actual = auth_vacancy_create.get_title_value()
        with allure.step(
            f"Введено {TITLE_MAX + 1}, длина: {len(actual)}"
        ):
            if len(actual) <= TITLE_MAX:
                assert len(actual) == TITLE_MAX
            else:
                auth_vacancy_create.click_create_vacancy()
                auth_vacancy_create.should_stay_on_create_page()

    @allure.title("Название: пустое")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_title_empty(self, auth_vacancy_create):
        auth_vacancy_create.fill_all_required_except("title")
        auth_vacancy_create.click_create_vacancy()
        auth_vacancy_create.should_stay_on_create_page()

    @allure.title("Название: 99 символов (внутри диапазона)")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_title_within_range(self, auth_vacancy_create):
        title = text_of_length(TITLE_MAX - 1)
        auth_vacancy_create.fill_all_required_except("title")
        auth_vacancy_create.enter_title(title)
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar(title)
        titles = sidebar.get_vacancy_titles()
        assert title in titles


# ═══════════════════════════════════════════════════════════
# СУММАРНЫЙ ЛИМИТ: Описание + О компании + Соц. пакет
# min 122 суммарно, max 9930 суммарно
# ═══════════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Валидация — Суммарный лимит текстовых полей")
@allure.story("Граница min (122 символов суммарно)")
class TestTotalTextMin:

    @allure.title("Суммарно ровно 122 символов — проходит")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_total_min_boundary(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST Min122")
        auth_vacancy_create.enter_description(
            text_of_length(100)
        )
        auth_vacancy_create.enter_company_description(
            text_of_length(22)
        )
        auth_vacancy_create.clear_social_package()
        # Соц. пакет = 0, итого 122
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar("ALIQATEST Min122")
        titles = sidebar.get_vacancy_titles()
        assert "ALIQATEST Min122" in titles

    @allure.title("Суммарно 149 символов — не проходит")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_total_below_min(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST Below150")
        auth_vacancy_create.enter_description(text_of_length(99))
        auth_vacancy_create.enter_company_description(text_of_length(22))
        auth_vacancy_create.clear_social_package().page.wait_for_timeout(3000)  # <-- добавь явную очистку
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()
        auth_vacancy_create.should_stay_on_create_page()

    @allure.title(
        "Описание 150 + О компании 0 — "
        "зависит от min О компании"
    )
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_all_in_description(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST AllInDesc")
        auth_vacancy_create.enter_description(
            text_of_length(150)
        )
        auth_vacancy_create.clear_social_package()
        auth_vacancy_create.clear_company_description()
        # О компании пустое
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()

        # О компании обязательное — должно не пройти
        auth_vacancy_create.should_stay_on_create_page()

    @allure.title(
        "Описание 80 + О компании 60 + Соц. пакет 10 = 150"
    )
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_total_150_split_three_fields(
        self, auth_vacancy_create
    ):
        auth_vacancy_create.enter_title("ALIQATEST Split150")
        auth_vacancy_create.enter_description(
            text_of_length(80)
        )
        auth_vacancy_create.enter_company_description(
            text_of_length(60)
        )
        auth_vacancy_create.enter_social_package(
            text_of_length(10)
        )
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar("ALIQATEST Split150")
        titles = sidebar.get_vacancy_titles()
        assert "ALIQATEST Split150" in titles


@allure.epic("Вакансии")
@allure.feature("Валидация — Суммарный лимит текстовых полей")
@allure.story("Граница max (9911 символов суммарно)")
class TestTotalTextMax:

    @allure.title("Суммарно ровно 9911 (с соц. пакетом) — проходит")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_total_max_boundary_with_social(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST Max9911")
        # Описание 3980 + О компании 2980 + Соц. 2951 = 9911
        auth_vacancy_create.enter_description(
            text_of_length(3980)
        )
        auth_vacancy_create.enter_company_description(
            text_of_length(2980)
        )
        auth_vacancy_create.enter_social_package(
            text_of_length(2951)
        )
        auth_vacancy_create.enter_salary(salary_to="200000")

        auth_vacancy_create.page.wait_for_timeout(3000)
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar("ALIQATEST Max9911")
        titles = sidebar.get_vacancy_titles()
        assert "ALIQATEST Max9911" in titles

    @allure.title("Суммарно ровно 9939 (только обязательные) — проходит")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_total_max_boundary_required_only(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST Max9939")

        # Описание 5000 + О компании 4939 = 9939
        auth_vacancy_create.enter_description(
            text_of_length(5000)
        )
        auth_vacancy_create.enter_company_description(
            text_of_length(4939)
        )
        auth_vacancy_create.clear_social_package()  # <-- явная очистка
        auth_vacancy_create.enter_salary(salary_to="200000")

        auth_vacancy_create.page.wait_for_timeout(3000)
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar("ALIQATEST Max9939", timeout=30000)
        titles = sidebar.get_vacancy_titles()
        assert "ALIQATEST Max9939" in titles

    @allure.title("Суммарно 9940 (только обязательные) — тост ошибки")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_total_exceeds_max_required_only(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST Over9939")

        # Описание 5000 + О компании 4940 = 9940
        auth_vacancy_create.enter_description(
            text_of_length(5000)
        )
        auth_vacancy_create.enter_company_description(
            text_of_length(4940)
        )
        auth_vacancy_create.clear_social_package()  # <-- явная очистка
        auth_vacancy_create.enter_salary(salary_to="200000")

        auth_vacancy_create.page.wait_for_timeout(3000)
        auth_vacancy_create.click_create_vacancy()

        auth_vacancy_create.should_show_char_limit_error()

    @allure.title("Суммарно 9912 (с соц. пакетом) — тост ошибки")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_total_exceeds_max_with_social(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST Over9911")
        # Описание 3980 + О компании 2980 + Соц. 2952 = 9912
        auth_vacancy_create.enter_description(
            text_of_length(3980)
        )
        auth_vacancy_create.enter_company_description(
            text_of_length(2980)
        )
        auth_vacancy_create.enter_social_package(
            text_of_length(2952)
        )
        auth_vacancy_create.enter_salary(salary_to="200000")

        auth_vacancy_create.page.wait_for_timeout(3000)
        auth_vacancy_create.click_create_vacancy()

        auth_vacancy_create.should_show_char_limit_error()


    @allure.title("Суммарно ~12000 — тост с правильным числом")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_total_way_over_max(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST Way Over")
        auth_vacancy_create.enter_description(
            text_of_length(5000)
        )
        auth_vacancy_create.enter_company_description(
            text_of_length(4000)
        )
        auth_vacancy_create.enter_social_package(
            text_of_length(3000)
        )
        auth_vacancy_create.enter_salary(salary_to="200000").page.wait_for_timeout(3000)
        auth_vacancy_create.click_create_vacancy()

        toast = auth_vacancy_create.page.locator(
            auth_vacancy_create.CHAR_LIMIT_TOAST
        )
        toast.wait_for(state="visible", timeout=5000)
        text = toast.inner_text()
        with allure.step(f"Текст тоста: {text}"):
            assert "Сократите" in text or "сократите" in text

    @allure.title(
        "Суммарно 9000 (внутри диапазона) — проходит"
    )
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_total_within_range(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST Within")
        auth_vacancy_create.enter_description(
            text_of_length(3000)
        )
        auth_vacancy_create.enter_company_description(
            text_of_length(3000)
        )
        auth_vacancy_create.enter_social_package(
            text_of_length(3000)
        )
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar("ALIQATEST Within")
        titles = sidebar.get_vacancy_titles()
        assert "ALIQATEST Within" in titles


@allure.epic("Вакансии")
@allure.feature("Валидация — Суммарный лимит текстовых полей")
@allure.story("Пустые обязательные поля")
class TestTotalTextEmpty:

    @allure.title("Все 3 текстовых поля пустые — не проходит")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_all_text_empty(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST Empty")
        auth_vacancy_create.clear_social_package()
        auth_vacancy_create.clear_company_description()
        auth_vacancy_create.clear_description()
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()
        auth_vacancy_create.should_stay_on_create_page()

    @allure.title("Только описание пустое — не проходит")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_description_empty(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST NoDesc")
        auth_vacancy_create.enter_company_description(
            text_of_length(100)
        )
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()
        auth_vacancy_create.should_stay_on_create_page()

    @allure.title("Только О компании пустое — не проходит")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_company_empty(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST NoCompany")
        auth_vacancy_create.enter_description(
            text_of_length(150)
        )
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()
        auth_vacancy_create.should_stay_on_create_page()

    @allure.title(
        "Соц. пакет пустой — проходит (необязательное поле)"
    )
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_social_empty_ok(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST NoSocial")
        auth_vacancy_create.enter_description(
            text_of_length(100)
        )
        auth_vacancy_create.enter_company_description(
            text_of_length(50)
        )
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()

        sidebar = SidebarPage(auth_vacancy_create.page)
        sidebar.wait_for_vacancy_in_sidebar("ALIQATEST NoSocial")
        titles = sidebar.get_vacancy_titles()
        assert "ALIQATEST NoSocial" in titles


# ═══════════════════════════════════════════════════════
# ТОЛЬКО ПРОБЕЛЫ
# ═══════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Валидация — Пробелы вместо текста")
class TestWhitespaceOnly:

    @allure.title("Название: только пробелы")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_title_whitespace(self, auth_vacancy_create):
        auth_vacancy_create.fill_all_required_except("title")
        auth_vacancy_create.enter_title("     ")
        auth_vacancy_create.click_create_vacancy()
        auth_vacancy_create.should_stay_on_create_page()

    @allure.title("Описание: только пробелы")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_description_whitespace(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST WhitespaceDesc")
        auth_vacancy_create.enter_description("     ")
        auth_vacancy_create.enter_company_description(
            text_of_length(100)
        )
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()
        auth_vacancy_create.should_stay_on_create_page()

    @allure.title("О компании: только пробелы")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_company_whitespace(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("ALIQATEST WhitespaceComp")
        auth_vacancy_create.enter_description(
            text_of_length(150)
        )
        auth_vacancy_create.enter_company_description("     ")
        auth_vacancy_create.enter_salary(salary_to="200000")
        auth_vacancy_create.click_create_vacancy()
        auth_vacancy_create.should_stay_on_create_page()


# ═══════════════════════════════════════════════════════
# ДОПУСТИМЫЕ СИМВОЛЫ
# ═══════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Валидация — Допустимые символы")
class TestAllowedChars:

    @allure.title("Описание: безопасные HTML теги (bold)")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_description_bold(self, auth_vacancy_create):
        editor = auth_vacancy_create.page.locator(
            auth_vacancy_create.DESCRIPTION_EDITOR
        )
        editor.click()
        auth_vacancy_create.page.keyboard.press("Control+A")
        auth_vacancy_create.page.keyboard.press("Delete")
        auth_vacancy_create.page.keyboard.type("А" * 150)

        auth_vacancy_create.page.keyboard.press("Control+A")
        auth_vacancy_create.page.locator(
            "button.ql-bold"
        ).first.click()

        html = editor.inner_html()
        assert "<strong>" in html or "<b>" in html

    @allure.title("Описание: переносы строк")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_description_newlines(self, auth_vacancy_create):
        editor = auth_vacancy_create.page.locator(
            auth_vacancy_create.DESCRIPTION_EDITOR
        )
        editor.click()
        auth_vacancy_create.page.keyboard.press("Control+A")
        auth_vacancy_create.page.keyboard.press("Delete")
        auth_vacancy_create.page.keyboard.type("Строка 1")
        auth_vacancy_create.page.keyboard.press("Enter")
        auth_vacancy_create.page.keyboard.type("Строка 2")
        auth_vacancy_create.page.keyboard.press("Enter")
        auth_vacancy_create.page.keyboard.type("А" * 100)

        text = editor.inner_text()
        assert "Строка 1" in text
        assert "Строка 2" in text

    @allure.title("Описание: emoji")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_description_emoji(self, auth_vacancy_create):
        text = "🚀 Мы ищем! 💻 " + "А" * 130
        auth_vacancy_create.enter_description(text)
        actual = auth_vacancy_create.page.locator(
            auth_vacancy_create.DESCRIPTION_EDITOR
        ).inner_text()
        assert "🚀" in actual or len(actual) > 100

    @allure.title("Название: кириллица + латиница + цифры")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_title_mixed(self, auth_vacancy_create):
        title = "QA Engineer 2025 (Тест)"
        auth_vacancy_create.enter_title(title)
        assert auth_vacancy_create.get_title_value() == title


# ═══════════════════════════════════════════════════════
# НЕДОПУСТИМЫЕ СИМВОЛЫ
# ═══════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Валидация — Недопустимые символы")
class TestForbiddenChars:

    @allure.title("Описание: <script> блокируется")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_description_script(self, auth_vacancy_create):
        xss = "<script>alert('xss')</script>" + "А" * 130
        auth_vacancy_create.enter_description(xss)

        html = auth_vacancy_create.page.locator(
            auth_vacancy_create.DESCRIPTION_EDITOR
        ).inner_html()
        assert "<script>" not in html

    @allure.title("Описание: <style> блокируется")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_description_style(self, auth_vacancy_create):
        css = "<style>body{display:none}</style>" + "А" * 130
        auth_vacancy_create.enter_description(css)

        html = auth_vacancy_create.page.locator(
            auth_vacancy_create.DESCRIPTION_EDITOR
        ).inner_html()
        assert "<style>" not in html

    @allure.title("Описание: <iframe> блокируется")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_description_iframe(self, auth_vacancy_create):
        iframe = (
            '<iframe src="https://evil.com"></iframe>'
            + "А" * 130
        )
        auth_vacancy_create.enter_description(iframe)

        html = auth_vacancy_create.page.locator(
            auth_vacancy_create.DESCRIPTION_EDITOR
        ).inner_html()
        assert "<iframe" not in html

    @allure.title("Описание: управляющие символы удаляются")
    @pytest.mark.vacancy
    @pytest.mark.validation
    @pytest.mark.xfail(
        reason="Продуктовое расхождение: санитайзер описания не удаляет "
               "control chars (\\x00, \\x07, \\x1B). HTML-теги "
               "(script/style/iframe) блокируются корректно. "
               "Требует уточнения требований у продакта.",
        strict=False,
    )
    def test_description_control_chars(self, auth_vacancy_create):
        text = "Тест\x00\x07\x1Bтекст" + "А" * 130
        auth_vacancy_create.enter_description(text)

        actual = auth_vacancy_create.page.locator(
            auth_vacancy_create.DESCRIPTION_EDITOR
        ).inner_text()
        assert "\x00" not in actual
        assert "\x07" not in actual
        assert "\x1B" not in actual

    @allure.title("Название: <script> в поле ввода")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_title_script(self, auth_vacancy_create):
        auth_vacancy_create.enter_title(
            "<script>alert(1)</script>"
        )
        actual = auth_vacancy_create.get_title_value()
        with allure.step(f"Значение: '{actual}'"):
            pass  # Фиксируем поведение

    @allure.title("Название: управляющие символы")
    @pytest.mark.vacancy
    @pytest.mark.validation
    @pytest.mark.xfail(
        reason="Продуктовое расхождение: поле 'Название' не стрипует "
               "control chars (\\x00, \\x07). Парные тесты на <script> и "
               "спецсимволы проходят. Требует уточнения требований.",
        strict=False,
    )
    def test_title_control_chars(self, auth_vacancy_create):
        auth_vacancy_create.enter_title("Test\x00\x07Title")
        actual = auth_vacancy_create.get_title_value()
        assert "\x00" not in actual
        assert "\x07" not in actual

    @allure.title("О компании: <script> блокируется")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_company_script(self, auth_vacancy_create):
        xss = "<script>alert(1)</script>" + "А" * 100
        auth_vacancy_create.enter_company_description(xss)

        html = auth_vacancy_create.page.locator(
            auth_vacancy_create.COMPANY_DESCRIPTION_EDITOR
        ).inner_html()
        assert "<script>" not in html

    @allure.title("Соц. пакет: HTML теги")
    @pytest.mark.vacancy
    @pytest.mark.validation
    def test_social_html(self, auth_vacancy_create):
        auth_vacancy_create.fill_all_required_except("none")
        auth_vacancy_create.enter_social_package(
            "<script>alert(1)</script>ДМС"
        )
        auth_vacancy_create.click_create_vacancy()
        auth_vacancy_create.page.wait_for_timeout(2000)