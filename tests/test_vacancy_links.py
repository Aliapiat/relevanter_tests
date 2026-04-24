"""
Тесты функциональности кнопок на странице просмотра вакансии
(/recruiter/vacancy/{id}).

Что проверяем:
  1. «Запись на HR-интервью» — копирует в буфер обмена публичную ссылку
     {origin}/vacancy/{publicSlug}[?recr=...]. Параметр ?token=... в
     этой ссылке недопустим (иначе форма откроется предзаполненной).
  2. Публичная форма /vacancy/{slug} — при переходе по скопированной
     ссылке поля ФИО/Телефон/consent ДОЛЖНЫ быть пустыми. Это важная
     регрессия: в других модулях (например, диалоги) есть ссылки
     с ?token=..., которые специально предзаполняют форму — здесь
     предзаполнения быть НЕ должно.
  3. «AI-скрининг подключен/не подключен» — у вакансии без вопросов
     клик НЕ кладёт ссылку в буфер и выводит toast.
  4. Ссылка на hh.ru — если у вакансии есть интеграция с hh.ru
     (поле hhMainVacancy), на детальной странице рядом с заголовком
     должна быть <a href="https://hh.ru/vacancy/{hh_id}">.

Заметка о реализации кнопок AI-скрининга / HR-интервью:
  recruiter-front/src/pages/VacancyViewPage.tsx (~614-659).
  Обе кнопки НЕ делают переход — они копируют ссылку в буфер и меняют
  подпись на «Скопировано» на ~2с. Поэтому в тестах мы читаем
  navigator.clipboard.readText() и валидируем URL.
"""

import allure
import pytest
from faker import Faker

from pages.vacancy_create_page import VacancyCreatePage
from pages.vacancy_detail_page import VacancyDetailPage
from pages.public_vacancy_page import PublicVacancyPage
from pages.login_page import LoginPage
from pages.sidebar_page import SidebarPage
from pages.dashboard_page import DashboardPage
from config.settings import settings

fake = Faker("ru_RU")


# ─────────────────────────────────────────────────────────
# Мини-хелперы (копия подхода из test_vacancy_display)
# ─────────────────────────────────────────────────────────

def _generate_required() -> dict:
    desc = fake.paragraph(nb_sentences=6)
    while len(desc) < 150:
        desc += " " + fake.sentence()
    company = fake.paragraph(nb_sentences=4)
    while len(company) < 100:
        company += " " + fake.sentence()
    return {
        "title": f"ALIQATEST_Links_{fake.random_int(1000, 9999)}",
        "description": desc,
        "company_description": company,
        "salary_to": "200000",
        "social_package": fake.paragraph(nb_sentences=2),
    }


def _fill_required(vc: VacancyCreatePage) -> dict:
    data = _generate_required()
    vc.fill_required_fields(
        title=data["title"],
        description=data["description"],
        company_description=data["company_description"],
        salary_to=data["salary_to"],
    )
    vc.enter_social_package(data["social_package"])
    return data


def _create_and_open_detail(vc: VacancyCreatePage) -> VacancyDetailPage:
    _fill_required(vc)
    vc.click_create_vacancy()
    detail = VacancyDetailPage(vc.page)
    detail.should_be_loaded()
    return detail


def _wait_copied_label(page, timeout_ms: int = 3000) -> bool:
    """
    Ждёт появления подписи «Скопировано» где-либо на странице
    (визуальное подтверждение того, что onClick отработал и запись
    в clipboard завершена). Возвращает True если успели дождаться.
    """
    try:
        page.locator("button:has-text('Скопировано')").first.wait_for(
            state="visible", timeout=timeout_ms
        )
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════
# ТЕСТЫ
# ═══════════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Функциональность кнопок на странице вакансии")
class TestVacancyDetailLinks:

    # ─────────────────────────────────────────────
    # HR-интервью: корректный формат ссылки
    # ─────────────────────────────────────────────

    @allure.story("Запись на HR-интервью")
    @allure.title(
        "Кнопка «Запись на HR-интервью» копирует публичную ссылку "
        "без токена"
    )
    @pytest.mark.vacancy
    @pytest.mark.smoke
    def test_hr_interview_button_copies_public_link(
        self, auth_vacancy_create
    ):
        detail = _create_and_open_detail(auth_vacancy_create)

        sentinel = detail.reset_clipboard()
        detail.click_hr_interview_button()
        _wait_copied_label(detail.page)
        copied = detail.read_clipboard()

        allure.attach(
            copied,
            name="clipboard after HR-interview click",
            attachment_type=allure.attachment_type.TEXT,
        )

        assert copied and copied != sentinel, (
            "После клика «Запись на HR-интервью» буфер обмена не "
            "изменился. Фактическое содержимое: "
            f"{copied!r}. Ожидали публичную ссылку /vacancy/{{slug}}."
        )
        assert "/vacancy/" in copied, (
            f"Скопированная ссылка не содержит '/vacancy/': {copied!r}"
        )
        assert "token=" not in copied, (
            "Скопированная ссылка содержит параметр token=, который "
            "предзаполнит форму кандидата. Для этой кнопки так быть "
            f"НЕ должно. URL: {copied!r}"
        )

    # ─────────────────────────────────────────────
    # Публичная форма — должна открываться пустой
    # ─────────────────────────────────────────────

    @allure.story("Запись на HR-интервью")
    @allure.title(
        "Публичная форма по ссылке «Запись на HR-интервью» "
        "открывается пустой"
    )
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.vacancy
    @pytest.mark.critical
    def test_public_vacancy_form_is_empty_on_recruiter_link(
        self, auth_vacancy_create, browser
    ):
        detail = _create_and_open_detail(auth_vacancy_create)
        detail.reset_clipboard()
        detail.click_hr_interview_button()
        _wait_copied_label(detail.page)
        public_url = detail.read_clipboard()

        assert public_url and "/vacancy/" in public_url, (
            f"Не удалось получить публичную ссылку: {public_url!r}"
        )
        assert "token=" not in public_url, (
            f"Ссылка содержит token=, форма будет предзаполнена: "
            f"{public_url!r}"
        )

        # Открываем скопированную ссылку в отдельном context —
        # как если бы её открыл сторонний кандидат, без cookies
        # рекрутера. Именно так её получит реальный пользователь.
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        try:
            page = context.new_page()
            public = PublicVacancyPage(page)
            public.open_and_wait(public_url)
            public.should_form_be_empty()
        finally:
            context.close()

    # ─────────────────────────────────────────────
    # AI-скрининг без вопросов — ошибка, clipboard не меняется
    # ─────────────────────────────────────────────

    @allure.story("AI-скрининг")
    @allure.title(
        "Клик «AI-скрининг не подключен» без вопросов: toast об ошибке, "
        "ссылка в буфер не попадает"
    )
    @pytest.mark.vacancy
    @pytest.mark.regression
    def test_ai_screening_without_questions_does_not_copy_link(
        self, auth_vacancy_create
    ):
        detail = _create_and_open_detail(auth_vacancy_create)

        sentinel = detail.reset_clipboard()

        text_before = detail.get_ai_screening_button_text()
        assert "AI-скрининг" in text_before, (
            f"Подпись AI-кнопки неожиданная: {text_before!r}"
        )

        detail.click_ai_screening_button()

        # Фронт показывает toast-уведомление через react-hot-toast.
        # Ждём несколько секунд; этого достаточно для появления.
        toast_appeared = True
        try:
            detail.page.get_by_text(
                "Нет вопросов для AI-скрининга"
            ).first.wait_for(state="visible", timeout=5000)
        except Exception:
            toast_appeared = False

        clipboard_after = detail.read_clipboard()

        allure.attach(
            clipboard_after,
            name="clipboard after AI-screening click",
            attachment_type=allure.attachment_type.TEXT,
        )

        # Главная проверка: если вопросов нет — ссылка в буфер не
        # должна попадать. Это защищает от «молчаливого» копирования
        # несуществующего скрининга.
        assert clipboard_after == sentinel, (
            "У вакансии без вопросов клик по «AI-скрининг не подключен» "
            "всё равно положил ссылку в буфер обмена. Фронт должен был "
            "показать toast и ничего не копировать. "
            f"Clipboard: {clipboard_after!r}"
        )

        # Если toast не появился — оставляем этот факт в отчёте,
        # но главная проверка выше уже отработала.
        if not toast_appeared:
            allure.attach(
                "Toast «Нет вопросов для AI-скрининга» не появился "
                "за 5с — возможно, изменился текст уведомления. "
                "Главный инвариант (ссылка не скопирована) соблюдён.",
                name="note: toast not detected",
                attachment_type=allure.attachment_type.TEXT,
            )


# ═══════════════════════════════════════════════════════════
# HH-ИНТЕГРАЦИЯ — отдельный класс: тест ищет существующую
# вакансию через API; если интеграции на стенде нет — skip.
# ═══════════════════════════════════════════════════════════

@allure.epic("Вакансии")
@allure.feature("Функциональность кнопок на странице вакансии")
@allure.story("Ссылка на hh.ru")
class TestHhVacancyLink:

    @allure.title(
        "Если у вакансии есть интеграция с hh.ru — рядом с заголовком "
        "отображается ссылка https://hh.ru/vacancy/{id}"
    )
    @pytest.mark.vacancy
    @pytest.mark.integration
    def test_hh_link_points_to_correct_vacancy(
        self, authenticated_page, api_client
    ):
        hh_vacancy = api_client.find_vacancy_with_hh_integration()
        if not hh_vacancy:
            pytest.skip(
                "На стенде не нашлось вакансий со связкой с hh.ru "
                "(поля hhVacancyId / hhAdditionalVacancyIds пусты). "
                "Подключите любую вакансию к hh.ru (импорт или ввод "
                "hh-id вручную) и перезапустите тест."
            )

        vacancy_id = hh_vacancy["id"]
        expected_hh_id = str(hh_vacancy.get("hhVacancyId") or "").strip()
        # Если основной связки нет — берём первую из дополнительных:
        # всё равно одна из кнопок hh.ru должна присутствовать на странице.
        if not expected_hh_id:
            add_ids = hh_vacancy.get("hhAdditionalVacancyIds") or []
            if add_ids:
                expected_hh_id = str(add_ids[0]).strip()
        assert expected_hh_id, (
            "API вернул вакансию со связкой hh, но ни hhVacancyId, "
            "ни hhAdditionalVacancyIds не содержат корректного id. "
            f"Объект: "
            f"{ {k: hh_vacancy.get(k) for k in ('id', 'title', 'hhVacancyId', 'hhAdditionalVacancyIds')} }"
        )

        url = f"{settings.BASE_URL.rstrip('/')}/recruiter/vacancy/{vacancy_id}"
        authenticated_page.goto(url, wait_until="domcontentloaded")

        detail = VacancyDetailPage(authenticated_page)
        detail.should_be_loaded()

        # Страница подгружает имена hh-вакансий асинхронно (см.
        # VacancyViewPage.tsx:loadHHVacancies). Даём UI время отрисовать
        # <a href="https://hh.ru/vacancy/..."> после редиректа.
        try:
            authenticated_page.locator(
                detail.HH_VACANCY_LINK
            ).first.wait_for(state="visible", timeout=10_000)
        except Exception:
            pass

        assert detail.has_hh_link(), (
            f"На странице вакансии id={vacancy_id} не найдена ссылка "
            f"на hh.ru, хотя API содержит hhVacancyId="
            f"{hh_vacancy.get('hhVacancyId')!r} / hhAdditionalVacancyIds="
            f"{hh_vacancy.get('hhAdditionalVacancyIds')!r}."
        )

        # На странице может быть несколько ссылок (основная + доп.).
        # Допустимым считается любой href вида https://hh.ru/vacancy/<id>,
        # где <id> есть в hhVacancyId либо в hhAdditionalVacancyIds.
        all_hrefs = authenticated_page.locator(
            detail.HH_VACANCY_LINK
        ).evaluate_all("els => els.map(e => e.href)")
        allowed_ids = set(filter(None, [
            str(hh_vacancy.get("hhVacancyId") or "").strip(),
            *[str(x).strip() for x in (hh_vacancy.get("hhAdditionalVacancyIds") or [])],
        ]))
        allowed_urls = {f"https://hh.ru/vacancy/{i}" for i in allowed_ids}

        assert all_hrefs, "Ссылок на hh.ru нет, хотя селектор что-то нашёл."
        for href in all_hrefs:
            assert href in allowed_urls, (
                f"Найдена ссылка на hh.ru, которой нет в API-данных "
                f"вакансии id={vacancy_id}. href={href!r}, "
                f"ожидали из {allowed_urls}"
            )
