"""
Сессионный реестр ID созданных тестами вакансий.

Зачем нужен
-----------
На общем стенде (hr-dev.acm-ai.ru) параллельно работают настоящие
пользователи и могут оставаться вакансии после предыдущих прогонов
автотестов, упавших до teardown. Если чистить «всё подряд по префиксу»,
есть шанс зацепить чужое — именно так мы уже получили инцидент, когда
cleanup снёс вакансию, созданную вручную до прогона.

Решение: каждое место, где автотест создаёт вакансию, обязано
зарегистрировать её id через `register()`. При teardown-очистке мы
сравниваем список найденных по префиксу ALIQATEST id с содержимым
реестра и удаляем ТОЛЬКО пересечение — то есть действительно «свои»
вакансии этой pytest-сессии.

Модуль устроен как singleton на уровне процесса (обычный модульный
state). Это корректно для pytest: одна сессия == один процесс.
Для xdist (несколько воркеров) каждый воркер имеет свой реестр —
это желаемое поведение: каждый воркер убирает за собой.
"""

from __future__ import annotations

import threading
from typing import Iterable


_created_ids: set[int] = set()
_lock = threading.Lock()


def register(vacancy_id: int | None) -> None:
    """Регистрирует id созданной тестом вакансии. None и не-int
    игнорируются — удобно звать из мест, где id ещё может быть
    не готов (например, ранний best-effort-путь в POM)."""
    if vacancy_id is None:
        return
    try:
        vid = int(vacancy_id)
    except (TypeError, ValueError):
        return
    with _lock:
        _created_ids.add(vid)


def register_many(ids: Iterable[int]) -> None:
    for vid in ids:
        register(vid)


def is_registered(vacancy_id: int) -> bool:
    with _lock:
        return int(vacancy_id) in _created_ids


def all_ids() -> set[int]:
    """Возвращает копию всех зарегистрированных id."""
    with _lock:
        return set(_created_ids)


def unregister(vacancy_id: int) -> None:
    """Удаляет id из реестра. Вызывается cleanup-кодом после
    успешного удаления вакансии на сервере."""
    with _lock:
        _created_ids.discard(int(vacancy_id))


def clear() -> None:
    """Полная очистка реестра. Нужно только в тестах самого реестра."""
    with _lock:
        _created_ids.clear()
