# Makefile цели для Playwright

> Выписка из корневого `hr-recruiter/Makefile` — все цели, относящиеся к автотестам.

```makefile
playwright: ## Открыть Playwright UI для запуска тестов
	@echo "$(GREEN)Запуск Playwright UI...$(NC)"
	cd autotests && npx playwright test --ui

playwright-run: ## Запустить все Playwright тесты (headed)
	@echo "$(GREEN)Запуск всех Playwright тестов...$(NC)"
	cd autotests && npx playwright test --headed

playwright-headed: ## Запустить Playwright тесты с видимым браузером (алиас)
	@$(MAKE) playwright-run

playwright-video: ## Открыть Playwright UI с записью видео (замедленно)
	@echo "$(GREEN)Запуск Playwright UI с видеозаписью (SLOW_MO=1000ms)...$(NC)"
	cd autotests && VIDEO=on SLOW_MO=1000 npx playwright test --ui

playwright-report: ## Открыть HTML-отчёт последнего запуска тестов
	@echo "$(GREEN)Открытие HTML-отчёта...$(NC)"
	cd autotests && npx playwright show-report results/report
```

## Команды (краткая справка)

| Команда | Что делает |
|---------|-----------|
| `make playwright` | Открыть Playwright UI (интерактивный выбор тестов и трейсов) |
| `make playwright-run` | Прогнать все тесты с видимым браузером (`--headed`) |
| `make playwright-headed` | Алиас для `playwright-run` |
| `make playwright-video` | UI-режим с записью видео и `SLOW_MO=1000ms` |
| `make playwright-report` | Открыть HTML-отчёт последнего прогона из `autotests/results/report` |

## Запуск из autotests/ напрямую

```bash
cd autotests
npx playwright test                   # все тесты, headless по умолчанию
npx playwright test --ui              # UI-режим
npx playwright test --headed          # с видимым браузером
npx playwright test TC-007            # один тест по имени файла
npx playwright test --grep @smoke     # по тегу
npx playwright show-report results/report  # отчёт
```

## Запуск с видео-склейкой (нестандартный путь)

См. `infra/run-with-video.js` — Node.js-скрипт для запуска тестов с записью видео и склейкой через ffmpeg-static. Группирует видео по ключевым словам в имени теста.
