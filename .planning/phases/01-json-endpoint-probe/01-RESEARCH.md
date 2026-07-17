# Phase 1: JSON endpoint probe - Research

**Researched:** 2026-07-17
**Domain:** HTTP-клиент к внутреннему API ChatGPT (`wham/usage`) с OAuth-токеном Codex CLI; Python 3.14 stdlib, Windows
**Confidence:** HIGH — схема ответа и заголовки подтверждены живым запросом с этой машины + исходниками openai/codex

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Рабочий код НЕ выкидывать и НЕ менять: `codex_balance_widget_chrome.py`, лончеры, батники — нетронуты. [LOCKED]
- Только дополнительный тестовый скрипт по структуре эндпоинта. [LOCKED]
- Эндпоинт: `GET https://chatgpt.com/backend-api/wham/usage`.
- Auth: Bearer access token из `~/.codex/auth.json` (его обновляет сам Codex CLI).
- Тем же эндпоинтом пользуется Codex CLI (`fetch_rate_limits`, ~60s poll).

### Claude's Discretion
- Имя и структура скрипта, stdlib-only vs зависимости (предпочтительно stdlib, как в claude_balance_widget_v1: urllib).
- Формат фикстуры и способ редакции секретов.
- Обработка вариантов схемы ответа (поля неизвестны до первого запуска).

### Deferred Ideas (OUT OF SCOPE)
- Интеграция JSON-источника в виджет с фолбэком на Chrome — Phase 2.
- Удаление Playwright/Chrome-пути — после подтверждения стабильности (за Phase 2).
</user_constraints>

## Summary

Главный риск фазы («схема ответа недокументирована») снят прямо в ресёрче: выполнен живой `GET https://chatgpt.com/backend-api/wham/usage` с этой машины через `urllib` с Bearer-токеном из `%USERPROFILE%\.codex\auth.json` — HTTP 200, `application/json`, полная схема зафиксирована ниже. [VERIFIED: live probe 2026-07-17] Схема совпадает с генерированными OpenAPI-моделями в исходниках openai/codex (`RateLimitStatusPayload` / `RateLimitStatusDetails` / `RateLimitWindowSnapshot` / `CreditStatusDetails`). [CITED: github.com/openai/codex, codex-rs/codex-backend-openapi-models]

Критическая находка, которую обязан учесть план: **`primary_window` — это НЕ обязательно 5-часовое окно.** На текущем аккаунте (plan_type=plus) `primary_window.limit_window_seconds = 604800` (неделя), а `secondary_window = null` — 5-часовое окно в ответе просто отсутствует. Окна нужно классифицировать по `limit_window_seconds` (18000 → 5h, 604800 → weekly), а не по позиции. Это же объясняет давний баг виджета «5h не найдено» на странице Usage.

Минимальные требования подтверждены: достаточно одного заголовка `Authorization: Bearer <tokens.access_token>` — работает даже с дефолтным UA `Python-urllib/3.14`, без `ChatGPT-Account-Id`. [VERIFIED: live probe] 401 возвращает чистый JSON `{"detail": "..."}` — не Cloudflare HTML. Токен — JWT с `exp` (~10 дней от `last_refresh`); Codex CLI сам его обновляет при использовании (порог staleness 8 дней в `manager.rs`).

**Primary recommendation:** один stdlib-скрипт `codex_usage_probe.py` (urllib + json + base64 + pathlib): читает `tokens.access_token` из auth.json (с учётом `CODEX_HOME`), шлёт GET с Bearer + `ChatGPT-Account-Id` (если есть `tokens.account_id`), классифицирует окна по `limit_window_seconds`, печатает извлечённые поля в терминах модели `Balance`, сохраняет фикстуру с редакцией PII (в ответе есть `email`, `user_id`, `account_id`!).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Чтение/валидация токена | Локальный скрипт (файл CLI) | — | auth.json обновляет Codex CLI; скрипт только читает |
| Refresh токена | Codex CLI (внешний процесс) | — | Вне скоупа: у CLI своя логика refresh (8 дней / JWT exp); скрипт при 401 советует запустить `codex` |
| Отдача usage-данных | ChatGPT backend-api (`/wham/usage`) | — | Единственный источник; тот же, что у `codex /status` |
| Классификация окон 5h/weekly | Локальный скрипт | — | Сервер не помечает окна; различаются только `limit_window_seconds` |
| Редакция секретов в фикстуре | Локальный скрипт | — | PII (email, user_id, account_id) приходит в ответе — нельзя коммитить сырьё |

## Standard Stack

### Core (только stdlib — решение в рамках Claude's Discretion, по образцу claude_balance_widget_v1)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `urllib.request` | stdlib 3.14 | GET + заголовки | Проверено живым запросом; тот же паттерн, что в `claude_balance_widget.py` `fetch()` [VERIFIED: live probe] |
| `json` | stdlib | Парсинг ответа/auth.json, фикстура | — |
| `pathlib` / `os` | stdlib | `Path.home()/".codex"/"auth.json"`, `CODEX_HOME` | — |
| `base64` + `json` | stdlib | Декодирование payload JWT (exp, plan) без верификации подписи | Диагностика «токен истёк» до запроса |
| `datetime` | stdlib | `reset_at` (epoch-секунды) → локальное время | — |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `argparse` | stdlib | флаги `--json`, `--fixture PATH`, `--timeout` | Если план захочет параметризовать |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| urllib | requests/httpx | Не нужны: один GET; зависимость нарушает предпочтение stdlib из CONTEXT.md |

**Installation:** не требуется — внешних пакетов нет.

## Package Legitimacy Audit

Фаза не устанавливает внешних пакетов (stdlib-only). Аудит не применим.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Endpoint Contract (VERIFIED)

### Запрос

```
GET https://chatgpt.com/backend-api/wham/usage
Authorization: Bearer <tokens.access_token из auth.json>      # обязателен
ChatGPT-Account-Id: <tokens.account_id>                        # опционален для personal; codex CLI шлёт, если задан
Accept: application/json                                       # хорошая практика
User-Agent: <любой>                                            # работает даже Python-urllib/3.14 [VERIFIED: live probe]
```

- Минимальный набор = только `Authorization`. [VERIFIED: live probe 2026-07-17, HTTP 200]
- Codex CLI шлёт UA `codex-cli` (или свой), auth-заголовки, `ChatGPT-Account-Id` (если известен), `X-OpenAI-Fedramp: true` (только FedRAMP). [CITED: codex-rs/backend-client/src/client.rs `headers()`]
- URL строится как `{base}/wham/usage` при base = `https://chatgpt.com/backend-api`. [CITED: codex-rs/backend-client/src/client/rate_limit_resets.rs `rate_limit_status_url()`]
- Для workspace/team-аккаунтов prior art считает `ChatGPT-Account-Id` обязательным → скрипту слать его всегда, когда `tokens.account_id` есть. [CITED: github.com/7shi/codex-oauth; knightli.com/en/2026/04/12/codex-usage-quota-check]

### Ответ (живой, 2026-07-17, plan=plus; PII заменено на `<redacted>`)

```json
{
  "user_id": "<redacted>",
  "account_id": "<redacted>",
  "email": "<redacted>",
  "plan_type": "plus",
  "rate_limit": {
    "allowed": true,
    "limit_reached": false,
    "primary_window": {
      "used_percent": 16,
      "limit_window_seconds": 604800,
      "reset_after_seconds": 511006,
      "reset_at": 1784792381
    },
    "secondary_window": null
  },
  "code_review_rate_limit": null,
  "additional_rate_limits": null,
  "credits": {
    "has_credits": false,
    "unlimited": false,
    "overage_limit_reached": false,
    "balance": "0",
    "approx_local_messages": [0, 0],
    "approx_cloud_messages": [0, 0]
  },
  "spend_control": { "reached": false, "individual_limit": "<redacted>" },
  "rate_limit_reached_type": null,
  "promo": null,
  "rate_limit_reset_credits": { "available_count": 3, "applicable_available_count": 0 }
}
```

### Типы полей (из генерированных OpenAPI-моделей codex)

[CITED: codex-rs/codex-backend-openapi-models/src/models/*.rs]

- `plan_type`: enum `guest|free|go|plus|pro|prolite|free_workspace|team|business|enterprise|edu|...|unknown`
- `rate_limit`: nullable объект `{allowed: bool, limit_reached: bool, primary_window: Window|null, secondary_window: Window|null}`
- `Window`: `{used_percent: int, limit_window_seconds: int, reset_after_seconds: int, reset_at: int}`
  - `reset_at` — **Unix-секунды** (в codex-protocol задокументировано: «Unix timestamp (seconds since epoch) when the window resets»; тип i32 физически не вмещает миллисекунды). [CITED: codex-rs/protocol/src/protocol.rs `RateLimitWindow`]
  - `used_percent` — процент ИЗРАСХОДОВАННОГО; виджет показывает остаток → `remaining = 100 - used_percent`
- `credits`: nullable `{has_credits: bool, unlimited: bool, balance: string|null, ...}` — `balance` строка ("0")
- `additional_rate_limits`: nullable массив `{limit_name: string, metered_feature: string, rate_limit: {...}}` — модельные лимиты (например GPT-5.x-pro)
- `rate_limit_reached_type`: nullable `{type: "rate_limit_reached"|"workspace_owner_usage_limit_reached"|...}`
- `rate_limit_reset_credits`: nullable `{available_count: int}` (+ недокументированное `applicable_available_count`)
- Поля `user_id/account_id/email/code_review_rate_limit/promo` в OpenAPI-модели codex отсутствуют (CLI их игнорирует), но реально приходят [VERIFIED: live probe] — парсер обязан терпеть неизвестные ключи.

### Семантика ошибок

| Статус | Content-Type | Значение | Реакция скрипта |
|--------|--------------|----------|-----------------|
| 401 | application/json `{"detail": "Could not parse your authentication token..."}` | Токен истёк/битый [VERIFIED: live probe с мусорным токеном] | «Токен Codex истёк. Запустите `codex` (любую команду) — CLI обновит auth.json — и повторите.» |
| 403 + JSON | application/json | Аккаунту недоступен эндпоинт / workspace без Account-Id | Подсказать про `ChatGPT-Account-Id` [CITED: knightli.com] |
| 403 + `text/html` | HTML | Cloudflare interstitial [CITED: steipete/CodexBar docs/codex.md «Login required or Cloudflare interstitial»] | Отдельная диагностика: «Cloudflare-заслон, повторите позже»; печатать первые ~200 символов тела |
| 429 | — | Троттлинг | Повторить позже |

## Token / auth.json Contract (VERIFIED)

Структура `~/.codex/auth.json` (подтверждена локально на этой машине И структурой `AuthDotJson` в codex): [VERIFIED: локальный файл + codex-rs/login/src/auth/storage.rs]

```json
{
  "auth_mode": "chatgpt",              // может быть и apikey-режим
  "OPENAI_API_KEY": null,              // при apikey-режиме здесь ключ, tokens может отсутствовать
  "tokens": {
    "id_token": "<JWT>",               // НЕ использовать для API
    "access_token": "<JWT>",           // ← Bearer для wham/usage
    "refresh_token": "<opaque>",       // не трогать — refresh делает CLI
    "account_id": "<uuid>"             // → заголовок ChatGPT-Account-Id
  },
  "last_refresh": "2026-07-15T09:58:07.855507600Z"
}
```

- Путь: `$CODEX_HOME/auth.json`, по умолчанию `~/.codex/` — скрипт должен уважать `CODEX_HOME`. [CITED: codex-rs storage.rs «Expected structure for $CODEX_HOME/auth.json»]
- `access_token` — JWT; payload содержит `exp` (у текущего токена exp = last_refresh + ~10 дней) и claim `https://api.openai.com/auth` с `chatgpt_plan_type`, `chatgpt_account_id`. [VERIFIED: локальное декодирование payload]
- Refresh делает сам Codex CLI: при `last_refresh` старше 8 дней (`TOKEN_REFRESH_INTERVAL = 8`) или когда JWT `exp` близко. [CITED: codex-rs/login/src/auth/manager.rs:180,2527] CodexBar документирует то же («refresh when last_refresh older than 8 days»). [CITED: steipete/CodexBar docs/codex.md]
- Скрипт-проба НЕ делает refresh (не жечь refresh_token, не гонять OAuth): при 401 — человекочитаемый совет запустить `codex`.

## Field Mapping → Balance (для планировщика)

Текущая модель `Balance` в `codex_balance_widget_chrome.py:194-204` (проценты — ОСТАТОК, всё строки):

| Balance field | JSON source | Преобразование |
|---------------|------------|----------------|
| `five_hour_percent` | окно с `limit_window_seconds == 18000` (искать в `rate_limit.primary_window`, `rate_limit.secondary_window`, затем в `additional_rate_limits[].rate_limit.*`) | `str(100 - used_percent)`; окна может НЕ быть (на plus сейчас его нет) → None + пометка в выводе |
| `weekly_percent` | окно с `limit_window_seconds == 604800` | `str(100 - used_percent)` |
| `credits` | `credits.balance` | строка как есть; показывать с учётом `has_credits`/`unlimited` |
| `five_hour_reset_text` | `reset_at` соответствующего окна | `datetime.fromtimestamp(reset_at)` → локальный текст (формат — на усмотрение пробы, это диагностический скрипт) |
| `weekly_reset_text` | аналогично | — |

**Классификация окон — только по `limit_window_seconds`, никогда по позиции primary/secondary.** Допуск: 5h = 17000–19000 сек, weekly = 600000–610000 сек; иные значения печатать как «неизвестное окно N сек».

## Architecture Patterns

### System Architecture Diagram

```
$CODEX_HOME/auth.json ──read──▶ load_token()
        │                          │ tokens.access_token (+ account_id)
        │                          ▼
        │                   decode_jwt_exp() ──istёк?──▶ warning (но всё равно пробуем)
        │                          │
        │                          ▼
        │              urllib GET chatgpt.com/backend-api/wham/usage
        │                 Authorization: Bearer, ChatGPT-Account-Id
        │                          │
        │            ┌── 200 JSON ─┴─── 401/403/HTML ──▶ human-readable diagnosis, exit 1
        │            ▼
        │      classify_windows(limit_window_seconds)
        │            │
        │            ├──▶ stdout: HTTP-статус, pretty JSON, извлечённые поля / список отсутствующих
        │            └──▶ redact() ──▶ фикстура wham_usage.fixture.json (без token/email/id)
```

### Recommended Project Structure

```
codex_balance_widget/
├── codex_usage_probe.py                      # НОВЫЙ standalone-скрипт (единственный артефакт кода)
├── codex_usage_fixture.json                  # редактированная фикстура (артефакт фазы)
└── codex_balance_widget_chrome.py            # НЕ ТРОГАТЬ [LOCKED]
```

(Имя/размещение фикстуры — Claude's Discretion; допустимо и `.planning/phases/01-json-endpoint-probe/`.)

### Pattern 1: токен из файла CLI + urllib + понятные ошибки
Референс уже в кодовой базе пользователя: `d:\00_Projects\claude_balance_widget_v1\claude_balance_widget.py` строки 240–326 (`_load_token()` / `fetch()`): чтение JSON-файла CLI, `urllib.request.Request(..., headers={Authorization: Bearer ...})`, маппинг 401/403/429/URLError/Timeout в RuntimeError с русским текстом, возврат отсортированного списка ключей payload. Проба должна повторить этот паттерн 1-в-1 (заменив ключи и эндпоинт). [VERIFIED: codebase]

### Pattern 2: редакция фикстуры по именам ключей
Рекурсивный обход JSON; заменять значения ключей из denylist: `user_id`, `account_id`, `email`, `chatgpt_user_id`, любые `*token*`, `session_id`. Дополнительно — пост-проверка сериализованной фикстуры: не содержит `eyJ` (префикс JWT) и `@` (email). Проверено на живом ответе — редактировать есть что. [VERIFIED: live probe]

### Pattern 3: диагностика вместо traceback
Каждый класс ошибки (нет файла auth.json / нет tokens (auth_mode=apikey) / JWT истёк / 401 / 403-JSON / 403-HTML / сеть / таймаут / не-JSON) → одна русская строка + exit code 1. Traceback только с флагом `--debug` (по желанию плана).

### Anti-Patterns to Avoid
- **primary=5h по позиции:** доказанно ложно на этом аккаунте — primary сейчас weekly. Только `limit_window_seconds`.
- **Строгая схема (падать на неизвестном ключе):** в ответе есть поля вне OpenAPI-модели (`promo`, `code_review_rate_limit`, PII) — парсить только нужное, остальное игнорировать; сырьё сохранять в фикстуру.
- **Использовать `id_token` вместо `access_token`:** оба JWT, легко перепутать; API принимает `tokens.access_token`.
- **Refresh токена из пробы:** refresh_token одноразовый у OAuth OpenAI («refresh token was already used» — ошибка в codex) — можно сломать сессию Codex CLI.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth refresh flow | Свой refresh к auth.openai.com | Codex CLI (запустить `codex`) | Одноразовые refresh-токены; риск разлогинить CLI |
| Верификация JWT | Проверку подписи | Только `base64` payload → `exp` | Нужна лишь диагностика срока; подпись не наша забота |
| HTTP-клиент с ретраями/куками | Cloudflare cookie-jar как в codex (`chatgpt_cloudflare_cookies.rs`) | Один GET без кук | Cookie-affinity нужна процессам с постоянным поллингом, не одноразовой пробе |
| Парсер «на все варианты схемы» | Обработку `five_hour`/`percent_left`/`reset_time_ms` и пр. из старых блогов | Каноническую схему выше | Схема подтверждена и исходниками, и живым ответом; вариативные имена из блогов — устаревшая самодеятельность |

**Key insight:** вся «сложность» фазы — не HTTP, а корректная интерпретация окон и гигиена секретов.

## Common Pitfalls

### Pitfall 1: 5-часового окна может не быть вовсе
**What goes wrong:** проба «не находит 5h %» и выглядит сломанной.
**Why it happens:** на plan=plus сейчас приходит только weekly-окно (`primary_window.limit_window_seconds=604800`, `secondary_window=null`). [VERIFIED: live probe]
**How to avoid:** классификация по `limit_window_seconds`; отсутствующее окно — это валидный результат («5h: отсутствует в ответе»), а не ошибка.
**Warning signs:** жёсткие обращения `data["rate_limit"]["primary_window"]` в значении «5h».

### Pitfall 2: PII в ответе → утечка через фикстуру
**What goes wrong:** сырой ответ содержит `email`, `user_id`, `account_id` — коммит фикстуры без редакции = утечка.
**How to avoid:** редакция по denylist ключей + пост-проверка на `eyJ`/`@`; фикстуру писать только редактированную.
**Warning signs:** `json.dump(response, fixture)` без обхода.

### Pitfall 3: nullable-каскад (`double_option`)
**What goes wrong:** `KeyError`/`TypeError` при `rate_limit: null` или отсутствующем ключе.
**Why it happens:** в OpenAPI-модели почти всё `Option<Option<...>>` — поле может отсутствовать ИЛИ быть null. [CITED: rate_limit_status_payload.rs]
**How to avoid:** везде `(d.get("rate_limit") or {})`-стиль (как в claude-виджете, строки 297–300).

### Pitfall 4: единицы `reset_at`
**What goes wrong:** дата «в 1970/56000-х» при делении/умножении на 1000.
**How to avoid:** `reset_at` — секунды epoch (см. Endpoint Contract); блоги про «миллисекунды» относятся к другим полям других версий. `datetime.fromtimestamp(reset_at)` без множителей; sanity-check: 2020 < год < 2100.

### Pitfall 5: 403 HTML от Cloudflare маскируется под ошибку парсинга
**How to avoid:** ветка по `Content-Type`: не-JSON → сообщение «Cloudflare/HTML-ответ», не «битый JSON». В `urllib` тело ошибки читается из `e.read()` у `HTTPError`.

### Pitfall 6: auth_mode=apikey
**What goes wrong:** `tokens` может отсутствовать, если пользователь залогинен API-ключом (`OPENAI_API_KEY` заполнен) — у пробы `KeyError`.
**How to avoid:** явная диагностика: «auth.json без ChatGPT-токенов (auth_mode=apikey). Выполните `codex login` через ChatGPT-аккаунт.» [CITED: AuthDotJson, storage.rs]

### Pitfall 7: Windows-кодировка stdout
**What goes wrong:** `UnicodeEncodeError` на cp1251/cp866 при печати русских строк/символов из JSON через pipe.
**How to avoid:** Python 3.14 использует UTF-8 mode по умолчанию на Windows; но при печати pretty JSON использовать `ensure_ascii=False` осознанно и/или `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.

## Code Examples

### Минимальный проверенный запрос (дословно то, что дало HTTP 200 на этой машине)

```python
# Source: живой запуск 2026-07-17, Python 3.14.5, Windows [VERIFIED]
import json, os, pathlib, urllib.request

codex_home = pathlib.Path(os.environ.get("CODEX_HOME", pathlib.Path.home() / ".codex"))
auth = json.loads((codex_home / "auth.json").read_text(encoding="utf-8"))
tokens = auth.get("tokens") or {}
headers = {
    "Authorization": f"Bearer {tokens['access_token']}",
    "Accept": "application/json",
    "User-Agent": "codex-usage-probe/0.1",
}
if tokens.get("account_id"):
    headers["ChatGPT-Account-Id"] = tokens["account_id"]

req = urllib.request.Request("https://chatgpt.com/backend-api/wham/usage", headers=headers)
with urllib.request.urlopen(req, timeout=15) as resp:
    payload = json.loads(resp.read().decode("utf-8"))
```

### Классификация окон

```python
# Source: выведено из RateLimitWindowSnapshot + живого ответа [VERIFIED]
FIVE_HOURS, WEEK = 5 * 3600, 7 * 24 * 3600

def collect_windows(payload: dict) -> list[dict]:
    out = []
    rl = payload.get("rate_limit") or {}
    for slot in ("primary_window", "secondary_window"):
        w = rl.get(slot)
        if isinstance(w, dict):
            out.append(w)
    for extra in payload.get("additional_rate_limits") or []:
        inner = (extra or {}).get("rate_limit") or {}
        for slot in ("primary_window", "secondary_window"):
            w = inner.get(slot)
            if isinstance(w, dict):
                out.append({**w, "limit_name": extra.get("limit_name")})
    return out

def pick(windows: list[dict], target_seconds: int, tol: int = 1200) -> dict | None:
    for w in windows:
        if abs(int(w.get("limit_window_seconds", -10**9)) - target_seconds) <= tol:
            return w
    return None
# remaining_percent = 100 - w["used_percent"]; reset local = datetime.fromtimestamp(w["reset_at"])
```

### Проверка срока JWT перед запросом

```python
# Source: локально проверено на реальном access_token [VERIFIED]
import base64, json, datetime

def jwt_exp(token: str) -> datetime.datetime | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return datetime.datetime.fromtimestamp(claims["exp"]) if "exp" in claims else None
    except Exception:
        return None
```

### Обработка ошибок (образец — claude-виджет пользователя)

`d:\00_Projects\claude_balance_widget_v1\claude_balance_widget.py:271-295` — готовый шаблон маппинга `HTTPError 401/403/429`, `URLError`, `TimeoutError`, `JSONDecodeError` в русские RuntimeError. Для 403 добавить ветку `Content-Type: text/html` → Cloudflare.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Chrome-скрейпинг страницы Usage (текущий виджет) | `GET /backend-api/wham/usage` c Bearer из auth.json | Codex CLI использует его для `/status` (поллинг ~60с) | Умирают Playwright/Chrome/профиль; источник тот же, что у самого CLI |
| primary=5h, secondary=weekly (старый прайор-арт) | Окна вариативны; на plus сейчас только weekly | Наблюдение 2026-07 [VERIFIED: live probe] | Классификация по длительности окна обязательна |
| Кредиты как число на странице | `credits.balance` (строка) + `rate_limit_reset_credits.available_count` (штучные «ресеты») | — | В UI «credits» теперь два разных понятия; проба печатает оба |

**Deprecated/outdated:** поля `five_hour`/`percent_left`/`reset_time_ms` из старых сниппетов в блогах — в актуальном ответе отсутствуют; не поддерживать.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Когда 5h-окно возвращается, оно имеет ту же форму `RateLimitWindowSnapshot` c `limit_window_seconds=18000` | Field Mapping | Низкий: форма гарантирована OpenAPI-моделью codex; неизвестно лишь точное значение секунд (допуск ±1200 в pick()) |
| A2 | `ChatGPT-Account-Id` обязателен для workspace/team-аккаунтов (на personal подтверждено, что НЕ обязателен) | Endpoint Contract | Низкий: слать заголовок всегда при наличии account_id — безвредно |
| A3 | Cloudflare может отдавать 403 HTML на этот эндпоинт при плохой репутации IP (у codex есть спец. cookie-store, у CodexBar — упоминание interstitial) | Pitfall 5 | Низкий: ветка диагностики просто не сработает никогда |

## Open Questions

1. **Как выглядит ответ при активном 5h-окне (оба окна сразу)?**
   - What we know: модель допускает оба окна; сейчас пришло одно (weekly).
   - What's unclear: появляется ли 5h-окно только под нагрузкой / на pro-плане.
   - Recommendation: проба должна печатать ВСЕ найденные окна с их `limit_window_seconds` — фикстуры с разными состояниями накопятся сами; Phase 2 закладывает «окно может отсутствовать».

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | скрипт | ✓ | 3.14.5 [VERIFIED] | — |
| `~/.codex/auth.json` c `tokens.access_token` | auth | ✓ (auth_mode=chatgpt, last_refresh 2026-07-15, JWT exp 2026-07-25) [VERIFIED] | — | при 401 — запустить `codex` |
| Сеть до chatgpt.com/backend-api | запрос | ✓ (HTTP 200 получен) [VERIFIED] | — | — |
| Внешние pip-пакеты | — | не требуются | — | — |

**Missing dependencies with no fallback:** нет.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | нет (в репо нет tests/ и test-фреймворка); проба — самопроверяющийся скрипт |
| Config file | none — Wave 0 не требуется |
| Quick run command | `python codex_usage_probe.py` |
| Full suite command | `python codex_usage_probe.py` + проверка редакции фикстуры (см. ниже) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROBE-01 | GET возвращает 200 + валидный JSON с `rate_limit` | live smoke | `python codex_usage_probe.py` (exit 0, печатает статус) | ❌ создаётся этой фазой |
| PROBE-02 | Извлечены/помечены отсутствующими: 5h %, weekly %, resets, credits | live smoke | тот же запуск — блок «Extracted fields» в stdout | ❌ |
| PROBE-03 | Фикстура сохранена и НЕ содержит секретов/PII | автопроверка | `python -c "import sys;s=open('codex_usage_fixture.json',encoding='utf-8').read();sys.exit(1 if ('eyJ' in s or '@' in s) else 0)"` | ❌ |
| PROBE-04 | 401/нет файла/apikey-режим → русская диагностика без traceback | manual-only (нельзя безопасно испортить реальный auth.json в автотесте; допустимо `CODEX_HOME=<пустая папка>` для ветки «нет файла») | `CODEX_HOME=%TEMP%\empty python codex_usage_probe.py` → exit 1 + сообщение | ❌ |

### Sampling Rate
- **Per task commit:** `python codex_usage_probe.py`
- **Per wave merge:** тот же запуск + PROBE-03 проверка фикстуры
- **Phase gate:** живой запуск HTTP 200 + фикстура без `eyJ`/`@` перед `/gsd-verify-work`

### Wave 0 Gaps
None — существующая инфраструктура не нужна; сам скрипт и есть тестовый артефакт фазы.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Bearer из auth.json; токен никогда не печатать/не логировать; refresh не делать |
| V3 Session Management | no | одноразовый GET, без сессий/кук |
| V4 Access Control | no | read-only эндпоинт собственного аккаунта |
| V5 Input Validation | yes | defensive-парсинг JSON (`.get() or {}`), проверка Content-Type до `json.loads` |
| V6 Cryptography | yes | JWT только декодировать (base64 payload), подпись не верифицировать и не реализовывать |
| V8 Data Protection | yes | фикстура — только после редакции (`email`, `user_id`, `account_id`, `*token*`); пост-проверка `eyJ`/`@`; auth.json не копировать |

### Known Threat Patterns for stdlib HTTP probe

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Утечка токена в stdout/лог/фикстуру | Information Disclosure | печатать только статус/поля; redact() перед записью; `--debug` не выводит заголовки |
| Утечка PII (email/ids) через git-коммит фикстуры | Information Disclosure | denylist-редакция + автопроверка PROBE-03 |
| Порча сессии Codex CLI | Denial of Service | auth.json открывать read-only, refresh_token не использовать |

## Project Constraints (from CLAUDE.md)

`./CLAUDE.md` в проекте отсутствует — проектных директив нет. Глобальные инструкции пользователя не содержат ограничений, релевантных фазе.

## Sources

### Primary (HIGH confidence)
- **Живой запрос с этой машины, 2026-07-17** — HTTP 200 схема; минимальные заголовки (только Bearer, дефолтный UA); 401-тело; JWT-claims; структура auth.json. [VERIFIED]
- github.com/openai/codex, `codex-rs/backend-client/src/client/rate_limit_resets.rs` — URL `{base}/wham/usage`
- github.com/openai/codex, `codex-rs/codex-backend-openapi-models/src/models/{rate_limit_status_payload,rate_limit_status_details,rate_limit_window_snapshot,credit_status_details,additional_rate_limit_details}.rs` — полная типизация ответа
- github.com/openai/codex, `codex-rs/protocol/src/protocol.rs` — `reset_at` = unix-секунды; `codex-rs/backend-client/src/client.rs` — `headers()` (UA, ChatGPT-Account-Id, X-OpenAI-Fedramp)
- github.com/openai/codex, `codex-rs/login/src/auth/{storage.rs,manager.rs,token_data.rs}` — AuthDotJson/TokenData, `TOKEN_REFRESH_INTERVAL=8` дней, `$CODEX_HOME`
- `d:\00_Projects\claude_balance_widget_v1\claude_balance_widget.py:240-326` — референс-паттерн клиента
- `codex_balance_widget_chrome.py:194-204,504-565` — целевая модель Balance (remaining-проценты, строки)

### Secondary (MEDIUM confidence)
- github.com/steipete/CodexBar `docs/codex.md` — refresh «older than 8 days», Cloudflare interstitial, primary/secondary→session/weekly lanes
- github.com/7shi/codex-oauth — ChatGPT-Account-Id, refresh endpoint auth.openai.com/oauth/token, CLIENT_ID
- knightli.com/en/2026/04/12/codex-usage-quota-check — Python-скрипт: tokens.access_token + tokens.account_id, семантика 401/403

### Tertiary (LOW confidence)
- github.com/openai/codex issue #10869 — только факт поллинга ~60с и цепочка вызовов (детали схемы там отсутствуют)

## Metadata

**Confidence breakdown:**
- Endpoint contract / схема: HIGH — живой ответ + генерированные модели из репо codex совпали
- auth.json / refresh: HIGH — локальный файл + исходники codex
- Поведение при 5h-окне: MEDIUM — на этом аккаунте окно отсутствует; форма гарантирована моделью (A1)
- Cloudflare-риски: MEDIUM — токен-путь работает; HTML-403 не воспроизведён (A3)

**Research date:** 2026-07-17
**Valid until:** ~2026-08-16 (внутренний эндпоинт; при смене схемы проба сама покажет diff через фикстуру)
