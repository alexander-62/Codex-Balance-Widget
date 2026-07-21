---
phase: 02-json-provider-integration
reviewed: 2026-07-21T06:48:11Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - codex_balance_widget_chrome.py
  - json_usage_provider.py
  - probe_wham_usage.py
  - test_codex_balance_widget_chrome.py
  - test_json_usage_provider.py
  - test_probe_wham_usage.py
findings:
  critical: 2
  warning: 2
  info: 2
  total: 6
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-07-21T06:48:11Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the JSON-provider integration (`json_usage_provider.py`, `probe_wham_usage.py`'s
`retryable` addition, and the `plan_fetch_outcome`/`fetch_once` rewiring in
`codex_balance_widget_chrome.py`) plus the accompanying unit tests, against the diff
range `de7df17b50186c43b47cb00858ee518c56c0997b^..HEAD`.

The retry policy for transient JSON errors (D-02/D-03 in `02-CONTEXT.md`) is implemented
correctly and is well covered by tests. However, the integration introduces two
correctness/robustness regressions relative to the pre-existing Chrome-only flow:

1. The new JSON "success" branch in `plan_fetch_outcome` never validates that the
   parsed `Balance` actually contains usage data — unlike the Chrome branch a few lines
   below it, which explicitly does. A structurally valid but empty/unexpected JSON
   response (e.g. `{}`, or a schema change) is treated as a fully successful update and
   silently overwrites the last-known-good balance shown in the UI, without ever
   attempting the Chrome fallback. This breaks the "keep last good data on failure" UX
   guarantee the codebase otherwise maintains everywhere else.
2. `JsonUsageProvider._fetch_with_retry` only catches `probe_wham_usage.ProbeError`.
   Several realistic failure modes inside `fetch_usage`/`extract_fields` (non-UTF-8
   response bodies, a non-dict `additional_rate_limits` entry, a connection reset during
   `response.read()`) raise exceptions that are *not* `ProbeError`. Because
   `CodexBalanceWidget.refresh_loop()` has no exception handling around
   `await self.fetch_once()`, any such exception permanently kills the periodic
   auto-refresh task for the rest of the process lifetime, with no visible error to the
   user (only a swallowed "exception was never retrieved" on the abandoned asyncio
   task).

Both are concrete, provable defects introduced by this phase's changes (not pre-existing
Phase-1 code). See below for details and fixes.

## Critical Issues

### CR-01: JSON "ok" success path skips `has_usage_data` validation, silently clobbering last-known-good balance

**File:** `codex_balance_widget_chrome.py:558-564`
**Issue:**
```python
if json_status == "ok":
    balance = build_balance_from_json_fields(json_fields or {})
    if is_weekly_limit_exhausted(balance):
        message = tr(language, "Codex unavailable: weekly limit exhausted", ...)
    else:
        message = tr(language, "Data is up to date", "Данные актуальны")
    return FetchOutcome("json", balance, message, "Balance updated (source: json)")
```
Unlike the Chrome branch a few lines further down (`if balance.has_usage_data: ... else: ...`
at `codex_balance_widget_chrome.py:576-586`), this branch never checks
`balance.has_usage_data` (or `json_fields.get("missing")`, which
`probe_wham_usage.extract_fields` already computes for exactly this purpose — see
`probe_wham_usage.py:219-228`). `json_usage_provider.JsonUsageProvider.fetch()` returns
`status="ok"` whenever the HTTP request succeeded and the body parsed as JSON — it makes
no judgement about whether any usage fields were actually found. So a 200 response with a
body like `{}` (or any payload where `rate_limit`/`additional_rate_limits`/`credits` are
absent/renamed, e.g. after a backend schema change) produces
`Balance(five_hour_percent=None, weekly_percent=None, credits=None, ...)`, and this code
path treats it as `FetchOutcome("json", balance, "Data is up to date", ...)`. Back in
`fetch_once` (`codex_balance_widget_chrome.py:2226-2229`), `outcome.balance is not None`
is true, so `update_balance_ui(outcome.balance)` is called: the last-known-good
percentages the user was looking at get overwritten with "not found" placeholders, the
status bar claims "Data is up to date", and Chrome fallback is never attempted — even
though `has_existing_data` was true and the symmetric Chrome branch would have preserved
the display in this exact situation. No test exercises `json_status="ok"` with empty
fields, which is how this gap went unnoticed (`test_codex_balance_widget_chrome.py`'s
`TestPlanFetchOutcome` only tests `json_status="ok"` with populated `five_hour_percent`/
`weekly_percent`/`credits`).

**Fix:** Check `has_usage_data` (or the `missing` list) before accepting the JSON result as
a success, and fall through to the Chrome-fallback logic otherwise, mirroring the Chrome
branch:
```python
if json_status == "ok":
    balance = build_balance_from_json_fields(json_fields or {})
    if balance.has_usage_data:
        if is_weekly_limit_exhausted(balance):
            message = tr(language, "Codex unavailable: weekly limit exhausted", "Codex недоступен: недельный лимит исчерпан")
        else:
            message = tr(language, "Data is up to date", "Данные актуальны")
        return FetchOutcome("json", balance, message, "Balance updated (source: json)")
    # Valid JSON but no recognizable usage fields — treat like a JSON error so the
    # existing Chrome-fallback / "keep last good data" logic below still applies.
    json_status = "error"
    json_error = "json response had no recognizable usage fields"
```
(and add a unit test for `json_status="ok"` + all-`None` fields, asserting
`outcome.source != "json"` when `has_existing_data` is true).

### CR-02: Non-`ProbeError` exceptions from the JSON path are uncaught and permanently kill the auto-refresh loop

**File:** `json_usage_provider.py:57-72`, `codex_balance_widget_chrome.py:2234-2237`
**Issue:**
```python
# json_usage_provider.py
async def _fetch_with_retry(self, access_token, account_id) -> JsonFetchResult:
    try:
        payload = await self._fetch_payload(access_token, account_id)
        return JsonFetchResult("ok", fields=probe_wham_usage.extract_fields(payload))
    except probe_wham_usage.ProbeError as exc:
        if not exc.retryable:
            return JsonFetchResult("error", error=str(exc))
    await asyncio.sleep(self.retry_delay)
    try:
        payload = await self._fetch_payload(access_token, account_id)
        return JsonFetchResult("ok", fields=probe_wham_usage.extract_fields(payload), retried=True)
    except probe_wham_usage.ProbeError as exc2:
        return JsonFetchResult("error", error=str(exc2), retried=True)
```
Only `probe_wham_usage.ProbeError` is caught. Several plausible failures are not
`ProbeError` instances and are not caught here or anywhere upstream:
- `probe_wham_usage.fetch_usage` decodes the response body with
  `response.read().decode("utf-8")` (`probe_wham_usage.py:285`) *before* validating
  `Content-Type`/JSON — a non-UTF-8 body raises `UnicodeDecodeError`.
- `collect_windows` (`probe_wham_usage.py:130-149`) does `rate_limit.get(slot)` after
  `payload.get("rate_limit") or {}` — if the backend ever sends `rate_limit` as a
  non-empty, non-dict value (or `additional_rate_limits` as a dict/string instead of a
  list of dicts), `.get()` raises `AttributeError`, contradicting the function's own
  docstring claim ("Defensive against nulls/missing keys at every level").
- `response.read()` itself can raise a bare `ConnectionResetError`/`OSError` that isn't
  wrapped into `urllib.error.URLError` in all cases.

Any of these propagates out of `_fetch_with_retry` → `JsonUsageProvider.fetch()` →
`CodexBalanceWidget.fetch_once()` (which has no `except` clause around
`await self.json_provider.fetch()`, only a `finally` that resets
`self.refresh_in_progress`) → `refresh_loop()`:
```python
async def refresh_loop(self) -> None:
    while True:
        await self.fetch_once()
        await asyncio.sleep(self.refresh_seconds)
```
`refresh_loop` has no exception handling either, so the exception terminates the
`while True` loop entirely. Since `refresh_loop` was scheduled via
`asyncio.run_coroutine_threadsafe(self.refresh_loop(), self.loop)` in
`schedule_refresh()` and its returned `Future` is never awaited/inspected, the task simply
dies silently — the widget stops auto-refreshing for the remainder of the process
lifetime, with nothing shown to the user (manual refresh via the button still works,
since it schedules a fresh `fetch_once()` call, but the periodic background refresh is
gone until restart).

**Fix:** Catch broadly around the payload/extraction call inside `_fetch_with_retry` (or at
minimum wrap `extract_fields` and the decode step) and convert unexpected exceptions into
`JsonFetchResult("error", ...)`, and add a defensive `try/except` in `refresh_loop` as a
second line of defense:
```python
# json_usage_provider.py
async def _fetch_with_retry(self, access_token, account_id) -> JsonFetchResult:
    try:
        payload = await self._fetch_payload(access_token, account_id)
        return JsonFetchResult("ok", fields=probe_wham_usage.extract_fields(payload))
    except probe_wham_usage.ProbeError as exc:
        if not exc.retryable:
            return JsonFetchResult("error", error=str(exc))
    except Exception as exc:  # unexpected schema/encoding/IO error - do not crash the loop
        return JsonFetchResult("error", error=f"{type(exc).__name__}: {exc}")

    await asyncio.sleep(self.retry_delay)
    try:
        payload = await self._fetch_payload(access_token, account_id)
        return JsonFetchResult("ok", fields=probe_wham_usage.extract_fields(payload), retried=True)
    except probe_wham_usage.ProbeError as exc2:
        return JsonFetchResult("error", error=str(exc2), retried=True)
    except Exception as exc2:
        return JsonFetchResult("error", error=f"{type(exc2).__name__}: {exc2}", retried=True)
```
```python
# codex_balance_widget_chrome.py
async def refresh_loop(self) -> None:
    while True:
        try:
            await self.fetch_once()
        except Exception as exc:
            write_log("refresh_loop: unexpected error, continuing:\n" + "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ))
        await asyncio.sleep(self.refresh_seconds)
```

## Warnings

### WR-01: Duplicated fetch/extract logic between the first attempt and the retry attempt

**File:** `json_usage_provider.py:57-72`
**Issue:** The two `try`/`except` blocks in `_fetch_with_retry` are near-identical
(fetch payload, call `extract_fields`, build `JsonFetchResult`), differing only in
`retried=True/False` and the exception variable name. This duplication makes it easy for
future edits (e.g. the CR-02 fix above) to be applied to one branch and forgotten in the
other.
**Fix:** Collapse into a small loop over at most 2 attempts:
```python
async def _fetch_with_retry(self, access_token, account_id) -> JsonFetchResult:
    last_error: str | None = None
    for attempt in range(2):
        if attempt == 1:
            await asyncio.sleep(self.retry_delay)
        try:
            payload = await self._fetch_payload(access_token, account_id)
            return JsonFetchResult(
                "ok", fields=probe_wham_usage.extract_fields(payload), retried=attempt == 1
            )
        except probe_wham_usage.ProbeError as exc:
            last_error = str(exc)
            if not exc.retryable:
                return JsonFetchResult("error", error=last_error, retried=attempt == 1)
    return JsonFetchResult("error", error=last_error, retried=True)
```

### WR-02: First (retryable) attempt's error detail is discarded before the retry

**File:** `json_usage_provider.py:61-65`
**Issue:** When the first attempt raises a retryable `ProbeError`, its message is never
stored — the code falls straight into `asyncio.sleep` and a second attempt. If the second
attempt also fails, only the second exception's message is surfaced
(`JsonFetchResult("error", error=str(exc2), retried=True)`). Useful diagnostic context
(e.g. "first failure was a timeout, second was a 429") is lost, which can make
`widget_launch.log` harder to interpret when diagnosing intermittent JSON-path failures.
**Fix:** Concatenate both messages when both attempts fail, e.g.
`error=f"{first_error}; retry: {exc2}"` (see WR-01's `last_error` variable for a
convenient place to keep the first message around).

## Info

### IN-01: `last_usage_text_length` diagnostic is always `None` on JSON success, with no source-specific label

**File:** `codex_balance_widget_chrome.py:2193-2194`, `2127`
**Issue:** `self.last_usage_text_length` is set to `None` whenever the JSON path succeeds
(`codex_balance_widget_chrome.py:2194`), but the Diagnostics screen always renders it under
the generic label "Размер текста Usage" (`codex_balance_widget_chrome.py:2127`) without
indicating that this field is Chrome-path-specific. After this phase, on a healthy system
where JSON succeeds every cycle, this line will permanently read "нет", which could read
as "nothing was ever fetched" to someone debugging via Diagnostics, even though updates are
working.
**Fix:** Either drop the field from Diagnostics when the last successful source was JSON,
or relabel it to make clear it only applies to the Chrome fallback path.

### IN-02: Diagnostics `last_fetch_status == "ok"` does not disambiguate JSON vs. Chrome source

**File:** `codex_balance_widget_chrome.py:2125`
**Issue:** Both the JSON success path and the Chrome success path set
`self.last_fetch_status = "ok"` (`codex_balance_widget_chrome.py:2192` and `2211`), so the
Diagnostics panel's "Последний статус fetch: ok" line cannot tell a user/support person
which transport actually served the last successful update — only `widget_launch.log`
records the `source: json`/`source: chrome` distinction (per D-05, a persistent UI badge
is explicitly out of scope, but Diagnostics is arguably a reasonable place for this since
it's not a "persistent badge").
**Fix:** Track `self.last_fetch_source` (`"json"`/`"chrome"`) alongside
`last_fetch_status` and surface it in `build_diagnostics_text()`.

---

_Reviewed: 2026-07-21T06:48:11Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
