---
title: "Стратегия слияния двух виджетов в один мультипровайдерный"
date: 2026-07-17
context: "Аудит codex_balance_widget + claude_balance_widget_v1 от 2026-07-17"
---

## Зачем

Два виджета ≈ 80% общего кода: Tk-окно, ProgressBar, weekly-burndown canvas,
pystray-трей, SettingsStore/HistoryStore, single-instance lock, скрытый лончер
(.pyw + vbs + bat), логирование. Различается только источник данных:

- **Claude** — чистый HTTP GET к API Anthropic c OAuth-токеном из `.credentials.json`
  Claude Code (лёгкий, <1 сек).
- **Codex** — Playwright + системный Chrome + persistent-профиль, парсинг regex'ами
  текста Usage-страницы (тяжёлый, ~10–20 сек, хрупкий).

## Целевая архитектура

Один проект `ai_balance_widget`:

- `providers/base.py` — интерфейс `Provider.fetch() -> Balance` с единой моделью:
  `five_hour_remaining: float|None`, `weekly_remaining: float|None`,
  `five_hour_reset: datetime|None`, `weekly_reset: datetime|None`, `extra: dict`.
- `providers/claude_api.py` — текущий HTTP-код claude-виджета.
- `providers/codex_chrome.py` — текущий Playwright-код (позже — JSON-перехват,
  см. seed [[codex-json-endpoint]]).
- Общий UI: одно окно, колонка/карточка на провайдера; один трей-айкон
  (tooltip ≤127 символов — суммарный, по строке на провайдера).
- Каждый провайдер — своя asyncio-задача со своим интервалом и backoff:
  тяжёлый codex-фетч не должен блокировать claude-обновления.

## Блокеры и риски слияния (исследовано 2026-07-17)

Жёстких блокеров нет, технологии совместимы (оба — Python 3.14, Tk, pystray).
Рабочие риски:

1. **Разные модели данных**: claude — float remaining + ISO datetime; codex — строковые
   проценты + свободный текст «Сброс …». Нужен единый Balance + конвертация
   codex-парсера в datetime (parse_reset_datetime уже есть).
2. **Миграция состояния**: два settings.json, два history.json, разные имена
   lock-файлов и Windows-событий активации. Нужен однократный мигратор.
3. **Playwright должен стать опциональным**: lazy-import только при включённом
   codex-провайдере, иначе claude-only установка тянет лишнее.
4. **Один трей на два статуса**: лимит tooltip 128 символов (уже ловили ValueError),
   иконка должна кодировать худший из двух балансов.
5. **i18n**: codex имеет tr(en/ru), claude — только ru. Переносить tr().
6. **Runtime-состояние** при слиянии сразу переносить в `%LOCALAPPDATA%\ai_balance_widget\`
   (профиль Chrome, логи, json) — вне git-дерева, с ротацией логов.

## Порядок

1. Сначала закрыть живые баги в обоих (todo: claude-widget-tooltip-and-401-retry,
   codex-5h-none-partial-parse) — мигрировать проще со стабильной базы.
2. Вынести общий код в пакет, поднять claude-провайдер (проще).
3. Перенести codex-провайдер как есть, затем seed про JSON-эндпоинт.
