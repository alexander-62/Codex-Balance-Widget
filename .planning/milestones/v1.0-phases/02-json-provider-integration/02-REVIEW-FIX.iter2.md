---
phase: 02-json-provider-integration
fixed_at: 2026-07-21T06:54:11Z
review_path: .planning/phases/02-json-provider-integration/02-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-07-21T06:54:11Z
**Source review:** .planning/phases/02-json-provider-integration/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (fix_scope: critical_warning -> CR-01, CR-02, WR-01, WR-02; IN-01/IN-02 out of scope)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: JSON "ok" success path skips `has_usage_data` validation, silently clobbering last-known-good balance

**Files modified:** `codex_balance_widget_chrome.py`, `test_codex_balance_widget_chrome.py`
**Commits:** `c9d3b94` (source fix), `dd101cc` (regression test)
**Applied fix:** In `plan_fetch_outcome`, the `json_status == "ok"` branch now checks
`balance.has_usage_data` before returning a `FetchOutcome("json", ...)` success, mirroring
the existing Chrome branch a few lines below. When a structurally valid JSON response has
no recognizable usage fields, `json_status` is downgraded to `"error"` (with an explanatory
`json_error`) and control falls through to the existing Chrome-fallback / "keep last known
good data" logic, exactly as the review's fix suggestion prescribed. Added a regression
test (`test_json_ok_empty_fields_falls_back_not_json_source`) asserting `outcome.source !=
"json"` when `json_fields={}` and `has_existing_data=True`, per the review's explicit test
request. Full suite (55 -> 56 tests) passes.

### CR-02: Non-`ProbeError` exceptions from the JSON path are uncaught and permanently kill the auto-refresh loop

**Files modified:** `json_usage_provider.py`, `codex_balance_widget_chrome.py`
**Commit:** `4370c0c`
**Applied fix:** Added a broad `except Exception` clause around each of the two fetch/extract
attempts in `JsonUsageProvider._fetch_with_retry`, converting unexpected exceptions
(`UnicodeDecodeError`, `AttributeError` from malformed nested JSON fields, bare `OSError`,
etc.) into `JsonFetchResult("error", ...)` instead of letting them propagate. Also added a
defensive `try/except Exception` around `await self.fetch_once()` inside
`CodexBalanceWidget.refresh_loop()` as a second line of defense, logging via the existing
`write_log`/`traceback` machinery and continuing the `while True` loop instead of silently
terminating the background auto-refresh task. Full test suite passes with no regressions.

### WR-01: Duplicated fetch/extract logic between the first attempt and the retry attempt

**Files modified:** `json_usage_provider.py`
**Commit:** `0983cda`
**Applied fix:** Collapsed the two near-identical `try`/`except` blocks in
`_fetch_with_retry` into a single `for attempt in range(2)` loop (adapted from the review's
suggested snippet to also retain the CR-02 broad-`Exception` handling committed just before
this fix, so both fixes coexist correctly). Generic (non-`ProbeError`) exceptions are treated
as non-retryable, matching the behavior established by the CR-02 fix. Full test suite
passes with no regressions (all existing status/retried/call_count assertions in
`test_json_usage_provider.py` still hold, since none depend on exact error-message text).

### WR-02: First (retryable) attempt's error detail is discarded before the retry

**Files modified:** `json_usage_provider.py`
**Commit:** `0983cda`
**Applied fix:** Combined with the WR-01 loop refactor (same commit, same function): a
`first_error` variable now retains the first attempt's failure message when it was
retryable, and if the retry also fails, the final `JsonFetchResult.error` is
`f"{first_error}; retry: {error_text}"` so both failure details are preserved for
diagnostics (e.g. in `widget_launch.log`), instead of discarding the first attempt's error.

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-07-21T06:54:11Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
