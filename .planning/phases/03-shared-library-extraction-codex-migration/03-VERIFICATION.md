---
phase: 03-shared-library-extraction-codex-migration
verified: 2026-07-22T22:45:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 3: Shared library extraction + Codex migration Verification Report

**Phase Goal:** A new stdlib-only shared package (`usage_widget_common`, at sibling repo `d:/00_Projects/usage_widget_common`) exposes retry-once, error-classification, redaction, and fetch-decision primitives extracted from Codex's already-proven `json_usage_provider.py`/`probe_wham_usage.py` patterns. The Codex widget consumes these from the shared package instead of its local copies, with no behavior change.

**Verified:** 2026-07-22T22:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (Roadmap Success Criterion) | Status | Evidence |
|---|---|---|---|
| 1 | A shared package exists exposing public retry-once, error-classification (`retryable` flag), redaction-denylist/`redaction_clean()`, and pure fetch-decision primitives, importable independently of any widget | VERIFIED | `d:/00_Projects/usage_widget_common` is a real, separate git repo (own `.git`, `main` branch, 5 commits: `ab43108`→`818632a`→`371fdfb`→`2f5624a`→`08acaf0`, no remote configured). Contains `errors.py` (`FetchError`), `redaction.py` (`redact`/`redaction_clean`), `retry.py` (`fetch_with_retry_once`), `fetch_decision.py` (`decide_fetch_source`), all re-exported from `__init__.py`. Independently ran `py -3 -c "import usage_widget_common as u; assert all([...])"` with `codex_balance_widget` explicitly stripped from `sys.path` — succeeded, all 5 symbols present. |
| 2 | `json_usage_provider.py` and `probe_wham_usage.py` import their retry/classification/redaction logic from the shared package instead of local copies | VERIFIED | `probe_wham_usage.py:62-63` — `from usage_widget_common.errors import FetchError`, `from usage_widget_common.redaction import redact as _redact_generic, redaction_clean`; line 87 `ProbeError = FetchError` (no local class remains — `grep -c "class ProbeError(RuntimeError)"` = 0); local `redact()` wrapper (line 264-270) delegates to `_redact_generic(obj, keys=REDACT_KEYS)`. `json_usage_provider.py:54` — `from usage_widget_common.retry import fetch_with_retry_once`; `_fetch_with_retry` (lines 86-100) delegates entirely to it, no manual `for attempt in range(2)` loop remains (`grep` = 0 matches). |
| 3 | All existing Codex widget/provider tests still pass unmodified in intent (import paths may change, behavior does not) | VERIFIED | Ran `py -3 -m unittest test_probe_wham_usage test_json_usage_provider test_codex_balance_widget_chrome -v` myself from the real repo root — **64/64 tests pass, exit 0**. `git diff --stat c301f77 HEAD -- test_probe_wham_usage.py test_json_usage_provider.py test_codex_balance_widget_chrome.py` (from before Phase 3 planning began) is **empty** — zero test-file edits of any kind. |
| 4 | Inspecting the shared package's imports shows stdlib only — no third-party dependencies introduced | VERIFIED | `grep -rhE "^(import |from )" usage_widget_common/*.py \| grep -Ev "<stdlib-allowlist>"` → 0 matches. Manual listing of every import line across all 5 package files confirms only `__future__`, `dataclasses`, `typing`, `asyncio`, and intra-package relative imports (`.errors`, `.redaction`, `.retry`, `.fetch_decision`). No `requirements.txt` change (`git diff --stat HEAD~1 HEAD -- requirements.txt` empty, per SUMMARY, and no such file exists in either repo). |
| 5 | The shared fetch-decision function is parameterized by primary/fallback semantics rather than hardcoded to Codex's JSON/Chrome sources, so a different widget can supply its own | VERIFIED | `decide_fetch_source(*, primary_ok: bool, fallback_ok: bool, has_existing_data: bool) -> FetchDecision` — confirmed via source read and via runtime introspection (`__code__.co_varnames` shows zero positional args, all 3 params keyword-only, no `json`/`chrome`/`codex`-named parameter anywhere). `codex_balance_widget_chrome.py:629-631` calls it with `primary_ok=False, fallback_ok=fallback_ok, has_existing_data=has_existing_data` — Chrome-specific sub-statuses (`browser_error`/`login_required`) are handled as local sub-branches of the generic `"none"` result, not baked into the shared function. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `d:/00_Projects/usage_widget_common/usage_widget_common/errors.py` | `FetchError(RuntimeError)` with keyword-only `retryable` | VERIFIED | Exists, 17 lines, exact signature `def __init__(self, message: str, *, retryable: bool = False)`; substantive (docstring + real logic), imported by `retry.py` and by `probe_wham_usage.py` (cross-repo) |
| `d:/00_Projects/usage_widget_common/usage_widget_common/redaction.py` | `redact`/`redaction_clean`, caller-supplied denylist | VERIFIED | Exists, 49 lines; `redact(obj, *, keys)` is now a **required** keyword-only arg (post-review-fix `08acaf0` — no unsafe default); `redaction_clean` with `DEFAULT_FORBIDDEN_SUBSTRINGS`; wired into `probe_wham_usage.py` via `_redact_generic(obj, keys=REDACT_KEYS)` |
| `d:/00_Projects/usage_widget_common/usage_widget_common/retry.py` | `fetch_with_retry_once(fetch_once, *, retry_delay=1.0) -> RetryOutcome` | VERIFIED | Exists, 54 lines; exact retry-once loop (`for attempt in range(2)`, single copy — confirmed 0 occurrences left in `json_usage_provider.py`); wired via `json_usage_provider._fetch_with_retry`'s `_do_fetch` closure |
| `d:/00_Projects/usage_widget_common/usage_widget_common/fetch_decision.py` | `decide_fetch_source(*, primary_ok, fallback_ok, has_existing_data) -> FetchDecision` | VERIFIED | Exists, 32 lines; exact 3-way branch (`primary`→`fallback`→`retain_existing`→`none`); wired via `codex_balance_widget_chrome.plan_fetch_outcome` |
| `d:/00_Projects/usage_widget_common/usage_widget_common/__init__.py` | Public re-export surface | VERIFIED | Exists, re-exports all 8 public names with `__all__` |
| `probe_wham_usage.py` | `ProbeError` alias + delegated redaction | VERIFIED | sys.path bootstrap (lines 40-60) + alias + wrapper, all present and exercised by the passing 37-test suite |
| `json_usage_provider.py` | `_fetch_with_retry` delegating to shared engine | VERIFIED | sys.path bootstrap (lines 34-52) + delegation, exercised by the passing 6-test suite |
| `codex_balance_widget_chrome.py` | `plan_fetch_outcome` delegating to `decide_fetch_source` | VERIFIED | sys.path bootstrap (lines 49-91, wrapped in try/except ModuleNotFoundError per WR-02 fix) + delegation (lines 623-664), exercised by the passing 21-test suite (10 `TestPlanFetchOutcome` + 3 `TestFetchOnceJsonOkNoUsageDataFallback` + others), byte-identical message/log strings confirmed via diff read |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `usage_widget_common/retry.py` | `usage_widget_common/errors.py` | `except FetchError:` | WIRED | Line 38 of `retry.py`: `except FetchError as exc:` distinguishes retryable vs. non-retryable |
| `usage_widget_common/__init__.py` | all 4 submodules | re-export imports | WIRED | All 4 `from .X import ...` lines present, `__all__` matches |
| `probe_wham_usage.py` | `usage_widget_common.errors.FetchError` | `ProbeError = FetchError` | WIRED | Confirmed exact alias line present, `grep -c "class ProbeError(RuntimeError)"` = 0, `grep -c "ProbeError = FetchError"` = 1 |
| `json_usage_provider.py` | `usage_widget_common.retry.fetch_with_retry_once` | `outcome = await fetch_with_retry_once(_do_fetch, retry_delay=self.retry_delay)` | WIRED | Confirmed exact call present at line 97 |
| `codex_balance_widget_chrome.py` | `usage_widget_common.fetch_decision.decide_fetch_source` | `decision = decide_fetch_source(primary_ok=False, fallback_ok=fallback_ok, has_existing_data=has_existing_data)` | WIRED | Confirmed exact call present at line 631 |
| `codex_balance_widget_launcher.pyw` | `codex_balance_widget_chrome.py`'s `SystemExit`/`ModuleNotFoundError` | `runpy.run_path(..., run_name="__main__")` + matching except-clauses | WIRED | Confirmed launcher has both `except SystemExit as exc:` (checks `exc.code not in (None, 0)`) and `except ModuleNotFoundError as exc:`, both guarded with `try/except OSError` around `write_log` (WR-03 fix), both call `messagebox.showerror` unconditionally after the guarded log attempt |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full `usage_widget_common` test suite passes | `cd /d/00_Projects/usage_widget_common && py -3 -m unittest discover -s tests -v` | `Ran 20 tests in 0.060s — OK` | PASS |
| Full Codex regression suite passes (64 tests) | `cd /d/00_Projects/codex_balance_widget && py -3 -m unittest test_probe_wham_usage test_json_usage_provider test_codex_balance_widget_chrome -v` | `Ran 64 tests in 0.068s — OK` | PASS |
| sys.path bootstrap resolves from the **real** repo location (not a worktree) with no manual `PYTHONPATH` | `py -3 -c "import probe_wham_usage, json_usage_provider"` and `py -3 -c "import codex_balance_widget_chrome"` run from `D:/00_Projects/codex_balance_widget` | Both exit 0, no traceback; `probe_wham_usage._SIBLING_COMMON` resolved to `D:\00_Projects\usage_widget_common` | PASS |
| Standalone `usage_widget_common` import with widget path stripped from `sys.path` | `py -3 -c "import sys; sys.path=[p for p in sys.path if 'codex_balance_widget' not in p.lower()]; import usage_widget_common as u; assert all([...])"` | `standalone import OK, all symbols present` | PASS |
| Missing-sibling diagnostic is clean (CR-01/WR-02 claim) — independently reproduced, not trusting SUMMARY | Copied `probe_wham_usage.py` alone into an isolated scratch dir (no sibling present) and ran it both as `__main__` and as an import | As `__main__`: `SystemExit`, exit code 1, one-line stderr message, **no traceback**. As import: `ModuleNotFoundError` (normal `unittest`-reportable exception) | PASS |
| No production test file modified during Phase 3 | `git diff --stat c301f77 HEAD -- test_probe_wham_usage.py test_json_usage_provider.py test_codex_balance_widget_chrome.py` | empty diff | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| SHARED-01 | 03-01 | Async retry-once wrapper for transient fetch errors | SATISFIED | `usage_widget_common.retry.fetch_with_retry_once`, 5 dedicated tests pass |
| SHARED-02 | 03-01 | Error classification (`retryable` flag) | SATISFIED | `usage_widget_common.errors.FetchError.retryable`, 3 dedicated tests pass |
| SHARED-03 | 03-01 | Redaction denylist + `redaction_clean()`-style post-check | SATISFIED | `usage_widget_common.redaction.redact`/`redaction_clean`, 6 dedicated tests pass; caller-supplied denylist enforced as required kwarg (post-fix) |
| SHARED-04 | 03-01 | Pure fetch-decision skeleton, parameterized | SATISFIED | `usage_widget_common.fetch_decision.decide_fetch_source`, 6 dedicated tests pass, confirmed generic signature |
| CODEX-01 | 03-02 | Codex widget consumes shared package, no behavior change | SATISFIED | All 3 production files migrated, 64/64 regression tests pass unmodified |

**Note (documentation lag, not a code gap):** `.planning/REQUIREMENTS.md`'s checkbox list and traceability table still show all 5 of these requirements as unchecked `[ ]` / "Pending", and `.planning/STATE.md` still shows `status: executing`, `Plan: 1 of 2`, `progress: 0%` — both stale relative to `.planning/ROADMAP.md`, which correctly shows Phase 3 as `[x]` complete with "2/2 plans complete" and a completion date. This is a tracking-doc bookkeeping gap in this repo's own `.planning/` metadata, not a deficiency in the delivered code — verified by reading `git log` for both files, which shows no commit since `bdb5aa6`/`69f1a7e` (both predating Phase 3's actual completion) touched them. Recommend the orchestrator update these two files' checkboxes/status when closing this phase, but this does not block the phase goal, which is about `usage_widget_common` and the Codex migration existing and working — both independently confirmed above.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | No `TBD`/`FIXME`/`XXX`/`HACK`/`TODO`/placeholder markers found in any of the 4 touched/created production files (`probe_wham_usage.py`, `json_usage_provider.py`, `codex_balance_widget_chrome.py`, `codex_balance_widget_launcher.pyw`) or the 5 `usage_widget_common` package files | — | INFO | Clean — grep scan returned zero debt markers. (One `REDACTED_PLACEHOLDER` constant name matched the word "PLACEHOLDER" but is a legitimate identifier, not a debt marker.) |
| `probe_wham_usage.py`, `json_usage_provider.py`, `codex_balance_widget_chrome.py` | bootstrap blocks | No regression test exercises the "sibling missing" code path (`Path.is_dir` returning False) for any of the 3 files, nor a launcher-level test for the `messagebox.showerror` dialog | INFO | Carried forward from `03-REVIEW.md` as IN-01, explicitly disclosed and left out of scope by the review-fix (critical+warning-only pass). I independently reproduced this path manually (see Behavioral Spot-Checks) and confirmed the current behavior is correct, but there is no automated test guarding it going forward — a future edit to any of the 3 bootstrap blocks could regress silently. |
| `probe_wham_usage.py`, `json_usage_provider.py`, `codex_balance_widget_chrome.py` | bootstrap blocks | The 3 sys.path bootstrap blocks are near-duplicated but not structurally identical (`probe_wham_usage.py`'s has an extra `__name__ == "__main__"` branch the other two lack) | INFO | Carried forward as IN-02. Functionally correct today (independently confirmed above) but a maintainability risk for future edits. |
| `probe_wham_usage.py:87` | `ProbeError = FetchError` | Traceback/`type(exc)` identity shows `usage_widget_common.errors.FetchError`, not a `probe_wham_usage`-local name | INFO | Carried forward as IN-03. Functionally inert, already documented in-code. |
| 3 bootstrap blocks | import-after-code (E402) | Unsuppressed `E402` lint warnings on the `from usage_widget_common...` import lines | INFO | Carried forward as IN-04. Cosmetic/tooling-only. |
| `codex_balance_widget_launcher.pyw:26-30` | comment | Misleading comment citing a scenario (`probe_wham_usage.py` raising `SystemExit` via the launcher) that cannot occur through the launcher's actual invocation chain | INFO | Carried forward as IN-05. Comment-only, no behavioral impact. |

All 5 of the above INFO items were independently confirmed to still be true by re-reading the actual current file contents (not merely trusting `03-REVIEW.md`'s claim that they remain). None rise to Warning/Blocker level — they were explicitly triaged as INFO by the phase's own 3-iteration review cycle, and I found no evidence contradicting that triage.

### Human Verification Required

None. This is a pure infra/refactor phase (no new user-facing behavior, per its own `03-CONTEXT.md` phase-boundary declaration). All success criteria are objectively verifiable via file inspection, git history inspection, and automated test execution — all of which were performed independently in this verification pass, including independent reproduction of the "sibling repo missing" edge case outside the normal test suite. No `<human-check>` blocks were found in either PLAN.md.

### Gaps Summary

No gaps. All 5 Roadmap Phase 3 Success Criteria are independently verified against the actual codebase (not just SUMMARY/REVIEW narrative):

1. The shared package genuinely exists as an independent git repository (5 commits, own history, no shared lineage with `codex_balance_widget`, confirmed via `git -C d:/00_Projects/usage_widget_common rev-parse --is-inside-work-tree` = `true` and `git log --oneline` showing its own commit chain) — not a worktree artifact, not a subdirectory of this repo.
2. All three named Codex files (`probe_wham_usage.py`, `json_usage_provider.py`, `codex_balance_widget_chrome.py`) genuinely import from the shared package — confirmed via direct source read of every import/delegation line, not via the SUMMARY's grep-count claims alone.
3. The sys.path bootstrap mechanism was independently exercised (a) from the real repo location with no manual `PYTHONPATH`, confirming it resolves correctly outside of the worktree environment the SUMMARY.md flagged as a testing complication, and (b) with the sibling deliberately made "missing" in an isolated scratch copy, confirming the documented clean-diagnostic behavior (SystemExit/ModuleNotFoundError split) is real, not just described.
4. The full 64-test Codex suite was re-run fresh by this verification (not copied from SUMMARY output) and passes, with an empty `git diff --stat` confirming zero test-file edits since before Phase 3 began.
5. No orphaned TBD/FIXME/XXX/stub/placeholder markers were found in any of the touched or created files; the 5 remaining Info-level findings from the phase's own review cycle were independently re-confirmed as still accurate and correctly classified as non-blocking.

One non-blocking documentation observation is noted above (stale `REQUIREMENTS.md`/`STATE.md` tracking metadata) for the orchestrator's awareness when closing this phase, but it does not affect the goal-achievement verdict.

---

_Verified: 2026-07-22T22:45:00Z_
_Verifier: Claude (gsd-verifier)_
