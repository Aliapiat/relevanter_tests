import allure
from pages.base_page import BasePage


class PublicVacancyPage(BasePage):
    """
    Публичная страница вакансии: /vacancy/{publicSlug}

    Это страница, которую открывает кандидат, чтобы записаться
    на интервью. На ней есть форма «Записаться на интервью»
    с полями ФИО, Телефон и checkbox согласия на обработку ПД.

    Соответствует компоненту recruiter-front/src/pages/VacancyPage.tsx
    (см. блок consentGiven=false, строки ~433-513).

    Ссылка на эту страницу копируется из детальной карточки вакансии
    кнопкой «Запись на HR-интервью». При переходе по такой ссылке
    (без параметра ?token=...) поля формы ДОЛЖНЫ быть пустыми —
    проверяется в test_vacancy_links.py.
    """

    PATH_PATTERN = "/vacancy/"

    FORM_HEADER = "h2:has-text('Записаться на интервью')"
    # input ФИО идёт ПЕРВЫМ <input type="text"> внутри формы consent.
    FIO_INPUT = "input[placeholder='Иван Иванов']"
    PHONE_INPUT = "input[placeholder=\"+7 (999) 123-45-67\"]"
    CONSENT_CHECKBOX = "input#consent[type='checkbox']"
    SUBMIT_BUTTON = "button[type='submit']"

    @allure.step("Открываем публичную ссылку и ждём формы записи")
    def open_and_wait(self, url: str):
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.locator(self.FORM_HEADER).wait_for(
            state="visible", timeout=20_000
        )
        return self

    @allure.step("Читаем значение поля ФИО")
    def get_fio(self) -> str:
        return self.page.locator(self.FIO_INPUT).input_value()

    @allure.step("Читаем значение поля Телефон")
    def get_phone(self) -> str:
        return self.page.locator(self.PHONE_INPUT).input_value()

    @allure.step("Состояние чекбокса согласия")
    def is_consent_checked(self) -> bool:
        return self.page.locator(self.CONSENT_CHECKBOX).is_checked()

    @allure.step("Кнопка submit отключена?")
    def is_submit_disabled(self) -> bool:
        return self.page.locator(self.SUBMIT_BUTTON).is_disabled()

    @allure.step(
        "Форма должна быть пустой: поля без значений, чекбокс снят"
    )
    def should_form_be_empty(self):
        """Агрегатная проверка: по ссылке с детальной карточки форма
        обязана открываться чистой, без предзаполнения.
        """
        fio = self.get_fio()
        phone = self.get_phone()
        consent = self.is_consent_checked()

        problems = []
        if fio:
            problems.append(f"ФИО заполнено: {fio!r}")
        if phone:
            problems.append(f"Телефон заполнен: {phone!r}")
        if consent:
            problems.append("Чекбокс согласия отмечен")

        assert not problems, (
            "Публичная форма записи на интервью открылась "
            "предзаполненной по ссылке «Запись на HR-интервью». "
            "В отличие от ссылок с ?token=... (из модуля диалогов), "
            "эта ссылка не должна содержать данные кандидата. "
            "Найдено: " + "; ".join(problems)
        )
        return self
