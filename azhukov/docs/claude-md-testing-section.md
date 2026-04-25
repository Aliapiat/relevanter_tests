# Раздел «Тестирование» из CLAUDE.md

> Выписка из основного файла инструкций проекта `hr-recruiter/CLAUDE.md` — раздел про автотесты и агента-наблюдателя. Это краткая операционная памятка; полные правила Playwright — в `docs/testing-best-practices.mdc`, полный промпт Watchdog — в `prompts/watchdog-monitor-prompt.md`.

---

## Тестирование

### Playwright E2E тесты

Автотесты расположены в `autotests/`. Подробные правила: `.cursor/rules/rules/testing.mdc`.

```bash
# Из корня hr-recruiter:
make playwright         # UI режим (интерактивный)
make playwright-run     # Все тесты с видимым браузером

# Из autotests/:
cd autotests
npx playwright test              # Все тесты
npx playwright test --ui         # UI режим
npx playwright test TC-007       # Конкретный тест
npx playwright test --grep @smoke  # По тегу
```

**Архитектура:**
- **globalSetup** (`auth.setup.ts`) — логин один раз, сохранение `storageState` (не отображается в Playwright UI)
- **Все тесты** стартуют авторизованными через `storageState` (без повторного логина)
- **Изоляция** — каждый тест получает свой BrowserContext (стандарт Playwright)
- **Headed mode** — `headless` не задан в конфиге; для видимого браузера: `--headed`, для UI: `--ui` (встроенный просмотрщик)

**Ключевые принципы:**
- Локаторы: `getByRole()` > `getByText()` > `getByLabel()` > `getByTestId()` (НЕ CSS-классы)
- Assertions: `await expect(locator).toBeVisible()` (web-first, с авто-ожиданием)
- НЕ использовать: `waitForTimeout()`, `waitForLoadState('networkidle')`, `page.locator('.css-class')`

### Агент-наблюдатель (Watchdog) при автотестах

При запуске E2E тестов **ОБЯЗАТЕЛЬНО** параллельно запускать фонового агента-наблюдателя:

```
Agent(subagent_type="general-purpose", run_in_background=true, description="watchdog: мониторинг логов")
```

Агент мониторит Docker-логи всех сервисов (`relevanter-back`, `business-back`, `olivia-back`, `nginx`), выявляет ошибки (500, 422, 504, таймауты, отсутствующие таблицы) и создаёт TODO-задачи:
- **[CRITICAL]** — блокирует тест, фиксить немедленно
- **[FIX]** — надо пофиксить после прохождения теста
- **[TEST]** — написать юнит-тест для обнаруженной проблемы
- **[CONFIG]** — настройка инфраструктуры

Подробный промпт для агента: см. `prompts/watchdog-monitor-prompt.md`.
