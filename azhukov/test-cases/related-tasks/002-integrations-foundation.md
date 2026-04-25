# Тест-кейсы: Фундамент интеграций — источники кандидатов для рассылок

---

## ПОЗИТИВНЫЕ СЦЕНАРИИ

### Фаза 1: source tracking (olivia-back)

#### TC-001: Создание кампании с HH кандидатами — source сохраняется
**Предусловия**: Рекрутер выбрал кандидатов из HH поиска
**Шаги**:
1. POST `/olivia/campaigns` с candidates: [{source: 'hh', externalId: '123', hhResumeId: '123', name: 'Иванов'}]
2. CampaignService создаёт CampaignCandidate

**Ожидаемый результат**:
- CampaignCandidate.source = 'HH'
- CampaignCandidate.sourceExternalId = '123'
- CampaignCandidate.hhResumeId = '123'

#### TC-002: Создание кампании с eStaff кандидатами — source сохраняется
**Предусловия**: Рекрутер выбрал кандидатов из eStaff поиска
**Шаги**:
1. POST `/olivia/campaigns` с candidates: [{source: 'estaff', externalId: '456', telegram: '@user', name: 'Петров'}]

**Ожидаемый результат**:
- CampaignCandidate.source = 'ESTAFF'
- CampaignCandidate.sourceExternalId = '456'
- CampaignCandidate.hhResumeId = null

#### TC-003: CampaignWorker — HH кандидат → HH переговоры
**Предусловия**: Активная кампания с HH кандидатом (status=PENDING), hhResumeId заполнен
**Шаги**:
1. CampaignWorker обрабатывает кандидата
2. ContactStrategyResolver определяет канал по source='HH'

**Ожидаемый результат**:
- Первый контакт через HH negotiations (sendInvitation через HhNegotiationClient)
- HTTP запрос к relevanter-back → api.hh.ru
- Conversation.successfulMessengerType = 'HH'

#### TC-004: CampaignWorker — eStaff кандидат → Telegram
**Предусловия**: Активная кампания с eStaff кандидатом (telegram заполнен)
**Шаги**:
1. CampaignWorker обрабатывает кандидата
2. ContactStrategyResolver: source='ESTAFF', есть telegram → TELEGRAM

**Ожидаемый результат**:
- Сообщение через Kafka topic messaging.outbound
- messengerType = 'TELEGRAM'
- Conversation.successfulMessengerType = 'TELEGRAM'

#### TC-005: CampaignWorker — eStaff кандидат без Telegram → WhatsApp
**Предусловия**: eStaff кандидат, telegram=null, whatsapp='+79991234567'
**Шаги**:
1. ContactStrategyResolver: source='ESTAFF', telegram=null, whatsapp есть → WHATSAPP

**Ожидаемый результат**:
- Сообщение через Kafka с messengerType = 'WHATSAPP'
- Используется шаблон sendFirstWhatsAppMessage() с templateKey='recruiter_offer'

#### TC-006: ContactStrategyResolver — приоритет messengerPriority
**Предусловия**: Кандидат с telegram И whatsapp, кампания с messengerPriority=['WHATSAPP','TELEGRAM']
**Шаги**:
1. ContactStrategyResolver проверяет порядок приоритета

**Ожидаемый результат**:
- Выбран WHATSAPP (выше в приоритете кампании), а не TELEGRAM

#### TC-007: Миграция данных — существующие записи
**Предусловия**: В БД есть CampaignCandidate без поля source, но с hh_resume_id
**Шаги**:
1. Применить миграцию add-source-to-campaign-candidates.sql

**Ожидаемый результат**:
- Записи с hh_resume_id → source='HH', source_external_id = hh_resume_id
- Записи без hh_resume_id → source='MANUAL' (default)
- Нет потери данных
- CampaignWorker продолжает работать без изменений

#### TC-008: Статистика кампании по источникам
**Предусловия**: Кампания с кандидатами из разных источников
**Шаги**:
1. GET `/olivia/campaigns/{id}/stats`

**Ожидаемый результат**:
- Статистика включает breakdown по source: { HH: 15, ESTAFF: 8, MANUAL: 3 }

### Фаза 2: eStaff per-user токены

#### TC-010: Привязка eStaff токена к пользователю
**Предусловия**: Пользователь авторизован в системе
**Шаги**:
1. Открыть настройки интеграций
2. Ввести eStaff API токен в EstaffKeySetupModal
3. POST `/api/tokens` с { type: 'ESTAFF', token: 'xxx' }

**Ожидаемый результат**:
- ExternalToken создан: userId + type='ESTAFF' + token
- Статус подключения: "Подключено"

#### TC-011: Поиск eStaff с per-user токеном
**Предусловия**: У пользователя сохранён eStaff токен в ExternalToken
**Шаги**:
1. Поиск через GET /api/applicants/search с фильтрами
2. estaffService.getClient(userId) ищет ExternalToken по userId + type='ESTAFF'
3. Использует найденный токен для запроса к meet-bot API

**Ожидаемый результат**:
- Запрос к meet-bot идёт с токеном конкретного пользователя
- Результаты возвращены успешно

#### TC-012: Обратная совместимость — существующие HH endpoints
**Предусловия**: Фронт использует GET /api/hh/search
**Шаги**:
1. GET /api/hh/search?text=JavaScript&cities=1

**Ожидаемый результат**:
- Status 200, формат ответа не изменился
- Никаких breaking changes

#### TC-013: Обратная совместимость — существующие eStaff endpoints
**Предусловия**: Фронт использует GET /api/applicants/search
**Шаги**:
1. GET /api/applicants/search?skills=Python

**Ожидаемый результат**:
- Status 200, формат ответа не изменился

### Фаза 3: Фронт — source-specific компоненты

#### TC-020: HH поиск → своя таблица с HH колонками
**Предусловия**: Пользователь выбрал source=HH
**Шаги**:
1. Переключить таб на "HH"
2. Выполнить поиск

**Ожидаемый результат**:
- Отображаются HH-специфичные фильтры (навыки, опыт, зарплата, регион, метро, professional_roles)
- Таблица результатов с HH колонками (ФИО, Должность, Опыт, Зарплата, Навыки)

#### TC-021: eStaff поиск → своя таблица с eStaff колонками
**Предусловия**: Пользователь выбрал source=eStaff
**Шаги**:
1. Переключить таб на "eStaff"
2. Выполнить поиск

**Ожидаемый результат**:
- Отображаются eStaff-специфичные фильтры
- Таблица результатов с eStaff колонками (могут отличаться от HH)

#### TC-022: "Добавить в рассылку" из HH результатов
**Предусловия**: Результаты HH поиска отображены, кандидаты выбраны
**Шаги**:
1. Выбрать кандидатов чекбоксами
2. Нажать "Создать рассылку"
3. hhToPayload() маппит каждого кандидата

**Ожидаемый результат**:
- Кандидаты маппятся с source='hh', hhResumeId заполнен
- POST /olivia/campaigns отправляется с правильным payload

#### TC-023: "Добавить в рассылку" из eStaff результатов
**Предусловия**: Результаты eStaff поиска отображены, кандидаты выбраны
**Шаги**:
1. Выбрать кандидатов чекбоксами
2. Нажать "Создать рассылку"
3. estaffToPayload() маппит каждого кандидата

**Ожидаемый результат**:
- Кандидаты маппятся с source='estaff', hhResumeId=null
- Контакты (telegram, whatsapp, phone) берутся из eStaff данных

#### TC-024: Badge источника в списке кандидатов кампании
**Предусловия**: Кампания с кандидатами из HH и eStaff
**Шаги**:
1. Открыть список кандидатов кампании

**Ожидаемый результат**:
- Рядом с именем каждого кандидата отображается badge/иконка источника (HH / eStaff)

---

## НЕГАТИВНЫЕ СЦЕНАРИИ

#### TC-101: eStaff поиск без per-user токена
**Предусловия**: У пользователя НЕТ eStaff токена в ExternalToken
**Шаги**:
1. Переключить на eStaff поиск

**Ожидаемый результат**:
- Показано сообщение: "Необходимо подключить eStaff аккаунт"
- Кнопка/ссылка для перехода к настройкам и привязке токена

#### TC-102: Кандидат без контактов — нет доступного канала
**Предусловия**: eStaff кандидат без telegram, whatsapp, phone
**Шаги**:
1. CampaignWorker обрабатывает кандидата
2. ContactStrategyResolver не находит ни одного канала

**Ожидаемый результат**:
- CampaignCandidate.status = SKIPPED (или ERROR с причиной "нет контактов")
- Кампания продолжает обрабатывать остальных кандидатов

#### TC-103: HH токен истёк во время обработки кампании
**Предусловия**: CampaignWorker обрабатывает HH кандидата, токен истёк
**Шаги**:
1. sendInvitation() получает 401 от HH API

**Ожидаемый результат**:
- CampaignCandidate.status не меняется (остаётся PENDING или IN_PROGRESS)
- Ошибка логируется
- Кампания продолжает работать, повторная попытка при следующем цикле

#### TC-104: Невалидный source в DTO кампании
**Предусловия**: Фронт отправляет невалидный source
**Шаги**:
1. POST /olivia/campaigns с candidates: [{source: 'INVALID'}]

**Ожидаемый результат**:
- Нормализация: неизвестный source → 'MANUAL' (безопасный fallback)
- Либо Status 400 с ошибкой валидации

---

## ИНТЕГРАЦИОННЫЕ СЦЕНАРИИ

#### TC-201: Полный цикл — eStaff поиск → кампания → Telegram
**Предусловия**: SUPER_ADMIN, eStaff токен привязан, Telegram аккаунт подключен
**Шаги**:
1. Переключить на eStaff, выполнить поиск
2. Выбрать 5 кандидатов (у всех заполнен telegram)
3. "Создать рассылку" → estaffToPayload() для каждого
4. POST /olivia/campaigns с source='estaff' для каждого кандидата
5. Запустить кампанию (POST /olivia/campaigns/{id}/start)
6. Дождаться CampaignWorker

**Ожидаемый результат**:
- Все 5 CampaignCandidate.source = 'ESTAFF'
- ContactStrategyResolver → TELEGRAM для каждого
- Сообщения отправлены через Kafka → messaging-back → Telegram
- Статусы: PENDING → IN_PROGRESS → CONTACTED

#### TC-202: Полный цикл — HH поиск → кампания → HH переговоры
**Предусловия**: Рекрутер, HH токен, HH вакансия
**Шаги**:
1. Поиск через HH таб
2. Выбрать 3 кандидата, hhToPayload()
3. POST /olivia/campaigns с source='hh', hhVacancyId
4. Запустить кампанию
5. Дождаться CampaignWorker

**Ожидаемый результат**:
- Все 3 CampaignCandidate.source = 'HH', hhResumeId заполнен
- ContactStrategyResolver → HH Negotiations
- Приглашения через HTTP: HhNegotiationClient → relevanter-back → api.hh.ru
- Статусы: PENDING → IN_PROGRESS → CONTACTED

#### TC-203: Смешанная кампания — HH + eStaff кандидаты
**Предусловия**: SUPER_ADMIN, оба токена, Telegram подключен
**Шаги**:
1. Создать кампанию с 3 HH и 2 eStaff кандидатами
2. Запустить кампанию

**Ожидаемый результат**:
- HH кандидаты → ContactStrategyResolver → HH negotiations (HTTP)
- eStaff кандидаты → ContactStrategyResolver → Telegram (Kafka)
- Статистика: { HH: 3, ESTAFF: 2 }
- Все обработаны без ошибок, каждый своим каналом
