import re

import allure
from pages.base_page import BasePage
from utils import session_registry
from utils.allure_hooks import attach_vacancy_id


class VacancyCreatePage(BasePage):
    """Страница создания новой вакансии"""

    PATH = "/recruiter/vacancy"

    # ═══════════════════════════════════════
    # ЗАГОЛОВОК И ТАБЫ
    # ═══════════════════════════════════════

    PAGE_TITLE = "h1:has-text('Новая вакансия')"

    # Табы переключения
    TAB_VACANCY_SETTINGS = "p:has-text('Настройка вакансии')"
    TAB_DIALOG_REQUIREMENTS = "p:has-text('Настройка рассылки')"
    TAB_INTERVIEW_SETTINGS = "p:has-text('Настройка интервью')"

    # ═══════════════════════════════════════
    # КНОПКИ ДЕЙСТВИЙ
    # ═══════════════════════════════════════

    # С осени 2025 primary-кнопка на шаге создания — одна и та же, её текст
    # зависит от состояния формы: "Далее: требования" (когда ещё не была
    # показана панель требований) → после клика открывается
    # RequirementsPanel и запускается AI-анализ; когда анализ завершился,
    # та же кнопка переключается на "Создать вакансию".
    NEXT_REQUIREMENTS_BUTTON = "button:has-text('Далее: требования')"
    CREATE_VACANCY_BUTTON = "button:has-text('Создать вакансию')"
    CANCEL_BUTTON = "button:has-text('Отмена')"
    SAVE_AND_CONTINUE_BUTTON = "button:has-text('Сохранить и продолжить')"

    # Янтарная (warning) подсказка под полем "Что входит в соц. пакет":
    # «Итоговое описание для HH.ru (все блоки вместе) — не менее 150 символов
    # (сейчас: N)». Пока она видна — форма блокирует Save / Сохранить и
    # продолжить (валидация длины). Для позитивных тестов ждём её исчезновения
    # перед кликом primary-кнопки.
    MIN_CHARS_WARNING = (
        "p.text-amber-600:has-text('не менее 150 символов')"
    )

    # Таймаут ожидания завершения AI-анализа требований (реальный запрос
    # к LLM-бэкенду может длиться десятки секунд).
    REQUIREMENTS_AI_TIMEOUT_MS = 90_000
    # Таймаут ожидания исчезновения amber-подсказки 150 символов.
    MIN_CHARS_WAIT_MS = 8_000

    # ═══════════════════════════════════════
    # AI АССИСТЕНТ
    # ═══════════════════════════════════════

    AI_ASSISTANT_PANEL = ".w-\\[420px\\]"
    AI_ASSISTANT_TITLE = ".w-\\[420px\\] span:has-text('Ассистент')"
    AI_ASSISTANT_TEXTAREA = (
        "textarea[placeholder='Добавьте описание вакансии']"
    )
    AI_ASSISTANT_RESET = "button:has-text('Сбросить')"
    AI_ASSISTANT_COLLAPSE = "button[title='Свернуть']"
    AI_IMPORT_HH = "button:has-text('Импорт')"

    # ═══════════════════════════════════════
    # ЛОКАТОРЫ ВАЛИДАЦИИ
    # ═══════════════════════════════════════

    TITLE_ERROR = "div[data-field-id='title'] .text-red-500, div[data-field-id='title'] [class*='error']"
    DESCRIPTION_ERROR = "div[data-field-id='description'] .text-red-500, div[data-field-id='description'] [class*='error']"
    COMPANY_ERROR = "div[data-field-id='companyDescription'] .text-red-500, div[data-field-id='companyDescription'] [class*='error']"
    SOCIAL_PACKAGE_ERROR = "div[data-field-id='socialPackage'] .text-red-500, div[data-field-id='socialPackage'] [class*='error']"

    # ═══════════════════════════════════════
    # ОСНОВНЫЕ ПАРАМЕТРЫ
    # ═══════════════════════════════════════

    # Название вакансии (обязательное)
    TITLE_FIELD = "div[data-field-id='title']"
    TITLE_INPUT = "div[data-field-id='title'] input[type='text']"
    TITLE_LABEL = "div[data-field-id='title'] label"
    ADD_INTERNAL_LABEL = "button:has-text('Добавить внутреннюю метку')"

    # Описание вакансии (обязательное, Quill editor)
    DESCRIPTION_FIELD = "div[data-field-id='description']"
    DESCRIPTION_EDITOR = (
        "div[data-field-id='description'] .ql-editor"
    )
    DESCRIPTION_LABEL = "div[data-field-id='description'] label"

    # О компании (обязательное, Quill editor)
    COMPANY_DESCRIPTION_FIELD = (
        "div[data-field-id='companyDescription']"
    )
    COMPANY_DESCRIPTION_EDITOR = (
        "div[data-field-id='companyDescription'] .ql-editor"
    )
    COMPANY_DESCRIPTION_LABEL = (
        "div[data-field-id='companyDescription'] label"
    )

    # Соц. пакет
    SOCIAL_PACKAGE_FIELD = "div[data-field-id='socialPackage']"
    SOCIAL_PACKAGE_TEXTAREA = (
        "div[data-field-id='socialPackage'] textarea"
    )

    # Отрасль
    INDUSTRY_FIELD = "div[data-field-id='industry']"
    INDUSTRY_BUTTON = "div[data-field-id='industry'] button"

    # Специализация
    SPECIALIZATION_BUTTON = "button:has-text('Выберите специализацию')"

    # ═══════════════════════════════════════
    # НАВЫКИ
    # ═══════════════════════════════════════

    SKILLS_SECTION = "div[data-field-id='skills']"
    SKILL_INPUT = (
        "div[data-field-id='skills'] input[placeholder='Добавьте навык...']"
    )
    SKILL_ADD_BUTTON = (
        "div[data-field-id='skills'] button:has-text('Добавить')"
    )
    ADD_MORE_SKILL_FIELD = "button:has-text('Добавить еще поле')"

    # ═══════════════════════════════════════
    # ОПЫТ РАБОТЫ
    # ═══════════════════════════════════════

    EXPERIENCE_SECTION = "div[data-field-id='experience']"
    EXCLUDE_JUMPERS = "span:has-text('Исключить кандидатов-джамперов')"

    # ═══════════════════════════════════════
    # УСЛОВИЯ (ЗАРПЛАТА)
    # ═══════════════════════════════════════

    SALARY_SECTION = "div[data-field-id='salary']"
    SALARY_FROM = (
        "div[data-field-id='salary'] input[placeholder='от']"
    )
    SALARY_TO = (
        "div[data-field-id='salary'] input[placeholder='до *']"
    )

    # ═══════════════════════════════════════
    # ГЕОГРАФИЯ
    # ═══════════════════════════════════════

    REGION_SECTION = "div[data-field-id='region']"
    CITY_BUTTON = "button:has-text('Выберите города')"
    AGE_FROM = (
        "div[data-field-id='region'] input[placeholder='от']"
    )
    AGE_TO = (
        "div[data-field-id='region'] input[placeholder='до']"
    )
    GENDER_ANY = "input[value='any']"
    GENDER_MALE = "input[value='male']"
    GENDER_FEMALE = "input[value='female']"

    # ═══════════════════════════════════════
    # ФОРМАТ РАБОТЫ
    # ═══════════════════════════════════════

    WORK_FORMAT_SECTION = "div[data-field-id='workFormat']"
    WORK_FORMAT_SELECT = (
        "div[data-field-id='workFormat'] select >> nth=0"
    )
    WORK_SCHEDULE_SELECT = (
        "div[data-field-id='workFormat'] select >> nth=1"
    )
    WORK_HOURS_SELECT = (
        "div[data-field-id='workFormat'] select >> nth=2"
    )

    # ═══════════════════════════════════════
    # ТОГЛЫ
    # ═══════════════════════════════════════

    AI_SCREENING_TOGGLE = (
        "span:has-text('AI-скрининг') >> "
        "xpath=../.. >> button[aria-pressed]"
    )
    HR_INTERVIEW_TOGGLE = (
        "span:has-text('HR-интервью') >> "
        "xpath=../.. >> button[aria-pressed]"
    )

    # ═══════════════════════════════════════
    # МЕТОДЫ — НАВИГАЦИЯ
    # ═══════════════════════════════════════

    def open(self):
        """Открывает страницу создания вакансии напрямую"""
        self.navigate(self.PATH)
        return self

    def get_vacancy_id_from_url(self) -> int | None:
        """Извлекает ID созданной вакансии из URL (pattern: /vacancy/{id}).

        Side-effect: если id успешно извлечён, регистрируем его в
        session_registry. Этот метод вызывают из тестов ПОСЛЕ того,
        как они уже дождались редиректа на detail-страницу созданной
        вакансии — то есть вызов почти всегда означает «вот id моей
        только что созданной вакансии». Регистрация здесь — вторая
        линия страховки к регистрации в click_create_vacancy:
        если best-effort там не уложился в таймаут, реестр всё равно
        получит нужный id из этой точки.
        """
        try:
            match = re.search(r'/vacancy/(\d+)', self.page.url)
            vid = int(match.group(1)) if match else None
        except Exception:
            return None
        if vid:
            session_registry.register(vid)
            # Дублируем привязку к Allure: если network-listener по какой-то
            # причине не отработал (например, вакансия создана не этим
            # page-контекстом), всё равно прикрепим vacancy_id к текущему
            # тесту, чтобы в отчёте было по чему искать.
            attach_vacancy_id(vid)
        return vid

    @allure.step("Проверяем загрузку страницы создания вакансии")
    def should_be_loaded(self):
        """Проверяет что страница создания вакансии загружена"""
        self.wait_for_visible(self.PAGE_TITLE)
        self.should_be_visible(self.PAGE_TITLE)
        self.should_be_visible(self.AI_ASSISTANT_TITLE)
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ЗАПОЛНЕНИЕ ПОЛЕЙ
    # ═══════════════════════════════════════

    @allure.step("Вводим название вакансии: {title}")
    def enter_title(self, title: str):
        """Заполняет название вакансии"""
        self.page.locator(self.TITLE_INPUT).fill(title)
        return self

    @allure.step("Вводим описание вакансии")
    def enter_description(self, text: str):
        """Заполняет описание вакансии (Quill editor)"""
        editor = self.page.locator(self.DESCRIPTION_EDITOR)
        editor.wait_for(state="visible", timeout=5000)

        # Вставляем текст напрямую через Quill API
        editor.evaluate(
            """(el, text) => {
                // Находим экземпляр Quill
                const quill = el.__quill 
                    || el.closest('.ql-container')?.__quill
                    || window.Quill?.find(el.closest('.ql-container'));

                if (quill) {
                    quill.setText(text);
                } else {
                    // Fallback: innerHTML + событие input
                    el.innerHTML = '<p>' + text + '</p>';
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }""",
            text
        )
        # Кликаем чтобы активировать валидацию фреймворка
        editor.click()
        self.page.wait_for_timeout(300)
        return self

    @allure.step("Вводим описание компании")
    def enter_company_description(self, text: str):
        """Заполняет описание компании (Quill editor)"""
        editor = self.page.locator(self.COMPANY_DESCRIPTION_EDITOR)
        editor.wait_for(state="visible", timeout=5000)

        editor.evaluate(
            """(el, text) => {
                const quill = el.__quill 
                    || el.closest('.ql-container')?.__quill
                    || window.Quill?.find(el.closest('.ql-container'));

                if (quill) {
                    quill.setText(text);
                } else {
                    el.innerHTML = '<p>' + text + '</p>';
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }""",
            text
        )

        editor.click()
        self.page.wait_for_timeout(300)
        return self

    @allure.step("Вводим соц. пакет: {text}")
    def enter_social_package(self, text: str):
        """Заполняет соц. пакет — очищает перед вводом"""
        textarea = self.page.locator(self.SOCIAL_PACKAGE_TEXTAREA)
        textarea.click()
        textarea.fill("")  # Очищаем
        textarea.fill(text)
        return self

    @allure.step("Вводим зарплату от: {salary_from}, до: {salary_to}")
    def enter_salary(self, salary_from: str = "", salary_to: str = ""):
        """Заполняет зарплатные ожидания"""
        if salary_from:
            self.page.locator(self.SALARY_FROM).fill(salary_from)
        if salary_to:
            self.page.locator(self.SALARY_TO).fill(salary_to)
        return self

    @allure.step("Добавляем навык: {skill}")
    def add_skill(self, skill: str):
        """Добавляет один навык"""
        self.page.locator(self.SKILL_INPUT).fill(skill)
        # exact=True чтобы не ловить "Добавить еще поле"
        self.page.locator(self.SKILLS_SECTION).get_by_role(
            "button", name="Добавить", exact=True
        ).click()
        return self

    @allure.step("Добавляем навыки: {skills}")
    def add_skills(self, skills: list[str]):
        """Добавляет список навыков"""
        for skill in skills:
            self.add_skill(skill)
        return self

    @allure.step('Выбираем формат работы: {value}')
    def select_work_format(self, value: str):
        select = self.page.locator(self.WORK_FORMAT_SELECT)
        select.wait_for(state='visible', timeout=10000)

        # Поддержка синтаксиса 'value=Офис'
        if value.startswith('value='):
            actual_value = value[6:]  # убираем префикс 'value='
            select.select_option(label=actual_value)
        else:
            try:
                select.select_option(label=value, timeout=5000)
            except Exception:
                mapping = {
                    'Удаленка': 'remote',
                    'Офис': 'office',
                    'Гибрид': 'hybrid',
                }
                eng_value = mapping.get(value, value)
                select.select_option(value=eng_value, timeout=5000)
        return self


    @allure.step("Выбираем график: {value}")
    def select_work_schedule(self, value: str):
        """Выбирает график работы"""
        self.page.locator(self.WORK_SCHEDULE_SELECT).select_option(value)
        return self

    @allure.step("Вводим возраст от: {age_from}, до: {age_to}")
    def enter_age(self, age_from: str = "", age_to: str = ""):
        """Заполняет возрастные ограничения"""
        if age_from:
            self.page.locator(self.AGE_FROM).fill(age_from)
        if age_to:
            self.page.locator(self.AGE_TO).fill(age_to)
        return self

    @allure.step("Выбираем пол: {gender}")
    def select_gender(self, gender: str):
        """Выбирает пол: 'any', 'male', 'female'"""
        self.page.locator(f"input[value='{gender}']").check()
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ЧЕКБОКСЫ ОПЫТА
    # ═══════════════════════════════════════

    @allure.step("Выбираем опыт в должности: {label}")
    def check_position_experience(self, label: str):
        """Выбирает чекбокс опыта в должности"""
        self.page.locator(
            f"div[data-field-id='experience'] >> nth=0 >> "
            f"label:has-text('{label}') input"
        ).check()
        return self

    @allure.step("Выбираем общий опыт: {label}")
    def check_total_experience(self, label: str):
        """Выбирает чекбокс общего опыта"""
        self.page.locator(
            f"div[data-field-id='experience'] >> nth=1 >> "
            f"label:has-text('{label}') input"
        ).check()
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ТОГЛЫ
    # ═══════════════════════════════════════

    def _get_toggle_by_label(self, label: str):
        """Находит тогл по его текстовой метке"""
        # Ищем карточку, содержащую нужный label
        card = self.page.locator(
            f".flex-1.bg-white.rounded-\\[16px\\]:has(span:has-text('{label}'))"
        )
        return card.locator("button[aria-pressed]")

    @allure.step("Переключаем AI-скрининг")
    def toggle_ai_screening(self):
        self._get_toggle_by_label("AI-скрининг").click()
        return self

    @allure.step("Переключаем HR-интервью")
    def toggle_hr_interview(self):
        self._get_toggle_by_label("HR-интервью").click()
        return self

    def is_ai_screening_enabled(self) -> bool:
        return self._get_toggle_by_label(
            "AI-скрининг"
        ).get_attribute("aria-pressed") == "true"

    def is_hr_interview_enabled(self) -> bool:
        return self._get_toggle_by_label(
            "HR-интервью"
        ).get_attribute("aria-pressed") == "true"

    # ═══════════════════════════════════════
    # МЕТОДЫ — КНОПКИ
    # ═══════════════════════════════════════

    @allure.step("Сохраняем вакансию ('Сохранить и продолжить')")
    def click_create_vacancy(self):
        """Создаёт вакансию и переходит на detail-страницу.

        Быстрый путь (используется по умолчанию):
            Клик по кнопке «Сохранить и продолжить» в нижней части формы.
            Этот путь НЕ запускает AI-анализ требований и не требует
            ожидания ответа LLM — сразу делает POST /api/v1/positions
            и SPA редиректит на /recruiter/vacancy/{id}.

        Fallback-пути (для обратной совместимости):
            — Если на форме уже отрендерена кнопка «Создать вакансию»
              (редкий путь: AI-анализ уже прошёл в рамках текущего сеанса),
              кликаем её напрямую.
            — Иначе — старый multi-step flow через «Далее: требования»
              с ожиданием окончания AI-анализа.

        NEXT_REQUIREMENTS_BUTTON остаётся в page-object как селектор,
        но в основных тестах не используется: он нужен только для
        специализированных сценариев проверки AI-панели требований.

        Перед кликом primary-кнопки метод ждёт исчезновения amber-подсказки
        «не менее 150 символов». Это типичная задержка перерасчёта счётчика
        у фронта после заполнения Quill-редакторов. Для negative-сценариев,
        где подсказка остаётся специально, таймаут истекает тихо, без
        исключения.
        """
        self._wait_min_chars_warning_cleared()

        save_continue = self.page.locator(self.SAVE_AND_CONTINUE_BUTTON)
        if save_continue.count() > 0 and save_continue.first.is_visible():
            save_continue.first.click()
            return self

        create_btn = self.page.locator(self.CREATE_VACANCY_BUTTON)
        if create_btn.count() > 0 and create_btn.first.is_visible():
            create_btn.first.click()
            return self

        next_btn = self.page.locator(self.NEXT_REQUIREMENTS_BUTTON)
        next_btn.first.wait_for(state="visible", timeout=10_000)
        next_btn.first.click()
        create_btn.first.wait_for(
            state="visible",
            timeout=self.REQUIREMENTS_AI_TIMEOUT_MS,
        )
        create_btn.first.click()
        return self

    # Заметка про регистрацию id созданной вакансии:
    # раньше здесь был блокирующий best-effort wait_for_url('/vacancy/\d+')
    # после каждого клика. Он:
    #   • для negative-тестов (нет редиректа) прибавлял 20 секунд простоя
    #     после клика — за это время успевал появиться и исчезнуть тост
    #     валидации, и следующий шаг теста не находил его;
    #   • для медленных тестов (9000 символов описания) удваивал ожидание
    #     с 20 до 40 секунд.
    # Теперь регистрация id происходит неблокирующе через network-listener
    # на POST /api/v1/positions (conftest.authenticated_page) — нулевая
    # задержка, плюс второй контур через get_vacancy_id_from_url как
    # страховка, если listener не успел сработать.

    def _wait_min_chars_warning_cleared(
        self, timeout: int | None = None
    ) -> None:
        """Ждёт исчезновения amber-подсказки «не менее 150 символов».

        Подсказка видна, пока суммарная длина текстовых полей (описание,
        О компании, соц. пакет) меньше 150. Фронт перерасчитывает счётчик
        с задержкой — особенно после Quill-редакторов. Ждём с «мягким»
        таймаутом: если подсказка так и осталась видна (negative-кейс
        или пустая форма), не кидаем исключение — просто возвращаем
        управление и даём тесту самому решать что проверять дальше.
        """
        timeout_ms = timeout if timeout is not None else self.MIN_CHARS_WAIT_MS
        try:
            warn = self.page.locator(self.MIN_CHARS_WARNING)
            if warn.count() > 0 and warn.first.is_visible():
                warn.first.wait_for(state="hidden", timeout=timeout_ms)
        except Exception:
            pass

    @allure.step("Нажимаем 'Отмена'")
    def click_cancel(self):
        """Нажимает кнопку 'Отмена'"""
        self.page.locator(self.CANCEL_BUTTON).click()
        return self

    @allure.step("Нажимаем 'Сохранить и продолжить'")
    def click_save_and_continue(self):
        """Нажимает кнопку 'Сохранить и продолжить'"""
        self.page.locator(self.SAVE_AND_CONTINUE_BUTTON).click()
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ТАБЫ
    # ═══════════════════════════════════════

    @allure.step("Переключаемся на таб '{tab_name}'")
    def switch_tab(self, tab_name: str):
        """Переключает таб: 'Настройка вакансии', 'Настройка рассылки', 'Настройка интервью'"""
        self.page.locator(f"p:has-text('{tab_name}')").click()
        return self

    def get_active_tab(self) -> str:
        """Возвращает текст активного таба (ищем <p> внутри контейнера с тенью)."""
        active = self.page.locator(
            "div.bg-white[class*='shadow-'] p"
        ).first
        return active.inner_text().strip()


    # ═══════════════════════════════════════
    # МЕТОДЫ — AI АССИСТЕНТ
    # ═══════════════════════════════════════

    @allure.step("Вводим текст в AI ассистент: {text}")
    def enter_ai_prompt(self, text: str):
        """Вводит текст в поле AI ассистента"""
        self.page.locator(self.AI_ASSISTANT_TEXTAREA).fill(text)
        return self

    @allure.step("Сбрасываем AI ассистент")
    def reset_ai_assistant(self):
        """Нажимает кнопку сброса AI ассистента"""
        self.page.locator(self.AI_ASSISTANT_RESET).click()
        return self

    @allure.step("Проверяем видимость AI Ассистента")
    def should_ai_assistant_be_visible(self):
        """Проверяет видимость AI ассистента в правой панели"""
        self.should_be_visible(self.AI_ASSISTANT_TITLE)
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ПРОВЕРКИ ПОЛЕЙ
    # ═══════════════════════════════════════

    def get_title_value(self) -> str:
        """Возвращает значение поля названия"""
        return self.page.locator(self.TITLE_INPUT).input_value()

    def get_salary_from_value(self) -> str:
        """Возвращает значение поля 'зарплата от'"""
        return self.page.locator(self.SALARY_FROM).input_value()

    def get_salary_to_value(self) -> str:
        """Возвращает значение поля 'зарплата до'"""
        return self.page.locator(self.SALARY_TO).input_value()

    def is_title_empty(self) -> bool:
        """Проверяет пустое ли поле названия"""
        return self.get_title_value() == ""

    # ═══════════════════════════════════════
    # МЕТОДЫ — КОМПЛЕКСНОЕ ЗАПОЛНЕНИЕ
    # ═══════════════════════════════════════

    @allure.step("Заполняем минимально необходимые поля")
    def fill_required_fields(
        self,
        title: str,
        description: str,
        company_description: str,
        salary_to: str,
    ):
        """Заполняет все обязательные поля"""
        self.enter_title(title)
        self.enter_description(description)
        self.enter_company_description(company_description)
        self.enter_salary(salary_to=salary_to)
        return self

    @allure.step("Заполняем все поля вакансии")
    def fill_full_vacancy(
        self,
        title: str,
        description: str,
        company_description: str,
        salary_from: str,
        salary_to: str,
        social_package: str = "",
        skills: list[str] = None,
        work_format: str = "",
        work_schedule: str = "",
    ):
        """Заполняет все поля вакансии"""
        self.enter_title(title)
        self.enter_description(description)
        self.enter_company_description(company_description)
        self.enter_salary(salary_from, salary_to)

        if social_package:
            self.enter_social_package(social_package)
        if skills:
            self.add_skills(skills)
        if work_format:
            self.select_work_format(work_format)
        if work_schedule:
            self.select_work_schedule(work_schedule)

        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ПОЛУЧЕНИЕ ДЛИНЫ ТЕКСТА
    # ═══════════════════════════════════════

    @allure.step("Получаем длину названия вакансии")
    def get_title_length(self) -> int:
        return len(self.get_title_value())

    @allure.step("Получаем длину описания вакансии")
    def get_description_length(self) -> int:
        text = self.page.locator(self.DESCRIPTION_EDITOR).inner_text()
        return len(text.strip())

    @allure.step("Получаем длину описания компании")
    def get_company_description_length(self) -> int:
        text = self.page.locator(
            self.COMPANY_DESCRIPTION_EDITOR
        ).inner_text()
        return len(text.strip())

    @allure.step("Получаем длину соц. пакета")
    def get_social_package_length(self) -> int:
        return len(
            self.page.locator(
                self.SOCIAL_PACKAGE_TEXTAREA
            ).input_value()
        )

    # ═══════════════════════════════════════
    # МЕТОДЫ — ОЧИСТКА ПОЛЕЙ
    # ═══════════════════════════════════════

    @allure.step("Очищаем название вакансии")
    def clear_title(self):
        self.page.locator(self.TITLE_INPUT).fill("")
        return self

    @allure.step("Очищаем описание вакансии")
    def clear_description(self):
        editor = self.page.locator(self.DESCRIPTION_EDITOR)
        editor.evaluate("el => el.innerHTML = ''")
        return self

    @allure.step("Очищаем описание компании")
    def clear_company_description(self):
        editor = self.page.locator(self.COMPANY_DESCRIPTION_EDITOR)
        editor.evaluate("el => el.innerHTML = ''")
        return self

    @allure.step("Очищаем соц. пакет")
    def clear_social_package(self):
        self.page.locator(self.SOCIAL_PACKAGE_TEXTAREA).fill("")
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ПРОВЕРКА ОШИБОК ВАЛИДАЦИИ
    # ═══════════════════════════════════════

    @allure.step("Проверяем наличие ошибки у названия")
    def should_title_have_error(self):
        """Проверяет что у поля названия есть ошибка валидации"""
        # Поле может подсветиться красным или появится текст ошибки
        title_input = self.page.locator(self.TITLE_INPUT)
        border_color = title_input.evaluate(
            "el => getComputedStyle(el).borderColor"
        )
        has_red_border = "rgb(239" in border_color or "rgb(255, 0" in border_color or "rgb(220" in border_color
        has_error_text = self.page.locator(self.TITLE_ERROR).count() > 0
        assert has_red_border or has_error_text, \
            f"Ожидалась ошибка валидации у названия. Border: {border_color}"
        return self

    @allure.step("Проверяем что страница осталась на создании (форма не отправлена)")
    def should_stay_on_create_page(self):
        """Проверяет что мы остались на странице создания"""
        self.should_be_visible(self.PAGE_TITLE)
        return self

    @allure.step("Заполняем все обязательные поля кроме: {skip_field}")
    def fill_all_required_except(self, skip_field: str):
        """
        Заполняет все обязательные поля валидными данными,
        кроме указанного.
        skip_field: 'title', 'description', 'company', 'salary_to', 'none'
        """
        if skip_field != "title":
            self.enter_title("ALIQATEST Валидация")
        if skip_field != "description":
            self.enter_description("А" * 150)
        if skip_field != "company":
            self.enter_company_description("А" * 100)
        if skip_field != "salary_to":
            self.enter_salary(salary_to="200000")
        return self

    # ═══════════════════════════════════════
    # МОДАЛКИ — ОБЩИЕ ЛОКАТОРЫ
    # ═══════════════════════════════════════

    MODAL_CONTAINER = ".modal-container"
    MODAL_SEARCH_INPUT = ".modal-container input[type='text']"
    MODAL_SAVE_BUTTON = ".modal-container button:has-text('Сохранить')"
    MODAL_CANCEL_BUTTON = ".modal-container button:has-text('Отменить')"
    MODAL_RESET_BUTTON = ".modal-container button:has-text('Сбросить')"
    MODAL_CLOSE_BUTTON = (".modal-container button.p-2.rounded-lg:has(svg path[d='M6 18 18 6M6 6l12 12'])"
    )

    # Все чекбоксы в модалках (Area/Industry/Specialization) используют общий
    # компонент HierarchicalCheckbox → <input id="hierarchical-checkbox-{id}">
    # с <label for="hierarchical-checkbox-{id}">. Это даёт чистые селекторы
    # без зависимости от tailwind-классов.
    MODAL_CHECKBOX = ".modal-container input[id^='hierarchical-checkbox-']"
    MODAL_LABEL = ".modal-container label[for^='hierarchical-checkbox-']"
    # Строка-обёртка одного элемента (ряд с чекбоксом + label + опционально
    # кнопкой-стрелкой для раскрытия детей).
    MODAL_ROW = ".modal-container div.py-2.px-3.flex.items-center"

    # Гражданство — отдельная структура
    CITIZENSHIP_MODAL = ".bg-white.rounded-\\[24px\\]"
    CITIZENSHIP_SEARCH = (
        ".bg-white.rounded-\\[24px\\] "
        "input[placeholder='Поиск страны...']"
    )
    CITIZENSHIP_APPLY = (
        ".bg-white.rounded-\\[24px\\] "
        "button:has-text('Применить')"
    )

    # ═══════════════════════════════════════
    # МОДАЛКИ — КНОПКИ ОТКРЫТИЯ
    # ═══════════════════════════════════════

    INDUSTRY_OPEN_BUTTON = (
        "div[data-field-id='industry'] button"
    )

    # Привязка к label, а не к placeholder-тексту кнопки.
    # После save placeholder заменяется именами выбранных элементов —
    # `has-text('Выберите ...')` становится stale. `label:text-is(...)`
    # работает и до, и после выбора.
    SPECIALIZATION_OPEN_BUTTON = (
        "label:text-is('Специализация') + button"
    )
    GEOGRAPHY_OPEN_BUTTON = (
        "div[data-field-id='region'] "
        "label:text-is('География') + div button"
    )
    CITIZENSHIP_OPEN_BUTTON = (
        "label:text-is('Гражданство') + button"
    )

    # Город (появляется при value=Офис/Гибрид)
    CITY_OPEN_BUTTON = (
        "div[data-field-id='workFormat'] "
        "label:text-is('Город') + button"
    )

    # ═══════════════════════════════════════
    # ФОРМАТ РАБОТЫ — УСЛОВНЫЕ ПОЛЯ
    # ═══════════════════════════════════════

    ADDRESS_INPUT = "input[placeholder='Например: ул. Ленина, 1']"
    METRO_BUTTON = (
        "div[data-field-id='workFormat'] "
        "label:has-text('Ближайшее метро') + div button"
    )
    ADD_ADDRESS_BUTTON = "button:has-text('+ Добавить адрес')"
    METRO_CHECKBOX = (
        "span:has-text('Учитывать в поиске станцию метро')"
    )

    # ═══════════════════════════════════════
    # МЕТОДЫ — ОТКРЫТИЕ МОДАЛОК
    # ═══════════════════════════════════════

    @allure.step("Открываем модалку отраслей")
    def open_industry_modal(self):
        btn = self.page.locator(self.INDUSTRY_OPEN_BUTTON).first
        btn.scroll_into_view_if_needed()
        btn.wait_for(state='visible', timeout=10000)
        btn.click()
        self.page.locator(self.MODAL_CONTAINER).wait_for(
            state='visible', timeout=5000
        )
        return self


    @allure.step("Открываем модалку специализаций")
    def open_specialization_modal(self):
        self.page.locator(self.SPECIALIZATION_OPEN_BUTTON).click()
        self.page.locator(self.MODAL_CONTAINER).wait_for(
            state="visible", timeout=5000
        )
        return self

    @allure.step("Открываем модалку географии")
    def open_geography_modal(self):
        self.page.locator(self.GEOGRAPHY_OPEN_BUTTON).click()
        self.page.locator(self.MODAL_CONTAINER).wait_for(
            state="visible", timeout=5000
        )
        return self

    @allure.step("Открываем модалку гражданства")
    def open_citizenship_modal(self):
        self.page.locator(self.CITIZENSHIP_OPEN_BUTTON).click()
        self.page.locator(self.CITIZENSHIP_MODAL).wait_for(
            state="visible", timeout=5000
        )
        return self

    @allure.step("Открываем модалку выбора города")
    def open_city_modal(self):
        self.page.locator(self.CITY_OPEN_BUTTON).click()
        self.page.locator(self.MODAL_CONTAINER).wait_for(
            state="visible", timeout=5000
        )
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ДЕЙСТВИЯ В МОДАЛКАХ
    # ═══════════════════════════════════════

    @allure.step("Ищем в модалке: {query}")
    def search_in_modal(self, query: str):
        search = self.page.locator(self.MODAL_SEARCH_INPUT)
        search.fill(query)
        self.page.locator(
            f".modal-container label:has-text('{query}')"
        ).first.wait_for(state="visible", timeout=5000)
        return self

    @allure.step("Выбираем элемент в модалке: {label}")
    def select_modal_item(self, label: str):
        """Кликает по label элемента в открытой модалке (вызывает onChange чекбокса)."""
        self.page.locator(self.MODAL_LABEL).filter(
            has_text=label
        ).first.click()
        return self

    @allure.step("Сохраняем модалку")
    def save_modal(self):
        btn = self.page.locator(self.MODAL_SAVE_BUTTON)
        btn.wait_for(state="visible", timeout=5000)
        btn.click(timeout=15000)
        self.page.locator(self.MODAL_CONTAINER).wait_for(
            state="hidden", timeout=5000
        )
        return self

    @allure.step("Отменяем модалку")
    def cancel_modal(self):
        self.page.locator(self.MODAL_CANCEL_BUTTON).click()
        self.page.locator(self.MODAL_CONTAINER).wait_for(state="hidden", timeout=5000)
        return self

    @allure.step("Сбрасываем модалку")
    def reset_modal(self):
        self.page.locator(self.MODAL_RESET_BUTTON).click()
        return self

    @allure.step("Закрываем модалку крестиком")
    def close_modal(self):
        self.page.locator(self.MODAL_CLOSE_BUTTON).click()
        self.page.locator(self.MODAL_CONTAINER).wait_for(state="hidden", timeout=5000)
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ГРАЖДАНСТВО
    # ═══════════════════════════════════════

    @allure.step("Ищем гражданство: {query}")
    def search_citizenship(self, query: str):
        self.page.locator(self.CITIZENSHIP_SEARCH).fill(query)
        self.page.locator(
            f"{self.CITIZENSHIP_MODAL} button:has(span:has-text('{query}'))"
        ).first.wait_for(state="visible", timeout=5000)
        return self

    @allure.step("Выбираем гражданство: {country}")
    def select_citizenship(self, country: str):
        self.page.locator(
            f".bg-white.rounded-\\[24px\\] "
            f"button:has(span:has-text('{country}'))"
        ).click()
        return self

    @allure.step("Применяем гражданство")
    def apply_citizenship(self):
        self.page.locator(self.CITIZENSHIP_APPLY).click()
        self.page.locator(self.CITIZENSHIP_MODAL).wait_for(state="hidden", timeout=5000)
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ГЕОГРАФИЯ (СТРАНЫ-КНОПКИ)
    # ═══════════════════════════════════════

    @allure.step("Выбираем страну: {country}")
    def select_geography_country(self, country: str):
        self.page.locator(
            f".modal-container "
            f"button:has(span:has-text('{country}'))"
        ).click()
        return self

    # ═══════════════════════════════════════
    # МЕТОДЫ — ФОРМАТ РАБОТЫ (УСЛОВНЫЕ ПОЛЯ)
    # ═══════════════════════════════════════

    @allure.step("Проверяем что город '{city}' отображается на форме")
    def should_selected_city_be_visible(self, city: str):
        """После сохранения city-модалки кнопка с именем города видна на форме."""
        btn = self.page.locator(
            f"div[data-field-id='workFormat'] button:has-text('{city}')"
        )
        btn.wait_for(state="visible", timeout=5000)
        return self

    @allure.step("Проверяем появление поля 'Город'")
    def should_city_field_be_visible(self):
        self.page.locator(self.CITY_OPEN_BUTTON).wait_for(
            state="visible", timeout=5000
        )
        return self

    @allure.step("Проверяем что поле 'Город' НЕ видно")
    def should_city_field_not_exist(self):
        assert self.page.locator(
            self.CITY_OPEN_BUTTON
        ).count() == 0 or not self.page.locator(
            self.CITY_OPEN_BUTTON
        ).is_visible()
        return self

    @allure.step("Проверяем появление поля 'Адрес'")
    def should_address_field_be_visible(self):
        self.page.locator(self.ADDRESS_INPUT).first.wait_for(
            state="visible", timeout=5000
        )
        return self

    @allure.step("Вводим адрес: {address}")
    def enter_address(self, address: str):
        self.page.locator(self.ADDRESS_INPUT).first.fill(address)
        return self

    @allure.step("Проверяем наличие дропдауна метро")
    def should_metro_be_visible(self):
        self.page.locator(
            "label:has-text('Ближайшее метро')"
        ).first.wait_for(state="visible", timeout=5000)
        return self

    @allure.step("Нажимаем '+ Добавить адрес или метро'")
    def click_add_address_or_metro(self):
        self.page.locator(self.ADD_ADDRESS_BUTTON).click()
        return self

    def get_address_count(self) -> int:
        return self.page.locator(self.ADDRESS_INPUT).count()

    # ═══════════════════════════════════════
    # МЕТОДЫ — ПРОВЕРКИ ОТОБРАЖЕНИЯ НА ФОРМЕ
    # ═══════════════════════════════════════

    @allure.step("Получаем текст кнопки географии")
    def get_geography_button_text(self) -> str:
        btn = self.page.locator(
            "div[data-field-id='region'] "
            "label:has-text('География') + div button"
        ).first
        return btn.inner_text()

    @allure.step("Получаем текст кнопки гражданства")
    def get_citizenship_button_text(self) -> str:
        btn = self.page.locator(
            "label:has-text('Гражданство') + button"
        )
        return btn.inner_text()

    @allure.step("Получаем текст кнопки отрасли")
    def get_industry_button_text(self) -> str:
        return self.page.locator(
            "div[data-field-id='industry'] button"
        ).first.inner_text()

    @allure.step("Получаем полный текст поля Отрасль")
    def get_industry_field_text(self) -> str:
        """Весь видимый текст зоны отрасли (теги + кнопки после сохранения)"""
        return self.page.locator(self.INDUSTRY_FIELD).inner_text()

    @allure.step("Получаем полный текст поля Специализация")
    def get_specialization_field_text(self) -> str:
        """Весь видимый текст зоны специализации (теги + кнопки после сохранения)"""
        spec = self.page.locator("div[data-field-id='specialization']")
        if spec.count() > 0:
            return spec.inner_text()
        # After saving the modal the button text changes — find section by label
        lbl = self.page.locator("label:has-text('Специализация')")
        if lbl.count() > 0:
            return lbl.locator("xpath=..").inner_text()
        # Fallback: button still says "Выберите специализацию" (before any selection)
        btn = self.page.locator(self.SPECIALIZATION_OPEN_BUTTON)
        if btn.count() > 0:
            return btn.locator("xpath=..").inner_text()
        return ""

    @allure.step("Получаем полный текст поля Регион/География")
    def get_geography_field_text(self) -> str:
        """Весь видимый текст секции региона (теги + кнопки после сохранения)"""
        return self.page.locator(self.REGION_SECTION).inner_text()

    @allure.step("Получаем полный текст секции Формат работы")
    def get_work_format_section_text(self) -> str:
        """Весь видимый текст секции формата работы (включая выбранный город)"""
        return self.page.locator(self.WORK_FORMAT_SECTION).inner_text()

    @allure.step("Выбираем несколько элементов в модалке через поиск: {items}")
    def select_modal_items(self, items: list[str]):
        """Выбирает каждый элемент в открытой модалке через поиск по имени"""
        for item in items:
            search = self.page.locator(self.MODAL_SEARCH_INPUT)
            search.fill(item)
            self.page.locator(
                f".modal-container label:has-text('{item}')"
            ).first.wait_for(state="visible", timeout=5000)
            self.select_modal_item(item)
        return self

    @allure.step("Раскрываем '{region}' и выбираем первые {n} городов")
    def expand_region_and_select_n_cities(
        self, region: str, n: int
    ) -> list[str]:
        """
        В открытой модалке находит регион, раскрывает его список городов
        и выбирает первые N. Возвращает список выбранных текстов.
        Работает для модалок Города (workFormat) и Географии.
        """
        search = self.page.locator(self.MODAL_SEARCH_INPUT)
        if search.count() > 0 and search.is_visible():
            search.fill(region)

        region_label = self.page.locator(
            f".modal-container label:has-text('{region}')"
        ).first
        region_label.wait_for(state="visible", timeout=10000)

        parent = region_label.locator("xpath=..")
        expand_btn = parent.locator("button:has(svg)")
        if expand_btn.count() > 0:
            expand_btn.click()
            self.page.wait_for_timeout(500)

        # Собираем labels городов — те, у чьих родителей нет expand-кнопки
        selected: list[str] = []
        all_labels = self.page.locator(".modal-container label")
        for i in range(all_labels.count()):
            if len(selected) >= n:
                break
            lbl = all_labels.nth(i)
            text = lbl.inner_text().strip()
            if not text or text == region:
                continue
            lbl_parent = lbl.locator("xpath=..")
            if lbl_parent.locator("button:has(svg)").count() > 0:
                continue  # Это другой регион, пропускаем
            checkbox = lbl_parent.locator("input[type='checkbox']")
            if checkbox.count() > 0 and not checkbox.is_checked():
                try:
                    if checkbox.is_disabled():
                        continue
                    checkbox.click()
                    selected.append(text)
                except Exception:
                    continue

        return selected

    @allure.step("Выбираем первые {n} элементов в модалке без поиска")
    def select_first_n_modal_items(self, n: int) -> list[str]:
        """
        Кликает по чекбоксам первых N видимых enabled-элементов модалки.
        Пропускает: служебные labels («Выбрать», «Выбрать все»),
        disabled-чекбоксы (фильтры типа «Период» в модалке отраслей).
        Возвращает список выбранных текстовых меток.
        """
        labels_loc = self.page.locator(".modal-container label")
        labels_loc.first.wait_for(state="visible", timeout=5000)
        total = labels_loc.count()
        result = []
        for i in range(total):
            if len(result) >= n:
                break
            lbl = labels_loc.nth(i)
            text = lbl.inner_text().strip()
            # Пропускаем пустые и служебные метки
            if not text or "Выбрать" in text:
                continue
            parent = lbl.locator("xpath=..")
            checkbox = parent.locator("input[type='checkbox']")
            if checkbox.count() == 0:
                continue
            try:
                if checkbox.is_disabled():
                    continue
                checkbox.click()
                result.append(text)
            except Exception:
                continue
        return result

    def _collect_modal_candidates(
        self, exclude_checked: bool, exclude_texts: set[str]
    ) -> tuple[list[dict], list[dict]]:
        """
        Возвращает (leaves, parents) — кандидаты для клика и для раскрытия.
        leaf  — ряд без expand-кнопки (конечный выбор).
        parent — ряд с expand-кнопкой (категория/регион).
        Каждый элемент: {"idx": int, "text": str, "checkbox_id": str}.
        """
        labels_loc = self.page.locator(self.MODAL_LABEL)
        total = labels_loc.count()
        leaves: list[dict] = []
        parents: list[dict] = []
        for i in range(total):
            lbl = labels_loc.nth(i)
            try:
                text = lbl.inner_text().strip()
            except Exception:
                continue
            if not text or text in exclude_texts:
                continue
            for_attr = lbl.get_attribute("for") or ""
            if not for_attr.startswith("hierarchical-checkbox-"):
                continue
            checkbox = self.page.locator(f"#{for_attr}")
            try:
                if checkbox.count() == 0 or checkbox.is_disabled():
                    continue
                if exclude_checked and checkbox.is_checked():
                    continue
            except Exception:
                continue

            # parent = label с expand-кнопкой в том же ряду.
            # Ряд — ближайший div.py-2.items-center вверх по DOM.
            row = lbl.locator(
                "xpath=ancestor::div[contains(@class,'py-2') "
                "and contains(@class,'items-center')][1]"
            )
            has_expand = False
            try:
                has_expand = row.locator("button").count() > 0
            except Exception:
                has_expand = False
            entry = {"idx": i, "text": text, "checkbox_id": for_attr}
            (parents if has_expand else leaves).append(entry)
        return leaves, parents

    def _expand_parent_row(self, parent_entry: dict) -> bool:
        """Кликает expand-кнопку parent-ряда. True если удалось."""
        labels_loc = self.page.locator(self.MODAL_LABEL)
        lbl = labels_loc.nth(parent_entry["idx"])
        row = lbl.locator(
            "xpath=ancestor::div[contains(@class,'py-2') "
            "and contains(@class,'items-center')][1]"
        )
        try:
            btn = row.locator("button").first
            if btn.count() == 0:
                return False
            btn.click(timeout=5000)
            self.page.wait_for_timeout(300)
            return True
        except Exception:
            return False

    def _hierarchical_select(
        self, n: int, exclude_checked: bool
    ) -> list[str]:
        """
        Выбирает N элементов в модалке с поддержкой иерархии.
        Стратегия:
          1. Собираем leaves (ряды без expand) и parents (с expand).
          2. Если есть leaves — кликаем случайный, запоминаем текст.
          3. Если leaves нет, но есть не раскрытые parents — раскрываем
             случайный и повторяем.
          4. Если leaves нет и parents нет/все раскрыты — плоский fallback:
             кликаем любой доступный верхний уровень (совместимость с
             модалкой отраслей, где top-level сам по себе leaf).
        """
        import random

        labels_loc = self.page.locator(self.MODAL_LABEL)
        labels_loc.first.wait_for(state="visible", timeout=5000)

        selected: list[str] = []
        tried_parent_texts: set[str] = set()
        # Защита от бесконечного цикла при странной структуре DOM.
        safety = 25
        while len(selected) < n and safety > 0:
            safety -= 1
            exclude = set(selected) | tried_parent_texts
            leaves, parents = self._collect_modal_candidates(
                exclude_checked=exclude_checked,
                exclude_texts=exclude,
            )

            if leaves:
                random.shuffle(leaves)
                for entry in leaves:
                    if len(selected) >= n:
                        break
                    try:
                        labels_loc.nth(entry["idx"]).click()
                        self.page.wait_for_timeout(100)
                        selected.append(entry["text"])
                    except Exception:
                        continue
                continue

            if parents:
                # Раскрываем случайный parent, которого ещё не пробовали.
                fresh_parents = [
                    p for p in parents if p["text"] not in tried_parent_texts
                ]
                pick_from = fresh_parents or parents
                parent = random.choice(pick_from)
                tried_parent_texts.add(parent["text"])
                if not self._expand_parent_row(parent):
                    continue
                continue

            # Совсем нет иерархии — fallback на плоский выбор
            # (industry-модалка или модалка с одним уровнем).
            flat_leaves, _ = self._collect_modal_candidates(
                exclude_checked=exclude_checked,
                exclude_texts=set(selected),
            )
            # ещё одна попытка взять всё что есть, игнорируя leaf/parent
            all_candidates = flat_leaves or parents
            if not all_candidates:
                break
            random.shuffle(all_candidates)
            for entry in all_candidates:
                if len(selected) >= n:
                    break
                try:
                    labels_loc.nth(entry["idx"]).click()
                    self.page.wait_for_timeout(100)
                    selected.append(entry["text"])
                except Exception:
                    continue
            break

        return selected

    # ─────────────────────────────────────────────────────────────
    # JS fast-path для работы с модалками
    #
    # Проблема: в иерархических модалках бывает до 500+ label'ов.
    # Классический Playwright-подход (`.count()`, `.inner_text()`,
    # `.get_attribute()` на каждый элемент) даёт тысячи round-trip'ов
    # Python↔браузер — по 5-15 мс каждый. Итого: десятки секунд на
    # один рандомный выбор.
    #
    # JS fast-path делает всю работу внутри одного `page.evaluate()`:
    # собирает кандидатов, делает Fisher–Yates shuffle и кликает
    # label.click() прямо в браузере. React реагирует так же, как
    # на пользовательский клик (label → checkbox onChange).
    # ─────────────────────────────────────────────────────────────

    _JS_FLAT_PICK_N = """
    ({ n, excludeChecked, excludeTexts }) => {
      const modal = document.querySelector('.modal-container');
      if (!modal) return { error: 'no modal' };
      const exclude = new Set(excludeTexts || []);
      const labels = Array.from(
        modal.querySelectorAll("label[for^='hierarchical-checkbox-']")
      );
      const entries = [];
      for (const lbl of labels) {
        const forId = lbl.getAttribute('for') || '';
        if (!forId.startsWith('hierarchical-checkbox-')) continue;
        const cb = document.getElementById(forId);
        if (!cb || cb.disabled) continue;
        if (excludeChecked && cb.checked) continue;
        const text = (lbl.textContent || '').trim();
        if (!text || exclude.has(text)) continue;
        entries.push({ lbl, text });
      }
      for (let i = entries.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [entries[i], entries[j]] = [entries[j], entries[i]];
      }
      const picked = [];
      for (const e of entries) {
        if (picked.length >= n) break;
        try { e.lbl.click(); picked.push(e.text); } catch (_) {}
      }
      return { picked, available: entries.length };
    }
    """

    def _js_flat_pick_n(
        self,
        n: int,
        exclude_checked: bool = False,
        exclude_texts: set[str] | None = None,
    ) -> list[str]:
        """Один `page.evaluate` — собрать кандидатов и кликнуть N.

        Поведение совпадает с `_flat_random_select`, но вместо тысяч
        round-trip'ов выполняется одним вызовом: React-click на label
        срабатывает так же, как user click (onChange чекбокса).
        """
        self.page.locator(self.MODAL_LABEL).first.wait_for(
            state="visible", timeout=5000
        )
        res = self.page.evaluate(
            self._JS_FLAT_PICK_N,
            {
                "n": n,
                "excludeChecked": bool(exclude_checked),
                "excludeTexts": list(exclude_texts or []),
            },
        )
        if isinstance(res, dict) and res.get("error"):
            return []
        return list(res.get("picked") or [])

    def _flat_random_select(
        self,
        n: int,
        exclude_checked: bool,
        exclude_texts: set[str] | None = None,
    ) -> list[str]:
        """Плоский случайный выбор. Пробует JS fast-path, fallback на Python."""
        picked = self._js_flat_pick_n(
            n=n,
            exclude_checked=exclude_checked,
            exclude_texts=exclude_texts,
        )
        if picked:
            return picked

        # Fallback: старый Python-путь (медленнее, но надёжнее в редких
        # DOM-структурах, где label.click() не вызывает onChange).
        import random

        labels_loc = self.page.locator(self.MODAL_LABEL)
        total = labels_loc.count()
        exclude = set(exclude_texts or [])
        entries: list[dict] = []
        for i in range(total):
            lbl = labels_loc.nth(i)
            try:
                text = lbl.inner_text().strip()
            except Exception:
                continue
            if not text or text in exclude:
                continue
            for_attr = lbl.get_attribute("for") or ""
            if not for_attr.startswith("hierarchical-checkbox-"):
                continue
            checkbox = self.page.locator(f"#{for_attr}")
            try:
                if checkbox.count() == 0 or checkbox.is_disabled():
                    continue
                if exclude_checked and checkbox.is_checked():
                    continue
            except Exception:
                continue
            entries.append({"idx": i, "text": text})

        random.shuffle(entries)
        selected: list[str] = []
        for entry in entries:
            if len(selected) >= n:
                break
            try:
                labels_loc.nth(entry["idx"]).click()
                selected.append(entry["text"])
            except Exception:
                continue
        return selected

    @allure.step("Выбираем {n} случайных элементов в модалке")
    def select_random_n_modal_items(
        self,
        n: int,
        exclude_texts: set[str] | None = None,
    ) -> list[str]:
        """
        Кликает по N случайным enabled-элементам top-level модалки
        (без раскрытия подкатегорий). Подходит для Отрасль / Специализация /
        География — top-level имена совпадают с тем, что показывается на
        форме создания вакансии после save.

        exclude_texts — значения, которые нельзя выбирать (например, набор
        уже использованных в параметризованных тестах значений).
        """
        return self._flat_random_select(
            n, exclude_checked=False, exclude_texts=exclude_texts
        )

    @allure.step("Выбираем {n} новых (ещё не выбранных) элементов в модалке")
    def select_random_new_items_in_modal(
        self,
        n: int,
        exclude_texts: set[str] | None = None,
    ) -> list[str]:
        """
        Кликает по N случайным top-level элементам, которые ещё НЕ были
        отмечены. Нужен для итеративного сценария — ранее выбранные top-level
        чекбоксы уже checked, их пропускаем и добавляем новые.
        """
        return self._flat_random_select(
            n, exclude_checked=True, exclude_texts=exclude_texts
        )

    @staticmethod
    def _matches_field_text(item: str, text: str) -> bool:
        """
        True если item представлен в тексте поля.
        Поле может показывать полное название, первое слово или короткий
        лейбл категории — нам достаточно, чтобы хоть один значимый токен
        (длиннее 3 символов) присутствовал в тексте.
        """
        if not item:
            return True
        if item in text:
            return True
        tokens = [t for t in item.split() if len(t) > 3]
        return any(tok in text for tok in tokens)

    @allure.step("Проверяем что '{item}' отображается в поле Отрасль на форме")
    def should_industry_field_contain(self, item: str):
        text = self.page.locator(self.INDUSTRY_FIELD).inner_text()
        assert self._matches_field_text(item, text), (
            f"Ожидали '{item}' в поле Отрасль, получили:\n{text}"
        )
        return self

    @allure.step("Проверяем что '{item}' отображается в поле Специализация на форме")
    def should_specialization_field_contain(self, item: str):
        text = self.get_specialization_field_text()
        assert self._matches_field_text(item, text), (
            f"Ожидали '{item}' в поле Специализация, получили:\n{text}"
        )
        return self

    @allure.step("Проверяем что '{item}' отображается в поле География на форме")
    def should_geography_field_contain(self, item: str):
        text = self.page.locator(self.REGION_SECTION).inner_text()
        assert self._matches_field_text(item, text), (
            f"Ожидали '{item}' в поле География, получили:\n{text}"
        )
        return self

    def is_modal_visible(self) -> bool:
        return self.page.locator(
            self.MODAL_CONTAINER
        ).is_visible()
    # ═══════════════════════════════════════
    # ТОСТ ОШИБКИ ЛИМИТА СИМВОЛОВ
    # ═══════════════════════════════════════

    CHAR_LIMIT_TOAST = "div[role='status'][aria-live='polite']"

    # ═══════════════════════════════════════
    # МЕТОДЫ — ПОДСЧЁТ СИМВОЛОВ
    # ═══════════════════════════════════════

    @allure.step("Получаем суммарную длину 3 текстовых полей")
    def get_total_text_length(self) -> int:
        desc = self.page.locator(
            self.DESCRIPTION_EDITOR
        ).inner_text().strip()
        company = self.page.locator(
            self.COMPANY_DESCRIPTION_EDITOR
        ).inner_text().strip()
        social = self.page.locator(
            self.SOCIAL_PACKAGE_TEXTAREA
        ).input_value()
        return len(desc) + len(company) + len(social)

    @allure.step("Проверяем появление тоста об ошибке лимита")
    def should_show_char_limit_error(self):
        toast = self.page.locator(self.CHAR_LIMIT_TOAST)
        toast.wait_for(state="visible", timeout=5000)
        text = toast.inner_text()
        assert "не более 10000 символов" in text.lower() or \
               "сократите" in text.lower(), \
            f"Ожидали ошибку лимита, получили: {text}"
        return self

    @allure.step("Проверяем тост об ошибке порядка зарплаты")
    def should_show_salary_order_error(self):
        toast = self.page.locator(self.CHAR_LIMIT_TOAST)
        toast.wait_for(state="visible", timeout=5000)
        text = toast.inner_text()
        assert "от" in text.lower() and "до" in text.lower(), \
            f"Ожидали ошибку порядка зарплаты, получили: {text}"
        return self

    @allure.step("Проверяем что тоста об ошибке лимита НЕТ")
    def should_not_show_char_limit_error(self):
        toast = self.page.locator(self.CHAR_LIMIT_TOAST)
        assert toast.count() == 0 or not toast.is_visible(), \
            "Тост об ошибке лимита не должен появляться"
        return self

    @allure.step("Проверяем что элемент '{label}' выбран в модалке")
    def is_modal_item_checked(self, label: str) -> bool:
        """
        Проверяет выбран ли элемент в модалке.
        Структура DOM:
          <div>                          ← родительский контейнер
            <span><input checkbox></span> ← чекбокс рядом с label
            <label>Текст</label>
          </div>
        """
        # Находим родительский div, содержащий label с нужным текстом
        container = self.page.locator(
            f".modal-container div:has(> label:has-text('{label}'))"
        )
        container.first.wait_for(state="visible", timeout=5000)

        # Ищем input[type='checkbox'] внутри этого div (он в соседнем span)
        checkbox = container.first.locator("input[type='checkbox']")

        if checkbox.count() > 0:
            return checkbox.is_checked()

        # Fallback: aria-checked
        custom = container.first.locator("[aria-checked]")
        if custom.count() > 0:
            return custom.get_attribute("aria-checked") == "true"

        return False

    @allure.step("Выбираем город '{city}' (регион: '{region}') в модалке")
    def select_city_in_modal(self, city: str, region: str = None) -> bool:
        """
        В открытой city-модалке раскрывает регион и выбирает город по имени.
        Использует точное совпадение по label (`text-is`), иначе "Москва"
        сматчит "Московская область" и кликнет по региону вместо города.
        Возвращает True если Save активен (React зарегистрировал выбор).
        """
        search = self.page.locator(self.MODAL_SEARCH_INPUT)
        save_btn = self.page.locator(self.MODAL_SAVE_BUTTON)
        label_base = (
            ".modal-container label[for^='hierarchical-checkbox-']"
        )

        # 1. Сужаем список поиском по региону (если известен)
        target_region = region or city
        if search.count() > 0 and search.is_visible():
            search.fill(target_region)
            self.page.wait_for_timeout(300)

        # 2. Находим ряд региона по точному тексту и раскрываем его
        region_label = self.page.locator(
            f"{label_base}:text-is('{target_region}')"
        ).first
        region_label.wait_for(state="visible", timeout=10000)
        region_row = region_label.locator(
            "xpath=ancestor::div[contains(@class,'py-2') "
            "and contains(@class,'items-center')][1]"
        )
        expand_btn = region_row.locator("button").first
        if expand_btn.count() > 0:
            expand_btn.click()
            self.page.wait_for_timeout(400)

        # 3. Ищем конкретный город → точное совпадение → клик
        if search.count() > 0 and search.is_visible():
            search.fill(city)
            self.page.wait_for_timeout(300)

        city_label = self.page.locator(
            f"{label_base}:text-is('{city}')"
        ).first
        city_label.wait_for(state="visible", timeout=10000)
        city_label.click()
        self.page.wait_for_timeout(300)

        return save_btn.count() > 0 and save_btn.is_enabled()

    def _reset_modal_state(self) -> None:
        """
        Приводит открытую модалку в предсказуемое состояние перед выбором:
          — очищает поисковую строку,
          — сворачивает все раскрытые parent-ряды.
        Нужно при повторном открытии модалки (итеративные сценарии),
        где React может сохранить UI-state предыдущего сеанса.
        """
        search = self.page.locator(self.MODAL_SEARCH_INPUT)
        try:
            if search.count() > 0 and search.is_visible():
                current = search.input_value()
                if current:
                    search.fill("")
                    self.page.wait_for_timeout(200)
        except Exception:
            pass

        # Свернуть любые раскрытые parent-ряды: если под parent'ом есть leaf
        # с тем же индексом-префиксом — это раскрытое состояние. Надёжный
        # эвристический признак — parent-ряды, которые видны, пока в модалке
        # есть хотя бы один leaf (ряд без expand-кнопки). Проходим и
        # кликаем expand всех видимых parent'ов, пока есть leaves.
        # Это гарантирует что после вызова все parents находятся в
        # одинаковом (свёрнутом) состоянии.
        for _ in range(5):
            leaves, parents = self._collect_modal_candidates(
                exclude_checked=False, exclude_texts=set()
            )
            if not leaves or not parents:
                break
            # Есть и leaves и parents → хотя бы один parent раскрыт.
            # Сворачиваем все parents (повторный клик expand-кнопки сворачивает).
            collapsed_any = False
            for p in parents:
                if self._expand_parent_row(p):
                    collapsed_any = True
            if not collapsed_any:
                break

    def _expand_region_by_text(self, region_text: str) -> bool:
        """Кликает expand-кнопку ряда региона, найденного по точному тексту."""
        label_base = ".modal-container label[for^='hierarchical-checkbox-']"
        region_loc = self.page.locator(
            f"{label_base}:text-is('{region_text}')"
        ).first
        if region_loc.count() == 0:
            return False
        try:
            region_loc.wait_for(state="visible", timeout=5000)
        except Exception:
            return False
        row = region_loc.locator(
            "xpath=ancestor::div[contains(@class,'py-2') "
            "and contains(@class,'items-center')][1]"
        )
        btn = row.locator("button").first
        if btn.count() == 0:
            return False
        try:
            btn.click(timeout=5000)
            self.page.wait_for_timeout(400)
            return True
        except Exception:
            return False

    _JS_CITY_PICK_RANDOM = """
    async ({ excludeRegions }) => {
      const modal = document.querySelector('.modal-container');
      if (!modal) return { error: 'no modal' };
      const exclude = new Set(excludeRegions || []);

      // 1. Очистим поиск, если что-то там есть.
      const search = modal.querySelector(
        "input[placeholder='Поиск регионов и городов']"
      );
      if (search && search.value) {
        const setter = Object.getOwnPropertyDescriptor(
          HTMLInputElement.prototype, 'value'
        ).set;
        setter.call(search, '');
        search.dispatchEvent(new Event('input', { bubbles: true }));
        await new Promise(r => requestAnimationFrame(r));
      }

      const labelsAll = () => Array.from(
        modal.querySelectorAll("label[for^='hierarchical-checkbox-']")
      );
      const getRow = (lbl) => lbl.closest("div[class*='py-2']");
      const hasExpand = (row) => !!(row && row.querySelector('button'));

      // 2. Собираем регионы (ряды с expand-кнопкой), исключая used.
      const rows = labelsAll().map(lbl => ({
        lbl,
        row: getRow(lbl),
        text: (lbl.textContent || '').trim(),
      }));
      const regions = rows
        .filter(r => r.row && hasExpand(r.row) && r.text && !exclude.has(r.text));

      if (regions.length === 0) return { error: 'no regions' };

      for (let i = regions.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [regions[i], regions[j]] = [regions[j], regions[i]];
      }

      const waitDomChange = (predicate, maxMs = 3000) => new Promise((resolve) => {
        const start = performance.now();
        const check = () => {
          if (predicate()) return resolve(true);
          if (performance.now() - start > maxMs) return resolve(false);
          requestAnimationFrame(check);
        };
        check();
      });

      // 3. Идём по регионам до первой удачной попытки:
      //    expand → достать появившиеся leaf-города → кликнуть случайный.
      for (const region of regions) {
        const beforeTexts = new Set(labelsAll().map(
          l => (l.textContent || '').trim()
        ));
        const beforeCount = beforeTexts.size;

        const expandBtn = region.row.querySelector('button');
        if (!expandBtn) continue;
        expandBtn.click();

        // Ждём, пока в DOM появятся новые labels (поддерево региона).
        await waitDomChange(() => labelsAll().length > beforeCount, 3000);

        // Собираем leaf'ы, появившиеся после expand.
        const afterLabels = labelsAll();
        const newLeaves = afterLabels
          .map(l => ({
            lbl: l,
            row: getRow(l),
            text: (l.textContent || '').trim(),
          }))
          .filter(r =>
            r.text &&
            !beforeTexts.has(r.text) &&
            r.row &&
            !hasExpand(r.row)
          );

        if (newLeaves.length === 0) {
          // Свернуть обратно и попробовать следующий регион.
          expandBtn.click();
          continue;
        }

        for (let i = newLeaves.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [newLeaves[i], newLeaves[j]] = [newLeaves[j], newLeaves[i]];
        }

        for (const leaf of newLeaves) {
          try {
            leaf.lbl.click();
            // Дать React'у отрендерить изменение стейта Save-кнопки.
            await new Promise(r => requestAnimationFrame(r));
            await new Promise(r => requestAnimationFrame(r));
            const saveBtn = Array.from(modal.querySelectorAll('button'))
              .find(b => (b.textContent || '').trim() === 'Сохранить');
            if (saveBtn && !saveBtn.disabled) {
              return { city: leaf.text, region: region.text };
            }
          } catch (_) {}
        }

        // Не получилось — сворачиваем и идём дальше.
        try { expandBtn.click(); } catch (_) {}
      }

      return { error: 'no city selected' };
    }
    """

    def _js_city_pick_random(
        self, exclude_regions: list[str] | None = None
    ) -> tuple[str, str]:
        """JS fast-path: выбрать случайный город в city-модалке.

        В одном `page.evaluate` (async) делает expand региона,
        ждёт появления городов через requestAnimationFrame и кликает
        случайный leaf. Заменяет ~десяток round-trip'ов + `wait_for_timeout`.
        """
        res = self.page.evaluate(
            self._JS_CITY_PICK_RANDOM,
            {"excludeRegions": list(exclude_regions or [])},
        )
        if isinstance(res, dict) and res.get("error"):
            return "", ""
        return res.get("city") or "", res.get("region") or ""

    @allure.step("Выбираем рандомный город в открытой city-модалке")
    def select_random_city_in_modal(
        self, exclude_regions: list = None
    ) -> tuple[str, str]:
        """
        Выбор случайного города в открытой city-модалке. Сначала пробуем
        JS fast-path (`_js_city_pick_random`) — он выполняется как
        единичный `page.evaluate` и работает с requestAnimationFrame для
        ожидания перерисовки поддерева региона. Если fast-path ничего
        не выбрал, откатываемся к старому Python-алгоритму (через
        текстовые селекторы и `:text-is(...)`).
        """
        # Fast-path: один JS-вызов вместо сотен round-trip'ов.
        city, region = self._js_city_pick_random(exclude_regions or [])
        if city:
            # Гонка React-а с нашим JS-кликом по label города иногда
            # приводит к тому, что к моменту возврата управления в
            # Python у кнопки «Сохранить» ещё disabled=true (React
            # только-только commit'нул onChange). Ждём реальный
            # enabled в Playwright: он поллит DOM до timeout'а,
            # а не полагается на rAF. Если за 3 сек React так и не
            # включил кнопку — это уже не гонка, а настоящая проблема
            # выбора: падаем обратно на Python-fallback (он ниже),
            # а не пытаемся кликать disabled-кнопку в save_modal.
            save_btn = self.page.locator(self.MODAL_SAVE_BUTTON)
            try:
                save_btn.wait_for(state="visible", timeout=3_000)
                # `is_enabled` поллинг делаем сами — у Playwright нет
                # ожидания enabled state у локатора без expect().
                import time
                deadline = time.monotonic() + 3.0
                while time.monotonic() < deadline:
                    if save_btn.is_enabled():
                        return city, region
                    self.page.wait_for_timeout(100)
            except Exception:
                pass
            # Fast-path «как будто выбрал», но React так и не включил
            # кнопку «Сохранить» — проваливаемся в Python-fallback.

        # Fallback — старый Python-путь (медленнее, но надёжнее, если
        # структура DOM модалки неожиданно поменяется).
        import random

        save_btn = self.page.locator(self.MODAL_SAVE_BUTTON)
        label_base = ".modal-container label[for^='hierarchical-checkbox-']"
        self._reset_modal_state()

        rows_loc = self.page.locator(self.MODAL_ROW)
        try:
            rows_loc.first.wait_for(state="visible", timeout=10000)
        except Exception:
            pass

        def _try_with_exclude(excluded: set[str]) -> tuple[str, str]:
            _, parents = self._collect_modal_candidates(
                exclude_checked=False, exclude_texts=set()
            )
            region_texts = [
                p["text"] for p in parents if p["text"] not in excluded
            ]
            random.shuffle(region_texts)

            for region_text in region_texts:
                if not self._expand_region_by_text(region_text):
                    continue

                # Собираем leaf-города, появившиеся после раскрытия.
                leaves, _ = self._collect_modal_candidates(
                    exclude_checked=False,
                    exclude_texts={region_text},
                )
                city_texts = [leaf["text"] for leaf in leaves]
                random.shuffle(city_texts)

                for city_text in city_texts:
                    city_loc = self.page.locator(
                        f"{label_base}:text-is('{city_text}')"
                    ).first
                    try:
                        city_loc.click(timeout=3000)
                        self.page.wait_for_timeout(300)
                        if save_btn.count() > 0 and save_btn.is_enabled():
                            return city_text, region_text
                    except Exception:
                        continue

                # Не получилось — сворачиваем регион (повторный expand)
                # и пробуем следующий.
                self._expand_region_by_text(region_text)
            return "", ""

        # Попытка 1 — с исключением уже использованных регионов.
        city, region = _try_with_exclude(set(exclude_regions or []))
        if city:
            return city, region

        # Попытка 2 — сбрасываем модалку и игнорируем exclude_regions.
        self._reset_modal_state()
        city, region = _try_with_exclude(set())
        if city:
            return city, region

        # Попытка 3 — плоский fallback: модалка не иерархическая.
        leaves, _ = self._collect_modal_candidates(
            exclude_checked=False, exclude_texts=set()
        )
        leaf_texts = [leaf["text"] for leaf in leaves]
        random.shuffle(leaf_texts)
        for leaf_text in leaf_texts:
            loc = self.page.locator(
                f"{label_base}:text-is('{leaf_text}')"
            ).first
            try:
                loc.click(timeout=3000)
                self.page.wait_for_timeout(300)
                if save_btn.count() > 0 and save_btn.is_enabled():
                    return leaf_text, ""
            except Exception:
                continue

        return "", ""

