---
phase: 02-json-provider-integration
fixed_at: 2026-07-21T07:15:48Z
review_path: .planning/phases/02-json-provider-integration/02-REVIEW.md
iteration: 3
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-07-21T07:15:48Z
**Source review:** .planning/phases/02-json-provider-integration/02-REVIEW.md
**Iteration:** 3 (final automated iteration)

**Summary:**

- Findings in scope: 1 (fix_scope: critical_warning -> WR-03; IN-04/IN-05/IN-06/IN-07 out of scope)
- Fixed: 1
- Skipped: 0

## Fixed Issues

### WR-03: `fetch_once()`'s JSON-ok/no-usage-data -> Chrome-fallback branch (the actual CR-01 fix point) still has no integration-level test

**Files modified:** `test_codex_balance_widget_chrome.py`
**Commit:** `efb4529`
**Applied fix:** Added a new `TestFetchOnceJsonOkNoUsageDataFallback` test class that
exercises `fetch_once()` itself, not just the pure `plan_fetch_outcome()` decision
function. Each test builds a `CodexBalanceWidget` via `CodexBalanceWidget.__new__(...)`
(bypassing `__init__` entirely, so no `tk.Tk()` root, background event-loop thread, Chrome
discovery, or settings/history I/O is needed) and manually sets only the attributes
`fetch_once()` actually touches: `refresh_in_progress`, `language`, `current_balance`,
`last_successful_update`, `last_fetch_status`, `last_fetch_error`, `last_usage_text_length`,
a mocked `json_provider` (`AsyncMock` on `.fetch()`), an optional mocked `browser`
(`AsyncMock` on `.fetch()`, or `None`), and mocked `set_status`/`update_balance_ui` (to
avoid needing `self.root`/`self.status_var`). `write_log` is patched at the module level
via `@patch("codex_balance_widget_chrome.write_log")` to avoid writing to the real
`widget_launch.log` file during tests.

Three tests were added:

- `test_json_ok_empty_fields_with_browser_attempts_chrome_fallback`: JSON returns
  `status="ok", fields={}` and a browser is configured -> asserts
  `widget.browser.fetch.assert_awaited_once()` and that `last_fetch_status` is not
  `"chrome_not_found"`. This is the exact CR-01 regression scenario.
- `test_json_ok_empty_fields_without_browser_reports_chrome_not_found`: same JSON input,
  but no browser configured -> asserts `last_fetch_status == "chrome_not_found"` and the
  localized "Google Chrome not found" error message is set.
- `test_json_ok_with_usage_data_skips_chrome_fallback`: sanity check on the other side of
  the branch -- a genuinely usable JSON payload must NOT trigger the Chrome fallback even
  when a browser is configured (`assert_not_awaited()`, `last_fetch_status == "ok"`).

**Verification performed:** Ran the full suite in the isolated worktree after adding the
tests -- 60/60 passing (57 existing + 3 new). Then, per the task's "make sure this fix is
solid" instruction, manually reverted the `json_ok_with_data` computation in
`fetch_once()` back to the pre-CR-01 `json_ok_with_data = json_result.status == "ok"`
(the exact regression WR-03 describes) and re-ran only the new test class: both of the
first two tests failed as expected (`browser.fetch` never awaited; `last_fetch_status`
stayed `"ok"` instead of `"chrome_not_found"`), confirming the new tests genuinely catch
the CR-01 regression that all 57 pre-existing tests missed. Restored the source file to
its committed state (verified via `git diff` showing no changes to
`codex_balance_widget_chrome.py`) and re-ran the full suite once more -- 60/60 passing --
before committing only the test file change.

This closes the test-coverage gap explicitly flagged as unaddressed in the iteration-2 fix
report and confirmed still open by the iteration-3 re-review (WR-03).

---

_Fixed: 2026-07-21T07:15:48Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3 (final)_
