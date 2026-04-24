import allure
from pages.base_page import BasePage


class DialogsPage(BasePage):
    """Вкладка «Диалоги» (мессенджер) на странице вакансии.

    URL: /recruiter/messenger

    Страница — трёхколоночный layout:
      [фильтры/список диалогов] [чат-окно] [инфа о кандидате]

    В POM — минимум селекторов, достаточных для навигации и
    базовых smoke-проверок.
    """

    PATH_PATTERN = "/recruiter/messenger"

    # ─── Левая колонка: поиск и фильтры диалогов ───
    CONVERSATIONS_SEARCH_INPUT = (
        "input[placeholder='Поиск по ФИО или сообщениям...']"
    )
    # text-is — exact-match, чтобы «Все» не путалось с «все статусы»
    # в сайдбаре.
    FILTER_ALL              = "button:text-is('Все')"
    FILTER_SOURCE           = "button:has-text('Источник')"
    FILTER_MESSENGER        = "button:has-text('Мессенджер')"
    FILTER_DIALOG_STATUS    = "button:has-text('Статус диалога')"
    FILTER_CANDIDATE_STATUS = "button:has-text('Статус кандидата')"
    FILTER_ALL_VACANCIES    = "button:has-text('Все вакансии')"
    DATE_FILTER_BUTTON      = "button:has-text('DD / MM / YYYY')"

    # ─── Центр: чат-область ───
    EMPTY_CHAT_TITLE = "h2:has-text('Не выбран')"
    MESSAGE_INPUT    = "textarea[placeholder='Напишите сообщение']"

    # ─── Правая колонка: инфа о кандидате + модераторские кнопки ───
    CANDIDATE_INFO_TITLE = "h3:has-text('Информация о кандидате')"
    APPROVE_CANDIDATE    = "button:has-text('Одобрить кандидата')"
    REJECT_CANDIDATE     = "button:has-text('Отказать кандидату')"

    # ═══════════════════════════════════════
    # ПРОВЕРКИ / ДЕЙСТВИЯ
    # ═══════════════════════════════════════

    @allure.step("Ждём, пока прогрузится вкладка «Диалоги»")
    def should_be_loaded(self, timeout: int = 30_000):
        self.page.wait_for_url(
            lambda u: self.PATH_PATTERN in u, timeout=timeout
        )
        self.page.locator(self.CONVERSATIONS_SEARCH_INPUT).first.wait_for(
            state="visible", timeout=timeout
        )
        return self

    @allure.step("Поиск диалогов по строке: '{query}'")
    def search_conversations(self, query: str):
        self.page.locator(self.CONVERSATIONS_SEARCH_INPUT).first.fill(query)
        return self
