ENVIRONMENTS = {
    "dev":   "https://hr-dev.acm-ai.ru/",
    "qa":    "https://hr-qa.acm-ai.ru/",
    "stage": "https://hr.acm-ai.ru/",
    "prod":  "https://app.relevanter.ru/",

    # ─── Алиасы для обратной совместимости ─────────────────────────────
    # Старые имена до переименования (staging → stage, preprod → qa).
    # Оставлены чтобы не ломать существующие скрипты, .env, pipeline'ы
    # и CI-настройки, где могут фигурировать прежние ключи.
    "staging": "https://hr.acm-ai.ru/",
    "preprod": "https://hr-qa.acm-ai.ru/",
}
