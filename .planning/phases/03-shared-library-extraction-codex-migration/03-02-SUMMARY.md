---
phase: 03-shared-library-extraction-codex-migration
plan: 02
subsystem: infra
tags: [python, stdlib, shared-library, retry, redaction, sibling-repo, refactor]

# Dependency graph
requires:
  - phase: 03-01
    provides: "usage_widget_common sibling package (errors.FetchError, redaction.redact/redaction_clean, retry.fetch_with_retry_once, fetch_decision.decide_fetch_source)"
provides:
  - "probe_wham_usage.py, json_usage_provider.py, codex_balance_widget_chrome.py all consume usage_widget_common instead of maintaining local copies of retry/error/redaction/fetch-decision logic"
  - "Proof-of-concept: the shared package works against Codex's real, tested production code, unblocking Phase 4's Claude widget adoption"
affects: [phase-4-claude-widget-adoption]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sys.path bootstrap (idempotent insert, computed from __file__) duplicated identically in 3 files to reach the sibling usage_widget_common package"
    - "ProbeError kept as a same-object alias to usage_widget_common.errors.FetchError so all existing except/isinstance call sites keep working unchanged"
    - "Domain-specific redaction denylist (REDACT_KEYS) deliberately stays local to probe_wham_usage.py, not centralized in the shared package"

key-files:
  created: []
  modified:
    - probe_wham_usage.py
    - json_usage_provider.py
    - codex_balance_widget_chrome.py

key-decisions:
  - "Followed the plan's explicit Task 2 instruction to combine both tasks' file edits into a single refactor(03-02) commit (rather than one commit per task), since the plan's own action text specifies staging all three files together at the end of Task 2 and gives one exact commit message covering the whole migration"
  - "Verified all acceptance-criteria test/import commands using PYTHONPATH=d:/00_Projects/usage_widget_common (or an explicit sys.path.insert in the one-liner the plan itself specifies) because this worktree checkout lives nested under .claude/worktrees/<id>/, so the runtime sys.path bootstrap's Path(__file__).resolve().parent.parent computation resolves to .claude/worktrees instead of d:/00_Projects inside this worktree only — the bootstrap code itself is unchanged from the plan's exact spec and resolves correctly once merged to the real d:/00_Projects/codex_balance_widget checkout"

requirements-completed: [CODEX-01]

# Metrics
duration: ~10min
completed: 2026-07-22
---

# Phase 3 Plan 2: Migrate Codex widget onto usage_widget_common Summary

**`probe_wham_usage.py`, `json_usage_provider.py`, and `codex_balance_widget_chrome.py` now import their retry-once, error-classification, redaction, and fetch-decision logic from the sibling `usage_widget_common` package via `sys.path` insertion, with all 64 pre-existing tests passing byte-for-byte unmodified.**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-07-22T17:00:21Z
- **Tasks:** 2/2 completed
- **Files modified:** 3 (all in `codex_balance_widget`, zero in the sibling `usage_widget_common` repo)

## Accomplishments

- `probe_wham_usage.ProbeError` is now `usage_widget_common.errors.FetchError` via a same-object alias — every existing `ProbeError(...)` construction, `isinstance` check, and `except ProbeError` clause keeps working unchanged
- `probe_wham_usage.redact()`/`redaction_clean()` delegate to `usage_widget_common.redaction`, with the Codex-specific `REDACT_KEYS` denylist deliberately left in place (not centralized into the shared package)
- `json_usage_provider.JsonUsageProvider._fetch_with_retry` now delegates entirely to `usage_widget_common.retry.fetch_with_retry_once`, replacing the hand-rolled `for attempt in range(2)` loop
- `codex_balance_widget_chrome.plan_fetch_outcome`'s 3-way chrome-fallback branch selection now delegates to `usage_widget_common.fetch_decision.decide_fetch_source`, with all Chrome-specific sub-branches (`browser_error`, `login_required`) kept local as sub-cases of the `"none"` decision
- Full 64-test regression suite (`test_probe_wham_usage` + `test_json_usage_provider` + `test_codex_balance_widget_chrome`) passes with zero edits to any of the three test files
- Confirmed zero changes to `d:/00_Projects/usage_widget_common` (the sibling repo) — this plan only reaches it via `sys.path` at import time

## Task Commits

Per this plan's own explicit Task 2 instruction, both tasks' file edits were combined into a single commit (see Decisions Made):

1. **Task 1 + Task 2: Migrate all three Codex files onto usage_widget_common** - `02ecb0b` (refactor) — `refactor(03-02): migrate probe_wham_usage/json_usage_provider/codex_balance_widget_chrome onto usage_widget_common (retry, error classification, redaction, fetch-decision) — no behavior change`

**Plan metadata:** captured in the final commit closing this plan (see this worktree's own git log after this SUMMARY.md is committed).

## Files Created/Modified

- `probe_wham_usage.py` — sys.path bootstrap to `usage_widget_common`; `ProbeError = FetchError` alias; `redact()` delegates to `usage_widget_common.redaction.redact` with local `REDACT_KEYS`; local `redaction_clean()` removed in favor of the shared import
- `json_usage_provider.py` — sys.path bootstrap; `_fetch_with_retry` rewritten as a thin `_do_fetch()` closure passed to `usage_widget_common.retry.fetch_with_retry_once`
- `codex_balance_widget_chrome.py` — sys.path bootstrap; `plan_fetch_outcome`'s chrome-fallback branch chain rewritten around `usage_widget_common.fetch_decision.decide_fetch_source`, preserving every message string and log line exactly

## Decisions Made

- Combined Task 1 and Task 2's file edits into one `refactor(03-02)` commit rather than two separate task commits, because the plan's Task 2 action text explicitly directs staging all three files together at the end and gives one exact commit message spanning the whole migration — this is an explicit plan-author decision on commit granularity, not a deviation from the standard per-task commit protocol.
- Verified all acceptance criteria (test runs, import checks) using `PYTHONPATH=d:/00_Projects/usage_widget_common` (in addition to the plan's own literal `sys.path.insert(0, r'd:/00_Projects/usage_widget_common')` one-liner for the final import-clean check) because this worktree checkout is nested under `.claude/worktrees/<id>/` — the shipped `sys.path` bootstrap code (`Path(__file__).resolve().parent.parent / "usage_widget_common"`) is exactly as the plan specifies and will resolve correctly once this branch is merged into the real `d:/00_Projects/codex_balance_widget` checkout, where `.parent.parent` correctly lands on `d:/00_Projects`.

## Deviations from Plan

None — plan executed exactly as written. The worktree-relative testing workaround above did not require changing any shipped code; it only affected how verification commands were invoked in this sandboxed worktree location.

## Issues Encountered

None beyond the worktree-path testing note documented above (resolved by pointing `PYTHONPATH` at the sibling package's true location for test invocations only).

## User Setup Required

None — no external service configuration required.

## Verification Results

All plan-specified verification commands were run and passed:

- `py -3 -m unittest test_probe_wham_usage test_json_usage_provider -v` (Task 1) — exit 0, 43 tests, 0 failures/errors
- `py -3 -c "import probe_wham_usage, json_usage_provider"` — exit 0, no traceback
- `py -3 -c "import codex_balance_widget_chrome"` (Task 2) — exit 0
- `py -3 -m unittest test_probe_wham_usage test_json_usage_provider test_codex_balance_widget_chrome -v` — exit 0, **64 tests, 0 failures/errors**
- `git diff --stat -- test_probe_wham_usage.py test_json_usage_provider.py test_codex_balance_widget_chrome.py` — empty, no test file touched
- `git -C /d/00_Projects/usage_widget_common status --porcelain` — empty, zero changes to the sibling repo
- `grep -c "class ProbeError(RuntimeError)" probe_wham_usage.py` — `0`; `grep -c "ProbeError = FetchError" probe_wham_usage.py` — `1`
- `grep -c "REDACT_KEYS" probe_wham_usage.py` — `3` (definition + denylist frozenset + use inside `redact()`)
- `grep -c "for attempt in range(2)" json_usage_provider.py` — `0`; `grep -c "fetch_with_retry_once" json_usage_provider.py` — `2`
- `grep -c "decide_fetch_source" codex_balance_widget_chrome.py` — `3`
- `grep -c 'chrome_status == "ok" and chrome_text' codex_balance_widget_chrome.py` — `1` (the single expected exception: the `chrome_balance = ... if (...) else None` input-computation line, not a branch — matches the plan's own acceptance-criteria caveat)
- `py -3 -c "import sys; sys.path.insert(0, r'd:/00_Projects/usage_widget_common'); import usage_widget_common; import probe_wham_usage, json_usage_provider, codex_balance_widget_chrome; print('all import clean')"` — printed `all import clean`
- `git diff --stat HEAD~1 HEAD -- requirements.txt` — empty, no new third-party dependency

## Success Criteria Status

- Roadmap Phase 3 Success Criterion 2 (`json_usage_provider.py`/`probe_wham_usage.py` import retry/classification/redaction from the shared package) — SATISFIED
- Success Criterion 3 (all existing Codex widget/provider tests pass unmodified) — SATISFIED, 64/64 tests pass with zero test-file edits
- Combined with Plan 03-01 (Success Criteria 1, 4, 5), all 5 Roadmap Phase 3 Success Criteria are now satisfied.

## Authentication Gates

None encountered.

## Known Stubs

None — all migrated code is fully wired to the shared package, no placeholders.

## Threat Flags

None — this plan's changes match exactly the surface already named in its own `<threat_model>` (T-3-04 sys.path bootstrap duplication, T-3-05 message/branch regression risk, T-3-06 shared-bug blast radius, T-3-SC no new installs). No new, unaccounted-for surface was introduced.

## Next Phase Readiness

- All 5 Roadmap Phase 3 Success Criteria satisfied; `usage_widget_common` is now proven against Codex's real production code with a full passing regression suite.
- Phase 4 (Claude widget adoption) can proceed: the shared package's API (`FetchError`, `redact`/`redaction_clean`, `fetch_with_retry_once`, `decide_fetch_source`) is generic and already validated by a second, independent consumer's full test suite.
- No blockers.

---
*Phase: 03-shared-library-extraction-codex-migration*
*Completed: 2026-07-22*

## Self-Check: PASSED

- `probe_wham_usage.py`, `json_usage_provider.py`, `codex_balance_widget_chrome.py` — all present and modified as described.
- Commit `02ecb0b` verified present in `git log --oneline --all`.
- This SUMMARY.md file verified present on disk at `.planning/phases/03-shared-library-extraction-codex-migration/03-02-SUMMARY.md`.
