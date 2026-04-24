"""
Интеграция с Allure: безопасные обёртки и session-wide мета-информация.

Здесь собрано всё, что касается обогащения Allure-отчётов, но НЕ относится
напрямую к тестовой логике. Вынесено отдельно, чтобы:

    • `session_registry` / POM-объекты не тянули за собой Allure-импорт
      и могли работать вне pytest (скрипты, REPL).
    • любой вызов был «fail-safe»: если нет активного теста, не подключён
      allure-listener, или упал сам allure — тест продолжает выполняться.

Публичный API:

    attach_vacancy_id(vid)
        Прикрепляет параметр "vacancy_id" к текущему тесту. Главное место,
        которое делает этот параметр видимым в отчёте:
        Allure → тест → вкладка "Parameters".

    write_environment_properties(results_dir)
        Пишет `environment.properties` с env/BASE_URL/browser/git-sha,
        чтобы в отчёте слева отображались реальные условия прогона.

    write_executor_json(results_dir)
        Пишет `executor.json` — полезно в CI: в отчёте рядом с билдом
        появится ссылка на GitHub Actions run.

    write_categories_json(results_dir)
        Пишет `categories.json` с правилами классификации падений:
        TimeoutError → "Flaky timeouts", AssertionError → "Product bugs" и т.д.
        В отчёте появится вкладка "Categories", которая группирует
        проблемы по типу — очень удобно менеджеру/QA-lead.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────────────────────────────────
# Per-test: параметры
# ──────────────────────────────────────────────────────────────────────────

def attach_vacancy_id(vid: Any) -> None:
    """Безопасно прикрепляет vacancy_id к текущему Allure-тесту.

    Вызывается из всех мест, где тест впервые узнаёт id созданной
    вакансии (network-listener, POM.get_vacancy_id_from_url,
    ручное добавление в cleanup_test_vacancies).

    Любая ошибка подавляется: если allure не установлен, вне теста,
    или listener не прицеплен — просто ничего не делаем.
    """
    if vid is None:
        return
    try:
        import allure  # локальный импорт: allure не должен быть hard dep
        allure.dynamic.parameter("vacancy_id", str(vid))
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────
# Session-wide: environment.properties
# ──────────────────────────────────────────────────────────────────────────

def _git_sha_short() -> str | None:
    """Возвращает короткий SHA HEAD-коммита. None — если git недоступен
    или мы не в репо (например, собранный Docker)."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parent.parent,
        )
        return out.decode("utf-8").strip() or None
    except Exception:
        return None


def _git_branch() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parent.parent,
        )
        return out.decode("utf-8").strip() or None
    except Exception:
        return None


def write_environment_properties(results_dir: str | Path) -> None:
    """Формирует `environment.properties` — Allure показывает этот
    блок слева на главной странице отчёта. Сюда кладём всё, что
    нужно знать о контексте прогона, чтобы потом отличить «упал в dev»
    от «упал в prod» не открывая логи.

    Пишется один раз в начале сессии. Файл игнорируется git'ом
    через .gitignore (он лежит в allure-results/, который уже в ignore).
    """
    try:
        from config.settings import settings
    except Exception:
        settings = None

    # Импорт ленивый: config.environments опционален вне pytest
    try:
        from config.environments import ENVIRONMENTS
    except Exception:
        ENVIRONMENTS = {}

    env_name = os.getenv("TEST_ENV", "dev")
    # ENVIRONMENTS в этом проекте — это dict[str, str] (env -> base_url).
    # Берём URL из settings.BASE_URL, если его нет — фоллбэк на словарь.
    base_url = getattr(settings, "BASE_URL", None) or ENVIRONMENTS.get(env_name, "")

    props: dict[str, str | None] = {
        "Environment": env_name,
        "Base.URL": base_url,
        "Browser": os.getenv("BROWSER", "chromium"),
        "Headless": str(getattr(settings, "HEADLESS", False)) if settings else "",
        "Viewport": "1920x1080",
        "Python": sys.version.split()[0],
        "OS": f"{platform.system()} {platform.release()}",
        "Git.Branch": _git_branch(),
        "Git.SHA": _git_sha_short(),
        "CI": os.getenv("GITHUB_ACTIONS") or os.getenv("CI") or "local",
    }

    # Для рекрутёра показываем только логин — пароль в отчёт не идёт
    recruiter = getattr(settings, "RECRUITER_EMAIL", None) if settings else None
    if recruiter:
        props["Recruiter.Account"] = recruiter

    path = Path(results_dir)
    path.mkdir(parents=True, exist_ok=True)
    with (path / "environment.properties").open("w", encoding="utf-8") as f:
        for k, v in props.items():
            if v is None or v == "":
                continue
            # Allure читает в формате key=value, одна пара на строку.
            # Пробелы в ключе ломают парсинг — заменяем на точку.
            safe_key = k.replace(" ", ".")
            f.write(f"{safe_key}={v}\n")


def write_executor_json(results_dir: str | Path) -> None:
    """Пишет `executor.json` с информацией о том, кто запустил прогон.
    В CI это GitHub Actions; локально — пользователь ОС. Allure покажет
    иконку и ссылку на билд на главной странице отчёта.
    """
    is_ci = os.getenv("GITHUB_ACTIONS") == "true"

    if is_ci:
        server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
        repo = os.getenv("GITHUB_REPOSITORY", "")
        run_id = os.getenv("GITHUB_RUN_ID", "")
        run_number = os.getenv("GITHUB_RUN_NUMBER", "")
        build_url = f"{server_url}/{repo}/actions/runs/{run_id}" if repo and run_id else ""
        data = {
            "name": "GitHub Actions",
            "type": "github",
            "url": build_url,
            "buildOrder": int(run_number) if run_number.isdigit() else 0,
            "buildName": f"#{run_number}" if run_number else "",
            "buildUrl": build_url,
            "reportUrl": "",
            "reportName": "Allure Report",
        }
    else:
        data = {
            "name": "Local",
            "type": "local",
            "buildName": f"local-{_git_sha_short() or 'unknown'}",
        }

    path = Path(results_dir)
    path.mkdir(parents=True, exist_ok=True)
    with (path / "executor.json").open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────────────
# Session-wide: categories.json — автоматическая классификация падений
# ──────────────────────────────────────────────────────────────────────────
#
# Allure позволяет задать регэкспы по сообщению/трейсу, и тогда на вкладке
# "Categories" все падения распределятся по осмысленным группам. Очень
# помогает: видно, что «из 20 упавших 15 — это Playwright timeouts
# (инфра/сеть), а 5 — реальные AssertionError (бизнес-логика)».
_CATEGORIES: list[dict] = [
    {
        "name": "Product defects — AssertionError",
        "matchedStatuses": ["failed"],
        "messageRegex": ".*AssertionError.*",
    },
    {
        "name": "Playwright timeouts (flaky/infra)",
        "matchedStatuses": ["broken", "failed"],
        "messageRegex": ".*(TimeoutError|Timeout \\d+ms exceeded).*",
    },
    {
        "name": "Element not found / selector issues",
        "matchedStatuses": ["broken", "failed"],
        "messageRegex": ".*(Locator|strict mode violation|waiting for locator).*",
    },
    {
        "name": "Network / HTTP errors",
        "matchedStatuses": ["broken", "failed"],
        "messageRegex": ".*(ConnectionError|ReadTimeout|HTTPError|ECONNRESET).*",
    },
    {
        "name": "Test infrastructure (fixtures / setup)",
        "matchedStatuses": ["broken"],
        "traceRegex": ".*conftest\\.py.*",
    },
]


def write_categories_json(results_dir: str | Path) -> None:
    path = Path(results_dir)
    path.mkdir(parents=True, exist_ok=True)
    with (path / "categories.json").open("w", encoding="utf-8") as f:
        json.dump(_CATEGORIES, f, ensure_ascii=False, indent=2)
