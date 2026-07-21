# Phase 1: JSON endpoint probe - Pattern Map

**Mapped:** 2026-07-17
**Files analyzed:** 3 новых файла (0 модификаций — `codex_balance_widget_chrome.py` [LOCKED])
**Analogs found:** 2 / 3 (фикстура — артефакт данных, аналога кода не требует; редакция секретов и JWT-декодирование — без аналога, паттерны из RESEARCH.md)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `codex_usage_probe.py` | standalone CLI utility (HTTP-клиент + диагностика) | request-response + file-I/O (auth.json чтение, фикстура запись) | `d:\00_Projects\claude_balance_widget_v1\claude_balance_widget.py` (`ClaudeUsageClient._load_token` / `fetch`) | exact (та же модель «токен из файла CLI + urllib GET + русские ошибки») |
| `test_codex_usage_probe.py` (или stdlib unittest-файл) | test | batch (чистые функции, без сети) | `d:\00_Projects\claude_balance_widget_v1\test_core.py` | role-match (там flat-assert скрипт; допустимо повторить или поднять до `unittest`) |
| `codex_usage_fixture.json` | config/data artifact (редактированный сырой ответ) | file-I/O (пишется пробой) | — | n/a — генерируется скриптом, кода не содержит |

**Reference-only (НЕ изменять):** `D:\00_Projects\codex_balance_widget\codex_balance_widget_chrome.py` — целевая модель `Balance`, на которую проба мапит поля JSON.

## Pattern Assignments

### `codex_usage_probe.py` (CLI utility, request-response)

**Analog:** `d:\00_Projects\claude_balance_widget_v1\claude_balance_widget.py` — рабочий клиент того же класса задач (недокументированный usage-эндпоинт + OAuth-токен из файла CLI). Копировать структуру 1-в-1, заменив пути/ключи/эндпоинт.

**Imports pattern** (`claude_balance_widget.py:9-25`, взять только нужное подмножество):
```python
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
```
Для пробы добавить stdlib: `base64` (JWT payload), `sys` (exit code, `stdout.reconfigure`), опционально `argparse`. Внешних пакетов нет — как в аналоге, `urllib`, не `requests`.

**Чтение токена из файла CLI** (`claude_balance_widget.py:240-256`, метод `_load_token`):
```python
def _load_token(self) -> str:
    try:
        data = json.loads(self.credentials_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Не найден файл авторизации Claude Code. Откройте Claude Code и выполните вход."
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Не удалось прочитать файл авторизации Claude Code.") from exc

    oauth = data.get("claudeAiOauth")
    token = oauth.get("accessToken") if isinstance(oauth, dict) else None
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError(
            "OAuth-токен Claude Code не найден. Откройте Claude Code и обновите вход."
        )
    return token.strip()
```
Адаптация для пробы: путь = `Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json"`; ключи = `data.get("tokens")` → `access_token` (+ `account_id` для заголовка `ChatGPT-Account-Id`); отдельная ветка «`tokens` отсутствует при `auth_mode=apikey`» → совет `codex login` (RESEARCH.md, Pitfall 6). Тексты ошибок — про Codex CLI, не Claude Code.

**HTTP GET с Bearer + маппинг ошибок в русские RuntimeError** (`claude_balance_widget.py:258-295`, метод `fetch` — ядро паттерна):
```python
def fetch(self) -> tuple[Balance, int, list[str]]:
    token = self._load_token()
    request = urllib.request.Request(
        API_URL,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": API_BETA_HEADER,
            "Accept": "application/json",
            "User-Agent": f"claude-balance-widget/{APP_VERSION}",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status = int(getattr(response, "status", 200))
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError(
                "Авторизация Claude Code истекла. Откройте Claude Code и обновите вход."
            ) from exc
        if exc.code == 403:
            raise RuntimeError("Anthropic не разрешил доступ к данным лимитов.") from exc
        if exc.code == 429:
            raise RuntimeError("Слишком много запросов к Anthropic. Повторите позже.") from exc
        raise RuntimeError(f"Anthropic вернул HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Нет соединения с Anthropic: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("Anthropic не ответил вовремя.") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ответ Anthropic не удалось разобрать.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Anthropic вернул данные неожиданного формата.")
```
Адаптация: URL = `https://chatgpt.com/backend-api/wham/usage`; заголовок `anthropic-beta` заменить на `ChatGPT-Account-Id` (слать, когда `tokens.account_id` есть); в ветке 403 добавить проверку `Content-Type` (`exc.headers.get("Content-Type")`, тело из `exc.read()`) — HTML → диагностика «Cloudflare-заслон», JSON → подсказка про Account-Id (RESEARCH.md, Endpoint Contract / Pitfall 5); текст 401 → «Токен Codex истёк. Запустите `codex` … и повторите.»

**Defensive-парсинг nullable-полей** (`claude_balance_widget.py:297-305` — тот же стиль обязателен для `rate_limit`/`credits`, см. Pitfall 3):
```python
five = payload.get("five_hour")
week = payload.get("seven_day")
five = five if isinstance(five, dict) else {}
week = week if isinstance(week, dict) else {}

five_used = clamp_percent(five.get("utilization"))
week_used = clamp_percent(week.get("utilization"))
five_remaining = round(100.0 - five_used, 2) if five_used is not None else None
week_remaining = round(100.0 - week_used, 2) if week_used is not None else None
```
Адаптация: та же семантика «remaining = 100 - used», но окна классифицировать по `limit_window_seconds` (18000 → 5h, 604800 → weekly), НИКОГДА по позиции primary/secondary — готовые `collect_windows()`/`pick()` в RESEARCH.md, раздел Code Examples. Отсутствующее окно — валидный результат, а не ошибка.

**Валидация процентов** (`claude_balance_widget.py:135-146`, `clamp_percent`/`format_percent` — включая вывод «не найдено» для None):
```python
def clamp_percent(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(max(0.0, min(100.0, float(value))), 2)

def format_percent(value: float | None) -> str:
    if value is None:
        return "не найдено"
    ...
```

**Точка входа / exit code:** аналог `fetch()` бросает `RuntimeError` — проба оборачивает верхним уровнем: `main()` → `try: ... except RuntimeError as exc: print(exc); sys.exit(1)`. Traceback только под `--debug` (RESEARCH.md, Pattern 3). В аналогах прямого образца нет (у них GUI-main) — это единственная новая склейка.

---

### Целевая модель полей — `codex_balance_widget_chrome.py` (reference-only, [LOCKED])

Проба печатает «Extracted fields» в терминах этой модели; Phase 2 будет заполнять именно её.

**`Balance` dataclass** (`codex_balance_widget_chrome.py:194-204`) — все значения строки, проценты = ОСТАТОК:
```python
@dataclass
class Balance:
    five_hour_percent: str | None = None
    weekly_percent: str | None = None
    credits: str | None = None
    five_hour_reset_text: str | None = None
    weekly_reset_text: str | None = None

    @property
    def has_usage_data(self) -> bool:
        return any([self.five_hour_percent, self.weekly_percent, self.credits])
```
Маппинг JSON → Balance (таблица «Field Mapping → Balance» в RESEARCH.md): `str(100 - used_percent)` для процентов; `credits.balance` (уже строка); `reset_at` (unix-СЕКУНДЫ) → `datetime.fromtimestamp(reset_at)` → локальный текст.

**Нормализация процентов на стороне виджета** (`codex_balance_widget_chrome.py:292-299`, `safe_int` — показывает, что виджет ждёт строку, конвертируемую в int 0..100):
```python
def safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return None
    return max(0, min(100, parsed))
```

**`parse_iso_datetime`** (`codex_balance_widget_chrome.py:830-836`) — стиль «None вместо исключения» для дат; пробе НЕ подходит напрямую (там ISO-строки, у `wham/usage` — epoch-секунды), но копировать сам стиль tolerant-парсинга:
```python
def parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
```

**`BalanceParser.parse`** (`codex_balance_widget_chrome.py:504-565`) — справочно: показывает, какие сущности виджет извлекает сегодня из текста страницы (5h %, weekly %, credits, два reset-текста). Проба должна выдать ровно тот же набор из JSON.

---

### `test_codex_usage_probe.py` (test, batch)

**Analog:** `d:\00_Projects\claude_balance_widget_v1\test_core.py` (файл целиком, 22 строки) — единственный тестовый файл в обеих кодовых базах:
```python
from datetime import datetime
from claude_balance_widget import (
    Balance,
    clamp_percent,
    format_compact_countdown,
    format_percent,
)

assert clamp_percent(101) == 100.0
assert clamp_percent(-1) == 0.0
assert format_percent(34.0) == "34%"
assert format_percent(34.5) == "34.5%"

b = Balance(five_hour_remaining=34, weekly_remaining=41)
assert b.available is True
...
print("Core tests passed.")
```
**Паттерн:** импортировать чистые функции из модуля пробы и гонять их на данных без сети. В репо нет тест-фреймворка (RESEARCH.md, Validation Architecture) — допустимо повторить flat-assert стиль аналога или оформить как `unittest.TestCase` (`python -m unittest test_codex_usage_probe`); оба варианта stdlib-only. Тестировать на фикстурных dict'ах: `collect_windows`/`pick` (оба окна / только weekly / `rate_limit: null` / `additional_rate_limits`), `redact` (после редакции нет `eyJ` и `@`), `jwt_exp` (битый токен → None), маппинг `used_percent` → remaining-строка. Живой HTTP в тесты не тянуть — это smoke-запуск самой пробы (PROBE-01/02).

---

## Shared Patterns

### Русская диагностика вместо traceback
**Source:** `claude_balance_widget.py:271-295` (каждый класс ошибки → одна русская строка через `RuntimeError(...) from exc`)
**Apply to:** все ветки ошибок пробы (нет auth.json / apikey-режим / JWT истёк / 401 / 403-JSON / 403-HTML / URLError / Timeout / не-JSON). Полная таблица статусов и текстов — RESEARCH.md, «Семантика ошибок».

### Гигиена токена
**Source:** `claude_balance_widget.py:1-7` (докстринг: «token … is never printed or written to logs») + весь `fetch()` — токен живёт только в заголовке.
**Apply to:** проба не печатает токен/заголовки даже в `--debug`; фикстура пишется только после `redact()`.

### Defensive `.get() or {}` для nullable-каскадов
**Source:** `claude_balance_widget.py:297-300`
**Apply to:** каждый доступ к `rate_limit`, `credits`, `additional_rate_limits`, `spend_control` (почти всё в схеме `Option<Option<...>>`).

### Опциональный файловый лог
**Source:** `codex_balance_widget_chrome.py:214-220` (`write_log`: timestamp + append, `except OSError: pass`)
**Apply to:** только если план захочет лог пробы; для диагностического скрипта достаточно stdout.

## No Analog Found

Файлы/куски без близкого аналога в кодовой базе — планировщику брать готовые сниппеты из RESEARCH.md (раздел Code Examples, все [VERIFIED]):

| Кусок | Role | Data Flow | Reason / Source |
|-------|------|-----------|-----------------|
| `redact()` + пост-проверка `eyJ`/`@` перед записью фикстуры | utility | transform | Ни один из виджетов не сохраняет сырые ответы; паттерн — RESEARCH.md Pattern 2 |
| `jwt_exp()` (base64-декодирование payload) | utility | transform | В кодовой базе JWT нигде не разбирается; готовый сниппет — RESEARCH.md «Проверка срока JWT» |
| `collect_windows()`/`pick()` (классификация окон по `limit_window_seconds`) | utility | transform | Уникально для схемы `wham/usage`; сниппет — RESEARCH.md «Классификация окон» |
| `codex_usage_fixture.json` | data artifact | file-I/O | Генерируется пробой; формат = редактированный JSON-ответ из Endpoint Contract |
| CLI-обвязка (`argparse`/`sys.exit(1)`) | config | request-response | У аналогов GUI-main; тривиальный stdlib-паттерн |

## Metadata

**Analog search scope:** `D:\00_Projects\codex_balance_widget` (1 py-файл), `d:\00_Projects\claude_balance_widget_v1` (2 py-файла)
**Files scanned:** 3 (все py-файлы обеих кодовых баз; проектного CLAUDE.md и `.claude/skills/` нет)
**Pattern extraction date:** 2026-07-17
