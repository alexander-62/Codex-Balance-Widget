---
phase: 02-json-provider-integration
reviewed: 2026-07-21T00:00:00Z
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
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues_found
---

# Phase 02: Code Review Report (re-review after fix pass)

**Reviewed:** 2026-07-21T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Re-reviewed after the fix pass for the previous report's CR-01, CR-02, WR-01, WR-02
(commits `c9d3b94`, `4370c0c`, `0983cda`, `dd101cc`). All four fixes were verified against
the current source and empirically exercised:

- **CR-02** (uncaught non-`ProbeError` exceptions crashing the auto-refresh loop) is
  **correctly fixed**. `json_usage_provider._fetch_with_retry` now catches broad
  `Exception` around both fetch/extract attempts and converts it to
  `JsonFetchResult("error", ...)`; `refresh_loop()` now also wraps `fetch_once()` in a
  `try/except` that logs and continues. Empirically verified: injecting an `AttributeError`
  from a mocked `fetch_usage` now returns `status="error"` instead of propagating (see
  reproduction in review notes below).
- **WR-01/WR-02** (duplicated retry logic / discarded first-attempt error) are **correctly
  fixed**. The two attempts are now collapsed into a `for attempt in range(2)` loop with a
  `first_error` variable that gets concatenated into the final error message when both
  attempts fail.
- **CR-01** (JSON "ok" success path skipping `has_usage_data` validation) is **only
  partially fixed**. `plan_fetch_outcome` itself now correctly refuses to treat an
  all-`None` JSON result as a "json" source success — this part is correct and covered by
  a new regression test. However, its caller, `CodexBalanceWidget.fetch_once()`, was never
  updated: whenever `json_result.status == "ok"` it unconditionally calls
  `plan_fetch_outcome(..., chrome_attempted=False, ...)`, regardless of whether
  `self.browser` actually exists. Because `plan_fetch_outcome` checks
  `if not chrome_attempted` before it ever looks at `has_existing_data`, this means: (a)
  Chrome fallback is **never actually attempted** in this scenario even when Chrome is
  configured and running, and (b) the user is shown the literal message "Google Chrome not
  found. Set CHROME_PATH." even when Chrome *is* found — it just was never tried. This is a
  new/updated Critical finding (see CR-01 below); it is a direct, provable consequence of
  the fact that the fix touched only the pure decision function and not its integration
  point, and it has no test coverage (all new/existing tests call `plan_fetch_outcome`
  directly and never exercise `fetch_once()` end-to-end).

Two lower-severity gaps were also found in the fixed code (see Warnings), and the two
Info-level items from the previous review (`last_usage_text_length`/`last_fetch_status`
not disambiguating JSON vs. Chrome sources) remain unaddressed, as expected since they were
explicitly out of scope for this fix pass.

## Critical Issues

### CR-01: `fetch_once()` still hardcodes `chrome_attempted=False` on JSON "ok", so the CR-01 fallback never actually triggers Chrome and shows a false "Chrome not found" message

**File:** `codex_balance_widget_chrome.py:2185-2199` (caller), `codex_balance_widget_chrome.py:558-574` (decision function)
**Issue:**
The previous fix (`c9d3b94`) correctly taught `plan_fetch_outcome` to reject a JSON "ok"
result with no usage data:
```python
if json_status == "ok":
    balance = build_balance_from_json_fields(json_fields or {})
    if balance.has_usage_data:
        ...
        return FetchOutcome("json", balance, message, "Balance updated (source: json)")
    json_status = "error"
    json_error = "json response had no recognizable usage fields"

if not chrome_attempted:
    message = tr(language, "Google Chrome not found. Set CHROME_PATH.", ...)
    log_line = f"JSON fetch failed ({json_error}); Chrome unavailable"
    return FetchOutcome("none", None, message, log_line)
```
But `fetch_once()`, the only caller of `plan_fetch_outcome` for the `json_status == "ok"`
branch, was never updated and still does:
```python
if json_result.status == "ok":
    outcome = plan_fetch_outcome(
        json_status="ok",
        json_fields=json_result.fields,
        json_error=None,
        chrome_attempted=False,   # <-- always False here, regardless of self.browser
        chrome_status=None,
        chrome_error=None,
        chrome_text=None,
        has_existing_data=self.current_balance.has_usage_data,
        language=self.language,
    )
    ...
elif not self.browser:
    ...
else:
    result = await self.browser.fetch()   # Chrome fallback only ever runs from here
    ...
```
Since Chrome fallback (`await self.browser.fetch()`) only happens in the `elif`/`else`
legs, which are only reached when `json_result.status != "ok"`, a JSON response that is
structurally "ok" but has no recognizable fields (the exact scenario CR-01 was written to
guard against) can **never** reach the actual Chrome fetch, no matter whether
`self.browser` is configured. Because `plan_fetch_outcome` checks `if not chrome_attempted`
*before* checking `has_existing_data`, this happens unconditionally — even when there is
existing good data to preserve (so the "clobbering" symptom from the original CR-01 is
avoided) and even when Chrome is fully configured and working.

Empirically reproduced:
```python
from codex_balance_widget_chrome import plan_fetch_outcome
outcome = plan_fetch_outcome(
    json_status="ok", json_fields={}, json_error=None,
    chrome_attempted=False, chrome_status=None, chrome_error=None, chrome_text=None,
    has_existing_data=True, language="en",
)
# FetchOutcome(source='none', balance=None,
#   status_message='Google Chrome not found. Set CHROME_PATH.',
#   log_line='JSON fetch failed (json response had no recognizable usage fields); Chrome unavailable')
```
This is exactly the call `fetch_once()` makes in this scenario. Two concrete user-facing
problems result:
1. **False diagnostic**: the widget tells the user Chrome isn't found/configured even when
   it is (`self.browser` is not `None`), which will send users down the wrong
   troubleshooting path (checking `CHROME_PATH`) for a problem that has nothing to do with
   Chrome.
2. **Fallback never engaged**: on a fresh install (`has_existing_data == False`) where the
   backend happens to return a 200 with an empty/unrecognized body (schema drift, feature
   flag, transient backend issue, etc.) and Chrome is properly configured, the widget will
   permanently report "Chrome not found" every refresh cycle and never attempt the working
   Chrome fallback to get real data — exactly the failure mode the original fix was
   supposed to close off, just relocated one level up the call stack.

No test exercises `fetch_once()` end-to-end (`test_codex_balance_widget_chrome.py`'s
`TestPlanFetchOutcome` class only calls `plan_fetch_outcome` directly with
hand-constructed `chrome_attempted` values), so this integration gap went undetected by
the fix's own regression test (`dd101cc`).

**Fix:** In `fetch_once()`, decide `chrome_attempted`/invoke Chrome based on whether the
*effective* result has usable data, not on the raw `json_result.status`. For example,
compute the balance/`has_usage_data` before branching, and only skip Chrome when JSON truly
produced usable data:
```python
if json_result.status == "ok":
    balance = build_balance_from_json_fields(json_result.fields or {})
    if balance.has_usage_data:
        outcome = plan_fetch_outcome(
            json_status="ok", json_fields=json_result.fields, json_error=None,
            chrome_attempted=False, chrome_status=None, chrome_error=None, chrome_text=None,
            has_existing_data=self.current_balance.has_usage_data, language=self.language,
        )
        self.last_fetch_status = "ok"
        self.last_fetch_error = None
        self.last_usage_text_length = None
    elif not self.browser:
        outcome = plan_fetch_outcome(
            json_status="error", json_fields=None,
            json_error="json response had no recognizable usage fields",
            chrome_attempted=False, chrome_status="chrome_not_found", chrome_error=None,
            chrome_text=None, has_existing_data=self.current_balance.has_usage_data,
            language=self.language,
        )
        self.last_fetch_status = "chrome_not_found"
        self.last_fetch_error = tr(self.language, "Google Chrome not found", "Google Chrome не найден")
    else:
        result = await self.browser.fetch()
        self.last_fetch_status = result.status
        self.last_fetch_error = result.error
        self.last_usage_text_length = len(result.text) if result.text else None
        outcome = plan_fetch_outcome(
            json_status="error", json_fields=None,
            json_error="json response had no recognizable usage fields",
            chrome_attempted=True, chrome_status=result.status, chrome_error=result.error,
            chrome_text=result.text, has_existing_data=self.current_balance.has_usage_data,
            language=self.language,
        )
elif not self.browser:
    ...  # unchanged
```
And add an integration-level regression test that calls `widget.fetch_once()` (or a
thin wrapper) with a mocked `json_provider.fetch()` returning `status="ok"` with empty
fields plus a mocked `self.browser`, asserting that `self.browser.fetch()` was actually
awaited.

## Warnings

### WR-01: Manual "Refresh" button still has no exception protection around `fetch_once()`

**File:** `codex_balance_widget_chrome.py:1889-1893`
**Issue:** The CR-02 fix added a `try/except` around `await self.fetch_once()` inside
`refresh_loop()` only. `manual_refresh()` schedules `fetch_once()` the same unprotected way
it always did:
```python
def manual_refresh(self) -> None:
    if self.refresh_in_progress:
        self.set_status(tr(self.language, "Refresh already in progress...", "..."))
        return
    asyncio.run_coroutine_threadsafe(self.fetch_once(), self.loop)
```
The returned `Future` is discarded, so if `fetch_once()` raises anything not already
handled internally (e.g. a future regression that reintroduces an uncaught exception, or
any exception from code added later on this code path), the click silently does nothing —
no status update, no log entry the user can see from the UI, and no exception surfaces
anywhere except an "exception was never retrieved" warning on stderr, which most users
running the packaged widget will never see. `self.refresh_in_progress` is still safely
reset via `fetch_once()`'s own `finally` block, so this does not hang the app, but the user
gets no feedback that their manual refresh failed.
**Fix:** Wrap the same way `refresh_loop` was fixed, or add a done-callback to the future
that logs/surfaces exceptions:
```python
def manual_refresh(self) -> None:
    if self.refresh_in_progress:
        self.set_status(tr(self.language, "Refresh already in progress...", "..."))
        return
    future = asyncio.run_coroutine_threadsafe(self.fetch_once(), self.loop)
    future.add_done_callback(self._log_manual_refresh_exception)

def _log_manual_refresh_exception(self, future: "asyncio.Future") -> None:
    exc = future.exception()
    if exc is not None:
        write_log("manual_refresh: unexpected error:\n" + "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ))
```

### WR-02: CR-02's new broad-`except Exception` path in `json_usage_provider.py` has no dedicated regression test

**File:** `json_usage_provider.py:76-78`, `test_json_usage_provider.py`
**Issue:** The fix that closes the original CR-02 hole (`except Exception as exc: ...`
inside `_fetch_with_retry`) is exactly the kind of change that is easy to silently regress
during a future refactor (e.g. someone "simplifies" the loop and drops the generic
`except`). `test_json_usage_provider.py` only exercises `probe_wham_usage.ProbeError`
paths (`test_non_retryable_error_no_retry`, `test_retryable_error_then_success`,
`test_retryable_error_twice_gives_up`); none of them mock `fetch_usage`/`extract_fields`
to raise a non-`ProbeError` exception (e.g. `AttributeError`, `UnicodeDecodeError`), so
there is no automated proof that the fix actually works, only manual verification (done as
part of this review — see CR-02 in the Summary — which confirms it currently behaves
correctly).
**Fix:** Add a test such as:
```python
@patch("probe_wham_usage.fetch_usage")
@patch("probe_wham_usage.load_tokens")
async def test_unexpected_exception_becomes_error_result(self, mock_load_tokens, mock_fetch_usage):
    mock_load_tokens.return_value = ("tok", None)
    mock_fetch_usage.side_effect = AttributeError("'str' object has no attribute 'get'")
    provider = JsonUsageProvider(retry_delay=0)
    result = await provider.fetch()
    self.assertEqual(result.status, "error")
    self.assertIn("AttributeError", result.error)
```

## Info

### IN-01: `last_usage_text_length` diagnostic is always `None` on JSON success, with no source-specific label (carried over, unaddressed)

**File:** `codex_balance_widget_chrome.py:2199`, `2127`
**Issue:** Unchanged from the previous review. `self.last_usage_text_length` is still set to
`None` whenever the JSON path reports success, and the Diagnostics screen still renders it
under the generic label "Размер текста Usage" without indicating it is Chrome-path-specific.
Explicitly out of scope for this fix pass (info-level, not requested); left as-is.
**Fix:** Unchanged from previous review — relabel or omit the field when the last
successful source was JSON.

### IN-02: Diagnostics `last_fetch_status == "ok"` still does not disambiguate JSON vs. Chrome source (carried over, unaddressed)

**File:** `codex_balance_widget_chrome.py:2125`, `2197`, `2216`
**Issue:** Unchanged from the previous review. Both the JSON success path and the Chrome
success path still set `self.last_fetch_status = "ok"`, so Diagnostics cannot show which
transport served the last successful update. Explicitly out of scope for this fix pass;
left as-is.
**Fix:** Unchanged from previous review — track `self.last_fetch_source` alongside
`last_fetch_status` and surface it in `build_diagnostics_text()`.

### IN-03: `_fetch_with_retry`'s trailing `return` after the loop is confirmed dead code

**File:** `json_usage_provider.py:87-89`
**Issue:** As the WR-01 fix's own comment acknowledges, the final
`return JsonFetchResult("error", error=first_error, retried=True)` after the
`for attempt in range(2):` loop is unreachable: attempt 0 either returns directly or
`continue`s into attempt 1, and attempt 1 always returns from inside the loop body. This
was traced and confirmed during this review. It is harmless (kept deliberately for static
analysis / type-checker satisfaction per the inline comment) but is still literally dead
code by the review's own detection criteria.
**Fix:** No action required if intentional; if desired, this can be restructured with a
`while True` (dropping the `for`/`range(2)` framing) to make the "always returns" property
structurally obvious rather than requiring a comment, e.g. `assert False, "unreachable"`
instead of a fabricated return value.

---

_Reviewed: 2026-07-21T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
