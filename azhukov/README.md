# azhukov / Playwright E2E автотесты — материалы на ревью

Это материалы работы azhukov над автотестированием в проекте `hr-recruiter`. Включают сами тесты, документацию, тест-кейсы, инфраструктуру и примеры результатов прогонов.

## Структура

```
azhukov/
├── README.md                     ← этот файл
│
├── group-003-auth/               ← E2E тесты, сгруппированные по областям UI
├── group-004-vacancy-create/
├── group-005-navigation/
├── group-006-estaff-search/
├── group-006-hh-export/
├── group-007-search/
│
├── docs/                         ← документация / правила тестирования
│   ├── testing-best-practices.mdc       — главный документ (734 строки):
│   │                                       структура, локаторы, assertions,
│   │                                       авторизация, антипаттерны, диагностика
│   ├── claude-md-testing-section.md     — выписка из CLAUDE.md (операционная памятка)
│   └── makefile-targets.md              — все Makefile-цели для Playwright
│
├── prompts/                      ← промпты для AI-агентов
│   ├── dataflow-research-template.md    — шаблон агента-исследователя для подготовки задач
│   └── watchdog-monitor-prompt.md       — промпт фонового агента, мониторящего логи Docker во время автотестов
│
├── test-cases/                   ← тест-кейсы и контекст задач
│   ├── 003-autotests-playwright/        — главная задача про автотесты:
│   │   ├── requirements.md                  ТЗ, FR-1..FR-6, архитектура
│   │   ├── test-cases.md                    TC-001..TC-006 базовые сценарии
│   │   ├── current-stage.md                 текущее состояние задачи
│   │   └── changelog.md                     история ревизий
│   ├── related-tasks/                   — test-cases.md остальных задач sprint4,
│   │                                       чьё поведение покрыто перенесёнными тестами
│   │   ├── 001-hh-export-validation.md
│   │   ├── 002-integrations-foundation.md
│   │   ├── 004-hh-contact-estaff-sync.md
│   │   ├── 005-unified-vacancy-validation-hh.md
│   │   ├── 006-metro-filter-not-saved-in-search.md
│   │   ├── 007-scoring-relevance-broken.md
│   │   ├── 008-estaff-scoring-quality.md
│   │   ├── 009-import-remote-city-clear.md
│   │   ├── 010-mailing-keep-no-phone.md
│   │   └── 011-estaff-candidate-sync.md
│   ├── sprint4-overview.md              — общий обзор sprint 4
│   ├── sprint4-tasks-list.md            — реестр задач sprint 4
│   └── hh-vacancy-validation.csv        — матрица валидации полей вакансии для HH.ru
│
├── infra/                        ← конфигурация и скрипты автотестов
│   ├── package.json                     — зависимости (@playwright/test, ffmpeg-static), npm-скрипты
│   ├── playwright.config.ts             — конфигурация: globalSetup, baseURL, trace, screenshot, video
│   ├── auth.setup.ts                    — globalSetup: логин и сохранение storageState
│   ├── auth-fixture.ts                  — фикстура с TEST_USER и login()
│   └── run-with-video.js                — Node.js-скрипт для запуска тестов с записью и склейкой видео
│
└── results/                      ← примеры артефактов прогонов (без бинарных файлов)
    ├── TC-009-album.md                  — альбом результатов TC-009 (E-Staff поиск): 15 сценариев
    └── logs/                            — текстовые логи прогонов
        ├── test-output.log
        ├── test-video-run.log
        ├── test-video-run2.log
        └── test-video-run3.log
```

## Тесты в проекте (всего 14 spec-файлов)

| Группа | Тест | Что проверяет |
|--------|------|---------------|
| group-003-auth | TC-006 | Авторизация |
| group-004-vacancy-create | TC-007 | Создание вакансии (полный флоу) |
| | TC-011 | Импорт из удалённого города |
| | TC-012 | API-валидация вакансии |
| | TC-013 | Очистка списка городов |
| | TC-014 | Очистка специализации (быстрый и медленный варианты) |
| group-005-navigation | TC-008 | Навигация по разделам |
| group-006-estaff-search | TC-009 | Поиск кандидатов через E-Staff (фильтры, пол, возраст, зарплата, должность, компании-доноры) |
| group-006-hh-export | TC-009 | Экспорт вакансии на HH.ru (диалоги модалок специализации/городов) |
| | TC-010 | Сохранение без специализации |
| | TC-011 | Валидация при экспорте |
| | TC-652 | Порядок валидации при публикации на HH |
| group-007-search | TC-645 | Независимость пагинации релевантности |

⚠️ **Тесты HH-экспорта** — в диалоге подтверждения отправки на HH.ru **всегда нажимается «Нет»**, никаких реальных публикаций (расход кредитов работодателя).

## Архитектурные особенности

- **Авторизация через storageState** — логин один раз в globalSetup, дальше все тесты стартуют уже авторизованными.
- **Изоляция через BrowserContext** — стандартный механизм Playwright.
- **Headed mode по умолчанию** — `headless` не задан в конфиге, чтобы корректно работал UI-режим.
- **Запуск из Docker MCP Playwright** — через адрес `host.docker.internal` вместо `localhost`.
- **Watchdog-агент** при запуске — фоновый AI-агент мониторит Docker-логи и заводит TODO для критических ошибок (см. `prompts/watchdog-monitor-prompt.md`).

## Что НЕ перенесено (намеренно)

- **Бинарные артефакты результатов**: PNG-скриншоты (~3.3 МБ, 30 файлов), `TC-009-merged.webm` (47 МБ), HTML-отчёт Playwright (генерируется автоматически).
- **`node_modules/`, `package-lock.json`, `test-results/`** — стандартное игнорирование в git.
- **Файлы внутри git-репозиториев основного проекта** (`business-back/`, `recruiter-front/` и т. п.) — это код задач, не относится к автотестам.
