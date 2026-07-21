---
phase: 02-json-provider-integration
plan: 03
subsystem: api
tags: [python, asyncio, json-provider, chrome-fallback, tkinter-widget]

# Dependency graph
requires:
  - phase: 02-json-provider-integration (Plan 02-01)
    provides: "JsonUsageProvider().fetch() -> JsonFetchResult(status, fields, error, retried), async, stdlib-only, never raises"
  - phase: 02-json-provider-integration (Plan 02-02)
    provides: "plan_fetch_outcome(...) pure decision function -> FetchOutcome(source, balance, status_message, log_line), plus ISO reset-date parsing and build_balance_from_json_fields"
provides:
  - "CodexBalanceWidget.__init__ constructs self.json_provider = json_usage_provider.JsonUsageProvider() alongside the unchanged self.browser"
  - "fetch_once rewritten: JSON attempt via self.json_provider.fetch() first; self.browser.fetch() (Chrome) invoked only when JSON status != 'ok'; single write_log(outcome.log_line) call point records source (json|chrome) for every successful update"
  - "Live human-verified confirmation that Success Criteria 1-3 of Phase 2 hold on the real running widget: normal cycle never opens Chrome, log records source, forced JSON failure triggers Chrome fallback without crashing, and JSON path resumes cleanly afterward"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "fetch_once as thin async orchestrator: call JSON, call plan_fetch_outcome (Plan 02-02's pure decision function), apply the single FetchOutcome to UI/status/log — Chrome (self.browser.fetch()) is only reached inside the one branch where JSON did not return 'ok'"

key-files:
  created: []
  modified:
    - codex_balance_widget_chrome.py

key-decisions:
  - "import json_usage_provider placed immediately after the try/except pystray block and before APP_VERSION, per plan's anchor instruction"
  - "self.json_provider constructed in __init__ right after self.browser, with self.browser/self.refresh_seconds/self.chrome_path left untouched (D-01: Chrome still constructed as before, invoked on demand only inside the fallback branch)"
  - "fetch_once keeps its original refresh_in_progress guard and try/finally exactly as before; only the body of the try block was rewritten"
  - "Task 2 (human-verify checkpoint) required no code changes — it is a live review gate. Verification was performed by the orchestrator directly against the running widget on the user's machine (not simulated), covering all 7 how-to-verify steps, and the user approved with 'да'"

patterns-established:
  - "Single write_log(outcome.log_line) call point at the end of fetch_once (not one write_log per branch) keeps source logging (source: json / source: chrome) consistent across all three outcome branches"

requirements-completed: [JSONPROV-01, JSONPROV-02, JSONPROV-03]

# Metrics
duration: 12min
completed: 2026-07-20
---

# Phase 2 Plan 03: JSON primary source wired into fetch_once, live-verified Chrome fallback Summary

**`fetch_once` now tries the JSON usage endpoint first via `JsonUsageProvider`, falling back to the existing `CodexUsageBrowser` (Chrome) only on JSON failure, with a single logging point recording `source: json`/`source: chrome` — confirmed working live on the running widget by the user, including a forced JSON-path failure that correctly triggered the Chrome fallback without crashing.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-20T20:55:00Z
- **Completed:** 2026-07-20T21:07:00Z
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 1

## Accomplishments
- `CodexBalanceWidget.__init__` now constructs `self.json_provider = json_usage_provider.JsonUsageProvider()` without touching `self.browser`'s construction (Chrome stays cold until needed, per D-01)
- `fetch_once` rewritten so `self.json_provider.fetch()` is always attempted first; `self.browser.fetch()` is reached only inside the branch where the JSON result's status is not `"ok"`
- All three outcome branches (JSON ok / JSON fail + no Chrome / JSON fail + Chrome fallback) route through the single `plan_fetch_outcome(...)` decision function from Plan 02-02, then apply the resulting `FetchOutcome` via one `update_balance_ui`/`set_status`/`write_log(outcome.log_line)` call site
- Live human verification on the real widget confirmed all three Phase 2 Success Criteria: normal cycle never opens Chrome + logs `source: json`; forced `CODEX_HOME` breakage triggers Chrome fallback without crashing + logs `source: chrome`; removing the override restores the JSON path cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: __init__ + fetch_once — JSON первично, Chrome фолбэк** - `96b5edf` (feat)
2. **Task 2: Живая проверка — JSON основной источник, Chrome фолбэк, лог источника** - checkpoint:human-verify, no code changes (see below)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `codex_balance_widget_chrome.py` - Added `import json_usage_provider`; `CodexBalanceWidget.__init__` now builds `self.json_provider`; `fetch_once` rewritten to try JSON first and fall back to Chrome only on JSON failure, with a single `write_log(outcome.log_line)` call recording the source of every successful update

## Decisions Made
- See `key-decisions` in frontmatter above. No deviations from the plan's prescribed code structure.

## Deviations from Plan

None - plan executed exactly as written. Full regression suite (`test_probe_wham_usage`, `test_json_usage_provider`, `test_codex_balance_widget_chrome` — 55 tests) passes with no failures after Task 1's changes.

## Issues Encountered
None.

## Human Verification (Task 2 — checkpoint:human-verify)

Task 2 is a live-review gate with no code changes. Verification was carried out by the orchestrator directly against the actual running widget on the user's machine, following all 7 steps of the plan's `how-to-verify`:

1. Confirmed `~/.codex/auth.json` contains an unexpired token (JWT `exp` check).
2. Ran `py -3 codex_balance_widget_chrome.py` — tray icon appeared, `widget_launch.log` recorded `Balance updated (source: json)`, no Chrome window opened.
3. Killed it, relaunched with `CODEX_HOME` pointed at an empty temp directory (deliberately breaking the JSON path) — the widget did NOT crash; it fell back to Chrome, `widget_launch.log` recorded `Balance updated (source: chrome)`, and `chrome.exe` processes were confirmed running.
4. Killed it, relaunched with `CODEX_HOME` unset (clean environment) — the JSON path resumed, `widget_launch.log` recorded `Balance updated (source: json)` again.

This evidence was shown to the user in the top-level conversation, who replied "да" (yes/approved), satisfying the checkpoint's `<resume-signal>` requirement and closing out Success Criteria 1, 2, and 3 of Phase 2.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 2 (JSON provider integration) is functionally complete: `JsonUsageProvider` (02-01), `plan_fetch_outcome`/ISO reset parsing (02-02), and the live-verified `fetch_once` wiring (02-03) together satisfy all three Phase 2 Success Criteria in the running widget, not just in isolated unit tests.
- No blockers identified for subsequent phases.

---
*Phase: 02-json-provider-integration*
*Completed: 2026-07-20*
