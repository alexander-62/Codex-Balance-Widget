---
phase: 04-claude-widget-adoption-bugfixes
reviewed: 2026-07-22T19:06:31Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py
  - d:/00_Projects/claude_balance_widget_v1/test_core.py
  - d:/00_Projects/claude_balance_widget_v1/claude_balance_widget_launcher.pyw
  - d:/00_Projects/claude_balance_widget_v1/install_dependencies.bat
  - d:/00_Projects/claude_balance_widget_v1/README_RU.md
findings:
  critical: 0
  warning: 0
  info: 4
  total: 4
status: issues_found
---

# Phase 04: Code Review Report (iteration 2 — re-review after fix pass)

**Reviewed:** 2026-07-22T19:06:31Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found (Info only — both prior Warnings verified fixed)

## Summary

This is a re-review of `d:/00_Projects/claude_balance_widget_v1` after fix commits `44da854` (WR-01) and `5dfce97` (WR-02) were applied on top of the phase-4 baseline reviewed in `04-REVIEW.iter1.md`. Both fixes were verified by reading the actual current code (not by trusting the commit messages) and by running `test_core.py`, which passes end-to-end (`py -3 test_core.py` → "Core tests passed...").

**WR-01 (verified FIXED).** `claude_balance_widget.py:306` now reads `oauth = data.get("claudeAiOauth") if isinstance(data, dict) else None`, correctly guarding the case where `.credentials.json` decodes to a non-dict JSON value (list/string/number/null). Traced by hand: for `data` = `[]`, `"str"`, `123`, or `None`, `isinstance(data, dict)` is `False` so `oauth` is `None`, then `token = oauth.get(...) if isinstance(oauth, dict) else None` also short-circuits to `None`, and the existing `if not isinstance(token, str) or not token.strip(): raise FetchError(...)` fires — a clean, localized `FetchError` instead of a raw `AttributeError`. `test_core.py:119-151` exercises exactly this: top-level `[]`, `"just a string"`, `123`, and a dict with `claudeAiOauth` set to a non-dict string, asserting `FetchError` is raised and no `AttributeError` leaks. Confirmed by running the suite.

**WR-02 (verified FIXED).** `claude_balance_widget.py:342-344` now raises `FetchError(f"Anthropic вернул HTTP {exc.code}.", retryable=500 <= exc.code < 600)` in the fallback branch of the `HTTPError` handler (after the 401/403/429 special cases). Traced by hand against `usage_widget_common/retry.py`'s `fetch_with_retry_once`: a `FetchError(retryable=True)` on the first attempt now correctly triggers the one-shot retry for 500/502/503/504, while non-5xx/429/403/401 codes (e.g. 404) remain `retryable=False`, matching the pre-existing "unchanged behavior" contract. `test_core.py:159-200` covers all of 500/502/503/504 (asserting `retryable is True`) plus a 404 sanity check (asserting `retryable is False`). Confirmed by running the suite.

No new Critical or Warning-level defects were introduced by either fix commit — both diffs are minimal (1-3 lines each in the non-test file) and self-contained; neither touches any other code path. A fresh full pass over `claude_balance_widget.py`, `test_core.py`, `claude_balance_widget_launcher.pyw`, `install_dependencies.bat`, and `README_RU.md` (checking for regressions, dead code, unused imports, race conditions, and re-verifying the retry/backoff/tooltip/token-loading logic end-to-end) found no additional Critical or Warning issues. The four Info items below are either carried forward from iteration 1 (still unaddressed, none introduced or worsened by this fix pass) or a new minor robustness note on the WR-02 diff itself.

## Info

### IN-01: `os.sys.executable` relies on an `os`-module implementation detail

**File:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py:1648`
**Issue:** `write_log(f"Starting {APP_VERSION} via {os.sys.executable}")` reaches through `os.sys` (works only because `os.py` happens to `import sys` internally) instead of the `sys` module already imported at the top of the file (`import sys`, line 16). Carried forward unchanged from iteration 1 (`04-REVIEW.iter1.md` IN-01); not touched by either fix commit.
**Fix:** `write_log(f"Starting {APP_VERSION} via {sys.executable}")`.

### IN-02: Tray-tooltip truncation limit (127) is a bare magic number

**File:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py:778`
**Issue:** `return tooltip[:127]` hardcodes the Windows tray-tooltip character limit inline, duplicated again in `test_core.py:208` (`assert len(_oversized_tooltip) <= 127`). Carried forward unchanged from iteration 1 (IN-02); not touched by either fix commit.
**Fix:** Add `TRAY_TOOLTIP_MAX_CHARS = 127` near the other module-level constants (e.g. next to `RETRY_BACKOFF_SCHEDULE_SECONDS`) and reference it from both `build_tray_tooltip()` and `test_core.py`.

### IN-03: `sys.path` bootstrap only catches `ModuleNotFoundError`, not the broader `ImportError`

**File:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py:65-83`; also `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget_launcher.pyw:39-49`
**Issue:** If `usage_widget_common` exists but is a stale checkout missing an expected symbol (e.g. `fetch_with_retry_once` renamed upstream), `from usage_widget_common.retry import fetch_with_retry_once` raises a plain `ImportError`, which the narrower `except ModuleNotFoundError as exc:` does not catch — bypassing the intended clean-`SystemExit` hardening on the direct-execution path (`py -3 claude_balance_widget.py`). Carried forward unchanged from iteration 1 (IN-03); not touched by either fix commit. Confirmed still present at the cited line numbers.
**Fix (if/when addressed):** Widen to `except (ModuleNotFoundError, ImportError) as exc:` in both files.

### IN-04: WR-02's new `500 <= exc.code < 600` comparison assumes `exc.code` is always an `int`

**File:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py:342-344`
**Issue:** Prior to commit `5dfce97`, `exc.code` was only ever compared with `==` (`exc.code == 401`, etc.), which is safe against any comparable type. The new fallback branch introduces an ordering comparison, `500 <= exc.code < 600`, which would raise `TypeError: '<=' not supported between instances of ...` if `exc.code` were ever `None` or non-numeric. In practice `urllib.request.urlopen`'s `HTTPDefaultErrorHandler` always constructs `HTTPError` with an `int` status code from the response line, so this is not reachable via the real network path and is not a practical regression — noted only as a defensive-coding gap newly introduced by this specific diff, not as a functional bug.
**Fix (optional, low priority):** `retryable=isinstance(exc.code, int) and 500 <= exc.code < 600` if defending against a hypothetical malformed `HTTPError` is desired; otherwise safe to leave as-is given `urllib`'s actual contract.

---

_Reviewed: 2026-07-22T19:06:31Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
