---
phase: 02-json-provider-integration
fixed_at: 2026-07-21T07:05:24Z
review_path: .planning/phases/02-json-provider-integration/02-REVIEW.md
iteration: 2
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-07-21T07:05:24Z
**Source review:** .planning/phases/02-json-provider-integration/02-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 3 (fix_scope: critical_warning -> CR-01, WR-01, WR-02; IN-01/IN-02/IN-03 out of scope)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: `fetch_once()` still hardcodes `chrome_attempted=False` on JSON "ok", so the CR-01 fallback never actually triggers Chrome and shows a false "Chrome not found" message

**Files modified:** `codex_balance_widget_chrome.py`
**Commit:** `e9f77c0`
**Applied fix:** In `fetch_once()`, the `json_result.status == "ok"` branch no longer
unconditionally treats the JSON fetch as fully successful. A new `json_ok_with_data`
flag is computed by calling `build_balance_from_json_fields(json_result.fields or {})`
and checking `.has_usage_data` before branching. Only when that flag is true does the
code take the JSON-success path (`chrome_attempted=False`, `last_fetch_status = "ok"`
unchanged from before). When JSON reports "ok" but carries no recognizable usage fields,
execution now falls through into the same `elif not self.browser` / `else` branches used
for a genuine JSON error, so the Chrome fallback (`await self.browser.fetch()`) is
actually attempted when `self.browser` is configured, and the "Google Chrome not found"
message is only shown when Chrome truly isn't configured. In both of those branches, a
small `json_error` helper expression substitutes the synthetic message
`"json response had no recognizable usage fields"` for `json_result.error` when the
underlying status was "ok" (since `json_result.error` is `None` in that case), preserving
the original passthrough of `json_result.error` for the pre-existing genuine-error path.
This collapses the three-way duplication suggested in REVIEW.md's fix snippet into a
single shared boolean check, keeping the diff minimal while producing equivalent
behavior. Verified against the full test suite (57 tests, all passing) after the change;
no existing test exercised this exact `fetch_once()` end-to-end path (as REVIEW.md notes),
so this fix is source-level only in this iteration — an integration-level regression test
for `fetch_once()` itself (as suggested in REVIEW.md) was not added and remains a gap for
a future pass.

### WR-01: Manual "Refresh" button still has no exception protection around `fetch_once()`

**Files modified:** `codex_balance_widget_chrome.py`
**Commit:** `c7a48b7`
**Applied fix:** `manual_refresh()` now keeps the `Future` returned by
`asyncio.run_coroutine_threadsafe(self.fetch_once(), self.loop)` and attaches a
`future.add_done_callback(self._log_manual_refresh_exception)`. The new
`_log_manual_refresh_exception` method retrieves `future.exception()` (guarding against
`asyncio.CancelledError`, which `future.exception()` re-raises if the future was
cancelled) and, if an exception is present, writes it to the log via `write_log(...)`
using the same `traceback.format_exception(...)` pattern already used in
`refresh_loop()`'s except handler. This matches the fix suggested in REVIEW.md, with the
added `CancelledError` guard as a defensive adaptation since `Future.exception()` does not
return `None` for a cancelled future — it raises.

### WR-02: CR-02's new broad-`except Exception` path in `json_usage_provider.py` has no dedicated regression test

**Files modified:** `test_json_usage_provider.py`
**Commit:** `294ea5f`
**Applied fix:** Added `test_unexpected_exception_becomes_error_result` to
`TestJsonUsageProviderFetch`, following the same `@patch("probe_wham_usage.fetch_usage")`
/ `@patch("probe_wham_usage.load_tokens")` pattern as the existing tests in the file. The
test sets `mock_fetch_usage.side_effect = AttributeError(...)` (a non-`ProbeError`
exception) and asserts that `provider.fetch()` returns `status="error"` with
`"AttributeError"` in the error message, `retried=False`, and exactly one call to
`mock_fetch_usage` (confirming the broad `except Exception` branch in
`_fetch_with_retry` treats unexpected exceptions as non-retryable, matching its current
`retryable = False` hardcoding). Full suite run after the change: 57 tests, all passing
(up from 56 before this test was added).

---

_Fixed: 2026-07-21T07:05:24Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
