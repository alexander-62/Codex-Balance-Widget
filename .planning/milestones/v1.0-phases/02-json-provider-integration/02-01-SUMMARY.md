---
phase: 02-json-provider-integration
plan: 01
subsystem: api
tags: [probe_wham_usage, asyncio, retry, error-classification, unittest]

# Dependency graph
requires:
  - phase: 01-json-endpoint-probe
    provides: "probe_wham_usage.py core (load_tokens, fetch_usage, extract_fields, ProbeError) with 23 green stdlib tests"
provides:
  - "ProbeError.retryable flag on probe_wham_usage.py, marking 429/URLError/TimeoutError as transient"
  - "json_usage_provider.py: JsonUsageProvider (async fetch, retry-once policy) + JsonFetchResult dataclass"
affects: [02-03-codex_balance_widget_chrome-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.to_thread wrapping of blocking stdlib urllib calls (first use in this codebase)"
    - "retryable flag on a shared exception class instead of exception subclassing, to distinguish transient vs terminal errors while keeping call sites simple"
    - "one-retry-then-give-up policy (D-02/D-03): non-retryable errors fail immediately, retryable errors get exactly one delayed retry before surfacing status='error'"

key-files:
  created: [json_usage_provider.py, test_json_usage_provider.py]
  modified: [probe_wham_usage.py, test_probe_wham_usage.py]

key-decisions:
  - "ProbeError gained a keyword-only retryable flag (default False) rather than new exception subclasses, preserving the 23 existing Phase 1 raise-site call patterns untouched."
  - "Only 429, URLError, and TimeoutError are marked retryable=True; all other raise sites (401, 403 html/json, other HTTP codes, non-JSON content-type, malformed JSON) default to retryable=False, matching D-02/D-03 exactly."
  - "json_usage_provider.py is a new standalone stdlib-only module (not merged into codex_balance_widget_chrome.py or probe_wham_usage.py), keeping the widget file untouched in this plan per its own frontmatter files_modified list and per D-CONTEXT's Claude's Discretion."
  - "JsonUsageProvider.fetch() does not retry on load_tokens failure (auth/config problems do not self-heal within a single fetch cycle) — retry-once only applies to the HTTP fetch_usage step, per plan's task 2 action spec."

patterns-established:
  - "Retry-once wrapper pattern: JsonUsageProvider._fetch_with_retry() catches ProbeError, branches on .retryable, sleeps once via asyncio.sleep(self.retry_delay), retries exactly once, and returns JsonFetchResult(retried=True) either way on the second attempt — no unbounded retry loop (mitigates T-2-01 DoS threat from unbounded retries on sustained 429)."

requirements-completed: [JSONPROV-02]

# Metrics
duration: 24min
completed: 2026-07-20
---

# Phase 2 Plan 1: ProbeError.retryable + json_usage_provider.py Summary

**Extended `probe_wham_usage.ProbeError` with a `retryable` flag (429/URLError/TimeoutError = True, all else False) and built `json_usage_provider.py` — a new stdlib-only async wrapper (`JsonUsageProvider.fetch()` / `JsonFetchResult`) implementing exactly one retry on transient errors and immediate fallback-signal on 401/403, fully unit-tested without network access.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-07-20T17:41:40Z (STATE.md last_updated at plan start)
- **Completed:** 2026-07-20T17:54:50Z
- **Tasks:** 2 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- `ProbeError.retryable` (keyword-only, default `False`) added without changing any existing public signature or any Russian diagnostic message text — all 23 pre-existing Phase 1 tests pass unchanged.
- `fetch_usage`'s three transient-error raise sites (HTTP 429, `urllib.error.URLError`, `TimeoutError`) now set `retryable=True`; every other raise site (401, 403 html/json, other HTTP codes, non-JSON content-type, malformed JSON) stays `retryable=False` by default — verified via `grep -c "retryable=True" probe_wham_usage.py` == 3.
- New `json_usage_provider.py`: `JsonUsageProvider.fetch()` (async) loads tokens, then attempts `fetch_usage` once; on a retryable `ProbeError` it sleeps briefly and retries exactly once; on a non-retryable `ProbeError` (or a second failure after retry) it returns `JsonFetchResult(status="error", ...)` immediately — implementing D-02 (401/403 → no retry) and D-03 (429/network/timeout → one retry) on top of the already-tested HTTP classification in `probe_wham_usage.fetch_usage`.
- 38 total unit tests pass with zero network access and no dependency on a real `~/.codex/auth.json` (23 Phase 1 + 10 new Task 1 classification tests + 5 new Task 2 provider tests).

## Task Commits

Each task was committed atomically using RED→GREEN TDD gates:

1. **Task 1: ProbeError.retryable in probe_wham_usage.py**
   - `de7df17` (test) - failing tests for `ProbeError.retryable` default/explicit + HTTP error classification (401/403-html/403-json/429/500/URLError/timeout/success)
   - `1442999` (feat) - `ProbeError.retryable` keyword-only flag; 429/URLError/TimeoutError marked `retryable=True`

2. **Task 2: json_usage_provider.py — async wrapper with retry-once**
   - `73a4c22` (test) - failing tests for `JsonUsageProvider.fetch` retry-once behavior (load_tokens failure, non-retryable, retryable-then-success, retryable-twice-gives-up, immediate-success)
   - `bacd31a` (feat) - `JsonUsageProvider` / `JsonFetchResult` implementation using `asyncio.to_thread` around blocking `probe_wham_usage` calls

_Note: worktree isolation mode — this plan does not update STATE.md/ROADMAP.md; orchestrator applies those after merge._

## Files Created/Modified
- `probe_wham_usage.py` - Added `ProbeError.retryable` keyword-only flag (default `False`); marked the 429, `URLError`, and `TimeoutError` raise sites in `fetch_usage` as `retryable=True`. No message text or public signature changed.
- `test_probe_wham_usage.py` - Added `TestProbeErrorRetryable` (2 tests) and `TestFetchUsageErrorClassification` (8 tests: 401, 403-html, 403-json, 429, 500, URLError, timeout, success) covering the full retryable/non-retryable matrix via mocked `urlopen`.
- `json_usage_provider.py` (new) - `JsonFetchResult` dataclass (`status`, `fields`, `error`, `retried`) and `JsonUsageProvider` class (`fetch()`, `_fetch_with_retry()`, `_fetch_payload()`), async, stdlib-only, no Tk/UI or widget-file dependency.
- `test_json_usage_provider.py` (new) - `unittest.IsolatedAsyncioTestCase` suite (5 tests) with `retry_delay=0` in every test to avoid real waits, mocking `probe_wham_usage.load_tokens` / `probe_wham_usage.fetch_usage`.

## Decisions Made
- See `key-decisions` in frontmatter above. All decisions were direct implementations of the plan's `<action>` specs and 02-CONTEXT.md's D-02/D-03/D-04 — no architectural deviation from plan.

## Deviations from Plan

None - plan executed exactly as written. Both tasks followed their `<behavior>`/`<action>` specs precisely; no Rule 1-4 auto-fixes were needed.

## Issues Encountered
- Minor `ResourceWarning: Implicitly cleaning up <HTTPError ...>` warnings appear in test output for some `HTTPError`-raising mock tests (unclosed `io.BytesIO` fp handled by `tempfile`'s finalizer, not a real resource leak since these are in-memory buffers). Does not affect test outcome (still `OK`, exit 0) or Phase 1 test count; not in scope to silence per the plan's acceptance criteria (only exit code and pass/fail count are gated). Left as-is; noted here for visibility.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `json_usage_provider.py` is a ready, fully-tested, async-compatible JSON data source for `codex_balance_widget_chrome.py`, to be wired in by Plan 02-03 at the `fetch_once` integration point identified in 02-PATTERNS.md.
- `codex_balance_widget_chrome.py` was not touched in this plan (verified via `git status --porcelain codex_balance_widget_chrome.py` — empty output), leaving it fully available for Plan 02-03's integration work.
- No blockers for downstream plans in this phase.

## Self-Check: PASSED

All created/modified files confirmed present (`probe_wham_usage.py`, `test_probe_wham_usage.py`, `json_usage_provider.py`, `test_json_usage_provider.py`, this SUMMARY.md). All 4 task commit hashes (`de7df17`, `1442999`, `73a4c22`, `bacd31a`) confirmed present in `git log --oneline --all`.

---
*Phase: 02-json-provider-integration*
*Completed: 2026-07-20*
