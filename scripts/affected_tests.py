#!/usr/bin/env python3
"""
Для заданного diff'а (список изменённых файлов) — печатает в stdout
pytest-аргументы для прогона затронутых тестов.

Используется в CI (phase 2 regression по affected files):

    CHANGED=$(git diff --name-only origin/main...HEAD)
    echo "$CHANGED" | python scripts/affected_tests.py

Стратегия маппинга
------------------
• Если изменился сам тестовый файл (`tests/test_*.py`) — запускаем его
  напрямую.
• Если изменился Page Object (`pages/*.py`) или общий тестовый код
  (`conftest.py`, `utils/*`, `config/*`) — ищем тесты, которые
  импортируют этот модуль по имени. Это хорошее приближение:
  page-object меняется редко без теста.
• Если изменился скрипт под `scripts/` (например, сам этот файл) —
  не добавляем ничего (скрипты смотрит не pytest).
• Если изменилась инфраструктура (`conftest.py`, `pytest.ini`,
  `requirements*.txt`, `.github/`) — это global-fallback: печатаем
  аргумент, запускающий ВСЕ тесты (`tests/`), плюс пометка на
  stderr «нужен полный прогон». Это безопасно, но медленно —
  используется как страховка.

На выходе — список уникальных аргументов для pytest. Порядок не
важен, pytest дедуплицирует. Если список пуст — на stdout ничего
не печатается, и CI в таком случае должен запустить ТОЛЬКО smoke
(см. .github/workflows/tests.yml).

Вход:
    пути через stdin (по одному на строку) или через --files arg1 arg2 …

Выход (stdout):
    pytest-аргументы, разделённые пробелом.

Пример:
    $ printf 'pages/login_page.py\\n' | python scripts/affected_tests.py
    tests/test_login.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Корень проекта — папка выше scripts/
ROOT = Path(__file__).resolve().parent.parent

TESTS_DIR = ROOT / "tests"
PAGES_DIR = ROOT / "pages"

# Файлы, изменение которых требует прогнать ВСЁ (слишком широкий
# blast radius, чтобы безопасно отфильтровать).
FULL_RUN_TRIGGERS = (
    "conftest.py",
    "pytest.ini",
    "requirements.txt",
    "requirements-dev.txt",
    ".github/",
    "config/",
    "utils/session_registry.py",
    "utils/api_client.py",
)

# Модули, которые осмысленно искать в `import`-строках тестов.
# Если изменился `pages/login_page.py`, ищем `from pages.login_page`
# или `import pages.login_page` в test_*.py.
IMPORT_SEARCH_PREFIXES = ("pages.", "utils.")

# Явный name-based fallback для POM, которые тесты используют
# ТОЛЬКО через фикстуры (без прямого import). Проверяли: test_login.py
# получает LoginPage через фикстуру login_page и сам pages.login_page
# не импортит — значит import-based поиск его не найдёт, и без этого
# правила регрессии логина не попали бы в affected.
#
# Ключ: stem файла в pages/ (без `_page` суффикса и без `.py`).
# Значение: имена тестовых файлов в tests/, которые надо добавить.
# Фолбэк — пустой список: тогда ориентируемся только на import-поиск.
PAGE_NAME_FALLBACK: dict[str, list[str]] = {
    # login_page — фундамент, задевает все тесты, которые логинятся
    "login": [
        "test_login.py",
    ],
    # dashboard — проверяется в логин-сценариях
    "dashboard": [
        "test_login.py",
    ],
    # sidebar — навигация к созданию и просмотру вакансии
    "sidebar": [
        "test_vacancy_create.py",
        "test_vacancy_validation.py",
    ],
    # create-page — трогает почти весь vacancy-слой
    "vacancy_create": [
        "test_vacancy_create.py",
        "test_vacancy_validation.py",
        "test_vacancy_modals.py",
        "test_vacancy_display.py",
        "test_vacancy_create_via_search_filter.py",
    ],
    # поиск — прицельно только filter-тесты
    "search": [
        "test_vacancy_create_via_search_filter.py",
    ],
    # detail/tab-pages — всё, что ходит по табам созданной вакансии
    "vacancy_detail": [
        "test_vacancy_tabs.py",
        "test_vacancy_links.py",
        "test_vacancy_display.py",
    ],
    # таб-POM, каждый — свой набор тестов
    "vacancy_tab": [
        "test_vacancy_tabs.py",
    ],
    "search_tab": [
        "test_vacancy_tabs.py",
    ],
    "dialogs_tab": [
        "test_vacancy_tabs.py",
    ],
    "interviews_tab": [
        "test_vacancy_tabs.py",
    ],
    "results_tab": [
        "test_vacancy_tabs.py",
    ],
    # публичная форма записи на интервью
    "public_vacancy": [
        "test_vacancy_links.py",
    ],
}


def _files_from_stdin_or_args(argv: list[str]) -> list[str]:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Список изменённых файлов (альтернатива stdin).",
    )
    args = parser.parse_args(argv)

    if args.files:
        return args.files

    return [
        line.strip()
        for line in sys.stdin.read().splitlines()
        if line.strip()
    ]


def _is_full_run(changed: list[str]) -> bool:
    for path in changed:
        norm = path.replace("\\", "/")
        for trigger in FULL_RUN_TRIGGERS:
            if trigger in norm:
                return True
    return False


def _direct_test_files(changed: list[str]) -> set[str]:
    """Вошедшие в diff файлы, которые сами являются тестами."""
    out: set[str] = set()
    for path in changed:
        norm = path.replace("\\", "/")
        if norm.startswith("tests/") and norm.endswith(".py"):
            out.add(norm)
    return out


def _tests_importing(module_dotted: str) -> set[str]:
    """Ищет в tests/*.py строки вида `from <module>` или
    `import <module>` и возвращает пути найденных файлов."""
    out: set[str] = set()
    if not TESTS_DIR.exists():
        return out
    pattern = re.compile(
        rf"^\s*(?:from\s+{re.escape(module_dotted)}(?:\s|\.)"
        rf"|import\s+{re.escape(module_dotted)}(?:\s|\.|$))",
        re.MULTILINE,
    )
    for test_file in TESTS_DIR.rglob("test_*.py"):
        try:
            text = test_file.read_text(encoding="utf-8")
        except Exception:
            continue
        if pattern.search(text):
            rel = test_file.relative_to(ROOT).as_posix()
            out.add(rel)
    return out


def _page_stem_from_path(path: str) -> str | None:
    """pages/vacancy_create_page.py → 'vacancy_create'
    pages/login_page.py → 'login'.
    Возвращает None, если путь не относится к pages/ или не кончается
    на `_page.py`.
    """
    norm = path.replace("\\", "/")
    if not norm.startswith("pages/") or not norm.endswith("_page.py"):
        return None
    fname = norm.rsplit("/", 1)[-1]  # vacancy_create_page.py
    stem = fname[:-len("_page.py")]  # vacancy_create
    return stem


def _dotted_module_from_path(path: str) -> str | None:
    """pages/login_page.py → pages.login_page. Возвращает None для
    путей, которые не кладутся в python-пакеты (например, __init__
    или файлы вне pages/utils)."""
    norm = path.replace("\\", "/")
    if not norm.endswith(".py"):
        return None
    if "/" not in norm:
        return None
    top = norm.split("/", 1)[0]
    accepted_prefix = False
    for p in IMPORT_SEARCH_PREFIXES:
        if top == p.rstrip("."):
            accepted_prefix = True
            break
    if not accepted_prefix:
        return None
    module = norm[:-3].replace("/", ".")
    return module


def resolve_affected(changed: list[str]) -> list[str]:
    if not changed:
        return []

    if _is_full_run(changed):
        # Явный сигнал для CI: полный прогон.
        print(
            "[affected_tests] FULL RUN triggered by changes in "
            "infra files (conftest/pytest.ini/.github/etc).",
            file=sys.stderr,
        )
        return ["tests/"]

    affected: set[str] = set()

    # 1) прямые изменения тестов
    affected |= _direct_test_files(changed)

    # 2) для каждого page object / utility ищем тесты, которые его
    #    импортируют
    for path in changed:
        module = _dotted_module_from_path(path)
        if not module:
            continue
        affected |= _tests_importing(module)

    # 3) name-based fallback: тесты, которые используют POM только
    #    через фикстуры (без прямого import)
    for path in changed:
        stem = _page_stem_from_path(path)
        if not stem:
            continue
        for test_name in PAGE_NAME_FALLBACK.get(stem, []):
            test_path = TESTS_DIR / test_name
            if test_path.exists():
                affected.add(test_path.relative_to(ROOT).as_posix())

    return sorted(affected)


def main() -> int:
    changed = _files_from_stdin_or_args(sys.argv[1:])
    affected = resolve_affected(changed)

    if affected:
        print(" ".join(affected))

    # Всегда exit 0: отсутствие результатов — валидный ответ
    # (тогда CI ограничится smoke).
    return 0


if __name__ == "__main__":
    sys.exit(main())
