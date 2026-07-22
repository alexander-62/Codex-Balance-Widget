---
phase: 04-claude-widget-adoption-bugfixes
plan: 01
subsystem: infra
tags: [usage_widget_common, retry, error-classification, tkinter, pystray, sys.path-bootstrap]

# Dependency graph
requires:
  - phase: 03-shared-library-extraction-codex-migration
    provides: "usage_widget_common package (errors.FetchError, retry.fetch_with_retry_once), and the hardened sys.path bootstrap / launcher / install-script pattern proven against codex_balance_widget"
provides:
  - "claude_balance_widget.py adopts usage_widget_common's FetchError classification and fetch_with_retry_once wrapper instead of raw RuntimeError"
  - "build_tray_tooltip() truncated to 127 chars (was 160), eliminating pystray's 'string too long (maximum length 128)' crash"
  - "compute_next_wait_seconds() 30/60/120s post-failure backoff schedule wired into the refresh loop via a consecutive_failures counter"
  - "Hardened sibling-repo-missing bootstrap (ModuleNotFoundError/SystemExit split) matching Phase 3's iteration-3 pattern, from day one of adoption"
  - "claude_balance_widget_launcher.pyw / install_dependencies.bat / README_RU.md updated for the new usage_widget_common dependency"
affects: [future claude_balance_widget_v1 work, any future merge/refactor of the two widgets]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sys.path sibling-repo bootstrap with ModuleNotFoundError/SystemExit split by __name__ == '__main__' (mirrored from codex_balance_widget_chrome.py)"
    - "FetchError(retryable=bool) classification: 429/URLError/TimeoutError retryable=True, everything else retryable=False"
    - "consecutive_failures counter driving compute_next_wait_seconds() backoff, reset on success"

key-files:
  created: []
  modified:
    - d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py
    - d:/00_Projects/claude_balance_widget_v1/test_core.py
    - d:/00_Projects/claude_balance_widget_v1/claude_balance_widget_launcher.pyw
    - d:/00_Projects/claude_balance_widget_v1/install_dependencies.bat
    - d:/00_Projects/claude_balance_widget_v1/README_RU.md

key-decisions:
  - "usage_widget_common.fetch_decision.decide_fetch_source NOT adopted (single data source, no primary/fallback choice to parameterize) — carried over from 04-CONTEXT.md discretion notes"
  - "usage_widget_common.redaction NOT adopted (no token/payload interpolation in any of claude_balance_widget.py's diagnostic strings, audited during planning and again during Task 1 conversion) — see threat model T-4-03"
  - "All 3 tasks' changes squashed into a single commit in claude_balance_widget_v1 (c1fbcf2), per the plan's explicit Task 3 instruction and acceptance criteria requiring exactly 2 commits total in that repo"

patterns-established:
  - "Any future widget adopting usage_widget_common should mirror this bootstrap/launcher/install-script/README pattern from its first commit, not retrofit it later"

requirements-completed: [CLAUDE-01, CLAUDE-02, CLAUDE-03]

# Metrics
duration: ~10min
completed: 2026-07-22
---

# Phase 4 Plan 1: Claude widget adoption + bugfixes Summary

**`claude_balance_widget.py` now delegates retry/error-classification to `usage_widget_common.retry.fetch_with_retry_once`/`errors.FetchError`, truncates tray tooltips to 127 chars, and backs off 30s/60s/120s after consecutive fetch failures — all shipped with the hardened sibling-repo-missing bootstrap from day one.**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-07-22T18:45:37Z
- **Tasks:** 3/3 completed
- **Files modified:** 5 (all in sibling repo `d:/00_Projects/claude_balance_widget_v1`)

## Accomplishments

- `claude_balance_widget.py` bootstraps `usage_widget_common` via the same hardened `sys.path` + `ModuleNotFoundError`/`SystemExit`-split pattern proven in Phase 3, wired in from this widget's very first adoption (not retrofitted later)
- All 12 `raise RuntimeError` sites in `ClaudeUsageClient` converted to `FetchError`, with HTTP 429 / `URLError` / `TimeoutError` correctly marked `retryable=True` and everything else (401, 403, other HTTP codes, malformed JSON/payload, missing usage data) left `retryable=False`
- `ClaudeUsageClient.fetch_with_retry()` added, delegating to the shared `fetch_with_retry_once`; `_fetch_once_worker` now calls it instead of the bare `fetch()`
- `build_tray_tooltip()` truncates to 127 chars (was 160), which previously could exceed pystray's 128-char limit and crash tray updates
- `compute_next_wait_seconds()` implements the 30 -> 60 -> 120s backoff schedule (capped, never grows unbounded), driven by a new `self.consecutive_failures` counter (reset on success, incremented on failure) and wired into `_refresh_worker`'s wait timeout
- `claude_balance_widget_launcher.pyw` hardened with a 3-way `except SystemExit` / `except ModuleNotFoundError` / `except Exception` split, each showing a Russian messagebox diagnostic, with all log-write calls guarded by `except OSError: pass` so a log failure can never suppress the dialog
- `install_dependencies.bat` now warns (Russian repo context, translated 1:1 from Codex's `install.bat`) if `../usage_widget_common` is missing
- `README_RU.md` gained a new `## Требования` section documenting the `usage_widget_common` sibling-repo dependency
- `test_core.py` extended with assertions covering all three retry/error-classification behaviors, tooltip truncation, and the four backoff-schedule values — full suite (`py -3 test_core.py`) exits 0

## Task Commits

All three tasks' code changes live in the sibling repo `d:/00_Projects/claude_balance_widget_v1` (NOT in this repo's own git history), per the plan's explicit two-repository structure. Per Task 3's explicit instruction and this plan's acceptance criteria ("exactly 2 commits total: baseline + this plan's commit"), the three tasks' changes were consolidated into a single commit in that repo:

1. **Tasks 1-3 combined (adopt retry/error-classification, fix tooltip truncation + backoff, harden launcher/install/README)** - `claude_balance_widget_v1@c1fbcf2` (feat)

`git -C /d/00_Projects/claude_balance_widget_v1 log --oneline`:

```text
c1fbcf2 feat(phase4): adopt usage_widget_common retry/error-classification; fix tooltip truncation and post-failure backoff (CLAUDE-01, CLAUDE-02, CLAUDE-03)
e1c240b Initial commit — claude_balance_widget_v1 baseline before merge with codex widget
```

**Note on commit history mechanics:** during execution, each task was initially committed atomically (3 separate commits: `58c4612` Task 1, `30e700f` Task 2, `407d455` Task 3) per the standard GSD per-task commit protocol. After completing Task 3 and re-reading its explicit "Finish this task (and the whole plan) with a single commit" instruction plus this plan's acceptance criteria requiring exactly 2 total commits, the three commits were squashed via `git reset --soft e1c240b` (safe — no shared/pushed history, no destructive `--hard`) followed by one combined commit (`c1fbcf2`) with the plan's exact specified message. No code content was lost or altered in this process; only commit-history shape changed. This repo's own worktree (`codex_balance_widget`) has no corresponding per-task commits since none of this plan's file changes live here.

**This repo's own plan metadata commit:** made separately below (SUMMARY.md only, in `codex_balance_widget`).

## Files Created/Modified

- `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py` - sys.path bootstrap, FetchError conversion (12 sites), `fetch_with_retry()`, `compute_next_wait_seconds()`, tooltip truncation, `consecutive_failures` tracking
- `d:/00_Projects/claude_balance_widget_v1/test_core.py` - retry/error-classification, tooltip truncation, and backoff-schedule test coverage
- `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget_launcher.pyw` - 3-way except split with OSError-guarded log writes and Russian messagebox diagnostics
- `d:/00_Projects/claude_balance_widget_v1/install_dependencies.bat` - sibling-repo-missing warning block
- `d:/00_Projects/claude_balance_widget_v1/README_RU.md` - new `## Требования` section

## Decisions Made

- `usage_widget_common.fetch_decision` and `usage_widget_common.redaction` deliberately not adopted (see key-decisions above and threat model T-4-03) — carried over from 04-CONTEXT.md's discretion notes, re-verified during Task 1 implementation.
- Consolidated the 3 tasks' sibling-repo commits into 1 final commit to satisfy the plan's explicit acceptance criteria (2 commits total in `claude_balance_widget_v1`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4-adjacent — plan-internal inconsistency, resolved via explicit action text] `raise FetchError` grep count is 13, not the acceptance criteria's stated 12**

- **Found during:** Task 1 verification
- **Issue:** The plan's acceptance criteria state `grep -c "raise FetchError" claude_balance_widget.py` should equal 12 (matching "12 sites total converted" from `RuntimeError`). However, the plan's own action text for `fetch_with_retry()` explicitly instructs adding a 13th, brand-new `raise FetchError(outcome.error or "Unknown fetch error")` inside that method — not a conversion of a pre-existing `RuntimeError`, so it was never part of the "12 sites converted" count. This is an internal inconsistency in the plan document (acceptance criteria didn't account for the new raise the action text explicitly requires).
- **Resolution:** Implemented exactly as the detailed action text instructs (13 total `raise FetchError` occurrences: 12 conversions + 1 new in `fetch_with_retry`), since the action text is the more specific/authoritative source of truth for what to build. All other Task 1 acceptance criteria (0 remaining `raise RuntimeError`, 3 `retryable=True`, single import lines, single `fetch_with_retry` definition, single call site) pass exactly as specified.
- **Files modified:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py`
- **Verification:** `py -3 test_core.py` exits 0; `py -3 -m py_compile claude_balance_widget.py` exits 0; behavior (transient-retry, non-retryable-401, unexpected-exception classification) all verified via test_core.py assertions with call-count checks.
- **Committed in:** `claude_balance_widget_v1@c1fbcf2` (final combined commit)

**2. [Rule 4-adjacent — plan-internal correction, applied per explicit Task 3 instruction] Combined 3 per-task commits into 1 final commit**

- **Found during:** Task 3 (after initially following the standard per-task commit protocol for Tasks 1 and 2)
- **Issue:** Standard GSD executor protocol commits each task atomically. This plan's Task 3 action explicitly overrides that for the sibling repo: "Finish this task (and the whole plan) with a single commit," and the plan's acceptance/verification criteria require `git -C claude_balance_widget_v1 log --oneline` to show exactly 2 commits total (baseline + this plan's commit).
- **Fix:** After Task 3's file edits, ran `git reset --soft e1c240b` (safe, non-destructive — no `--hard`, no shared history) to un-commit the 3 task commits back into staged changes, then created one combined commit with the plan's exact specified message.
- **Files modified:** none beyond the already-edited 5 files; only commit-history shape changed.
- **Verification:** `git -C claude_balance_widget_v1 log --oneline` shows exactly 2 commits (`e1c240b`, `c1fbcf2`); `git diff --diff-filter=D --name-only e1c240b HEAD` empty (no deletions); `py -3 test_core.py` and `py -3 -m py_compile` both still pass post-squash.
- **Committed in:** `claude_balance_widget_v1@c1fbcf2`

---

**Total deviations:** 2 (both plan-internal inconsistencies resolved by following the more explicit/authoritative instruction in the plan text; no scope creep, no unplanned functionality added).
**Impact on plan:** None on functionality — both deviations are about matching plan text precisely, not behavior changes.

## Issues Encountered

None beyond the two plan-internal inconsistencies documented above.

## Known Stubs

None.

## Threat Flags

None — this plan's threat model (T-4-01 through T-4-04, T-4-SC) fully covers the new surface introduced (sys.path bootstrap, FetchError message content, shared-retry-logic blast radius, package-manager installs). No new network endpoints, auth paths, or schema changes were introduced beyond what the threat model already anticipated.

## User Setup Required

None - no external service configuration required. The `usage_widget_common` sibling repo was already present at `d:/00_Projects/usage_widget_common` (built in Phase 3) throughout this plan's execution; the bootstrap/launcher/install-script hardening added here only takes effect if that directory is ever absent on a future fresh clone.

## Next Phase Readiness

- Roadmap Phase 4 Success Criteria 1-4 all satisfied: shared retry/error-classification adopted, tooltip crash fixed, post-failure backoff implemented, `test_core.py` passes end-to-end with no regression.
- REQUIREMENTS.md CLAUDE-01, CLAUDE-02, CLAUDE-03 ready to move from "Pending" to "Complete" (orchestrator's responsibility, not this worktree agent's).
- No blockers for milestone v1.1 completion.

---
*Phase: 04-claude-widget-adoption-bugfixes*
*Completed: 2026-07-22*

## Self-Check: PASSED

- FOUND: d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py
- FOUND: d:/00_Projects/claude_balance_widget_v1/test_core.py
- FOUND: d:/00_Projects/claude_balance_widget_v1/claude_balance_widget_launcher.pyw
- FOUND: d:/00_Projects/claude_balance_widget_v1/install_dependencies.bat
- FOUND: d:/00_Projects/claude_balance_widget_v1/README_RU.md
- FOUND: claude_balance_widget_v1@c1fbcf2 (git log --oneline --all)
