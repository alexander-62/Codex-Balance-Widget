---
phase: 02-json-provider-integration
plan: 02
subsystem: api
tags: [python, unittest, dataclasses, regex, datetime]

# Dependency graph
requires:
  - phase: 02-json-provider-integration (Plan 02-01)
    provides: "probe_wham_usage.extract_fields() dict shape (five_hour_percent, weekly_percent, credits, five_hour_reset_text, weekly_reset_text) and its ISO '%Y-%m-%d %H:%M' reset-text format"
provides:
  - "ISO reset-date branch in parse_reset_datetime, so JSON-provider reset strings parse to absolute datetimes instead of being misread as 'next occurrence today/tomorrow'"
  - "build_balance_from_json_fields(fields) -> Balance, a pure JSON-to-Balance mapper mirroring BalanceParser.parse's constructor shape"
  - "FetchOutcome dataclass + plan_fetch_outcome(...) pure decision function reproducing fetch_once's full current branching (JSON success, JSON-fail without Chrome, JSON-fail+Chrome success/failure, keep-last-data-on-screen) plus D-05 source logging and Chrome-fallback status suffix"
  - "test_codex_balance_widget_chrome.py — first unit test file for codex_balance_widget_chrome.py (17 tests, no Tkinter/Chrome)"
affects: [02-json-provider-integration (Plan 02-03 fetch_once integration)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure decision function (plan_fetch_outcome) separated from async I/O orchestration, so fetch_once can become a thin wrapper in Plan 02-03"
    - "TDD RED/GREEN commit pairs per task (test(...) then feat(...))"

key-files:
  created:
    - test_codex_balance_widget_chrome.py
  modified:
    - codex_balance_widget_chrome.py

key-decisions:
  - "ISO reset-date branch placed after en_match and before the relative/time-only fallbacks in parse_reset_datetime, so full ISO datetimes are captured before the time-only regex could truncate them to just hour:minute"
  - "build_balance_from_json_fields and FetchOutcome/plan_fetch_outcome placed between format_compact_countdown and BalanceParser, per repo convention for helper placement"
  - "plan_fetch_outcome takes keyword-only args and returns FetchOutcome without touching UI/asyncio state, so fetch_once (Plan 02-03) only needs to call it and apply the result"

patterns-established:
  - "Pure business-logic helpers for fetch_once are unit-tested directly via plan_fetch_outcome, without constructing CodexBalanceWidget or launching Tkinter/Chrome"

requirements-completed: [JSONPROV-01, JSONPROV-03]

# Metrics
duration: 25min
completed: 2026-07-20
---

# Phase 2 Plan 02: ISO reset-date parsing + JSON-to-Balance glue + fetch decision function Summary

**Added ISO reset-date parsing, a JSON-fields-to-Balance mapper, and a pure `plan_fetch_outcome` decision function that reproduces every status message currently in `fetch_once`, all covered by 17 new unit tests — `fetch_once` itself is untouched, ready for Plan 02-03 to wire it in.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-20T20:52:00+03:00 (approx)
- **Completed:** 2026-07-20T20:56:14+03:00
- **Tasks:** 2 completed
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- `parse_reset_datetime` now correctly parses ISO `"%Y-%m-%d %H:%M"` reset strings (the exact format `probe_wham_usage._reset_text` produces) into absolute datetimes, fixing the pre-existing regression where such strings fell through to the time-only fallback and lost their date
- `build_balance_from_json_fields` maps `probe_wham_usage.extract_fields()` dicts directly onto `Balance`, with no text parsing, using `.get()` so extra keys (`windows`, `missing`) are ignored safely
- `FetchOutcome`/`plan_fetch_outcome` fully reproduce `fetch_once`'s current decision tree (JSON success incl. weekly-exhausted messaging, JSON-fail with no Chrome available, JSON-fail+Chrome success/failure in all sub-cases, and the "show last saved data" UX gate) plus the new D-05 source-tracking log line and Chrome-fallback status suffix (never duplicated on messages that already mention Chrome)
- First unit test file for `codex_balance_widget_chrome.py` (`test_codex_balance_widget_chrome.py`), 17 tests, stdlib `unittest` only, no Tkinter/Chrome/network

## Task Commits

Each task followed TDD RED -> GREEN:

1. **Task 1: ISO reset-date + build_balance_from_json_fields**
   - `e380f96` test(02-02): add failing tests for ISO reset date + build_balance_from_json_fields
   - `109c1e5` feat(02-02): add ISO reset-date parsing + build_balance_from_json_fields
2. **Task 2: FetchOutcome / plan_fetch_outcome**
   - `f894e9a` test(02-02): add failing tests for FetchOutcome/plan_fetch_outcome
   - `b7dd668` feat(02-02): add FetchOutcome/plan_fetch_outcome decision function

_TDD gate sequence verified: each task has a `test(...)` commit (confirmed failing via ImportError before the fix) followed by a `feat(...)` commit (confirmed all tests green after)._

## Files Created/Modified
- `codex_balance_widget_chrome.py` - added ISO branch in `parse_reset_datetime`; added `build_balance_from_json_fields`, `FetchOutcome`, `plan_fetch_outcome` between `format_compact_countdown` and `class BalanceParser`; `fetch_once`/`__init__` untouched (verified via diff against phase-start commit)
- `test_codex_balance_widget_chrome.py` - new file; `TestParseResetDatetimeIso` (6 tests), `TestBuildBalanceFromJsonFields` (2 tests), `TestPlanFetchOutcome` (9 tests)

## Decisions Made
None beyond what's captured in `key-decisions` above — implementation followed the plan's specified logic and placement exactly.

## Deviations from Plan

None - plan executed exactly as written. Followed strict TDD by reverting the pre-written implementation with `git checkout -- codex_balance_widget_chrome.py` before writing tests, confirming each RED failure (ImportError) before re-applying the implementation and confirming GREEN, to keep the `test(...)` -> `feat(...)` commit pairing accurate to the actual RED/GREEN cycle rather than committing tests that were already passing.

## Issues Encountered
None.

## TDD Gate Compliance

Both tasks have a `test(...)` commit followed by a `feat(...)` commit in git log, with RED (ImportError, confirmed via `py -3 -m unittest`) verified before each `feat` commit and GREEN (17/17 passing) verified after. No gate violations.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`build_balance_from_json_fields` and `plan_fetch_outcome` are pure, fully tested, and ready for Plan 02-03 to call from inside `fetch_once` without further logic changes. `fetch_once`/`__init__` remain exactly as they were at phase start (verified via `git diff` against the pre-plan commit and `git status --porcelain` on `json_usage_provider.py`/`probe_wham_usage.py` showing no changes to Plan 02-01's files). `test_probe_wham_usage.py` remains green (23/23), confirming no regression to Phase 1's work.

---
*Phase: 02-json-provider-integration*
*Completed: 2026-07-20*

## Self-Check: PASSED

- FOUND: test_codex_balance_widget_chrome.py
- FOUND: .planning/phases/02-json-provider-integration/02-02-SUMMARY.md
- FOUND commit: e380f96 (test(02-02): failing tests for ISO reset date + build_balance_from_json_fields)
- FOUND commit: 109c1e5 (feat(02-02): ISO reset-date parsing + build_balance_from_json_fields)
- FOUND commit: f894e9a (test(02-02): failing tests for FetchOutcome/plan_fetch_outcome)
- FOUND commit: b7dd668 (feat(02-02): FetchOutcome/plan_fetch_outcome decision function)
