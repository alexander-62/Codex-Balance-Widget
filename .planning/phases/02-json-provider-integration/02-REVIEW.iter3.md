---
phase: 02-json-provider-integration
reviewed: 2026-07-21T12:00:00Z
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
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 02: Code Review Report (re-review, auto-fix iteration 3 of 3)

**Reviewed:** 2026-07-21T12:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Re-reviewed after the iteration-2 fix pass for CR-01, WR-01, WR-02 (commits `e9f77c0`,
`c7a48b7`, `294ea5f`). All three fixes were verified against the current source, traced
line-by-line, and exercised via the full test suite (`python -m pytest` — 57/57 passing,
`py_compile` clean on all six files).

- **CR-01 (fetch_once() hardcoded chrome_attempted=False on JSON "ok" with no usage
  data) — verified fixed.** `fetch_once()` (`codex_balance_widget_chrome.py:2187-2266`) now
  computes `json_ok_with_data = build_balance_from_json_fields(json_result.fields or
  {}).has_usage_data` before branching, and only takes the JSON-success/`chrome_attempted=
  False` path when that flag is true. When JSON is structurally "ok" but has no
  recognizable fields, execution now falls into the same `elif not self.browser` / `else`
  legs used for a genuine JSON error, so `await self.browser.fetch()` is actually invoked
  when Chrome is configured, and the "Chrome not found" message is only shown when
  `self.browser` really is `None`. Traced both branches; the `json_error` substitution
  (`json_result.error if json_result.status != "ok" else "json response had no
  recognizable usage fields"`) is correct in both the `elif` and `else` legs.
- **WR-01 (manual_refresh had no exception protection) — verified fixed.**
  `manual_refresh()` (`codex_balance_widget_chrome.py:1889-1904`) now keeps the `Future`
  from `asyncio.run_coroutine_threadsafe(...)` and attaches
  `_log_manual_refresh_exception`, which calls `future.exception()` inside a
  `try/except asyncio.CancelledError: return` guard and logs via the existing
  `write_log`/`traceback.format_exception` pattern when an exception is present. Correct:
  `concurrent.futures.Future.exception()` (the actual runtime type returned by
  `run_coroutine_threadsafe`) does raise `CancelledError` on a cancelled future rather than
  returning it, so the guard is necessary and present.
- **WR-02 (no regression test for the broad `except Exception` fallback) — verified
  fixed.** `test_json_usage_provider.py::test_unexpected_exception_becomes_error_result`
  mocks `fetch_usage` to raise `AttributeError`, and asserts `status="error"`,
  `"AttributeError"` in the message, `retried=False`, `call_count == 1`. Ran this test in
  isolation — passes, and correctly fails if the `except Exception` clause in
  `_fetch_with_retry` (`json_usage_provider.py:76-78`) is removed (verified by temporarily
  reverting that line locally and re-running the test, then restoring it).

No new Critical or additional Warning-level defects were found in the code paths touched by
these three fixes. One new Warning (test-coverage gap, explicitly flagged as unaddressed by
the iteration-2 fix report itself) and a few minor Info-level nits were found during this
pass; the three carried-over Info items (IN-01/IN-02/IN-03) from the previous review remain
true and unaddressed by design (explicitly out of scope for the fix pass).

## Warnings

### WR-03: `fetch_once()`'s JSON-ok/no-usage-data → Chrome-fallback branch (the actual CR-01 fix point) still has no integration-level test

**File:** `codex_balance_widget_chrome.py:2187-2266`, `test_codex_balance_widget_chrome.py`
**Issue:** The CR-01 fix's own fix report (`02-REVIEW-FIX.iter2.md`) explicitly flags this
as a remaining gap: "no existing test exercised this exact `fetch_once()` end-to-end path
... an integration-level regression test for `fetch_once()` itself ... was not added and
remains a gap for a future pass." This is still true after iteration 3.
`test_codex_balance_widget_chrome.py::TestPlanFetchOutcome` only calls the pure
`plan_fetch_outcome()` decision function directly with hand-constructed `chrome_attempted`
values — it never constructs a `CodexBalanceWidget`, never mocks `self.json_provider.fetch()`
/ `self.browser.fetch()`, and never asserts that `self.browser.fetch()` is actually awaited
when JSON returns `status="ok"` with empty/unrecognized fields. Because the CR-01 defect
lived entirely in the *glue code* inside `fetch_once()` (not in `plan_fetch_outcome()`,
which was correct all along), a future refactor of `fetch_once()`'s branching (e.g.
someone "simplifies" the `json_ok_with_data` check back to `json_result.status == "ok"`)
would silently reintroduce the exact CR-01 regression with none of the 57 existing tests
catching it — verified by manually reverting the `json_ok_with_data` computation locally:
all 57 tests still pass with the CR-01 bug reintroduced.
**Fix:** Add a test that instantiates `CodexBalanceWidget` with Tk mocked/skipped (or
extracts the branching logic in `fetch_once()` into a standalone async helper that takes
`json_result`, `browser`, and current state as parameters, testable without Tk), mocks
`json_provider.fetch()` to return `JsonFetchResult("ok", fields={})`, mocks `self.browser`
with an `AsyncMock` for `.fetch()`, calls `fetch_once()`, and asserts
`self.browser.fetch.assert_awaited_once()`. At minimum, a lighter-weight regression could
assert on the `json_ok_with_data` boolean itself if it were extracted as a standalone pure
function (e.g. `def json_result_has_usage_data(json_result) -> bool`), which would also
reduce the branch's cyclomatic complexity.

## Info

### IN-04: Duplicated `json_error` ternary in `fetch_once()`'s `elif`/`else` legs

**File:** `codex_balance_widget_chrome.py:2219-2223`, `2242-2246`
**Issue:** The CR-01 fix introduces the identical three-line expression in both branches:
```python
json_error = (
    json_result.error
    if json_result.status != "ok"
    else "json response had no recognizable usage fields"
)
```
Correct in both places, but duplicated rather than computed once before the `elif`/`else`
split (it doesn't depend on anything branch-specific).
**Fix:** Hoist the computation once, right after `json_ok_with_data` is computed:
```python
json_error = (
    json_result.error
    if json_result.status != "ok"
    else "json response had no recognizable usage fields"
)
```
then reference `json_error` in both the `elif not self.browser` and `else` legs without
recomputing it.

### IN-05: `_log_manual_refresh_exception`'s `future` parameter is annotated as `asyncio.Future` but the runtime type is `concurrent.futures.Future`

**File:** `codex_balance_widget_chrome.py:1896`
**Issue:** `asyncio.run_coroutine_threadsafe(coro, loop)` returns a
`concurrent.futures.Future`, not an `asyncio.Future` (they share an `.exception()`/
`.add_done_callback()`-shaped interface but are different classes with different threading
semantics). The parameter is typed `future: "asyncio.Future"`, which is misleading for
future maintainers reasoning about thread-safety of calls on this object.
**Fix:** `def _log_manual_refresh_exception(self, future: "concurrent.futures.Future") ->
None:` (with `import concurrent.futures` or `from concurrent.futures import Future`).

### IN-06 (carried over, unaddressed by design): Diagnostics fields don't disambiguate JSON vs. Chrome source

**File:** `codex_balance_widget_chrome.py:2125`, `2141-2143`, `2215-2217`
**Issue:** Unchanged from the previous two reviews. `self.last_fetch_status` is `"ok"` for
both a JSON success and a Chrome success, and `self.last_usage_text_length` is always
`None` on the JSON path — Diagnostics still cannot show which transport served the last
update. Explicitly out of scope for the fix passes so far.
**Fix:** Unchanged from previous reviews — track `self.last_fetch_source` and surface it in
`build_diagnostics_text()`.

### IN-07 (carried over, unaddressed by design): `_fetch_with_retry`'s trailing `return` is confirmed dead code

**File:** `json_usage_provider.py:87-89`
**Issue:** Unchanged from the previous review — the final
`return JsonFetchResult("error", error=first_error, retried=True)` after
`for attempt in range(2):` is unreachable (both loop iterations always return or
`continue`). Kept deliberately per the inline comment for static-analysis/type-checker
satisfaction.
**Fix:** No action required if intentional.

---

_Reviewed: 2026-07-21T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
