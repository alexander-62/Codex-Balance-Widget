# Phase 2: JSON provider integration - Context

**Gathered:** 2026-07-20
**Status:** Ready for planning
**Source:** User instruction via /gsd-discuss-phase 2 (user delegated implementation calls to Claude)

<domain>
## Phase Boundary

Виджет получает данные через JSON-эндпоинт (`probe_wham_usage.py`'s core, built in
Phase 1) как основной источник. Chrome-скрейпинг (Playwright) остаётся фолбэком,
пока JSON-путь не подтвердит стабильность (удаление Chrome-пути — вне скоупа этой
фазы, отдельная будущая фаза). Обычный цикл обновления не должен запускать Chrome
при исправном JSON-пути; лог фиксирует источник каждого успешного обновления.

</domain>

<decisions>
## Implementation Decisions

### Стратегия фолбэка на Chrome
- **D-01:** Chrome-контекст НЕ держим прогретым в фоне — запускаем по требованию,
  как сейчас (`browser.fetch()` в `fetch_once`). Это desktop tray-виджет — не стоит
  тратить ресурсы на постоянно открытый Chrome ради fallback-сценария.
- **D-02:** 401 / 403 (JSON или HTML/Cloudflare) → сразу fallback на Chrome без
  ретраев в JSON-пути. Эти классы ошибок не самолечатся внутри процесса.
- **D-03:** 429 / сетевая ошибка (URLError) / таймаут → один быстрый повтор JSON-
  запроса перед fallback на Chrome — эти классы транзиентны (см. 01-RESEARCH.md
  "Семантика ошибок" таблица).

### 401 / просроченный токен Codex CLI
- **D-04:** Виджет НЕ инициирует refresh токена и не ждёт его обновления —
  вне скоупа (Phase 1 RESEARCH уже зафиксировал: "скрипт-проба НЕ делает refresh").
  `~/.codex/auth.json` обновляет сам Codex CLI как внешний процесс. Если к
  следующему циклу опроса токен уже свежий — JSON-путь просто заработает сам,
  без специального кода ожидания.

### Индикация источника
- **D-05:** Success criteria фазы требует только лог (`json` | `chrome`) для
  каждого успешного обновления — постоянный UI-бейдж источника не добавляется
  (не в скоупе, не запрошено). Строку статуса дополняем пометкой источника
  ТОЛЬКО когда активен fallback (например "Chrome-фолбэк"), по аналогии с
  существующими статус-сообщениями в `fetch_once` (строки ~2090-2112 в
  `codex_balance_widget_chrome.py`).

### Критерий стабильности для удаления Chrome-пути
- **D-06:** Числовая метрика "стабильности" НЕ фиксируется в этой фазе — Roadmap
  явно откладывает удаление Playwright-пути на будущую фазу (уже отмечено как
  deferred idea в 01-CONTEXT.md). Формулировка порога — отдельное обсуждение тогда.

### Claude's Discretion
- Точное имя/расположение нового JSON-provider модуля (новый файл vs добавление
  в `codex_balance_widget_chrome.py`) — решает планировщик/executor с учётом
  архитектуры проекта.
- Частота опроса JSON-эндпоинта: сохранять текущий `refresh_seconds` виджета
  (не менять пользовательский интервал без явного запроса) — Codex CLI поллит
  ~60s, но переход на JSON не обязывает виджет ускоряться.
- Точная формулировка лог-строк ("source: json" / "source: chrome") и куда они
  пишутся (существующий `write_log` в `codex_balance_widget_chrome.py`).
- Как переиспользовать код из `probe_wham_usage.py` (Phase 1): импорт как
  модуль vs копирование релевантных функций (`load_tokens`, `fetch_usage`,
  `extract_fields`, `collect_windows`) — решает планировщик, ориентируясь на
  "рабочий код виджета не изменяется бесконтрольно" из Phase 1 [LOCKED] и на
  то, что теперь JSON-путь официально становится частью рабочего кода.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Источник данных и контракт эндпоинта (Phase 1)
- `.planning/phases/01-json-endpoint-probe/01-RESEARCH.md` — Endpoint Contract,
  таблица "Семантика ошибок" (401/403-JSON/403-HTML/429/URLError/Timeout),
  Pitfall 5 (Cloudflare HTML маскируется под ошибку парсинга).
- `.planning/phases/01-json-endpoint-probe/01-SUMMARY.md` и
  `01-02-SUMMARY.md` — что уже построено и живо подтверждено (probe script,
  fixture, extracted fields).
- `probe_wham_usage.py` — готовые функции: `load_tokens`, `jwt_exp`,
  `collect_windows`, `pick_window`, `extract_fields`, `redact`,
  `redaction_clean`, `build_headers`, `fetch_usage`. Источник для
  переиспользования в JSON-провайдере.
- `wham_usage_fixture.json` — редактированная живая фикстура ответа
  (plan_type=plus, weekly window only) — референс для тестов парсера.

### Текущая модель данных и fallback-логика (для интеграции)
- `codex_balance_widget_chrome.py` — класс `Balance` (~строка 195),
  `BalanceParser` (~строка 504), `fetch_once`/`refresh_loop` (~строки
  2073-2119): текущий Chrome-путь, статус-сообщения, куда встраивается JSON-
  путь как приоритетный источник с fallback на существующую логику.
- `codex_balance_widget_chrome.py:214` (`write_log`) — существующий логгер,
  куда должна попасть запись источника (json|chrome).

### Референс лёгкого HTTP-клиента с токеном из файла CLI
- `d:\00_Projects\claude_balance_widget_v1\claude_balance_widget.py`,
  строки 240-326 (`_load_token()` / `fetch()`) — тот же паттерн для другого
  похожего виджета; `probe_wham_usage.py` уже построен по этому образцу.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `probe_wham_usage.py` (Phase 1, stdlib-only, 23 зелёных теста) — готовый,
  протестированный клиент для `wham/usage`: auth-загрузка, redaction,
  извлечение полей, классификация окон по `limit_window_seconds`.
- `wham_usage_fixture.json` — референсная фикстура для юнит-тестов парсера
  JSON-провайдера (без необходимости живого запроса в тестах).

### Established Patterns
- Русскоязычная человекочитаемая диагностика ошибок (401/403/429/network/
  timeout), без traceback — уже реализовано в `probe_wham_usage.py`, тот же
  стиль ожидается и в интеграции с виджетом.
- `Balance` — plain dataclass с полями `five_hour_percent`, `weekly_percent`,
  `credits`, `five_hour_reset_text`, `weekly_reset_text`,
  `has_usage_data` property — JSON-провайдер должен производить именно этот
  объект (или совместимую структуру) для `update_balance_ui`.
- `fetch_once` уже реализует паттерн "текущие данные остаются на экране при
  сбое обновления" (`current_balance.has_usage_data` check) — сохранить эту
  UX-гарантию и для JSON-пути.

### Integration Points
- `fetch_once` (~строка 2073) — точка, где сегодня вызывается
  `self.browser.fetch()` + `BalanceParser.parse()`; JSON-путь встраивается
  здесь как первая попытка перед Chrome-фолбэком.
- `write_log` (~строка 214) — точка логирования источника обновления.

</code_context>

<specifics>
## Specific Ideas

Нет специфичных UI-пожеланий сверх зафиксированных решений выше — пользователь
делегировал детали реализации ("я не знаю, м.б. тебе и так все понятно?").

</specifics>

<deferred>
## Deferred Ideas

- Удаление Playwright/Chrome-пути целиком — после подтверждения стабильности
  JSON-пути; критерий стабильности не зафиксирован (см. D-06). Уже отмечено
  как deferred в 01-CONTEXT.md.
- Постоянный UI-индикатор источника (бейдж json/chrome) — не запрошено,
  см. D-05; если понадобится — отдельная мелкая фаза/полировка.
- Более частый опрос (использовать возможность JSON быть дешевле Chrome) —
  не в скоупе, см. Claude's Discretion выше; можно поднять в отдельном
  обсуждении при желании.

</deferred>

---

*Phase: 02-json-provider-integration*
*Context gathered: 2026-07-20*
