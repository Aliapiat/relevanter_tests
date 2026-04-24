import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BASE_URL: str = ""
    CURRENT_ENV: str = ""

    # Админский аккаунт. Используется ТОЛЬКО в тестах логина
    # (tests/test_login.py) — там проверяем позитив/негатив входа и
    # все кейсы вокруг авторизации. В остальных тестах админом НЕ
    # логинимся, чтобы не видеть чужие вакансии в списке и не
    # зацепить их cleanup-ом.
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")

    # Обычный аккаунт рекрутёра — основной юзер для UI и API-тестов.
    # Есть на всех стендах (dev/qa/stage/prod). Значения
    # нигде в коде не хардкодим: локально — из .env, в CI —
    # из secrets.RECRUITER_EMAIL / secrets.RECRUITER_PASSWORD.
    # См. README → «Secrets, которые нужно завести в репозитории».
    RECRUITER_EMAIL: str = os.getenv("RECRUITER_EMAIL", "")
    RECRUITER_PASSWORD: str = os.getenv("RECRUITER_PASSWORD", "")

    DEFAULT_TIMEOUT: int = int(os.getenv("DEFAULT_TIMEOUT", "30000"))
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
    SLOW_MO: int = int(os.getenv("SLOW_MO", "0"))
    BROWSER: str = os.getenv("BROWSER", "chromium")

settings = Settings()
