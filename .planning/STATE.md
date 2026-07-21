---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Shared usage-provider core
status: planning
last_updated: "2026-07-21T15:21:58.125Z"
last_activity: 2026-07-21
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/ROADMAP.md (updated 2026-07-17)

**Core value:** Виджет баланса Codex без Chrome-скрейпинга — надёжный JSON-источник.
**Current focus:** Phase 02 — json provider integration

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-07-21 — Milestone v1.1 started

## Accumulated Context

### Roadmap Evolution

- Phase 01.1 inserted after Phase 1: Address Phase 1 code-review debt (CR-01/CR-02/WR-01) before completing milestone v1.0 (URGENT)

### Decisions

- Рабочий код виджета (Chrome-скрейпинг) в Phase 1 не изменяется — только новый тестовый скрипт.
- Источник данных: `GET https://chatgpt.com/backend-api/wham/usage`, Bearer-токен из `~/.codex/auth.json` (см. .planning/seeds/codex-json-endpoint.md).

### Blockers

- Схема ответа wham/usage недокументирована — Phase 1 существует, чтобы её зафиксировать.

### Overrides

- Phase 2 planning: decision coverage gate flagged D-06 (метрика стабильности для удаления Chrome-пути НЕ фиксируется в этой фазе) как непокрытую ни одним планом. Оператор подтвердил "Продолжить как есть" — D-06 корректно отсутствует в планах, т.к. решение описывает NOT-в-скоупе для Phase 2 (см. 02-CONTEXT.md D-06). verify-phase может пере-поднять это при необходимости.

## Deferred Items

Items acknowledged and deferred at milestone v1.0 close on 2026-07-21:

| Category | Item | Status |
|----------|------|--------|
| todo | claude-widget-tooltip-and-401-retry.md | pending, high priority — out of this milestone's scope (claude_balance_widget.py, separate project) |
| todo | codex-5h-none-partial-parse.md | pending, high priority — live parsing bug, candidate for v1.1 milestone |

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
