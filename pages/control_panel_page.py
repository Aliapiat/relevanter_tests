"""
POM для страницы `/recruiter/control` (TeamManagementPage).

На фронте источник правды — `recruiter-front/src/components/TeamManagementPage.tsx`.
Левая панель «Управление» содержит набор табов, который зависит от роли:

    Видны всем (RECRUITER / ADMIN / OWNER / SUPER_ADMIN):
        • «Процесс интервью»     (id=interview-process)
        • «Брендирование»        (id=branding)
        • «Моя команда»          (id=team)         — disabled через TEAM_SECTION_DISABLED
        • «Настройки интеграций» (id=integrations)
        • «Личная информация»    (id=personal)

    Дополнительно для ADMIN / OWNER / SUPER_ADMIN (canManageAccounts):
        • «Управление аккаунтами» (id=accounts)

    Дополнительно ТОЛЬКО для SUPER_ADMIN:
        • «Компании» (id=companies)
        • «Жалобы»   (id=complaints)

URL принимает query-параметр `?tab=...` со значениями из `availableTabs`
(`branding | team | personal | accounts | interview-process`). При пустом
параметре активен `interview-process`. При `tab=team` форсится
`interview-process` (раздел отключён).
"""

from config.settings import settings
from pages.base_page import BasePage


class ControlPanelPage(BasePage):
    PATH = "/recruiter/control"

    # ── Заголовки ──
    # Заголовок страницы «Управление» рендерится как <p> внутри
    # обёртки `text-[24px]` (см. TeamManagementPage.tsx). Тот же текст
    # «Управление» — префикс таба «Управление аккаунтами» (виден
    # админам), поэтому используем text-is (точное совпадение) вместо
    # has-text (substring) — иначе строгая ловушка матчит и таб тоже.
    SECTION_HEADING = "p:text-is('Управление')"
    # Заголовок раздела «Личная информация» в правой панели тоже <p>
    # под `text-[24px]`, но в DOM есть ещё <p> внутри <button>-таба
    # слева с тем же текстом. Скоупим в обёртку text-[24px] (она же
    # не button).
    PERSONAL_HEADING = "div.text-\\[24px\\] p:text-is('Личная информация')"

    # ── Табы левой панели ──
    # Все табы — это <button> с <p> внутри, у которого ровно текст таба.
    # Используем точное соответствие текста, чтобы не зацепить случайно
    # другой элемент UI с тем же фрагментом.
    TAB_INTERVIEW_PROCESS = "button:has(p:text-is('Процесс интервью'))"
    TAB_BRANDING = "button:has(p:text-is('Брендирование'))"
    TAB_TEAM = "button:has(p:text-is('Моя команда'))"
    TAB_INTEGRATIONS = "button:has(p:text-is('Настройки интеграций'))"
    TAB_PERSONAL = "button:has(p:text-is('Личная информация'))"
    TAB_ACCOUNTS = "button:has(p:text-is('Управление аккаунтами'))"
    TAB_COMPANIES = "button:has(p:text-is('Компании'))"
    TAB_COMPLAINTS = "button:has(p:text-is('Жалобы'))"

    # ── PersonalInfoPage / UserEditForm в режиме personal ──
    # Поля формы рендерит UserEditForm; ярлыки совпадают с
    # `recruiter-front/src/components/UserEditForm.tsx` (label="Email",
    # label="Имя", label="Фамилия").
    PERSONAL_EMAIL_LABEL = "label:has-text('Email')"
    PERSONAL_FIRST_NAME_LABEL = "label:has-text('Имя')"
    PERSONAL_LAST_NAME_LABEL = "label:has-text('Фамилия')"

    # Все табы, которые в принципе могут отрисоваться. Перечень
    # синхронизирован с `managementItems` во фронте.
    ALL_TAB_LABELS = (
        "Процесс интервью",
        "Брендирование",
        "Моя команда",
        "Настройки интеграций",
        "Управление аккаунтами",
        "Компании",
        "Жалобы",
        "Личная информация",
    )

    def open(self, tab: str = "personal") -> "ControlPanelPage":
        """Открывает страницу управления с указанным активным табом.
        По умолчанию — «Личная информация», т.к. это основной кейс
        перехода с кнопки профиля в сайдбаре.

        ВАЖНО про URL: settings.BASE_URL заканчивается на '/' (см.
        config/environments.py), а PATH начинается с '/'. Если
        склеить «как есть», получится `https://host//recruiter/control?...`
        с двойным слэшем — на dev стенде SPA роутер именно для
        /recruiter/control такой URL не понимает и редиректит на
        дашборд (другие роуты nginx нормализует, а этот — нет).
        Поэтому делаем `rstrip('/')` явно, как уже сделано в
        VacancyEditPage.open_in_edit_mode.
        """
        url = f"{settings.BASE_URL.rstrip('/')}{self.PATH}?tab={tab}"
        self.page.goto(url, wait_until="domcontentloaded")
        self.should_be_loaded()
        return self

    def should_be_loaded(self) -> "ControlPanelPage":
        """Ждёт появления заголовка «Управление» — это якорь страницы,
        который рендерится одинаково для всех ролей.
        """
        self.wait_for_visible(self.SECTION_HEADING)
        return self

    def get_visible_tab_labels(self) -> list[str]:
        """Возвращает список текстовых ярлыков табов, фактически
        отрисованных в левой панели «Управление». Используется для
        ассертов «список табов для роли X состоит из N пунктов».

        Реализация: фильтруем фиксированный белый список ALL_TAB_LABELS
        по фактической видимости — не используем «возьмём всё, что
        похоже на таб», чтобы не словить ложные срабатывания на
        других <p>-блоках в правом контенте.
        """
        visible: list[str] = []
        for label in self.ALL_TAB_LABELS:
            loc = self.page.locator(f"button:has(p:text-is('{label}'))")
            if loc.count() > 0 and loc.first.is_visible():
                visible.append(label)
        return visible

    def should_show_personal_section(self) -> "ControlPanelPage":
        """Проверяет, что справа отрисована карточка «Личная информация»
        с полями Email / Имя / Фамилия.

        Карточка имеет такой же `<p>Личная информация</p>` заголовок,
        как и сам таб слева, поэтому ассерт «заголовок видим» в любом
        случае проходит через .first — нам важно подтвердить факт
        активного раздела, а не позицию на странице.
        """
        self.wait_for_visible(self.PERSONAL_HEADING)
        self.wait_for_visible(self.PERSONAL_EMAIL_LABEL)
        self.wait_for_visible(self.PERSONAL_FIRST_NAME_LABEL)
        self.wait_for_visible(self.PERSONAL_LAST_NAME_LABEL)
        return self
