# Relevanter Autotests

E2E автотесты для фронтенда [HR Recruiter / Relevanter](https://hr-dev.acm-ai.ru/) — платформы рекрутинга с AI-скринингом и HR-интервью (React 18 + TypeScript + Tailwind). Написаны на **Playwright + Python + pytest**, отчёты — **Allure**.

## О проекте

Relevanter — SPA-CRM для рекрутёров: создание вакансий, работа с кандидатами, интеграция с hh.ru, AI-скрининг, автособеседование. В автотестах покрываем:

- **Авторизация**: UI, HTML5-валидация, позитив / невалидные креды, «запомнить меня».
- **Создание вакансии**: минимальные/полные поля, валидации (длина, диапазон зарплат, обязательные поля).
- **Модалки**: отрасль, специализация, география, город (fast-path через `page.evaluate` + fallback).
- **Табы на странице вакансии**: Настройка / Диалог / Интервью / Поиск / Результаты.
- **Ссылки и интеграции**: переход на hh.ru, AI-скрининг, публичная форма записи на HR-интервью.
- **Проверка через поиск**: все введённые при создании поля должны корректно улетать в URL-фильтры на вкладке «Поиск».

## Стенды

| Env   | URL                                  | Запуск в CI          |
| ----- | ------------------------------------ | -------------------- |
| dev   | https://hr-dev.acm-ai.ru/            | на каждый push       |
| qa    | https://hr-qa.acm-ai.ru/             | только вручную       |
| stage | https://hr.acm-ai.ru/                | только вручную       |
| prod  | https://app.relevanter.ru/           | только вручную       |

> URL-ы берутся из [`config/environments.py`](config/environments.py). Если список меняется — правим там, CI подхватывает через `--env <name>`. Исторические имена `staging` и `preprod` оставлены как алиасы к `stage` и `qa` соответственно — существующие скрипты и `.env` работают без правок.

## Локальный запуск

```bash
# 1. Создать venv и поставить зависимости
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install --with-deps chromium

# 2. Заполнить .env (скопировать из .env.example, реальный .env gitignored)
#    ADMIN_EMAIL=...       # ТОЛЬКО для тестов логина (test_login.py)
#    ADMIN_PASSWORD=...
#    RECRUITER_EMAIL=...   # основной юзер для всего остального
#    RECRUITER_PASSWORD=...
#    HEADLESS=false
# В коде дефолтов нет: если переменная не задана, тесты, которым она
# нужна, упадут с понятной ошибкой на стадии логина.

# 3. Запуск
pytest --env dev                                   # все тесты на dev
pytest --env dev -m smoke_critical -x              # быстрый блокирующий слой (~20 сек)
pytest --env dev -m "smoke and not smoke_critical" # обычный smoke (~5 мин)
pytest -m vacancy                                  # только тесты вакансий
pytest -k test_create_minimal_vacancy              # по имени
pytest -n 4                                        # параллельно (xdist)
```

Windows PowerShell под капотом любит cp1252, и allure/пайтон печатает эмоджи. Если видите `UnicodeEncodeError`:

```powershell
$env:PYTHONIOENCODING="utf-8"
```

## Маркеры

```text
smoke_critical  - 5 тестов-блокеров. CI прогоняет их ПЕРВЫМИ с `-x` (fail-fast).
                  Если что-то из них упало — смысла идти дальше нет: логин
                  сломан или вакансия не создаётся.
smoke           - расширенный smoke, ~10 функциональных тестов.
                  Запускается только если smoke_critical зелёный.
vacancy         - всё про создание и отображение вакансии
modals          - отрасль / специализация / география / город
validation      - длины полей, зарплата, обязательные поля
login           - авторизация
integration     - тесты с внешними интеграциями (hh.ru)
regression      - regression-маркер (явно помеченные регрессии)
critical        - критический инвариант продукта
```

## Cleanup тестовых вакансий

На общем стенде живёт множество «чужих» вакансий — ронять чужие данные нельзя. Две страховки работают одновременно:

1. **Единый префикс `ALIQATEST`** в начале title любой вакансии, которую создают тесты.
2. **`session_registry`** (`utils/session_registry.py`) — singleton, в который автоматически попадают id всех вакансий, созданных в рамках текущей pytest-сессии. Наполнение идёт неблокирующим network-listener'ом на `POST /api/v1/positions` (см. `tests/conftest.py → _register_vacancy_from_response`).

Cleanup удаляет **только пересечение**: «имеет префикс `ALIQATEST`» ∩ «зарегистрировано в этой сессии». Всё, что имеет префикс `ALIQATEST`, но не попало в реестр (например — остатки упавшего прошлого прогона или параллельная сессия), в логах помечается как `foreign_ids` и **не удаляется**.

Ручной cleanup, если нужно разобрать хвосты:

```bash
python scripts/cleanup_vacancies.py --all           # все ALIQATEST вакансии на стенде
python scripts/cleanup_vacancies.py --id 1234 5678  # точечно по id
```

## CI на GitLab

Файл: `.gitlab-ci.yml`. Запускается на `push`, `merge_request_event` и ручной запуск через UI (`Build → Pipelines → Run pipeline`).

Управление прогоном — через переменные пайплайна (`Run pipeline → variables`):

| Переменная | Значения | Что делает |
|---|---|---|
| `TEST_ENV` | `dev` / `qa` / `stage` / `prod` | Стенд, против которого гонять. По умолчанию `dev`. Алиасы `staging` и `preprod` тоже работают. |
| `SCOPE` | `smoke` (default) / `affected` / `all` / `vacancy` / `modals` / `login` / `validation` | Набор тестов. Маркеры `vacancy`/`modals`/`login`/`validation` — точечно для отладки CI. |

Этапы пайплайна совпадают с GitHub Actions (смотрите таблицу ниже): `smoke_critical -x` (fail-fast) → `smoke` → `affected` / `full_regression` / `single_marker` → `generate_report` (Allure) → `pages` (публикация отчёта).

### Секреты в GitLab

`Project → Settings → CI/CD → Variables`. Завести **четыре** masked + protected переменные:

| Переменная | Значение |
|---|---|
| `ADMIN_EMAIL` | логин админа (только для `tests/test_login.py`) |
| `ADMIN_PASSWORD` | пароль админа |
| `RECRUITER_EMAIL` | логин рекрутёра `forauto@test.py` |
| `RECRUITER_PASSWORD` | пароль рекрутёра |

### Allure-отчёт на GitLab Pages

Публикуется только для `main`. URL после первого успешного пайплайна: `Settings → Pages`. История трендов между прогонами сохраняется в кэше per-branch (`allure-history-<ref-slug>`), так что график на главной странице отчёта будет копиться.

## CI (GitHub Actions)

Workflow `.github/workflows/tests.yml` — трёхступенчатый:

| scope (trigger)              | Step 1                | Step 2                         | Step 3                                  |
| ---------------------------- | --------------------- | ------------------------------ | --------------------------------------- |
| `smoke` (push в main)        | `smoke_critical -x`   | `smoke and not smoke_critical` | —                                       |
| `affected` (workflow_dispatch) | `smoke_critical -x` | `smoke`                        | тесты из git diff (affected_tests.py)   |
| `all` (workflow_dispatch)    | `smoke_critical -x`   | `smoke`                        | `not smoke and not smoke_critical`      |
| `vacancy` / `modals` / …     | —                     | —                              | только выбранный marker (точечная отладка) |

Поведение:

- **Step 1 падает** → `-x` останавливает шаг, Step 2 и Step 3 не запускаются. Это и есть «если критичный падает — дальнейший прогон бессмысленен».
- **Step 2 / Step 3 падают** → `continue-on-error: true`, чтобы Allure собрал полную картину.
- **`affected`** считает `git diff --name-only <base>...HEAD` и прогоняет через `scripts/affected_tests.py` — там два уровня резолва: поиск `from pages.xxx` в тестах + name-based fallback для POM, которые тесты используют только через фикстуры (например, `pages/login_page.py` → `test_login.py`).
- **Infra-файлы** (`conftest.py`, `pytest.ini`, `.github/`, `utils/api_client.py`, `config/`) автоматически форсируют полный прогон.

### Ссылки на отчёты

| Стенд     | URL |
| --------- | --- |
| 🏠 Индекс | https://aliapiat.github.io/relevanter-autotests/ |
| 🟢 DEV    | https://aliapiat.github.io/relevanter-autotests/dev/ |
| 🟡 STAGING | https://aliapiat.github.io/relevanter-autotests/staging/ |
| 🟣 PREPROD | https://aliapiat.github.io/relevanter-autotests/preprod/ |
| 🔴 PROD   | https://aliapiat.github.io/relevanter-autotests/prod/ |

> В **Settings → Pages** источник должен быть `Deploy from a branch` → ветка `gh-pages` → папка `/ (root)`.

### Secrets, которые нужно завести в репозитории

CI читает переменные окружения в `.github/workflows/tests.yml` (блок `env:` у job'ы `test`). Все значения хранятся в GitHub Secrets — прямо в коде их нет.

Нужно завести **четыре** секрета:

| Имя секрета          | Кого использует                                                                                           | Где задаётся в workflow              |
| -------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `ADMIN_EMAIL`        | только `tests/test_login.py` (позитив/негатив входа, регистр, пробелы, XSS). Админ остаётся в `smoke_critical`. | `env: ADMIN_EMAIL: ${{ secrets.ADMIN_EMAIL }}`       |
| `ADMIN_PASSWORD`     | см. выше                                                                                                   | `env: ADMIN_PASSWORD: ${{ secrets.ADMIN_PASSWORD }}` |
| `RECRUITER_EMAIL`    | всё остальное — `authenticated_page`, создание вакансий, модалки, табы, фильтры, API cleanup (`utils/api_client.py`). На всех стендах есть общий аккаунт `forauto@test.py`, у которого логин и пароль совпадают. | `env: RECRUITER_EMAIL: ${{ secrets.RECRUITER_EMAIL }}` |
| `RECRUITER_PASSWORD` | см. выше                                                                                                   | `env: RECRUITER_PASSWORD: ${{ secrets.RECRUITER_PASSWORD }}` |

#### Как завести в GitHub (раз и навсегда)

1. Открываете свой репозиторий на GitHub.
2. **Settings** (шестерёнка в правом верхнем углу страницы репозитория).
3. Слева в меню — **Secrets and variables** → **Actions**.
4. Кнопка **New repository secret** в правом верхнем углу.
5. Для каждого секрета из таблицы выше:
   - **Name** — ровно как в первой колонке (`ADMIN_EMAIL`, потом `ADMIN_PASSWORD`, потом `RECRUITER_EMAIL`, потом `RECRUITER_PASSWORD`). Регистр важен, лишние пробелы — нет.
   - **Secret** — значение (email в одном секрете, пароль в другом).
   - Жмёте **Add secret** и повторяете для следующего.
6. После того как все четыре добавлены, в списке должно быть видно:
   ```
   ADMIN_EMAIL          · Updated just now
   ADMIN_PASSWORD       · Updated just now
   RECRUITER_EMAIL      · Updated just now
   RECRUITER_PASSWORD   · Updated just now
   ```
   Сами значения GitHub больше не покажет — они доступны только workflow'ам.

#### Как проверить, что сработало

- Зайдите в **Actions** → выберите последний прогон `🧪 Tests` → джоб `🎭 Tests on dev`.
- В шаге `🔥 Smoke critical (fail-fast)` не должно быть строк вроде `401 Unauthorized` или `ADMIN_EMAIL is empty`.
- Если `ADMIN_*` не заведены — упадут `test_login.py::*` (на логине).
- Если `RECRUITER_*` не заведены — упадёт уже `test_create_minimal_vacancy` и дальше, т.к. `authenticated_page` не сможет залогиниться.

#### Если на стенде другой рекрутёр

Заводите отдельный набор секретов на стенд (например, `RECRUITER_EMAIL_PROD` / `RECRUITER_PASSWORD_PROD`) и в `env:` workflow'а выбирайте нужный по `matrix.env`. По умолчанию — один и тот же рекрутёр на всех стендах (так и устроен `forauto@test.py`).

### Зачем два аккаунта

- **Админ видит вакансии всех пользователей стенда.** Если тесты будут бегать под админом, API `/positions` и UI-список покажут чужие `ALIQATEST`-вакансии из параллельных прогонов. Несмотря на страховки (`session_registry` + whitelist), риск задеть чужое выше всего именно у админа.
- **Рекрутёр видит только свои вакансии.** Его пул изолирован от всех остальных. Это третья линия защиты поверх префикса `ALIQATEST` и `session_registry`.
- **Тесты логина остаются на админе** — это специально: в `smoke_critical` мы не просто «какой-то логин», а проверяем, что боевой админский аккаунт жив. Если упал — стенд, скорее всего, лежит.

## Allure локально

```bash
pytest --env dev --alluredir=allure-results
allure generate allure-results --clean -o allure-report
allure open allure-report
```

### Что есть в отчёте помимо тестов

- **Environment** (блок слева на главной) — стенд, BASE_URL, ветка/git-sha, OS, Python, браузер, учётная запись рекрутёра. Пишется один раз на сессию в `allure-results/environment.properties` (см. `utils/allure_hooks.py`).
- **Executor** — в CI ссылка на конкретный GitHub Actions run (`allure-results/executor.json`). Локально показывает `local-<sha>`.
- **Categories** — вкладка автоматической классификации падений: `Product defects (AssertionError)`, `Playwright timeouts (flaky/infra)`, `Selector issues`, `Network/HTTP`, `Fixtures setup`. Сразу видно, 15 падений — это реальные баги или тайм-ауты сети.
- **Severity** — проставляется автоматически по pytest-маркеру: `smoke_critical` → `blocker`, `smoke` → `critical`, `validation`/`modals`/`navigation` → `normal`, всё остальное (UI-видимость, плейсхолдеры) → `minor`. Явный `@allure.severity(...)` на тесте/классе всегда побеждает. Логика живёт в autouse-фикстуре `_default_allure_severity` в `tests/conftest.py`.
- **Параметр `vacancy_id`** — в каждом тесте, который создаёт вакансию, в отчёте появится параметр `vacancy_id=<id>` (видно во вкладке «Parameters» у теста). По нему можно открыть саму вакансию на стенде и разобрать падение без reproducing'а. Прикрепляется в трёх местах: network-listener на `POST /api/v1/positions`, `VacancyCreatePage.get_vacancy_id_from_url()` и при ручном `cleanup_test_vacancies.append(vid)`.

### Как размечаются тесты

Используются все четыре уровня Allure:

| Уровень | Назначение | Пример |
|---|---|---|
| `@allure.epic` | Крупная бизнес-область | `"Авторизация"`, `"Вакансии"` |
| `@allure.feature` | Фича внутри epic | `"Позитивные сценарии — создание вакансии"` |
| `@allure.story` | Под-сценарий внутри feature (где это уместно) | `"Ввод и сохранение значений в полях формы"` |
| `@allure.title` | Человекочитаемое название теста | `"Создание вакансии с минимально-допустимыми полями"` |

Если в тесте задействован `vacancy_id` / параметризация, используйте `allure.dynamic.title(...)` / `allure.dynamic.parameter(...)` — в отчёте появятся актуальные значения, а не шаблон.

## Структура

```text
relevanter-autotests/
├── config/                 # environments.py, settings.py (URL стендов)
├── pages/                  # POM: base_page, login_page, sidebar_page,
│                           #      vacancy_create_page, vacancy_detail_page,
│                           #      search_page, <tab>_tab.py, public_vacancy_page
├── tests/                  # test_*.py + conftest.py (фикстуры страниц + network listener)
├── utils/                  # api_client.py, session_registry.py, helpers
├── scripts/                # cleanup_vacancies.py, affected_tests.py
├── .github/workflows/      # tests.yml
├── conftest.py             # pytest_addoption --env
├── pytest.ini              # marker'ы
├── requirements.txt
├── run_tests.bat           # Windows-обёртка
├── .env / .env.example     # (.env gitignored)
└── .gitignore
```

## Что уже покрыто

| Файл                                     | Сценарии                                                         |
| ---------------------------------------- | ---------------------------------------------------------------- |
| `test_login.py`                          | UI, позитив, неверный пароль / несуществующий юзер, пробелы, XSS |
| `test_vacancy_create.py`                 | Минимальный набор полей, ошибки валидации зарплат, обязательные  |
| `test_vacancy_validation.py`             | Длины полей, суммарные лимиты, min-chars warning                 |
| `test_vacancy_modals.py`                 | Отрасль / специализация / география / город — выбор, сброс      |
| `test_vacancy_display.py`                | Что выбрано в модалках — корректно показывается на детальной    |
| `test_vacancy_create_via_search_filter.py` | Поля вакансии → URL фильтров на вкладке «Поиск»                 |
| `test_vacancy_tabs.py`                   | Все 5 табов на странице вакансии переключаются                   |
| `test_vacancy_links.py`                  | hh.ru, AI-скрининг, публичная форма HR-интервью (пустые поля)    |

## Конвенции

- **Локаторы**: `get_by_role` / `get_by_placeholder` / `get_by_text` и устойчивые CSS; классовые селекторы — только как вынужденный fallback.
- **Ожидания**: `expect(...)` / `locator.wait_for(state=...)` — никаких `sleep`-ов.
- **Названия вакансий в тестах**: всегда начинаются с `ALIQATEST` (жёсткий контракт cleanup'а).
- **Скриншот при падении** — автоматически, через `pytest_runtest_makereport` (`tests/conftest.py`).
- **Лейбл стенда** в Allure выставляется в CI через post-processing `allure-results/*-result.json`.
- **Best-effort ≠ блокирующее ожидание**: если побочный эффект важен только «если доедет» (например, регистрация id созданной вакансии), реализуется как неблокирующий `page.on("response", …)`, а не `wait_for_url` — иначе любые негативные/медленные сценарии получают вдогонку десятки секунд простоя.
