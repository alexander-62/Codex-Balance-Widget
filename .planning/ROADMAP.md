# Roadmap: Codex Balance Widget — переход на JSON-источник данных

## Overview

Уйти от Chrome-скрейпинга Usage-страницы к прямому JSON-эндпоинту
`chatgpt.com/backend-api/wham/usage` (Bearer-токен из `~/.codex/auth.json`).
Сначала доказать жизнеспособность отдельным тестовым скриптом, не трогая
рабочий код виджета; затем — интеграция провайдером.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: JSON endpoint probe** - Отдельный тестовый скрипт: auth.json → wham/usage → структура ответа. Рабочий код виджета не изменяется.
- [ ] **Phase 2: JSON provider integration** - Встроить JSON-источник в виджет с фолбэком на Chrome-скрейпинг.

## Phase Details

### Phase 1: JSON endpoint probe
**Goal**: Доказать отдельным скриптом, что usage-данные Codex (5h %, weekly %, resets, credits) достаются одним HTTP GET к `https://chatgpt.com/backend-api/wham/usage` с токеном из `~/.codex/auth.json` — без браузера. Существующий код виджета не меняется.
**Depends on**: Nothing (first phase)
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. Запуск `py -3 probe_wham_usage.py` печатает HTTP-статус и красиво отформатированный JSON ответа эндпоинта.
  2. Скрипт извлекает и печатает поля, эквивалентные текущему Balance: 5-часовой %, недельный %, времена сброса (и кредиты, если присутствуют), либо честно сообщает, каких полей нет.
  3. Скрипт сохраняет сырой ответ в файл-фикстуру (с редакцией токена) для будущих тестов парсера.
  4. При отсутствии/протухании токена скрипт печатает понятную диагностику (какой файл, какое поле, HTTP-код), а не traceback.
  5. `git status` показывает только новые файлы — ни одна строка `codex_balance_widget_chrome.py` и лончеров не изменена.
**Plans**: TBD

### Phase 2: JSON provider integration
**Goal**: Виджет получает данные через JSON-эндпоинт как основной источник; Chrome-скрейпинг остаётся фолбэком до подтверждения стабильности.
**Depends on**: Phase 1
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. Обычный цикл обновления не запускает Chrome.
  2. При ошибке JSON-пути виджет падает обратно на текущий Chrome-механизм.
  3. Лог фиксирует источник каждого успешного обновления (json | chrome).
**Plans**: TBD
