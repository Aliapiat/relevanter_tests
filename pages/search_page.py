import re
import allure
from pages.base_page import BasePage


class SearchPage(BasePage):
    """Вкладка «Поиск» на странице вакансии.

    URL: /recruiter/search?<query>

    При переходе на вкладку из карточки вакансии фронт автоматически
    проксирует параметры вакансии (название, ЗП, навыки, отрасль,
    специализацию, формат, город и т.д.) в URL и использует их как
    текущие фильтры поиска. Поэтому именно здесь удобно валидировать
    «что вакансия корректно сохранилась» — не заходя в режим
    редактирования.

    Панель «Фильтры» (правый сайд-бар) раскрывает детали этих фильтров
    в виде формы; методы get_filter_* ниже считывают оттуда значения.
    """

    PATH_PATTERN = "/recruiter/search"

    # ─── Заголовок страницы ───
    PAGE_TITLE = "h1:has-text('Поиск из источников')"

    # ─── Источники поиска ───
    SOURCE_HEADHUNTER_BUTTON = "button:has-text('HeadHunter')"
    HH_SETTINGS_BUTTON       = "button:has-text('Настройки HH.ru')"

    # ─── Основные кнопки формы ───
    SEARCH_BUTTON        = "button:has-text('Найти')"
    RESET_FILTERS_BUTTON = "button:has-text('Сбросить фильтры')"
    FILTERS_BUTTON       = "button:has-text('Фильтры')"

    # ─── Фильтры релевантности (чипсы) ───
    RELEVANCE_85_PLUS = "button:has-text('≥85%')"
    RELEVANCE_70_84   = "button:has-text('70-84%')"
    RELEVANCE_LT_70   = "button:has-text('<70%')"

    # ─── Фильтры периода / сортировки / пагинации ───
    PERIOD_DROPDOWN    = "button:has-text('За все время')"
    SORT_DROPDOWN      = "button:has-text('По релевантности')"
    PAGE_SIZE_DROPDOWN = "button:has-text('20 резюме')"

    # ─── Поля верхней поисковой панели ───
    SEARCH_INPUT = "input[placeholder='Поиск']"

    # ─── Панель «Фильтры» ───
    #
    # Важный нюанс рендеринга: на чистом goto /recruiter/search даже с
    # positionName= в URL input'ы фильтра не отрисуются. Форма появится
    # только ПОСЛЕ клика по кнопке «Фильтры» — именно она одновременно
    # открывает правый sidebar и «применяет» вакансию на панель, дополнив
    # URL полным search-query (source=hh&limit=20&sortBy=relevance&…).
    # Поэтому в open_filters() ниже мы всегда кликаем кнопку.
    #
    # Внутренние поля панели — без data-testid, поэтому якоримся
    # по placeholder.
    FILTER_TITLE_INPUT       = "input[placeholder='Введите должность']"
    FILTER_SALARY_FROM_INPUT = "input[placeholder='от']"
    FILTER_SALARY_TO_INPUT   = "input[placeholder='до']"

    # ═══════════════════════════════════════
    # НАВИГАЦИЯ / ЛОАДЕР
    # ═══════════════════════════════════════

    @allure.step("Ждём, пока прогрузится вкладка «Поиск»")
    def should_be_loaded(self, timeout: int = 30_000):
        self.page.wait_for_url(
            lambda u: self.PATH_PATTERN in u, timeout=timeout
        )
        self.page.locator(self.PAGE_TITLE).first.wait_for(
            state="visible", timeout=timeout
        )
        return self


    @allure.step("Нажимаем «Найти»")
    def click_search(self):
        self.page.locator(self.SEARCH_BUTTON).first.click()
        return self

    @allure.step("Нажимаем «Сбросить фильтры»")
    def click_reset_filters(self):
        self.page.locator(self.RESET_FILTERS_BUTTON).first.click()
        return self

    # ═══════════════════════════════════════
    # ПАНЕЛЬ «ФИЛЬТРЫ»
    # ═══════════════════════════════════════

    @allure.step("Открываем панель «Фильтры»")
    def open_filters(self, timeout: int = 20_000):
        """Гарантирует, что правая панель «Фильтры» открыта и
        поля фильтра уже отрисованы.

        Нюанс фронта:
          • На ширине ≥1280 панель «Фильтры» рендерится как
            ПОСТОЯННЫЙ sidebar и по умолчанию открыта (если в URL
            уже есть контекст поиска — positionName=…).
            В этом случае кнопка FILTERS_BUTTON — тумблер: клик
            её ЗАКРОЕТ. Поэтому сначала проверяем, видим ли мы
            уже поле «Должность», и кликаем кнопку только если нет.

          • На узком viewport / при «чистом» /recruiter/search
            (без query) панель закрыта, поля нет — тогда жмём
            кнопку и ждём появления input.
        """
        # На широких viewport'ах (≥1280) панель «Фильтры» обычно
        # уже открыта по умолчанию — input «Должность» виден сразу.
        # Если так — возвращаемся. Иначе кликаем кнопку «Фильтры».
        title_input = self.page.locator(self.FILTER_TITLE_INPUT).first
        try:
            title_input.wait_for(state="visible", timeout=3_000)
            return self
        except Exception:
            pass

        filters_btn = self.page.locator(self.FILTERS_BUTTON).first
        filters_btn.wait_for(state="visible", timeout=timeout)
        filters_btn.click()
        title_input.wait_for(state="visible", timeout=timeout)
        return self

    # ─── Простые inputs ───

    @allure.step("Читаем значение поля «Должность» в фильтре")
    def get_filter_title(self) -> str:
        return (
            self.page.locator(self.FILTER_TITLE_INPUT)
            .first.input_value()
            .strip()
        )

    @allure.step("Читаем значение поля «до» (ЗП) в фильтре")
    def get_filter_salary_to(self) -> str:
        """Возвращает значение без пробелов, т.е. '200 000' → '200000'."""
        raw = (
            self.page.locator(self.FILTER_SALARY_TO_INPUT)
            .first.input_value()
        )
        return re.sub(r"\s+", "", raw)

    @allure.step("Читаем значение поля «от» (ЗП) в фильтре")
    def get_filter_salary_from(self) -> str:
        raw = (
            self.page.locator(self.FILTER_SALARY_FROM_INPUT)
            .first.input_value()
        )
        return re.sub(r"\s+", "", raw)

    # ─── Универсальное чтение «значения раздела» ───
    #
    # Разделы внутри панели «Фильтры» имеют структуру:
    #
    #     <div> <... заголовок типа «Отрасль» ...> </div>
    #     <div> <... выбранное значение: «Информационные технологии ...» ...> </div>
    #
    # То есть текст «под заголовком» живёт в ближайшем соседе вверх по
    # родителю. Поэтому берём первый текстовый узел, равный точному
    # заголовку, поднимаемся максимум на 3 уровня и берём
    # nextElementSibling.innerText.

    _JS_GET_SECTION_VALUE = """
    (label) => {
      const nodes = Array.from(document.querySelectorAll('*'))
        .filter(el => el.children.length === 0
                   && el.textContent.trim() === label);
      for (const node of nodes) {
        let p = node.parentElement;
        for (let i = 0; i < 4 && p; i++) {
          if (p.nextElementSibling) {
            return p.nextElementSibling.innerText.trim();
          }
          p = p.parentElement;
        }
      }
      return null;
    }
    """

    @allure.step("Читаем значение раздела «{section_label}» в фильтре")
    def get_filter_section_value(self, section_label: str) -> str:
        """Возвращает текст, отображающийся под заголовком раздела
        фильтра (например, для 'Отрасль' — название выбранной отрасли,
        для 'Формат работы' — 'Удаленка' / 'Офис' / 'Гибрид',
        для 'География' — 'Выбрано: N', и т.п.).

        Если раздел не найден или у него нет соседа со значением —
        возвращает пустую строку.
        """
        value = self.page.evaluate(self._JS_GET_SECTION_VALUE, section_label)
        return (value or "").strip()

    # ─── Проверки ───

    @allure.step("Должность в фильтре содержит «{expected}»")
    def should_filter_title_contain(self, expected: str):
        actual = self.get_filter_title()
        assert expected.strip() in actual, (
            f"Ожидали, что в поле «Должность» фильтра будет "
            f"«{expected}», получили: {actual!r}"
        )
        return self

    @allure.step("Поле «до» (ЗП) в фильтре равно «{expected}»")
    def should_filter_salary_to_equal(self, expected: str):
        actual = self.get_filter_salary_to()
        expected_clean = re.sub(r"\s+", "", expected)
        assert actual == expected_clean, (
            f"Ожидали зарплату до «{expected_clean}», "
            f"получили: {actual!r}"
        )
        return self

    @allure.step("Раздел «{section_label}» содержит «{expected}»")
    def should_filter_section_contain(self, section_label: str, expected: str):
        actual = self.get_filter_section_value(section_label)
        assert expected in actual, (
            f"В разделе «{section_label}» панели «Фильтры» ожидали "
            f"«{expected}», получили: {actual!r}"
        )
        return self
