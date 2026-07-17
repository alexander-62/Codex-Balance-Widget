# Phase 1: JSON endpoint probe - Context

**Gathered:** 2026-07-17
**Status:** Ready for planning
**Source:** User instruction via /gsd-plan-phase args + /gsd-explore session 2026-07-17

<domain>
## Phase Boundary

Отдельный тестовый скрипт, доказывающий, что usage-данные Codex достаются
одним HTTP-запросом `GET https://chatgpt.com/backend-api/wham/usage`
с Bearer-токеном из `~/.codex/auth.json` — без Chrome/Playwright.
Фаза заканчивается зафиксированной схемой ответа (фикстура) и маппингом
полей ответа на текущую модель `Balance`.

</domain>

<decisions>
## Implementation Decisions

### Скоуп (явное требование пользователя)
- Рабочий код НЕ выкидывать и НЕ менять: `codex_balance_widget_chrome.py`,
  лончеры, батники — нетронуты. [LOCKED]
- Только дополнительный тестовый скрипт по структуре эндпоинта. [LOCKED]

### Источник данных (из ресёрча /gsd-explore, seed codex-json-endpoint)
- Эндпоинт: `GET https://chatgpt.com/backend-api/wham/usage`.
- Auth: Bearer access token из `~/.codex/auth.json` (его обновляет сам Codex CLI).
- Тем же эндпоинтом пользуется Codex CLI (`fetch_rate_limits`, ~60s poll).

### Claude's Discretion
- Имя и структура скрипта, stdlib-only vs зависимости (предпочтительно stdlib,
  как в claude_balance_widget_v1: urllib).
- Формат фикстуры и способ редакции секретов.
- Обработка вариантов схемы ответа (поля неизвестны до первого запуска).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Источник и блокеры
- `.planning/seeds/codex-json-endpoint.md` — эндпоинт, auth, риски, prior art.

### Текущая модель данных (для маппинга полей)
- `codex_balance_widget_chrome.py` — класс `Balance` (~строка 199) и
  `BalanceParser` (~строка 504): какие поля виджету нужны от нового источника.
  Читать только для справки — файл не изменять.

### Референс лёгкого HTTP-клиента с токеном из файла CLI
- `d:\00_Projects\claude_balance_widget_v1\claude_balance_widget.py` —
  `_load_token()` / `fetch()` (~строки 240–326): та же модель
  «читай токен из файла CLI + urllib GET + понятные ошибки».

</canonical_refs>

<specifics>
## Specific Ideas

- Скрипт печатает: HTTP-статус, pretty JSON, извлечённые поля (5h %, weekly %,
  resets, credits) или список отсутствующих полей.
- Сырой ответ сохраняется в фикстуру с зарезанным токеном/идентификаторами.
- Ошибки токена/401 — человекочитаемая диагностика, не traceback.
- Prior art для сверки схемы: steipete/CodexBar, fberbert/codex-widget,
  openai/codex issue #10869.

</specifics>

<deferred>
## Deferred Ideas

- Интеграция JSON-источника в виджет с фолбэком на Chrome — Phase 2.
- Удаление Playwright/Chrome-пути — после подтверждения стабильности (за Phase 2).

</deferred>

---

*Phase: 01-json-endpoint-probe*
*Context gathered: 2026-07-17*
