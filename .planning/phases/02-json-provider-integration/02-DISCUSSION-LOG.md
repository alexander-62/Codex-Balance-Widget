# Phase 2: JSON provider integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-20
**Phase:** 02-json-provider-integration
**Areas discussed:** Стратегия фолбэка, 401/просроченный токен, Индикация источника в UI, Критерий стабильности для удаления Chrome

---

## Gray areas presented

| Area | Description | Selected |
|------|-------------|----------|
| Стратегия фолбэка | Retry vs немедленный fallback; держать Chrome прогретым или запускать по требованию | delegated to Claude |
| 401 / просроченный токен | Ждать/ретраить refresh или сразу fallback | delegated to Claude |
| Индикация источника в UI | Постоянный бейдж vs только лог | delegated to Claude |
| Критерий стабильности для удаления Chrome | Фиксировать метрику сейчас или отложить | delegated to Claude |

**User's response:** "я не знаю, м.б. тебе и так все понятно?" — пользователь делегировал
все четыре решения Claude, не выбирая по отдельности.

**Notes:** Claude использовал контекст из 01-RESEARCH.md (таблица "Семантика ошибок")
и существующий код `codex_balance_widget_chrome.py` (`fetch_once`, `write_log`) для
принятия обоснованных решений. Итоговые решения представлены пользователю как
сводка на русском перед записью в CONTEXT.md; явных возражений не получено.

---

## Claude's Discretion

- Стратегия фолбэка (D-01..D-03 в CONTEXT.md): без прогретого Chrome-контекста;
  401/403 → немедленный fallback; 429/network/timeout → один ретрай перед fallback.
- 401/токен (D-04): не инициировать refresh, полагаться на Codex CLI как внешний процесс.
- Индикация источника (D-05): лог обязателен, UI-бейдж не добавляется, статус-строка
  помечается только при активном fallback.
- Критерий стабильности (D-06): не фиксируется в этой фазе.
- Имя/расположение JSON-provider модуля, частота опроса, формулировка лог-строк,
  способ переиспользования кода из `probe_wham_usage.py` — оставлено планировщику/executor.

## Deferred Ideas

- Удаление Playwright/Chrome-пути целиком — будущая фаза, критерий стабильности не определён.
- Постоянный UI-индикатор источника (бейдж json/chrome) — не запрошено, возможна отдельная полировка.
- Более частый опрос за счёт дешевизны JSON — вне скоупа, можно поднять отдельно.
