# Roadmap: Codex Balance Widget — переход на JSON-источник данных

## Overview

Уйти от Chrome-скрейпинга страницы Usage к прямому JSON-эндпоинту
`chatgpt.com/backend-api/wham/usage` (Bearer-токен из `~/.codex/auth.json`).
Сначала доказать жизнеспособность отдельным тестовым скриптом, не трогая
рабочий код виджета; затем — интеграция провайдером.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: JSON endpoint probe** - Отдельный тестовый скрипт: auth.json → wham/usage → структура ответа. Рабочий код виджета не изменяется. (completed 2026-07-20)
- [x] **Phase 2: JSON provider integration** - Встроить JSON-источник в виджет с фолбэком на Chrome-скрейпинг. (completed 2026-07-21)

## Phase Details

### Phase 1: JSON endpoint probe

**Goal**: Доказать отдельным скриптом, что usage-данные Codex (5h %, weekly %, resets, credits) достаются одним HTTP GET к `https://chatgpt.com/backend-api/wham/usage` с токеном из `~/.codex/auth.json` — без браузера. Существующий код виджета не меняется.
**Depends on**: Nothing (first phase)
**Requirements**: PROBE-01, PROBE-02, PROBE-03, PROBE-04
**Success Criteria** (what must be TRUE):

  1. Запуск `py -3 probe_wham_usage.py` печатает HTTP-статус и красиво отформатированный JSON ответа эндпоинта.
  2. Скрипт извлекает и печатает поля, эквивалентные текущему Balance: 5-часовой %, недельный %, времена сброса (и кредиты, если присутствуют), либо честно сообщает, каких полей нет.
  3. Скрипт сохраняет сырой ответ в файл-фикстуру (с редакцией токена) для будущих тестов парсера.
  4. При отсутствии/протухании токена скрипт печатает понятную диагностику (какой файл, какое поле, HTTP-код), а не traceback.
  5. `git status` показывает только новые файлы — ни одна строка `codex_balance_widget_chrome.py` и лончеров не изменена.

**Plans**: 2 plans

Plans:

- [x] 01-01-PLAN.md — Проба probe_wham_usage.py (чистое ядро + HTTP + CLI-диагностика) и unit-тесты test_probe_wham_usage.py (wave 1, autonomous)
- [x] 01-02-PLAN.md — Живой запуск: HTTP 200, фикстура wham_usage_fixture.json с редакцией, git-чистота + human-verify (wave 2, checkpoint)

### Phase 01.1: Address Phase 1 tech debt: redaction post-check, malformed-payload AttributeError, main() exception scope (INSERTED)

**Goal:** Close CR-01 (stdout redaction lacks the redaction_clean() post-check that write_fixture() has), CR-02 (collect_windows() crashes on non-dict rate_limit/additional_rate_limits entries), and WR-01 (main() only catches ProbeError) in probe_wham_usage.py, exactly as identified in 01-REVIEW.md / 01-VERIFICATION.md.
**Requirements**: tech-debt-closure
**Depends on:** Phase 1
**Plans:** 1/1 plans complete

Plans:
- [x] 01.1-01-PLAN.md — Regression tests + fixes for CR-01/CR-02/WR-01 in probe_wham_usage.py (wave 1, autonomous)

### Phase 2: JSON provider integration

**Goal**: Виджет получает данные через JSON-эндпоинт как основной источник; Chrome-скрейпинг остаётся фолбэком до подтверждения стабильности.
**Depends on**: Phase 1
**Requirements**: JSONPROV-01, JSONPROV-02, JSONPROV-03
**Success Criteria** (what must be TRUE):

  1. Обычный цикл обновления не запускает Chrome. (JSONPROV-01)
  2. При ошибке JSON-пути виджет падает обратно на текущий Chrome-механизм. (JSONPROV-02)
  3. Лог фиксирует источник каждого успешного обновления (json | chrome). (JSONPROV-03)

**Plans**: 3 plans
Plans:
**Wave 1**

- [x] 02-01-PLAN.md — probe_wham_usage.py: ProbeError.retryable + json_usage_provider.py (async, retry-once по D-02/D-03) (wave 1, autonomous)
- [x] 02-02-PLAN.md — Чистые хелперы виджета: ISO reset-дата в parse_reset_datetime, build_balance_from_json_fields, plan_fetch_outcome (wave 1, autonomous)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-03-PLAN.md — Врезка в fetch_once: JSON основной источник + Chrome-фолбэк + лог источника, живая проверка (wave 2, checkpoint)
