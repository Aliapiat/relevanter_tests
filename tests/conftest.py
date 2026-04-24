# tests/conftest.py

import os

import pytest
import allure
from playwright.sync_api import Page

from pages.login_page import LoginPage
from pages.dashboard_page import DashboardPage
from pages.sidebar_page import SidebarPage
from pages.vacancy_create_page import VacancyCreatePage
from config.settings import settings
from utils.api_client import APIClient
from utils import session_registry
from utils.allure_hooks import (
    attach_vacancy_id,
    write_environment_properties,
    write_executor_json,
    write_categories_json,
)


# ═══════════════════════════════════════════
# НАСТРОЙКИ БРАУЗЕРА
# ═══════════════════════════════════════════

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        # Для тестов, читающих то, что скопировано кнопками
        # «AI-скрининг подключен» / «Запись на HR-интервью»
        # через navigator.clipboard.readText().
        "permissions": ["clipboard-read", "clipboard-write"],
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "headless": settings.HEADLESS,
        "slow_mo": settings.SLOW_MO,
    }


# ═══════════════════════════════════════════
# БАЗОВЫЕ ФИКСТУРЫ СТРАНИЦ
# ═══════════════════════════════════════════

@pytest.fixture
def login_page(page: Page) -> LoginPage:
    return LoginPage(page)


@pytest.fixture
def dashboard_page(page: Page) -> DashboardPage:
    return DashboardPage(page)


@pytest.fixture
def sidebar_page(page: Page) -> SidebarPage:
    return SidebarPage(page)


@pytest.fixture
def vacancy_create_page(page: Page) -> VacancyCreatePage:
    return VacancyCreatePage(page)


# ═══════════════════════════════════════════
# АВТОРИЗОВАННОЕ СОСТОЯНИЕ
# ═══════════════════════════════════════════

def _register_vacancy_from_response(response) -> None:
    """Неблокирующий коллбэк для page.on('response'): ловит успешный
    POST /api/v1/positions, достаёт id из response body и регистрирует
    его в session_registry. Это ГЛАВНЫЙ механизм регистрации созданных
    в тесте вакансий — работает в фоне и не замедляет тесты.

    Почему именно network-listener, а не wait_for_url:
        • listener срабатывает сразу, когда бэкенд ответил 2xx на POST,
          т.е. ещё до того, как фронт сделал редирект. Не блокирует поток.
        • для negative-сценариев (бэкенд вернул 4xx, клиентская
          валидация вообще не дошла до сети) — callback просто не
          вызовется, лишних задержек нет.
        • работает и в UI-тестах, и если будущий API-only клиент
          сделает тот же POST через тот же page-контекст.

    Всё защищено try/except: любой сбой в listener'е (например, body
    не JSON) не должен ронять тест.
    """
    try:
        req = response.request
        if req.method != "POST":
            return
        if "/api/v1/positions" not in response.url:
            return
        # Берём только финальный успешный ответ. Редиректы 3xx фронт
        # обрабатывает сам, идемпотентный POST их обычно не отдаёт.
        if not (200 <= response.status < 300):
            return
        try:
            body = response.json()
        except Exception:
            return
        if not isinstance(body, dict):
            return
        vid = body.get("id")
        if vid is not None:
            session_registry.register(vid)
            # Прикрепляем vacancy_id к текущему Allure-тесту.
            # Листенер работает в контексте теста (page.on был повешен
            # в authenticated_page), поэтому allure.dynamic.parameter
            # найдёт активный test-case.
            attach_vacancy_id(vid)
    except Exception:
        pass


@pytest.fixture
def authenticated_page(page: Page) -> Page:
    """
    Логинится под рекрутёром (settings.RECRUITER_EMAIL) и возвращает
    page в авторизованном состоянии.

    Почему РЕКРУТЁР, а не ADMIN:
        • ADMIN на стенде видит вакансии всех пользователей. Тест,
          залогиненный админом, в UI-списке «Мои вакансии» и в API
          `/positions` увидит чужие ALIQATEST-вакансии из параллельных
          прогонов — и хотя cleanup отфильтрует их через
          session_registry, при любой ошибке в этой логике риск
          задеть чужое максимален именно у админа.
        • Рекрутёр `forauto@test.py` — отдельный аккаунт, заведённый
          на всех стендах специально под автотесты. Его список
          вакансий изолирован, поэтому `find_vacancies_by_prefix`
          вернёт ровно то, что насоздавали мы. Это второй контур
          защиты сверху ALIQATEST-префикса и session_registry.

    Сверх авторизации вешает network-listener, регистрирующий в
    session_registry все вакансии, созданные через POST /positions
    в рамках теста. Listener снимается в teardown — это важно,
    т.к. playwright может переиспользовать Page между тестами
    внутри одного контекста.
    """
    login = LoginPage(page)
    login.open()
    login.login(settings.RECRUITER_EMAIL, settings.RECRUITER_PASSWORD)

    page.wait_for_url(
        lambda url: "/login" not in url,
        timeout=15000
    )

    DashboardPage(page).should_be_loaded()

    page.on("response", _register_vacancy_from_response)
    try:
        yield page
    finally:
        try:
            page.remove_listener("response", _register_vacancy_from_response)
        except Exception:
            pass


@pytest.fixture
def auth_sidebar(authenticated_page: Page) -> SidebarPage:
    """Авторизованный сайдбар"""
    sidebar = SidebarPage(authenticated_page)
    sidebar.should_be_loaded()
    return sidebar


@pytest.fixture
def auth_vacancy_create(authenticated_page: Page, api_client: APIClient) -> VacancyCreatePage:
    """
    Авторизуется → нажимает 'Новая вакансия' →
    возвращает страницу создания вакансии.

    После теста удаляет вакансию если она была создана (URL содержит ID).
    Работает и для позитивных тестов, и для случаев когда вакансия
    создалась неожиданно (например при невалидных данных).
    """
    sidebar = SidebarPage(authenticated_page)
    sidebar.should_be_loaded()
    sidebar.click_new_vacancy()

    vacancy_page = VacancyCreatePage(authenticated_page)
    vacancy_page.should_be_loaded()

    yield vacancy_page

    vacancy_id = vacancy_page.get_vacancy_id_from_url()
    if vacancy_id:
        try:
            api_client.delete_vacancy(vacancy_id)
        except Exception as e:
            print(f"[cleanup] Не удалось удалить вакансию id={vacancy_id}: {e}")
            # Резервная очистка по префиксам — c защитой реальных QA-вакансий
            _bulk_delete(api_client, "fallback")


# ═══════════════════════════════════════════
# ALLURE — автодефолты и сессионная мета-информация
# ═══════════════════════════════════════════
#
# Идея: писать @allure.severity на 150+ тестов вручную — плохо, завтра
# добавим новый тест и забудем. Вместо этого — autouse-фикстура, которая
# маппит pytest-маркеры на severity. Явный @allure.severity на тесте
# всегда побеждает: allure-pytest сам запишет его из маркера allure_severity,
# и наш фолбэк ничего не перезапишет (мы проверяем iter_markers ниже).

_MARKER_TO_SEVERITY = [
    # порядок имеет значение: проверяем от «сильнейшего» к «слабейшему»
    ("smoke_critical", "blocker"),
    ("smoke", "critical"),
    ("validation", "normal"),
    ("modals", "normal"),
    ("navigation", "normal"),
]


@pytest.fixture(autouse=True)
def _default_allure_severity(request):
    """Проставляет severity по умолчанию на основании pytest-маркеров.

    Явный @allure.severity(...) на тесте/классе имеет приоритет: allure
    прячет все свои декораторы за единым pytest-маркером `allure_label`
    с kwargs['label_type']='severity' (см. allure_pytest.utils). Если он
    уже есть — мы молча уходим, чтобы не ставить второй label и не
    получить в отчёте `severity=[blocker, blocker]`.
    """
    for m in request.node.iter_markers("allure_label"):
        if m.kwargs.get("label_type") == "severity":
            return

    try:
        import allure
    except Exception:
        return

    marker_names = {m.name for m in request.node.iter_markers()}
    chosen = "minor"  # дефолт для «UI-видимости»/плейсхолдеров и прочей мелочи
    for marker, sev in _MARKER_TO_SEVERITY:
        if marker in marker_names:
            chosen = sev
            break

    try:
        allure.dynamic.severity(getattr(allure.severity_level, chosen.upper()))
    except Exception:
        pass


def pytest_configure(config):
    """Один раз за сессию пишет в allure-results/ метаданные окружения,
    информацию об исполнителе (CI/локально) и categories.json.

    Реализовано через hook (а не autouse-фикстуру) намеренно:
        • pytest_configure выполняется ДО сбора тестов и до того,
          как allure-pytest начнёт писать свои result-файлы. Наши
          метаданные гарантированно окажутся в той же папке.
        • config.getoption даёт путь после парсинга pytest'ом —
          это надёжнее, чем разбирать sys.argv руками.
    """
    results_dir = config.getoption("--alluredir", None)
    if not results_dir:
        # fallback по ENV — удобно в CI задавать один раз
        results_dir = os.getenv("ALLURE_RESULTS_DIR")
    if not results_dir:
        return
    try:
        write_environment_properties(results_dir)
        write_executor_json(results_dir)
        write_categories_json(results_dir)
    except Exception as e:
        print(f"[allure-env] Не удалось записать метаданные: {e}")


# ═══════════════════════════════════════════
# СКРИНШОТ ПРИ ПАДЕНИИ
# ═══════════════════════════════════════════

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """При падении теста собираем максимум контекста для Allure.

    Минимум — скриншот. Добавляем ещё URL, заголовок и HTML body,
    потому что в CI картинка часто неинформативна (spinner или белый
    экран), а текст страницы точно говорит, куда нас занесло:
    залогинились ли, не редиректнуло ли на /login, не вернул ли
    бэкенд 500/403 и т.д.
    """
    outcome = yield
    report = outcome.get_result()
    if report.when not in ("setup", "call") or not report.failed:
        return

    page = item.funcargs.get("page")
    if not page:
        return

    try:
        allure.attach(
            page.screenshot(full_page=True),
            name="failure_screenshot",
            attachment_type=allure.attachment_type.PNG,
        )
    except Exception:
        pass

    try:
        allure.attach(
            f"URL: {page.url}\nTitle: {page.title()}",
            name="page_context",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:
        pass

    try:
        html = page.content()
        if len(html) > 200_000:
            html = html[:200_000] + "\n<!-- ... truncated ... -->"
        allure.attach(
            html,
            name="page_html",
            attachment_type=allure.attachment_type.HTML,
        )
    except Exception:
        pass


@pytest.fixture(scope="session")
def api_client() -> APIClient:
    """
    API-клиент с авторизацией.
    Использует тот же стенд что и UI-тесты.
    """
    client = APIClient()  # возьмёт из settings.BASE_URL который уже установлен
    client.authenticate()
    return client


# ─── Префиксы тестовых вакансий ────────────────────────────────────────────
# ВАЖНО: любой тест, который создаёт вакансию, ОБЯЗАН давать ей название,
# начинающееся с одного из префиксов ниже. Cleanup удаляет вакансии ТОЛЬКО
# по этим префиксам — это единственный способ гарантировать, что мы не
# заденем чужие (пользовательские) вакансии на общем стенде.
#
# На момент перехода на единый идентификатор используем только "ALIQATEST":
# подходит и "ALIQATEST_..." (с подчёркиванием), и "ALIQATEST Название"
# (с пробелом). Исторические префиксы ("AutoTest_", "Тест " и т.д.) удалены
# из этого списка намеренно: подобные названия встречаются в «живых»
# вакансиях, не созданных автотестами, и удалять их небезопасно.
_CLEANUP_PREFIXES = ("ALIQATEST",)

# Защита от случайного удаления реальных вакансий.
# Если в названии встречается любая из подстрок (case-insensitive), вакансия
# НЕ удаляется даже если её заголовок начинается с тестового префикса.
# Страховочный слой поверх _CLEANUP_PREFIXES — на случай, если кто-то
# сознательно назвал рабочую вакансию "ALIQATEST ..." и её нужно уберечь.
PROTECTED_TITLE_SUBSTRINGS = (
    "qa auto",
    "qa-auto",
    "автотест",
    "автоматизатор",
    "automation",
    "sdet",
)


def _is_protected(title: str) -> bool:
    if not title:
        return False
    low = title.lower()
    return any(sub in low for sub in PROTECTED_TITLE_SUBSTRINGS)


def _bulk_delete(client: APIClient, label: str = "") -> None:
    """Удаляет только те вакансии с префиксом ALIQATEST, которые
    зарегистрированы в session_registry как созданные в этой pytest-сессии.

    Алгоритм:
        1. Ищем кандидатов по префиксу — это быстрый фильтр, чтобы
           не таскать все вакансии стенда.
        2. Пересекаем найденные id с тем, что зарегистрировал POM
           после click_create_vacancy (utils/session_registry.py).
        3. Удаляем только пересечение. Если по префиксу пришла вакансия,
           которой нет в реестре — это либо чужой прогон, либо остаток
           упавшего предыдущего CI. Мы её НЕ трогаем и явно об этом
           логируем, чтобы человек мог разобраться руками через
           scripts/cleanup_vacancies.py.

    Дополнительный страховочный слой: PROTECTED_TITLE_SUBSTRINGS.
    Даже если id оказался в реестре, но в title подстрока из whitelist
    (например «QA Auto Engineer»), мы не удаляем — на случай, если
    id случайно попал в реестр по ошибке.
    """
    tag = f"[cleanup{' ' + label if label else ''}]"

    registered = session_registry.all_ids()
    if not registered:
        # До click_create_vacancy ни один тест не добежал — удалять
        # нечего. Для before-session это норма.
        print(f"{tag} session_registry пуст — пропускаем")
        return

    candidates_by_prefix: dict[int, dict] = {}
    for prefix in _CLEANUP_PREFIXES:
        try:
            for v in client.find_vacancies_by_prefix(prefix):
                vid = v.get("id")
                if vid is not None:
                    candidates_by_prefix[vid] = v
        except Exception as e:
            print(f"{tag} ОШИБКА при поиске префикса '{prefix}': {e}")

    # id, которые реестр считает «нашими»:
    owned_ids = registered & set(candidates_by_prefix.keys())
    # id, которые реестр утверждает, что создавал, но API их уже не
    # отдаёт (успел удалиться в рамках теста или упал 404):
    registered_but_missing = registered - set(candidates_by_prefix.keys())
    # id, которые есть на стенде с префиксом, но НЕ регистрировались
    # в этой сессии — чужие:
    foreign_ids = set(candidates_by_prefix.keys()) - registered

    if foreign_ids:
        print(
            f"{tag} SKIP {len(foreign_ids)} вакансий с префиксом "
            f"ALIQATEST, которые не создавались в этой сессии "
            f"(не удаляем чужое): "
            f"{sorted(foreign_ids)}"
        )

    if registered_but_missing:
        print(
            f"{tag} в реестре есть id {sorted(registered_but_missing)}, "
            f"но сервер уже не отдаёт их по префиксу — вероятно, тест "
            f"удалил их сам. Чистим из реестра."
        )
        for vid in registered_but_missing:
            session_registry.unregister(vid)

    total_deleted = 0
    total_skipped = 0
    for vid in sorted(owned_ids):
        v = candidates_by_prefix[vid]
        title = v.get("title", "")
        if _is_protected(title):
            print(f"{tag} SKIP id={vid} '{title}' (protected whitelist)")
            total_skipped += 1
            continue
        try:
            status = client.delete_vacancy(vid)
            print(f"{tag} удалена id={vid} '{title}' → {status}")
            session_registry.unregister(vid)
            total_deleted += 1
        except Exception as e:
            print(f"{tag} ОШИБКА удаления id={vid} '{title}': {e}")

    print(
        f"{tag} итого: удалено {total_deleted}, "
        f"пропущено по whitelist {total_skipped}, "
        f"чужих пропущено {len(foreign_ids)}"
    )


@pytest.fixture(scope="session", autouse=True)
def session_vacancy_cleanup(api_client: APIClient):
    # До сессии реестр гарантированно пуст — before-session ничего
    # не удалит по дизайну. Оставляем вызов для логирующих целей:
    # если по какой-то причине реестр уже наполнен (например,
    # пересборка между сессиями в одном процессе), отработает как
    # обычный cleanup.
    _bulk_delete(api_client, "before-session")
    yield
    _bulk_delete(api_client, "after-session")


@pytest.fixture
def cleanup_test_vacancies(api_client):
    """
    Фикстура для очистки тестовых вакансий в рамках одного теста.

    Использование 1 — опираться на автоматическую регистрацию:
        def test_something(cleanup_test_vacancies, auth_vacancy_create):
            # click_create_vacancy() сам зарегистрирует id вакансии
            # в session_registry. Фикстура в teardown удалит только те
            # id, которые оказались в реестре и пришли с API под
            # префиксом ALIQATEST.
            ...

    Использование 2 — ручное добавление ID (для API-only-тестов,
    которые создают вакансии в обход UI):
        def test_something(cleanup_test_vacancies):
            vid = api_client.create_via_raw_post(...)
            cleanup_test_vacancies.append(vid)

    Важно: фикстура НИКОГДА не удаляет вакансии, которых нет в
    session_registry, даже если их имя начинается с ALIQATEST. Это
    гарантирует, что один падающий тест не унесёт за собой чужие
    ALIQATEST-вакансии от параллельного прогона.
    """
    manual_ids: list[int] = []
    yield manual_ids

    # Любой id, переданный вручную, тоже считаем «своим»
    # и кладём в реестр — чтобы общая сессионная очистка его
    # увидела и посчитала. Заодно прикрепляем к Allure: API-only
    # тесты никогда не проходят через page.on('response'), так что
    # без этой строчки в отчёте не будет vacancy_id.
    for vid in manual_ids:
        session_registry.register(vid)
        attach_vacancy_id(vid)

    # Точечная очистка здесь: удаляем строго по реестру, пересекая
    # с тем, что реально отдаёт API по префиксу ALIQATEST.
    registered = session_registry.all_ids()
    if not registered:
        return

    for prefix in _CLEANUP_PREFIXES:
        try:
            vacancies = api_client.find_vacancies_by_prefix(prefix)
        except Exception:
            continue
        for v in vacancies:
            vid = v.get("id")
            if vid is None or vid not in registered:
                continue
            title = v.get("title", "")
            if _is_protected(title):
                continue
            try:
                api_client.delete_vacancy(vid)
                session_registry.unregister(vid)
            except Exception:
                pass