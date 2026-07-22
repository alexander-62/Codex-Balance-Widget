---
phase: 04-claude-widget-adoption-bugfixes
verified: 2026-07-22T21:30:00Z
status: human_needed
score: 8/9 must-haves verified (1 requires live human spot-check)
overrides_applied: 0
human_verification:
  - test: "Launch claude_balance_widget.py end-to-end (via claude_balance_widget_launcher.pyw or `py -3 claude_balance_widget.py`) against a real Claude Code .credentials.json and observe at least one full fetch cycle, ideally including one induced failure (e.g. temporarily invalidate/rename the credentials file, or block the network) to observe the 30s/60s/120s backoff and tray tooltip in real conditions."
    expected: "Usage percentages populate in the main window and tray tooltip exactly as before this phase; on an induced failure the widget's next attempt fires at ~30s (not the full 300s refresh_seconds), tray tooltip never crashes even with a long status string, and a subsequent success resets the backoff and displays fresh data with no visible regression versus pre-phase behavior."
    why_human: "Requires a live GUI session, a real OAuth-authenticated Claude Code installation, and visual/timing observation (tray icon rendering, backoff timing over multiple minutes) that cannot be replicated by grep or the existing plain-assert test_core.py suite. ROADMAP.md's own Phase 4 Success Criterion 4 explicitly names this 'manual verification' as part of the truth condition, and no live-run evidence exists in this verification session (no .credentials.json found on this machine; the plan itself marked this check 'optional follow-up, not a blocking gate' when executed autonomously with no human-verify checkpoint)."
---

# Phase 4: Claude widget adoption + bugfixes Verification Report

**Phase Goal:** `claude_balance_widget.py` (sibling repo `d:/00_Projects/claude_balance_widget_v1`) consumes the shared `usage_widget_common` package for its retry/error-classification logic, and its two known bugs (tooltip-truncation crash and slow post-401 retry) are fixed as a natural consequence of wiring in the new retry/backoff logic.
**Verified:** 2026-07-22T21:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `claude_balance_widget.py` calls the shared package's retry-once wrapper and error classification instead of any local duplicate logic (Roadmap SC1 / CLAUDE-01) | VERIFIED | `claude_balance_widget.py:63-64` imports `from usage_widget_common.errors import FetchError` and `from usage_widget_common.retry import fetch_with_retry_once`; `ClaudeUsageClient.fetch_with_retry()` (line 387-394) calls `asyncio.run(fetch_with_retry_once(_do_fetch, retry_delay=self.retry_delay))`; `_fetch_once_worker` (line 1275) calls `self.client.fetch_with_retry()` — no local duplicate retry loop exists anywhere in the file (`grep` for `time.sleep`/`for attempt in range` in the widget returns nothing). Confirmed `fetch_with_retry_once`'s actual signature/behavior in `usage_widget_common/retry.py` matches how it is called. |
| 2 | Tray tooltip truncated to 127 chars (not 160); no `ValueError: string too long` (Roadmap SC2 / CLAUDE-02) | VERIFIED | `build_tray_tooltip()` line 778: `return tooltip[:127]`. `grep -c "tooltip\[:160\]"` = 0, `grep -c "tooltip\[:127\]"` = 1. `test_core.py:206-208` builds a deliberately oversized (500-char) status string and asserts `len(result) <= 127`; ran the suite live — passes. |
| 3 | After a 401/transient error, widget retries via shared 30s→60s→120s backoff instead of the full `refresh_seconds` (Roadmap SC3 / CLAUDE-03) | VERIFIED | `compute_next_wait_seconds()` (line 270-274) implements `RETRY_BACKOFF_SCHEDULE_SECONDS = (30, 60, 120)` with correct capping; wired into `_refresh_worker` (line 1264-1266): `self.refresh_wakeup.wait(timeout=compute_next_wait_seconds(self.consecutive_failures, self.refresh_seconds))`. `self.consecutive_failures` is reset to 0 on success (line 1278) and incremented on any exception (line 1301) — read directly by `_refresh_worker` after each fetch attempt completes, so it is genuinely live-wired, not defined-but-unused. `test_core.py:212-216` asserts all 4 documented value pairs (0→300, 1→30, 2→60, 3→120, 10→120); ran live — passes. |
| 4 | Widget runs end-to-end with the new wiring, showing usage updates via the shared retry path with no behavioral regression (Roadmap SC4, roadmap text explicitly says "manual verification") | **UNCERTAIN — needs human** | `test_core.py` passes end-to-end (13+ assertions incl. retry classification, backoff, tooltip) and both sibling-repo-missing failure-mode reproductions were independently re-run in this verification session and match spec exactly (see Behavioral Spot-Checks). However, no live run against a real, authenticated `.credentials.json` was performed in this session (none found on this machine), and the ROADMAP.md phrasing for SC4 explicitly parenthesizes "(manual verification)" as part of the truth condition itself — this is a human-observable outcome (GUI rendering, live timing of the backoff over real minutes, real API response shape) that a plain-assert unit-test script cannot fully stand in for. The plan text itself acknowledges this as "optional follow-up, not a blocking gate," which is a planning-time judgment call, not evidence the live behavior was actually observed. |
| 5 | `ClaudeUsageClient.fetch()` classifies retryable errors correctly (429/network/timeout/5xx retryable=True; 401/403/other 4xx/malformed data retryable=False) | VERIFIED (exceeds original spec, in a good way) | All 13 `raise FetchError` sites read directly (lines 300-383): 401 (332-335) and 403 (336-337) → default `retryable=False`; 429 (338-341) → `retryable=True`; fallback non-2xx (342-344) → `retryable=500 <= exc.code < 600` (added by WR-02 fix pass, verified present); `URLError` (345-346) and `TimeoutError` (347-348) → `retryable=True`; JSON-decode/non-dict-payload/missing-usage-data (352-355, 383) → default `retryable=False`. `grep -c "retryable=True"` = 3 (429, URLError, TimeoutError literal sites) plus the computed 5xx expression — matches plan's acceptance criteria (3 literal `retryable=True` occurrences) with the WR-02 fix adding a 4th, computed, classification path on top, a superset of the original plan's narrower spec, not a contradiction. Test suite (`test_core.py:159-200`) exercises 500/502/503/504 (asserting `retryable is True`) and 404 (asserting `retryable is False`) live via monkeypatched `urllib.request.urlopen` — passes. |
| 6 | Sibling-repo-missing bootstrap: clean `SystemExit` (script/launcher path) vs. plain `ModuleNotFoundError` (module-import path, e.g. `test_core.py`) | VERIFIED | Read `claude_balance_widget.py:45-83` directly: existence check raises `ModuleNotFoundError` inside a `try`, caught by `except ModuleNotFoundError as exc:`, branching on `__name__ == "__main__"` to `raise SystemExit(str(exc)) from None` vs. bare `raise`. **Independently reproduced in this verification session** (not just read) via two subprocess invocations with `pathlib.Path.is_dir` monkeypatched to `False`: (a) `runpy.run_path(..., run_name="__main__")` → returncode 1, stderr contains "usage_widget_common not found", no "Traceback"; (b) `import claude_balance_widget` → non-zero exit, stderr contains both "ModuleNotFoundError" and "usage_widget_common not found". Both match the plan's exact acceptance criteria. |
| 7 | `claude_balance_widget_launcher.pyw` shows a Russian messagebox diagnostic for both SystemExit and ModuleNotFoundError sibling-missing cases; log-write failures never suppress the dialog | VERIFIED | Read launcher file directly (lines 21-60): 3-way `except SystemExit as exc` / `except ModuleNotFoundError as exc` / `except Exception` split; each wraps its `write_log(...)` call in its own `try/except OSError: pass` before the unconditional `messagebox.showerror(...)` call, so a log failure structurally cannot prevent the dialog. `grep` counts confirm exactly 1 occurrence each of `except SystemExit as exc`, `except ModuleNotFoundError as exc`, `from tkinter import messagebox`. `py -3 -m py_compile` passes. |
| 8 | `install_dependencies.bat` and `README_RU.md` document the new sibling-repo dependency | VERIFIED | `install_dependencies.bat:20-28` — `if not exist "%~dp0..\usage_widget_common\"` warning block present (3 occurrences of `usage_widget_common`). `README_RU.md:34-43` — new `## Требования` section documents the `../usage_widget_common` sibling-directory requirement in Russian, placed immediately before `## Установка` as specified. |
| 9 | `py -3 test_core.py` exits 0, covering all new retry/backoff/tooltip behaviors alongside pre-existing Balance/format assertions | VERIFIED | Ran live in this verification session: `cd /d/00_Projects/claude_balance_widget_v1 && py -3 test_core.py` → `Core tests passed (incl. retry/error-classification, tooltip truncation, backoff schedule).` exit 0. `py -3 -m py_compile claude_balance_widget.py claude_balance_widget_launcher.pyw` also exits 0. |

**Score:** 8/9 truths verified programmatically; 1 (#4, end-to-end live behavior) routed to human verification per ROADMAP.md's own "(manual verification)" wording for that success criterion.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py` | sys.path bootstrap, FetchError classification, `fetch_with_retry()`, `compute_next_wait_seconds()`, tooltip truncated to 127 | VERIFIED | All elements present, substantive (not stubs), and wired (see Truths 1, 3, 5, 6 above). |
| `d:/00_Projects/claude_balance_widget_v1/test_core.py` | Assertions covering retry/error-classification, backoff, tooltip | VERIFIED | 218-line plain-assert script; all new assertions present and executed live, exit 0. |
| `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget_launcher.pyw` | 3-way except split, OSError-guarded log writes, messagebox diagnostics | VERIFIED | Confirmed by direct read + grep counts + `py_compile`. |
| `d:/00_Projects/claude_balance_widget_v1/install_dependencies.bat` | Warning check for missing `usage_widget_common` | VERIFIED | Block present at lines 20-28, mirrors Codex's `install.bat` pattern. |
| `d:/00_Projects/claude_balance_widget_v1/README_RU.md` | `## Требования` section documenting sibling-repo dependency | VERIFIED | Present, correctly placed, in Russian, matching existing document tone. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `claude_balance_widget.py` | `usage_widget_common.errors.FetchError` | `from usage_widget_common.errors import FetchError` | WIRED | Line 63; used in 13 `raise FetchError(...)` sites throughout `ClaudeUsageClient`. |
| `claude_balance_widget.py` | `usage_widget_common.retry.fetch_with_retry_once` | `outcome = asyncio.run(fetch_with_retry_once(_do_fetch, retry_delay=self.retry_delay))` | WIRED | Line 391, inside `ClaudeUsageClient.fetch_with_retry()`; confirmed against the shared package's actual `async def fetch_with_retry_once(...)` signature in `usage_widget_common/retry.py`. |
| `ClaudeBalanceWidget._fetch_once_worker` | `ClaudeUsageClient.fetch_with_retry` | `balance, status, keys = self.client.fetch_with_retry()` | WIRED | Line 1275; result feeds `success()`/`failure()` closures that update UI state (`apply_balance`, tray tooltip) — not a dead/ignored call. |
| `ClaudeBalanceWidget._refresh_worker` | `compute_next_wait_seconds` | `self.refresh_wakeup.wait(timeout=compute_next_wait_seconds(self.consecutive_failures, self.refresh_seconds))` | WIRED | Line 1264-1266; `self.consecutive_failures` is a real, mutated state variable (reset on success line 1278, incremented on failure line 1301), not a hardcoded/static input. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `_refresh_worker`'s wait timeout | `self.consecutive_failures` | Set in `_fetch_once_worker`'s try/except (line 1278 reset-on-success, line 1301 increment-on-failure), read one thread-iteration later in `_refresh_worker` | Yes — genuinely mutated by real fetch outcomes, not a static/hardcoded value | FLOWING |
| Tray tooltip text | `status` param to `build_tray_tooltip` | `self.status_var.get()`, itself set by `set_status()` calls throughout the fetch success/failure paths | Yes — reflects real fetch state, not a static placeholder | FLOWING |
| `ClaudeUsageClient.fetch_with_retry()` return value | `outcome.value` from `fetch_with_retry_once` | Real `self.fetch()` HTTP call against `api.anthropic.com/api/oauth/usage` (unchanged endpoint) | Yes — no static/empty return substituted | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes | `cd /d/00_Projects/claude_balance_widget_v1 && py -3 test_core.py` | `Core tests passed (incl. retry/error-classification, tooltip truncation, backoff schedule).` exit 0 | PASS |
| Both modified `.py`/`.pyw` files compile cleanly | `py -3 -m py_compile claude_balance_widget.py claude_balance_widget_launcher.pyw` | exit 0 | PASS |
| Sibling-missing bootstrap: direct/launcher path → clean `SystemExit`, no traceback | Subprocess with `pathlib.Path.is_dir` monkeypatched to `False`, `runpy.run_path(..., run_name="__main__")` | returncode 1; stderr contains "usage_widget_common not found"; no "Traceback" | PASS |
| Sibling-missing bootstrap: module-import path → `ModuleNotFoundError` | Same monkeypatch, `import claude_balance_widget` | non-zero exit; stderr contains "ModuleNotFoundError" and "usage_widget_common not found" | PASS |
| All plan-specified grep/acceptance-criteria counts (13 `raise FetchError`, 0 `raise RuntimeError`, 3 literal `retryable=True`, 1 each of the import/definition/call-site greps, 1 `tooltip[:127]`, 0 `tooltip[:160]`, ≥2 `RETRY_BACKOFF_SCHEDULE_SECONDS`, ≥4 `self.consecutive_failures`) | `grep -c` on each pattern in `claude_balance_widget.py` | All match or exceed plan expectations (13 vs. plan's stated 12 is an explicitly-documented, justified deviation — see Deviations below) | PASS |
| Launcher/install-script/README grep counts | `grep -c` on each file | All ≥ plan's minimums | PASS |

Step 7b note: this is a Tkinter/pystray GUI application with a `mainloop()` and a background tray thread — it cannot be spot-checked further via non-interactive shell commands without starting a persistent process. The bootstrap/error-path checks above are the maximal safe automated spot-checks; the live GUI/network path is routed to Human Verification below.

### Probe Execution

No `scripts/*/tests/probe-*.sh` conventions or explicit probe declarations found in this phase's PLAN/SUMMARY. Step 7c: SKIPPED (no runnable probes declared or discovered for this phase; verification instead used the plan's own `test_core.py` suite plus direct subprocess reproductions above).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|------------|--------------|--------|----------|
| CLAUDE-01 | 04-01-PLAN.md | Adopt shared package's retry-once wrapper and error classification | SATISFIED | Truths 1, 5; Key Links 1-3 |
| CLAUDE-02 | 04-01-PLAN.md | Tray tooltip truncated to 127, no `ValueError: string too long` | SATISFIED | Truth 2 |
| CLAUDE-03 | 04-01-PLAN.md | 30s→60s→120s backoff after transient/auth error instead of full `refresh_seconds` | SATISFIED | Truth 3; Key Link 4 |

No orphaned requirements: `.planning/REQUIREMENTS.md`'s traceability table maps only CLAUDE-01/02/03 to Phase 4, and all three appear in `04-01-PLAN.md`'s `requirements:` frontmatter.

**Bookkeeping note (not a phase-goal gap):** `.planning/REQUIREMENTS.md` still shows CLAUDE-01/02/03 as unchecked `[ ]` / "Pending" in its traceability table as of this verification. The SUMMARY explicitly defers updating this to "the orchestrator's responsibility, not this worktree agent's" — flagging here so the orchestrator closes this bookkeeping step; it does not indicate the underlying code work is incomplete (verified independently above).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TODO`/`FIXME`/`HACK`/`PLACEHOLDER`/`TBD`/`XXX` markers found in any of the 5 modified files | — | None found — clean |
| `claude_balance_widget.py` | 1648 | `os.sys.executable` instead of the already-imported `sys.executable` (IN-01, carried from 04-REVIEW.md, deliberately deferred as out-of-scope info-level) | Info | Cosmetic only — works correctly today via CPython implementation detail, not a functional risk |
| `claude_balance_widget.py` | 778 | `tooltip[:127]` and `test_core.py`'s `<= 127` are both bare magic numbers, not a shared named constant (IN-02, deliberately deferred) | Info | Maintainability note only — no functional impact, values are consistent between the two files today |
| `claude_balance_widget.py` / `claude_balance_widget_launcher.pyw` | 65-83 / 39-49 | `except ModuleNotFoundError` does not also catch the broader `ImportError` for a stale/mismatched `usage_widget_common` checkout (IN-03, pre-existing pattern also in the already-reviewed Codex widget, deliberately deferred) | Info | Only affects the direct-execution (`py -3 claude_balance_widget.py`) path with a corrupted sibling checkout — the launcher's outer generic `except Exception:` still catches this gracefully |
| `claude_balance_widget.py` | 342-344 | WR-02's `500 <= exc.code < 600` assumes `exc.code` is always `int` (IN-04, deliberately deferred, not reachable via real `urllib` contract) | Info | Purely defensive-coding gap, not a practical regression |

All four Info items were independently confirmed present at the cited lines during this verification (not merely trusted from 04-REVIEW.md) and match the review's own "deliberately left, out of scope" disposition. No Critical or Warning-level anti-patterns found — both prior Warnings (WR-01, WR-02) were independently re-verified fixed in the actual code (see Truth 5 and the `_load_token` guard at line 306-307).

### Human Verification Required

### 1. Live end-to-end run against real Claude Code credentials

**Test:** Launch `claude_balance_widget.py` (via `claude_balance_widget_launcher.pyw` or directly) on a machine with an authenticated Claude Code installation (`~/.claude/.credentials.json` present and valid). Observe at least one successful fetch cycle. If feasible, temporarily break the credentials/network to induce a failure and observe the retry timing.
**Expected:** Usage percentages populate the main window and tray tooltip exactly as they did before this phase (no regression). On an induced failure, the widget's next fetch attempt fires at approximately 30 seconds (not the full 300-second `refresh_seconds`), escalating to 60s then 120s on repeated failures; a subsequent success resets to the normal interval and displays fresh data; the tray tooltip never raises `ValueError: string too long` even with an unusually long status message.
**Why human:** This is exactly what ROADMAP.md's Phase 4 Success Criterion 4 names as "(manual verification)" — it requires a live GUI session, a real OAuth-authenticated token, and observation of real wall-clock timing and tray-icon rendering, none of which `test_core.py`'s plain-assert script (or any grep-based check) can substitute for. No `.credentials.json` was found on the verification machine in this session, and the plan itself executed autonomously with this check marked "optional follow-up, not a blocking gate" — a planning-time judgment, not evidence the live path was actually exercised.

## Gaps Summary

No functional gaps found. All 9 derived truths pass static/automated verification except one (#4), which is not a code defect but an evidentiary gap: the phase's own roadmap-level success criterion explicitly calls for manual verification, and none has occurred yet in any session (this one included). This phase's plan made a deliberate, documented decision to treat that manual check as non-blocking and proceed autonomously — a reasonable call given the strength of the automated coverage (13 test assertions plus 2 independently-reproduced bootstrap failure-mode checks in this verification), but it does mean Success Criterion 4's literal wording ("manual verification") has not yet been satisfied by anyone. Recommend a brief live smoke-test (a few minutes, one fetch cycle, ideally one induced-failure cycle) before treating Phase 4 as fully closed, particularly since this widget touches real user credentials and was not exercised with a live token in this milestone's Phase 4 execution, review, or verification passes.

---

*Verified: 2026-07-22T21:30:00Z*
*Verifier: Claude (gsd-verifier)*
