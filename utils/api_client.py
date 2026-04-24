import requests
import os
from config.settings import settings
from config.environments import ENVIRONMENTS


class APIClient:
    """HTTP-клиент для работы с API"""

    def __init__(self, env: str = None):
        # 1. Берём из settings если уже установлен (запуск через pytest)
        # 2. Иначе берём из параметра env
        # 3. Иначе из переменной окружения ENV
        # 4. Fallback на "dev"
        base = settings.BASE_URL

        if not base:
            env_name = env or os.getenv("ENV", "dev")
            base = ENVIRONMENTS.get(env_name)
            if not base:
                raise ValueError(
                    f"Неизвестный стенд: '{env_name}'. "
                    f"Доступные: {list(ENVIRONMENTS.keys())}"
                )

        self.base_url = base.rstrip("/") + "/api/v1"
        self.token: str | None = None

    def authenticate(
            self,
            email: str = None,
            password: str = None,
    ) -> str:
        # По дефолту логинимся РЕКРУТЁРОМ, не админом — см. подробное
        # обоснование в tests/conftest.py::authenticated_page. Кратко:
        # API-клиент зовёт `/positions` и `delete_vacancy` в cleanup.
        # Если токен админский, в выборке будут вакансии всех
        # пользователей стенда (включая чужие ALIQATEST из параллельных
        # прогонов). Под рекрутёром список изолирован — это дополнительная
        # страховка поверх session_registry и префикса ALIQATEST.
        # Если явно нужен админ (например, для проверки прав) — передаём
        # email/password аргументами.
        email = email or settings.RECRUITER_EMAIL
        password = password or settings.RECRUITER_PASSWORD

        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()
        self.token = data["token"]
        return self.token

    def _headers(self) -> dict:
        """Формирует заголовки с авторизацией"""
        if not self.token:
            raise RuntimeError(
                "Токен не установлен. Вызовите authenticate() первым."
            )
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # ══════════════════════════════════════
    # ВАКАНСИИ (POSITIONS)
    # ══════════════════════════════════════

    def get_vacancy(self, vacancy_id: int) -> dict:
        """Возвращает полный объект вакансии по ID.

        Используется тестами, которым нужны поля, не попадающие в список
        (например, publicSlug, hhMainVacancy, aiScreeningEnabled).
        """
        response = requests.get(
            f"{self.base_url}/positions/{vacancy_id}",
            headers=self._headers(),
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def find_vacancy_with_hh_integration(self) -> dict | None:
        """Ищет на стенде вакансию, связанную с вакансией на hh.ru.

        Связь определяется по полям, которые читает фронт
        (recruiter-front/src/pages/VacancyViewPage.tsx:256-297):
          • hhVacancyId          — id основной вакансии hh.ru
          • hhAdditionalVacancyIds — список id дополнительных

        В списке /positions эти поля могут быть урезаны, поэтому при
        необходимости доrequest'им полный объект через /positions/{id}.
        Возвращает первую подошедшую вакансию или None, если таких нет.
        """
        def _has_hh(obj: dict) -> bool:
            if not isinstance(obj, dict):
                return False
            if obj.get("hhVacancyId"):
                return True
            add = obj.get("hhAdditionalVacancyIds") or []
            return bool(add)

        for v in self.get_vacancies():
            if _has_hh(v):
                return v
            vid = v.get("id") if isinstance(v, dict) else None
            if not vid:
                continue
            try:
                full = self.get_vacancy(vid)
            except Exception:
                continue
            if _has_hh(full):
                return full
        return None

    def delete_vacancy(self, vacancy_id: int) -> int:
        """
        Удаляет вакансию по ID.
        Возвращает HTTP status code (204 = успех).
        Выбрасывает HTTPError при статусе 4xx/5xx.
        """
        response = requests.delete(
            f"{self.base_url}/positions/{vacancy_id}",
            headers=self._headers(),
            timeout=15,
        )
        response.raise_for_status()
        return response.status_code

    def get_vacancies(self) -> list[dict]:
        """
        Получает список всех вакансий с поддержкой Spring Boot пагинации.
        Формат ответа: {"content": [...], "totalPages": N, ...}
        """
        all_vacancies: list[dict] = []
        page = 0

        while True:
            response = requests.get(
                f"{self.base_url}/positions",
                headers=self._headers(),
                params={"page": page, "size": 100},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data

            if isinstance(data, dict) and "content" in data:
                all_vacancies.extend(data["content"])
                total_pages = data.get("totalPages", 1)
                if page + 1 >= total_pages:
                    break
                page += 1
            else:
                print(f"[api] get_vacancies: неожиданный формат: "
                      f"{list(data.keys()) if isinstance(data, dict) else type(data)}")
                break

        return all_vacancies

    def find_vacancies_by_prefix(
        self, prefix: str
    ) -> list[dict]:
        """
        Находит вакансии, название которых начинается с prefix.
        Удобно для поиска тестовых вакансий (префикс ALIQATEST).
        """
        all_vacancies = self.get_vacancies()
        return [
            v for v in all_vacancies
            if v.get("title", "").startswith(prefix)
        ]

    def delete_vacancies_by_prefix(
        self, prefix: str
    ) -> dict:
        """
        Удаляет все вакансии с указанным префиксом.
        Возвращает статистику: {deleted: [...], failed: [...]}.
        """
        vacancies = self.find_vacancies_by_prefix(prefix)
        result = {"deleted": [], "failed": []}

        for v in vacancies:
            vacancy_id = v.get("id")
            title = v.get("title", "")
            status = self.delete_vacancy(vacancy_id)

            if status == 204:
                result["deleted"].append(
                    {"id": vacancy_id, "title": title}
                )
            else:
                result["failed"].append(
                    {
                        "id": vacancy_id,
                        "title": title,
                        "status": status,
                    }
                )

        return result
