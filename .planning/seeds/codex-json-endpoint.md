---
title: "Codex: перейти со скрейпинга Usage-страницы на JSON-эндпоинт"
trigger_condition: "После закрытия todo codex-5h-none-partial-parse (или сразу вместо него)"
planted_date: 2026-07-17
---

## Находка (ресёрч 2026-07-17)

Скрейпинг Chrome не нужен вообще. Есть внутренний эндпоинт, которым пользуется сам Codex CLI:

- `GET https://chatgpt.com/backend-api/wham/usage`
- Auth: **Bearer-токен из `~/.codex/auth.json`** (ChatGPT OAuth), не куки браузера.
- Codex CLI опрашивает его ~каждые 60 сек (`fetch_rate_limits`) для `/status` —
  отдаёт проценты 5-часового и недельного лимитов + время сброса.
- Источник: github.com/openai/codex issue #10869.

## Блокеры / риски

- **Cloudflare/anti-bot** стоит на пути кук+браузера, но токен-авторизованный путь CLI
  работает headless без браузера — это и есть обход главного блокера текущей схемы.
- **Схема ответа недокументирована** (confidence MEDIUM) — нужен парсер с фолбэком
  и логированием сырого JSON при смене формата.
- **Официального API нет** (mid-2026) — эндпоинт внутренний, может измениться;
  но прецедентов работы много (см. prior art), а Codex CLI сам на нём живёт.
- Нужен рефреш токена: auth.json обновляет сам Codex CLI (как Claude Code
  обновляет .credentials.json) — та же модель, что в claude-виджете: читать файл,
  при 401 быстрый ретрай.

## Prior art

- fberbert/codex-widget — плавающий десктоп-виджет, прогресс-бары + reset.
- steipete/CodexBar — macOS menu bar, читает auth.json.
- mryll/codexbar — Bash/Waybar.
- douglasmonsky/codex-usage-tracker — по JSONL-логам CLI
  (альтернативный источник: `token_count.rate_limits` в логах Codex CLI).

## Эффект

- Умирают: Playwright, системный Chrome, persistent-профиль с живой сессией
  (риск утечки), prune-каждые-5-минут, regex-парсер текста, баг «5h не найдено».
- Codex-провайдер становится симметричен claude-провайдеру (HTTP + токен из файла CLI) —
  слияние виджетов (см. [[merge-widgets-strategy]]) сильно упрощается.
