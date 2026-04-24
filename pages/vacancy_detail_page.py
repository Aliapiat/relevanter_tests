import allure
from pages.base_page import BasePage


class VacancyDetailPage(BasePage):
    """
    Страница просмотра вакансии: /recruiter/vacancy/{id}

    Структура информационного блока:
      <div class="space-y-2 text-sm">
        <div>
          <span class="text-[#868c98]">Отрасль:</span>
          <span class="text-[#0a0d14]">Информационные технологии, ...</span>
        </div>
        ...
      </div>
    """

    PATH_PATTERN = "/recruiter/vacancy/"

    VACANCY_TITLE = "h2.text-2xl.font-semibold"
    INFO_SECTION  = "div.space-y-2.text-sm"

    # Кнопка «AI-скрининг подключен» / «AI-скрининг не подключен» /
    # «Скопировано» (после успешного копирования). Текст зависит от
    # состояния, поэтому таргетимся по фрагменту «AI-скрининг» + fallback
    # на «Скопировано» (после клика).
    AI_SCREENING_BUTTON = (
        "button:has-text('AI-скрининг'), "
        "button:has(svg):has-text('Скопировано')"
    )
    # Кнопка «Запись на HR-интервью» / «Скопировано»
    HR_INTERVIEW_BUTTON = "button:has-text('Запись на HR-интервью')"

    # Ссылка на вакансию hh.ru рядом с заголовком.
    # Селектор берёт конкретно внешнюю <a>, чтобы не задеть «hh.ru»-badge.
    HH_VACANCY_LINK = "a[href^='https://hh.ru/vacancy/']"

    # ═══════════════════════════════════════
    # НАВИГАЦИОННЫЕ ВКЛАДКИ (снизу под заголовком вакансии)
    # ═══════════════════════════════════════
    #
    # Табы — это обычные <a href="/recruiter/...">, data-testid у них нет,
    # поэтому якоримся по href. «Вакансия» имеет динамический id,
    # поэтому матчим по префиксу (href*=).
    NAV_TAB_VACANCY    = 'a[href*="/recruiter/vacancy/"]'
    NAV_TAB_SEARCH     = 'a[href="/recruiter/search"]'
    NAV_TAB_DIALOGS    = 'a[href="/recruiter/messenger"]'
    NAV_TAB_INTERVIEWS = 'a[href="/recruiter/interviews"]'
    NAV_TAB_REPORTS    = 'a[href="/recruiter/reports"]'

    # Ключ → (селектор, подстрока URL, якорь контента на вкладке).
    # Якорь — элемент, который гарантированно есть на странице таба,
    # независимо от состояния (пустой список/есть данные).
    NAV_TABS = {
        "vacancy": {
            "selector": NAV_TAB_VACANCY,
            "url_sub":  "/recruiter/vacancy/",
            # Кнопка «Редактировать» есть всегда — и на полноценно
            # заполненной вакансии, и на свежесозданной тестовой,
            # где h2 «Описание вакансии» может и не появиться.
            "anchor":   "button:has-text('Редактировать')",
        },
        "search": {
            "selector": NAV_TAB_SEARCH,
            "url_sub":  "/recruiter/search",
            "anchor":   "h1:has-text('Поиск из источников')",
        },
        "dialogs": {
            "selector": NAV_TAB_DIALOGS,
            "url_sub":  "/recruiter/messenger",
            "anchor":   "input[placeholder='Поиск по ФИО или сообщениям...']",
        },
        "interviews": {
            "selector": NAV_TAB_INTERVIEWS,
            "url_sub":  "/recruiter/interviews",
            "anchor":   "h2:has-text('Собеседования')",
        },
        "reports": {
            "selector": NAV_TAB_REPORTS,
            "url_sub":  "/recruiter/reports",
            "anchor":   "h1:has-text('Итоги Подбора')",
        },
    }

    # ═══════════════════════════════════════
    # НАВИГАЦИЯ / ЗАГРУЗКА
    # ═══════════════════════════════════════

    @allure.step("Ждём перехода на страницу вакансии")
    def should_be_loaded(self):
        self.page.wait_for_url(
            lambda url: self.PATH_PATTERN in url,
            timeout=15000,
        )
        # После редиректа SPA может рендерить h2 не мгновенно (особенно
        # в первом тесте сессии). 20с — запас, который убирает flaky
        # без риска реального зависания.
        self.page.locator(self.VACANCY_TITLE).wait_for(
            state="visible", timeout=20000
        )
        return self

    @allure.step("Нажимаем 'Редактировать'")
    def click_edit_vacancy(self):
        btn = self.page.locator("button:has-text('Редактировать')")
        btn.wait_for(state="visible", timeout=5000)
        btn.click()
        return self

    # ═══════════════════════════════════════
    # ЧТЕНИЕ ПОЛЕЙ
    # ═══════════════════════════════════════

    @allure.step("Читаем значение поля '{label}'")
    def get_field_value(self, label: str) -> str:
        """
        Находит строку «Метка: Значение» в info-блоке и возвращает текст значения.
        nth(1) — второй <span> в строке, он содержит значение.
        """
        row = self.page.locator(
            f"{self.INFO_SECTION} div:has(span:has-text('{label}:'))"
        ).first
        row.wait_for(state="visible", timeout=5000)
        return row.locator("span").nth(1).inner_text().strip()

    def get_industry(self) -> str:
        return self.get_field_value("Отрасль")

    def get_specialization(self) -> str:
        return self.get_field_value("Специализация")

    def get_city(self) -> str:
        return self.get_field_value("Город")

    def get_work_format(self) -> str:
        return self.get_field_value("Формат работы")

    def get_citizenship(self) -> str:
        return self.get_field_value("Гражданство")

    # ═══════════════════════════════════════
    # ASSERTIONS
    # ═══════════════════════════════════════

    @allure.step("'{label}' содержит '{expected}'")
    def should_field_contain(self, label: str, expected: str):
        value = self.get_field_value(label)
        assert expected in value, (
            f"Поле «{label}»: ожидали «{expected}», получили: {value!r}"
        )
        return self

    @allure.step("Страница содержит текстовый фрагмент")
    def should_body_contain(self, text: str, snippet_len: int = 40):
        """Проверяет что первые snippet_len символов текста видны на странице."""
        snippet = text[:snippet_len].strip()
        body_text = self.page.inner_text("body")
        assert snippet in body_text, (
            f"Текст «{snippet}…» не найден на странице вакансии"
        )
        return self

    @allure.step("'{label}' содержит все значения: {items}")
    def should_field_contain_all(self, label: str, items: list[str]):
        """Проверяет что хотя бы первое слово каждого item есть в значении поля."""
        value = self.get_field_value(label)
        for item in items:
            keyword = item.split()[0]
            assert keyword in value, (
                f"Поле «{label}»: «{item}» (keyword: «{keyword}») не найдено. "
                f"Значение: {value!r}"
            )
        return self

    # ═══════════════════════════════════════
    # КНОПКИ «AI-СКРИНИНГ» / «ЗАПИСЬ НА HR-ИНТЕРВЬЮ»
    # ═══════════════════════════════════════
    #
    # Важный нюанс реализации (recruiter-front/src/pages/VacancyViewPage.tsx):
    #
    # - Обе кнопки НЕ переходят, а копируют ссылку в буфер обмена.
    # - AI-скрининг копирует {origin}/candidate/interview/{vacancyId},
    #   но только если у вакансии есть вопросы (hasQuestions=true).
    #   Если вопросов нет — всплывает toast «Нет вопросов для AI-скрининга»
    #   и clipboard НЕ трогается.
    # - HR-интервью копирует {origin}/vacancy/{publicSlug}?recr=<base64(userId)>
    #   ВСЕГДА (если у вакансии есть publicSlug).
    # - После клика текст кнопки меняется на «Скопировано» (на ~2 секунды).

    @allure.step("Читаем буфер обмена")
    def read_clipboard(self) -> str:
        """Возвращает текст, который сейчас лежит в буфере обмена.

        Требует permissions=['clipboard-read'] в browser_context_args
        (настроены в tests/conftest.py).
        """
        try:
            return self.page.evaluate("() => navigator.clipboard.readText()")
        except Exception:
            return ""

    @allure.step("Устанавливаем заведомо-пустое значение в буфер обмена")
    def reset_clipboard(self, sentinel: str = "__AUTOTEST_CLIPBOARD_SENTINEL__") -> str:
        """Кладёт в буфер маркер, чтобы потом отличить «не было скопировано»
        от «скопировано то же самое, что и раньше».
        """
        self.page.evaluate(
            "(v) => navigator.clipboard.writeText(v)", sentinel
        )
        return sentinel

    @allure.step("Клик по кнопке «AI-скрининг»")
    def click_ai_screening_button(self):
        btn = self.page.locator(self.AI_SCREENING_BUTTON).first
        btn.wait_for(state="visible", timeout=5000)
        btn.click()
        return self

    @allure.step("Клик по кнопке «Запись на HR-интервью»")
    def click_hr_interview_button(self):
        btn = self.page.locator(self.HR_INTERVIEW_BUTTON).first
        btn.wait_for(state="visible", timeout=5000)
        btn.click()
        return self

    def get_ai_screening_button_text(self) -> str:
        return (
            self.page.locator(self.AI_SCREENING_BUTTON).first
            .inner_text().strip()
        )

    def get_hr_interview_button_text(self) -> str:
        return (
            self.page.locator(self.HR_INTERVIEW_BUTTON).first
            .inner_text().strip()
        )

    # ═══════════════════════════════════════
    # ССЫЛКА НА hh.ru
    # ═══════════════════════════════════════

    def has_hh_link(self) -> bool:
        return self.page.locator(self.HH_VACANCY_LINK).count() > 0

    @allure.step("Читаем href первой ссылки на hh.ru")
    def get_hh_link_href(self) -> str:
        link = self.page.locator(self.HH_VACANCY_LINK).first
        link.wait_for(state="visible", timeout=5000)
        return link.get_attribute("href") or ""

    # ═══════════════════════════════════════
    # ПЕРЕКЛЮЧЕНИЕ НАВИГАЦИОННЫХ ВКЛАДОК
    # ═══════════════════════════════════════

    @allure.step("Переходим на вкладку '{tab_key}'")
    def switch_nav_tab(self, tab_key: str, timeout: int = 15_000):
        """Кликает по навигационному табу и ждёт, пока поменяется URL
        и появится якорь контента на целевой странице.

        tab_key: один из ключей NAV_TABS — 'vacancy', 'search',
        'dialogs', 'interviews', 'reports'.
        """
        if tab_key not in self.NAV_TABS:
            raise ValueError(
                f"Неизвестный таб '{tab_key}'. "
                f"Доступны: {list(self.NAV_TABS)}"
            )

        tab = self.NAV_TABS[tab_key]
        self.page.locator(tab["selector"]).first.click()
        self.page.wait_for_url(
            lambda u: tab["url_sub"] in u,
            timeout=timeout,
        )
        self.page.locator(tab["anchor"]).first.wait_for(
            state="visible", timeout=timeout
        )
        return self

    def is_nav_tab_active(self, tab_key: str) -> bool:
        """Хрупкая проверка активности таба по Tailwind-классам:
        у активного есть `border-b-2` и нет `text-[var(--text-medium)]`.
        Используется как вспомогательная — основная проверка всё равно
        через URL (см. switch_nav_tab).
        """
        tab = self.NAV_TABS[tab_key]
        cls = (
            self.page.locator(tab["selector"])
            .first.get_attribute("class")
            or ""
        )
        return "border-b-2" in cls and "text-[var(--text-medium)]" not in cls
