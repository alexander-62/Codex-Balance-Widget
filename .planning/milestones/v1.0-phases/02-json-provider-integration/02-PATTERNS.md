# Phase 2: JSON provider integration - Pattern Map

**Mapped:** 2026-07-20
**Files analyzed:** 6 (1 new module, 1 new/extended test file, 4 modification points inside `codex_balance_widget_chrome.py`)
**Analogs found:** 5 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| new JSON provider module (name TBD by planner, e.g. `json_usage_provider.py`) | service | request-response | `probe_wham_usage.py` (whole module) | exact (reuse target, same repo, same endpoint) |
| new JSON provider module — provider-object shape (`fetch()` + `set_status` callback) | service | request-response w/ fallback | `CodexUsageBrowser` class, `codex_balance_widget_chrome.py:839-857` | role-match |
| `codex_balance_widget_chrome.py` — `fetch_once` (lines 2073-2119) | controller (async orchestrator) | request-response w/ retry+fallback | itself (existing fallback shape) + `CodexUsageBrowser.fetch()` (839-857) | exact (extend in place) |
| `codex_balance_widget_chrome.py` — new retry wrapper for 429/URLError/timeout (D-03) | utility | request-response w/ retry | *(none — see "No Analog Found")* | partial (build from `fetch_usage` error classification) |
| `codex_balance_widget_chrome.py` — `write_log` call sites for `source: json\|chrome` (near D-05) | utility (logging call site) | event-driven (log write) | `write_log` itself (214-220) + existing call sites (850-853, 896, 899) | exact |
| JSON→`Balance` glue (map `extract_fields()` dict onto `Balance` dataclass) | transform | transform | `BalanceParser.parse()` return statement, `codex_balance_widget_chrome.py:559-565` | role-match |
| new/extended test file (e.g. `test_json_usage_provider.py` or extend `test_probe_wham_usage.py`) | test | request-response (mocked) | `test_probe_wham_usage.py` (whole file, 247 lines) | exact |

## Pattern Assignments

### New JSON provider module (service, request-response)

**Primary analog:** `D:\00_Projects\codex_balance_widget\probe_wham_usage.py` — this is the reuse target named explicitly in CONTEXT.md's Claude's Discretion. It is stdlib-only, already tested (23 green tests), and already produces exactly the fields `Balance` needs.

**Reusable functions to import or copy** (whole file is 399 lines, already read in full):

- `auth_json_path()` (lines 55-58) — resolves `$CODEX_HOME/auth.json`.
- `load_tokens(path)` (lines 61-102) — reads `tokens.access_token` + optional `account_id`, raises `ProbeError` with Russian diagnostics on every failure branch (missing file, unreadable, apikey-only auth_mode, missing/empty token). Never touches `refresh_token`.
- `jwt_exp(token)` (lines 105-118) — decodes JWT `exp` claim without verifying; returns `None` on any parse error (used only for a warning print, not blocking behavior — matches D-04: widget never waits on token refresh).
- `collect_windows(payload)` / `pick_window(windows, target_seconds)` (lines 121-154) — classify rate-limit windows strictly by `limit_window_seconds`, never by primary/secondary position.
- `extract_fields(payload)` (lines 191-220) — maps raw payload onto the exact `Balance` field names (`five_hour_percent`, `weekly_percent`, `credits`, `five_hour_reset_text`, `weekly_reset_text`) plus a `windows` list and `missing` list.
- `redact(obj)` / `redaction_clean(text)` (lines 223-245) — for any logging of raw payload content (keep tokens out of logs, matching existing widget security bar).
- `build_headers(access_token, account_id)` (lines 248-257) — `Authorization: Bearer`, `Accept: application/json`, `ChatGPT-Account-Id` header when present.
- `fetch_usage(access_token, account_id, timeout)` (lines 260-321) — **the core HTTP call and error classification to reuse directly.** Maps every failure branch to a `ProbeError` with a Russian message:

```python
# probe_wham_usage.py:277-309 — error classification (exact code to reuse/adapt)
except urllib.error.HTTPError as exc:
    ...
    if exc.code == 401:
        raise ProbeError(
            "Токен Codex истёк или недействителен (HTTP 401). Запустите "
            "любую команду codex — CLI обновит auth.json — и повторите."
        ) from exc
    if exc.code == 403:
        if "html" in error_content_type.lower():
            snippet = body.decode("utf-8", errors="replace")[:200]
            raise ProbeError(
                "Cloudflare-заслон (HTTP 403, HTML). Повторите позже.\n"
                f"{snippet}"
            ) from exc
        raise ProbeError(
            "Доступ запрещён (HTTP 403). Проверьте ChatGPT-Account-Id и "
            "доступность эндпоинта wham/usage для этого аккаунта."
        ) from exc
    if exc.code == 429:
        raise ProbeError("Слишком много запросов (HTTP 429). Повторите позже.") from exc
    raise ProbeError(f"wham/usage вернул HTTP {exc.code}.") from exc
except urllib.error.URLError as exc:
    raise ProbeError(f"Нет соединения с chatgpt.com: {exc.reason}") from exc
except TimeoutError as exc:
    raise ProbeError(f"chatgpt.com не ответил за {timeout} с.") from exc
```

This classification already lines up exactly with CONTEXT.md's D-02/D-03 decision table (401/403 → no retry → fallback; 429/URLError/timeout → one retry). The provider only needs a thin retry wrapper around this call (see "No Analog Found" below) — the classification itself does not need to change.

**Structural analog (provider-object shape):** `CodexUsageBrowser` class, `codex_balance_widget_chrome.py:839-857`

```python
# codex_balance_widget_chrome.py:839-857
class CodexUsageBrowser:
    def __init__(self, chrome_path: str, set_status):
        self.chrome_path = chrome_path
        self.set_status = set_status

    async def fetch(self) -> FetchResult:
        if has_saved_chrome_session():
            self.set_status("Обновляю в фоновом Chrome...")
            background_result = await self._fetch_once(visible=False, wait_for_login=False)
            if background_result.status == "ok":
                return background_result
            write_log(
                f"Background fetch did not complete: {background_result.status} "
                f"{background_result.error or ''}"
            )

        self.set_status("Открою Chrome для входа или проверки сессии...")
        return await self._fetch_once(visible=True, wait_for_login=True)
```

This is the pattern to copy for "try primary path, log on failure, fall through to secondary path" — the JSON→Chrome fallback in `fetch_once` should mirror this "try, log, fall through" shape (JSON is primary now instead of the background-Chrome attempt). Returning a `FetchResult`-like object (status/text/error) or directly a `Balance` is a decision point for the planner — see `FetchResult` dataclass at `codex_balance_widget_chrome.py:207-211`.

**Secondary cross-project reference:** `d:\00_Projects\claude_balance_widget_v1\claude_balance_widget.py:240-326` (`_load_token()` / `fetch()`) — same "token from CLI-managed JSON file → Bearer header → urllib request → typed dataclass" shape for a structurally identical widget. `probe_wham_usage.py` was already built from this template (per CONTEXT.md), so treat this file as tertiary/historical reference only if `probe_wham_usage.py` needs extending in a way that has no direct precedent there.

```python
# claude_balance_widget.py:240-256 — token load with Russian diagnostics (compare shape to load_tokens above)
def _load_token(self) -> str:
    try:
        data = json.loads(self.credentials_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Не найден файл авторизации Claude Code. Откройте Claude Code и выполните вход."
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Не удалось прочитать файл авторизации Claude Code.") from exc
    ...
```

---

### `codex_balance_widget_chrome.py` — `fetch_once` (controller, request-response w/ retry+fallback)

**Analog:** itself, lines 2073-2119 (extend in place — do not rewrite from scratch)

```python
# codex_balance_widget_chrome.py:2073-2119 — current shape to extend
async def fetch_once(self) -> None:
    if self.refresh_in_progress:
        self.set_status(tr(self.language, "Refresh already in progress...", "Обновление уже идет..."))
        return

    self.refresh_in_progress = True
    try:
        if not self.browser:
            self.last_fetch_status = "chrome_not_found"
            self.last_fetch_error = tr(self.language, "Google Chrome not found", "Google Chrome не найден")
            self.set_status(tr(self.language, "Google Chrome not found. Set CHROME_PATH.", "Google Chrome не найден. Укажите CHROME_PATH."))
            return

        result = await self.browser.fetch()
        self.last_fetch_status = result.status
        self.last_fetch_error = result.error
        self.last_usage_text_length = len(result.text) if result.text else None
        if result.status != "ok" or not result.text:
            if self.current_balance.has_usage_data:
                self.set_status(tr(self.language, "Showing last saved data · refresh failed", "Показаны последние данные · обновить не удалось"))
            elif result.status == "browser_error":
                self.set_status(tr(self.language, "Chrome failed to start. See widget_launch.log", "Chrome не запустился. Подробности в widget_launch.log"))
            elif result.status == "login_required":
                self.set_status(tr(self.language, "Sign in to ChatGPT. Click Refresh to open Chrome.", "Нужен вход в ChatGPT. Нажмите Обновить, чтобы открыть Chrome."))
            else:
                self.set_status(tr(self.language, "Usage data timed out. Click Refresh.", "Не дождался данных Usage. Нажмите Обновить."))
            return

        balance = BalanceParser.parse(result.text)
        if balance.has_usage_data:
            self.last_successful_update = datetime.now()
            self.update_balance_ui(balance)
            if is_weekly_limit_exhausted(balance):
                self.set_status(tr(self.language, "Codex unavailable: weekly limit exhausted", "Codex недоступен: недельный лимит исчерпан"))
            else:
                self.set_status(tr(self.language, "Data is up to date", "Данные актуальны"))
        elif self.current_balance.has_usage_data:
            self.set_status(tr(self.language, "Showing last saved data · new data not recognized", "Показаны последние данные · новые не распознаны"))
        else:
            self.set_status(tr(self.language, "Data not recognized", "Данные не распознаны"))
    finally:
        self.refresh_in_progress = False
```

**Key patterns to preserve/reuse:**
- `refresh_in_progress` guard (lines 2074-2076) — must stay first, applies equally to JSON attempts.
- **"Keep last data on screen" UX gate** (line 2091, `self.current_balance.has_usage_data`) — CONTEXT.md explicitly requires preserving this for the JSON path too.
- `tr(self.language, en, ru)` bilingual status strings — every new status message (e.g. Chrome-fallback indicator per D-05) must use this helper, not raw strings.
- `try/finally` around `self.refresh_in_progress = False` — must wrap the new JSON-then-Chrome sequence, not just the Chrome call.
- Integration point: `result = await self.browser.fetch()` (line 2086) is exactly where the JSON attempt is inserted first, with Chrome as the `else` branch — mirrors the "try, log, fall through" shape already used inside `CodexUsageBrowser.fetch()` above.

---

### `codex_balance_widget_chrome.py` — retry wrapper (429 / URLError / timeout, D-03)

**No close analog exists in the codebase** — no retry loop is present anywhere in `codex_balance_widget_chrome.py` or `probe_wham_usage.py`. Build this from the existing error classification in `fetch_usage` (lines 260-321, excerpted above), which already separates 401/403 (no-retry) from 429/URLError/timeout (retry-eligible) via distinct `ProbeError` raise sites. The wrapper is a thin loop: catch the retry-eligible `ProbeError` subclasses/markers once, sleep briefly, call `fetch_usage` a second time, then let any subsequent failure (including a second retry-eligible one) fall through to Chrome fallback. Since `probe_wham_usage.ProbeError` collapses all failures into one exception type with only the message differing, the planner will need either (a) a lightweight marker (e.g. a `retryable: bool` attribute set at each raise site) or (b) matching on the HTTP status code before `fetch_usage` raises, to distinguish "retry once" from "fallback immediately" per D-02/D-03.

---

### `codex_balance_widget_chrome.py` — `write_log` source logging (utility, event-driven)

**Analog:** `write_log` definition + existing call sites

```python
# codex_balance_widget_chrome.py:214-220 — logger to reuse as-is (no change needed)
def write_log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass
```

```python
# codex_balance_widget_chrome.py:850-853 — existing call-site style to copy for "fallback happened" logging
write_log(
    f"Background fetch did not complete: {background_result.status} "
    f"{background_result.error or ''}"
)
```

CONTEXT.md's Claude's Discretion leaves the exact log line wording open; match this call-site style (`write_log(f"...")`, single line, no structured logging framework) and land the `source: json` / `source: chrome` marker on every successful update inside `fetch_once`, right where `self.last_successful_update = datetime.now()` is currently set (line 2103).

---

### JSON→`Balance` glue (transform)

**Analog:** `BalanceParser.parse()` return statement, `codex_balance_widget_chrome.py:559-565`

```python
# codex_balance_widget_chrome.py:559-565 — exact Balance(...) constructor shape to match
return Balance(
    five_hour_percent=five_hour,
    weekly_percent=weekly,
    credits=credits,
    five_hour_reset_text=normalize_reset_text(five_hour_reset),
    weekly_reset_text=normalize_reset_text(weekly_reset),
)
```

`probe_wham_usage.extract_fields()` (lines 191-220) already returns a dict keyed with these exact field names (`five_hour_percent`, `weekly_percent`, `credits`, `five_hour_reset_text`, `weekly_reset_text`), so the glue is a direct `Balance(**{k: v for k, v in fields.items() if k in Balance.__dataclass_fields__})` or explicit keyword mapping — no text parsing/regex needed (unlike `BalanceParser`, which parses rendered HTML text). Note `extract_fields` does **not** call `normalize_reset_text()` on its reset strings — it uses its own `_reset_text()` helper (lines 157-166) that formats via `strftime("%Y-%m-%d %H:%M")`. The planner must confirm whether `Balance.five_hour_reset_text` / `weekly_reset_text` downstream consumers (e.g. `parse_reset_datetime`, `format_countdown` used at lines 1652/1661/1674/1678) expect the `BalanceParser`-style "Сброс ..." prefix format or can accept the raw `extract_fields` format — this is a format-compatibility question, not a pattern gap.

---

### Test file (test, request-response mocked)

**Analog:** `D:\00_Projects\codex_balance_widget\test_probe_wham_usage.py` (whole file, 247 lines)

```python
# test_probe_wham_usage.py:1-27 — header + JWT-fixture-builder pattern to copy
"""Unit tests for probe_wham_usage.py core functions.

Stdlib unittest only. No network access, no reading of the real
~/.codex/auth.json — all cases use inline dict fixtures and
tempfile.TemporaryDirectory.
"""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import probe_wham_usage


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(claims: dict) -> str:
    header = _b64url(json.dumps({"alg": "none"}).encode("utf-8"))
    payload = _b64url(json.dumps(claims).encode("utf-8"))
    return f"{header}.{payload}.sig"
```

Conventions to copy: stdlib `unittest` (no pytest, no mocking framework beyond stdlib), no real network access, no reads of the real `~/.codex/auth.json`, inline dict payload fixtures, `tempfile.TemporaryDirectory()` for any file-path-dependent test (e.g. `load_tokens`), one `TestXxx(unittest.TestCase)` class per function-group (`TestWindows`, etc. — see lines 30+). If the new provider module is a thin wrapper around `probe_wham_usage` functions, extending `test_probe_wham_usage.py` directly may be simpler than a new file; if it has new retry/fallback logic of its own, a new `test_json_usage_provider.py` following the same header/fixture conventions is cleaner — planner's call per CONTEXT.md's "no unnecessary abstraction" spirit.

---

## Shared Patterns

### Russian human-readable error diagnostics (no traceback)
**Source:** `probe_wham_usage.py` `ProbeError` class (lines 51-52) and every raise site in `fetch_usage` (260-321)
**Apply to:** the new JSON provider module — every failure branch (missing token, HTTP 401/403/429/other, URLError, timeout, non-JSON content-type, malformed JSON) must produce exactly one Russian-language message, matching the existing tone/style, and must never leak the Bearer token.

### Bilingual status strings via `tr()`
**Source:** used throughout `fetch_once` (e.g. `codex_balance_widget_chrome.py:2075`, `2083`, `2092`, `2094`, `2096`, `2098`, `2106`, `2108`, `2110`, `2112`)
```python
tr(self.language, "Showing last saved data · refresh failed", "Показаны последние данные · обновить не удалось")
```
**Apply to:** any new status message shown during JSON attempt, retry, or Chrome-fallback (D-05 requires a fallback-only status marker, e.g. "Chrome-фолбэк").

### "Keep last data on screen when refresh fails" gate
**Source:** `self.current_balance.has_usage_data` check, `codex_balance_widget_chrome.py:2091` and `2109`
**Apply to:** both the JSON-attempt failure branch and the Chrome-fallback failure branch inside the extended `fetch_once` — this UX guarantee must hold for both paths per CONTEXT.md's Established Patterns section.

### "Try primary, log, fall through to secondary" control flow
**Source:** `CodexUsageBrowser.fetch()`, `codex_balance_widget_chrome.py:844-856`
**Apply to:** the top of the extended `fetch_once` — JSON is the new "primary" (was: background Chrome), existing full Chrome flow (`self.browser.fetch()`) becomes the "secondary" fallback, matching D-01/D-02/D-03's fallback triggers (401/403 → immediate fallback, 429/URLError/timeout → one retry then fallback).

### Async method wrapping a blocking stdlib HTTP call
**Gap — no existing pattern in this codebase.** `fetch_once` and `CodexUsageBrowser.fetch()` are `async def`, but `probe_wham_usage.fetch_usage()` uses blocking `urllib.request.urlopen`. There is no existing `asyncio.to_thread` / `run_in_executor` usage anywhere in `codex_balance_widget_chrome.py` (confirmed via full-file grep). The planner should wrap the JSON provider's blocking call (e.g. `await asyncio.to_thread(fetch_usage, access_token, account_id, timeout)`) to avoid blocking the Tk/asyncio event loop that also drives the UI and the Chrome path — flag this explicitly in the relevant plan since there is no in-repo precedent to copy verbatim.

## No Analog Found

| File / Concern | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Retry wrapper for 429/URLError/timeout (D-03) | utility | request-response w/ retry | No retry loop exists anywhere in the codebase; build from `fetch_usage`'s existing per-status-code error classification (see Pattern Assignments above) rather than a copied analog. |
| Async-wrapping of a blocking urllib call | utility/glue | request-response | No `asyncio.to_thread`/`run_in_executor` usage exists in `codex_balance_widget_chrome.py`; this is new territory for the codebase (see Shared Patterns gap above). |

## Metadata

**Analog search scope:** `D:\00_Projects\codex_balance_widget\` (all `.py` files: `codex_balance_widget_chrome.py`, `probe_wham_usage.py`, `test_probe_wham_usage.py`) and `d:\00_Projects\claude_balance_widget_v1\claude_balance_widget.py` (explicit cross-project reference named in CONTEXT.md canonical_refs).
**Files scanned:** 4 (3 in-repo, 1 cross-project reference)
**Pattern extraction date:** 2026-07-20
