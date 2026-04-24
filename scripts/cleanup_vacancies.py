"""
Скрипт ручного удаления тестовых вакансий.

ВАЖНО: скрипт удаляет ТОЛЬКО вакансии, название которых начинается
с префикса "ALIQATEST". Это контракт: все автотесты обязаны называть
создаваемые ими вакансии с этим префиксом. Удаление чужих вакансий
(созданных руками пользователей или другими автотестами с иным префиксом)
по дизайну невозможно — это защита от случайной чистки продового контента
на общем стенде.

Примеры запуска:
    # удалить все вакансии, чьё название начинается с ALIQATEST
    python scripts/cleanup_vacancies.py --all

    # то же на staging
    python scripts/cleanup_vacancies.py --env staging --all

    # "сухой" прогон — только показать, что удалит
    python scripts/cleanup_vacancies.py --all --dry-run

    # точечное удаление по id (даже если имя не содержит ALIQATEST —
    # ответственность на операторе скрипта)
    python scripts/cleanup_vacancies.py --id 200042 200043
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.api_client import APIClient
from config.environments import ENVIRONMENTS

# Единственный разрешённый префикс для массового удаления. Менять нельзя —
# это контракт с тестами (см. tests/conftest.py::_CLEANUP_PREFIXES).
ALIQATEST_PREFIX = "ALIQATEST"

# Страховочный фильтр. Если в названии встречается любая из подстрок
# (case-insensitive), вакансия НЕ удаляется, даже если имя начинается
# с ALIQATEST. Защищает реальные QA-учётки вида "QA Auto Engineer".
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


def _delete_by_ids(client: APIClient, ids: list[int], dry_run: bool) -> None:
    """Удаляет вакансии по списку id. Используется, когда оператор
    точно знает id и сознательно берёт ответственность за то, что
    это «свои» вакансии (например, остатки от упавших CI-ранов)."""
    for vid in ids:
        if dry_run:
            print(f"[DRY RUN] удалил бы вакансию id={vid}")
            continue
        try:
            status = client.delete_vacancy(vid)
            print(f"✅ id={vid} удалена (HTTP {status})")
        except Exception as e:
            print(f"❌ id={vid}: {e}")


def _delete_all_aliqatest(client: APIClient, dry_run: bool) -> None:
    """Удаляет все вакансии, чей title начинается с ALIQATEST_PREFIX,
    кроме тех, что попали под PROTECTED_TITLE_SUBSTRINGS."""
    print(f"🔍 Ищем вакансии с префиксом '{ALIQATEST_PREFIX}'...")
    vacancies = client.find_vacancies_by_prefix(ALIQATEST_PREFIX)

    if not vacancies:
        print("   Не найдено — стенд чист.")
        return

    print(f"   Найдено: {len(vacancies)}")

    deleted = failed = protected = 0
    for v in vacancies:
        vid = v.get("id")
        title = v.get("title", "???")

        if _is_protected(title):
            print(f"   🛡 SKIP id={vid}: '{title}' (в whitelist)")
            protected += 1
            continue

        if dry_run:
            print(f"   [DRY RUN] id={vid}: '{title}'")
            continue

        try:
            status = client.delete_vacancy(vid)
            print(f"   ✅ id={vid}: '{title}' (HTTP {status})")
            deleted += 1
        except Exception as e:
            print(f"   ❌ id={vid}: '{title}' — {e}")
            failed += 1

    print()
    if dry_run:
        print(
            f"Готово (DRY RUN). Было бы удалено: "
            f"{len(vacancies) - protected}, защищено: {protected}"
        )
    else:
        print(
            f"Готово. Удалено: {deleted}, "
            f"ошибок: {failed}, защищено: {protected}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            f"Удаляет тестовые вакансии через API. "
            f"Массовый режим работает ТОЛЬКО по префиксу "
            f"'{ALIQATEST_PREFIX}' — чужие вакансии не трогает."
        )
    )
    parser.add_argument(
        "--env",
        type=str,
        default="dev",
        choices=list(ENVIRONMENTS.keys()),
        help="Стенд (по умолчанию: dev)",
    )
    parser.add_argument(
        "--id",
        type=int,
        nargs="+",
        help="Точечное удаление по id. Можно несколько.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_aliqatest",
        help=(
            f"Удалить ВСЕ вакансии, имя которых начинается с "
            f"'{ALIQATEST_PREFIX}' (с учётом whitelist защитных подстрок)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать, что будет удалено, не удалять.",
    )

    args = parser.parse_args()

    if not args.id and not args.all_aliqatest:
        parser.print_help()
        print(
            "\nℹ️  Не указан ни --id, ни --all — нечего делать. "
            "Для массовой очистки запусти с --all."
        )
        return

    client = APIClient(env=args.env)
    print(f"🔗 Стенд: {args.env} → {client.base_url}")
    client.authenticate()
    print("✅ Авторизация успешна\n")

    if args.id:
        _delete_by_ids(client, args.id, args.dry_run)
        print()

    if args.all_aliqatest:
        _delete_all_aliqatest(client, args.dry_run)


if __name__ == "__main__":
    main()
