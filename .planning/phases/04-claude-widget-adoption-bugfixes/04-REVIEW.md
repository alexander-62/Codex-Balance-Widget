---
phase: 04-claude-widget-adoption-bugfixes
reviewed: 2026-07-22T00:00:00Z
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
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-07-22
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed `claude_balance_widget.py`'s adoption of `usage_widget_common` (all 13 `RuntimeError` → `FetchError` conversions verified, each correctly classified as `retryable=True`/`False`), the new `fetch_with_retry()` wrapper around `fetch_with_retry_once`, the `compute_next_wait_seconds()` backoff schedule, the tray-tooltip truncation fix, and the hardened `sys.path` bootstrap plus the launcher/install-script/README updates that support it. Cross-referenced `usage_widget_common/errors.py` and `usage_widget_common/retry.py` (not re-reviewed themselves, per scope) only to verify the new consumer code calls them correctly.

Specifically verified clean (per the plan-checker's flagged concern): the `_load_token()` raise for a missing/empty OAuth token (line 309-311) sits outside any `except` block and correctly omits `from exc` — there is no `NameError: name 'exc' is not defined` risk anywhere in `claude_balance_widget.py`. All four `raise FetchError(...) from exc` sites inside `except urllib.error.HTTPError as exc:` (401/403/429/other) remain correctly nested within that same `except` block via `if`/fallthrough, not separate blocks, so `exc` stays bound. `test_core.py`'s new retry/backoff/tooltip assertions match the implementation's actual behavior (traced by hand against `compute_next_wait_seconds` and `fetch_with_retry_once`).

No Critical/Blocker-level defects found (no injection, no hardcoded secrets, no crash-on-steady-state-path, no OAuth token logging/persistence). Two Warnings and three Info items below are genuine gaps worth addressing, none of which block shipping this phase.

## Warnings

### WR-01: `_load_token()` can leak a raw `AttributeError` instead of a friendly `FetchError`

**File:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py:296-312`
**Issue:** `_load_token()` reads and JSON-decodes the credentials file, then does:
```python
oauth = data.get("claudeAiOauth")
token = oauth.get("accessToken") if isinstance(oauth, dict) else None
```
This guards `oauth` being a non-dict, but not `data` itself. If `.credentials.json` contains syntactically valid JSON that isn't an object (e.g. a corrupted file that decodes to `[]`, `"..."`, or `123`), `data.get("claudeAiOauth")` raises `AttributeError: '<type>' object has no attribute 'get'`. This is not caught by the surrounding `except (OSError, json.JSONDecodeError)` (that `try` block only wraps the `read_text`/`json.loads` call, and closes before this line runs), so it propagates out of `fetch()` uncaught by any `FetchError` path. It is only rescued one layer up by `fetch_with_retry_once`'s generic `except Exception as exc: error_text = f"{type(exc).__name__}: {exc}"`, which means the end user sees a raw, non-localized string like `AttributeError: 'list' object has no attribute 'get'` in the status bar/diagnostics instead of the Russian-language friendly message every other failure path produces.

The sibling method `credentials_state()` (lines 286-294) already guards this exact same shape of malformed data by including `AttributeError` in its `except (OSError, json.JSONDecodeError, AttributeError):` clause — `_load_token()` is inconsistent with it.

**Fix:**
```python
def _load_token(self) -> str:
    try:
        data = json.loads(self.credentials_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FetchError(
            "Не найден файл авторизации Claude Code. Откройте Claude Code и выполните вход."
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise FetchError("Не удалось прочитать файл авторизации Claude Code.") from exc

    oauth = data.get("claudeAiOauth") if isinstance(data, dict) else None
    token = oauth.get("accessToken") if isinstance(oauth, dict) else None
    ...
```

### WR-02: Non-429 HTTP error responses (including 5xx) are never classified as retryable

**File:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py:331-342`
**Issue:** In `fetch()`'s `except urllib.error.HTTPError as exc:` handler, only `429` gets `retryable=True`; every other HTTP status falls through to:
```python
raise FetchError(f"Anthropic вернул HTTP {exc.code}.") from exc
```
with the default `retryable=False`. This means transient server-side failures (500/502/503/504, which Anthropic's endpoint can plausibly return under load) do not get `fetch_with_retry_once`'s immediate one-shot retry — the exact "retry classification" behavior this phase was built to introduce. (Impact is partially mitigated because `_fetch_once_worker` increments `consecutive_failures` on *any* exception, so the next full refresh cycle still uses the fast 30s backoff rather than the full interval — but the in-place single retry is skipped for a class of errors that is textbook-transient.)
**Fix:**
```python
raise FetchError(
    f"Anthropic вернул HTTP {exc.code}.",
    retryable=exc.code >= 500,
) from exc
```

## Info

### IN-01: `os.sys.executable` relies on an `os`-module implementation detail

**File:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py:1646`
**Issue:** `write_log(f"Starting {APP_VERSION} via {os.sys.executable}")` reaches through `os.sys` (which only works because `os.py` happens to `import sys` internally, not because `os` documents/re-exports `sys`) instead of using the `sys` module already imported at the top of this file (`import sys`, line 16, added by this very phase for the `sys.path` bootstrap).
**Fix:** `write_log(f"Starting {APP_VERSION} via {sys.executable}")`.

### IN-02: Tray-tooltip truncation limit (127) is a bare magic number

**File:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py:776`
**Issue:** `return tooltip[:127]` hardcodes the Windows tray-tooltip character limit inline, unlike the parallel backoff schedule this same phase introduced as a named constant (`RETRY_BACKOFF_SCHEDULE_SECONDS`). The value is duplicated again in `test_core.py:114` (`assert len(_oversized_tooltip) <= 127`), so the two files must be kept in sync by hand.
**Fix:** Add `TRAY_TOOLTIP_MAX_CHARS = 127` near the other module-level constants (e.g. next to `RETRY_BACKOFF_SCHEDULE_SECONDS`) and reference it from both `build_tray_tooltip()` and `test_core.py`.

### IN-03: `sys.path` bootstrap only catches `ModuleNotFoundError`, not the broader `ImportError`

**File:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py:45-83`; also `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget_launcher.pyw:39-49`
**Issue:** `except ModuleNotFoundError as exc:` handles the sibling directory being entirely absent. If instead `d:/00_Projects/usage_widget_common` exists but is a stale/mismatched checkout missing an expected symbol (e.g. `fetch_with_retry_once` renamed/removed upstream), `from usage_widget_common.retry import fetch_with_retry_once` raises a plain `ImportError` ("cannot import name ..."), which is **not** a `ModuleNotFoundError` subclass instance from Python's perspective at the point it's raised as a distinct exception, so this `except` clause does not catch it. Run directly (`py -3 claude_balance_widget.py`), this bypasses the intended "convert to one-line `SystemExit`" hardening entirely and dumps a raw multi-frame traceback — precisely what this hardening pattern exists to avoid. (Via the launcher, the outer generic `except Exception:` still catches it gracefully, so this only affects the direct-execution path.)

Note this identical pattern (only catching `ModuleNotFoundError`) also exists in the already-reviewed `codex_balance_widget_chrome.py` bootstrap, so this is a pre-existing, fleet-wide characteristic rather than something newly introduced by this phase — flagging for awareness/future tracking, not as a phase-4 regression.
**Fix (if/when addressed):** Widen to `except (ModuleNotFoundError, ImportError) as exc:` in both files (safe, since `ModuleNotFoundError` is already a subclass of `ImportError`).

---

_Reviewed: 2026-07-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
