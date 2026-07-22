---
phase: 03-shared-library-extraction-codex-migration
reviewed: 2026-07-22T22:15:00Z
depth: standard
iteration: 3
files_reviewed: 12
files_reviewed_list:
  - probe_wham_usage.py
  - json_usage_provider.py
  - codex_balance_widget_chrome.py
  - codex_balance_widget_launcher.pyw
  - README.md
  - README.ru.md
  - install.bat
  - d:/00_Projects/usage_widget_common/usage_widget_common/errors.py
  - d:/00_Projects/usage_widget_common/usage_widget_common/redaction.py
  - d:/00_Projects/usage_widget_common/usage_widget_common/retry.py
  - d:/00_Projects/usage_widget_common/usage_widget_common/fetch_decision.py
  - d:/00_Projects/usage_widget_common/usage_widget_common/__init__.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 03: Code Review Report (Re-review, Iteration 3 — FINAL)

**Reviewed:** 2026-07-22T22:15:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

This is the third and final allowed review iteration for this phase (3-iteration cap). I did not trust `03-REVIEW-FIX.md`'s claims at face value. For each of the 2 findings it claims to have fixed (WR-01 and WR-02 from iteration 2), I re-read the actual current file contents line-by-line, wrote and ran isolated reproduction scripts (in the scratchpad, not touching this repo) that simulate the sibling-repo-missing condition via `pathlib.Path.is_dir` monkeypatching plus `runpy.run_path`, byte-compiled all four touched files, and re-ran both full test suites from scratch (`codex_balance_widget`: 64/64 passing; `usage_widget_common`: 20/20 passing).

**Verdict on the 2 claimed fixes: both are real and correctly implemented for their stated scope.** See "Fix Verification" below for the concrete evidence. However, this fresh full pass over all 12 files found 3 new Warnings — most notably, iteration 2's own code change silently re-broke the very docstring accuracy that iteration 1's WR-01 fix had established, and iteration 2's fix report's own "known residual trade-off" (raw traceback on direct invocation with sibling missing) is still live and unresolved for 2 of the 3 bootstrapped files — plus 5 Info items (2 new, 3 carried forward from prior iterations, still unaddressed, still valid). No Critical/Blocker issues remain. Since this is the last automated iteration, all findings below are recorded as the final state of this phase's review; none should be assumed silently resolved by a future auto-fix pass.

## Fix Verification (Iteration 2 Findings)

### WR-01 (iter2) — `SystemExit`-at-import breaks `unittest` reporting: **FIXED, verified independently**

Confirmed current code in all three files:

- `probe_wham_usage.py:43-54` — dual-behavior check: `raise SystemExit(_sibling_missing_msg)` only when `__name__ == "__main__"`, else `raise ModuleNotFoundError(_sibling_missing_msg)`.
- `json_usage_provider.py:34-45` and `codex_balance_widget_chrome.py:52-65` — unconditional `raise ModuleNotFoundError(...)`.
- `codex_balance_widget_launcher.pyw:26-41` — now has both `except SystemExit as exc:` (dialog only when `exc.code not in (None, 0)`) and `except ModuleNotFoundError as exc:` (always shows `messagebox.showerror`).

I independently reproduced all three invocation modes with a monkeypatched `Path.is_dir` (scratchpad scripts, sibling directory never actually touched):

- `import probe_wham_usage` as a non-`__main__` module → raises `ModuleNotFoundError` (an `Exception` subclass), confirming `unittest`'s direct-module-name loader now reports this cleanly instead of the old silent `SystemExit` abort.
- `runpy.run_path("probe_wham_usage.py", run_name="__main__")` (mirrors `py -3 probe_wham_usage.py`) → clean single-line message on stderr, exit code 1, **no traceback** — the standalone-CLI contract is preserved.
- Direct `codex_balance_widget_chrome.py` import chain → `probe_wham_usage.py`'s check fires first (as claimed) and raises `ModuleNotFoundError`, confirming the "other two files' checks are defensive fallbacks that rarely fire first" claim is accurate.

Both test suites re-run clean: `codex_balance_widget` 64/64, `usage_widget_common` 20/20. This finding is genuinely closed **for the two scenarios it targeted** (unittest reporting, GUI launcher dialog) — see WR-02 below for a related, still-open gap the fix report itself flagged as an accepted trade-off.

### WR-02 (iter2) — README/install.bat clone instructions had no source: **FIXED, verified independently**

`README.md:25-31`, `README.ru.md:24-30`, and `install.bat:6-14` all now explicitly state `usage_widget_common` is a local, unpublished package with no git remote or PyPI listing and instruct the reader to get it from the maintainer or copy it manually — no dead-end `git clone <url>` instructions remain (grepped both READMEs and `install.bat` for "clone"/"Склонируйте"; every remaining occurrence explicitly says cloning-by-URL is *not* possible). `install.bat`'s functional presence check (`if not exist "%~dp0..\usage_widget_common\"`) is unchanged and still correct.

## Warnings

### WR-01: Iteration 2's own `ModuleNotFoundError` fix silently re-broke the docstring accuracy that iteration 1's WR-01 fix established

**File:** `probe_wham_usage.py:15-20`, `json_usage_provider.py:15-22`

**Issue:** Iteration 1 flagged stale docstrings as WR-01 and the fix was verified correct in iteration 2's review ("`probe_wham_usage.py:15-19` and `json_usage_provider.py:15-21` both now accurately describe... the possibility of `SystemExit` on a missing sibling"). That verification was accurate *at the time* — but iteration 2's own subsequent fix pass (commit `a9cd1b9`, addressing iteration-2's WR-01) then changed the actual bootstrap behavior to raise `ModuleNotFoundError` instead of `SystemExit` in almost every real invocation path, **without revisiting these same two docstrings**. They currently still read:

```text
probe_wham_usage.py:19    cloned next to this one (see README) or the bootstrap raises SystemExit.
json_usage_provider.py:18-21  ... That sibling repo must be cloned next to this one (see README) or
                               the bootstrap raises SystemExit. ... (and
                               will raise SystemExit if usage_widget_common is missing).
```

Both claims are now wrong for the overwhelmingly common case: any `import probe_wham_usage`/`import json_usage_provider` (unittest, `json_usage_provider.py` importing `probe_wham_usage`, `codex_balance_widget_chrome.py`'s transitive chain) raises `ModuleNotFoundError`, not `SystemExit` — `SystemExit` now only happens for `probe_wham_usage.py`'s own direct `__main__` invocation. The docstrings also still say "cloned next to this one," which now contradicts the corrected README wording from WR-02 (iter2) that explicitly states the sibling **cannot** be obtained via `git clone <url>`. This is the exact same class of defect iteration-1's WR-01 was created to close, reintroduced by a later, unrelated-looking fix that changed the code but not the docs it made stale — precisely the kind of drift a future contributor would trust without re-verifying.

**Fix:**

```python
"""...
Only stdlib is used directly by this module, plus the sibling
`usage_widget_common` package (also stdlib-only) reached via a
sys.path bootstrap — see the top of this file. If that sibling repo
is missing, this raises SystemExit when run directly as a script
(py -3 probe_wham_usage.py) or ModuleNotFoundError when imported
(e.g. by unittest, or by json_usage_provider.py / codex_balance_widget_chrome.py).
It must be present as a sibling directory of this repo (see README for
how to obtain it — it is not published, so `git clone <url>` will not work).
"""
```

Apply the equivalent correction to `json_usage_provider.py`'s docstring (it never has a `__main__` case at all, so its own bootstrap check only ever raises `ModuleNotFoundError` — the current "will raise SystemExit if usage_widget_common is missing" line is unconditionally false for this file).

### WR-02: The original CR-01 (iteration 1) "raw traceback on direct invocation" regression is still live for 2 of the 3 bootstrapped files — documented as an accepted trade-off, but unresolved

**File:** `json_usage_provider.py:34-45`, `codex_balance_widget_chrome.py:52-65`

**Issue:** Iteration 1's CR-01 explicitly called out `py -3 codex_balance_widget_chrome.py` (README's own documented debugging path, `README.md:44-48`) printing "a raw, untranslated Python traceback... breaking this codebase's otherwise-consistent... design" as unacceptable. `03-REVIEW-FIX.md` itself documents, as a "known residual trade-off," that its iteration-2 fix reintroduces exactly this for `json_usage_provider.py` and `codex_balance_widget_chrome.py` whenever the sibling repo is missing, because `probe_wham_usage.py`'s bootstrap check (which now fires first in both files' import chains) raises `ModuleNotFoundError`, not `SystemExit`, whenever its own `__name__` isn't `"__main__"` — which it never is when reached via these two files.

I verified this concretely with an isolated repro (`runpy.run_path`, sibling directory monkeypatched missing, real repo untouched):

```text
=== direct invocation of json_usage_provider.py, sibling missing ===
Traceback (most recent call last):
  ...
  File ".../json_usage_provider.py", line 31, in <module>
    import probe_wham_usage
  File ".../probe_wham_usage.py", line 54, in <module>
    raise ModuleNotFoundError(_sibling_missing_msg)
ModuleNotFoundError: usage_widget_common not found at ...
RETURNCODE: 1

=== direct invocation of codex_balance_widget_chrome.py, sibling missing ===
Traceback (most recent call last):
  ...
  File ".../codex_balance_widget_chrome.py", line 49, in <module>
    import json_usage_provider
  File ".../json_usage_provider.py", line 31, in <module>
    import probe_wham_usage
  File ".../probe_wham_usage.py", line 54, in <module>
    raise ModuleNotFoundError(_sibling_missing_msg)
ModuleNotFoundError: usage_widget_common not found at ...
RETURNCODE: 1
```

Only `probe_wham_usage.py`'s own direct invocation keeps the clean, traceback-free one-liner. The primary audience CR-01 was written for (GUI launcher users) remains fully fixed — the launcher shows a clean `messagebox.showerror` regardless. But the README's own documented debug command, `py -3 codex_balance_widget_chrome.py` (README.md:44-48), will show a raw multi-frame traceback to the user in exactly this one failure scenario, contradicting the "every failure path shows a clean diagnostic" principle this codebase otherwise follows carefully (e.g. `probe_wham_usage.load_tokens`'s worded `ProbeError` messages). Since this is the last auto-fix iteration and the gap was explicitly acknowledged rather than closed, it is recorded here as the final, unresolved state of this concern.

**Fix:** As iteration-2's fix report itself suggests: restructure the bootstrap check into a function invoked from within each file's own entry point / a `try/except` at import time, so `codex_balance_widget_chrome.py` (and, if it ever gains a CLI entry point, `json_usage_provider.py`) can catch `ModuleNotFoundError` at its *own* top level and re-raise as `SystemExit(str(exc))` before any transitive import propagates a raw traceback — mirroring what the launcher already does one layer up.

### WR-03: The launcher's own diagnostic-writing except-clauses have no fallback if `write_log`/`LOG_PATH.open` itself fails — the CR-01 "always show something" guarantee has a silent hole

**File:** `codex_balance_widget_launcher.pyw:16-49`

**Issue:** All three except-clauses in the launcher's top-level try/except (`except SystemExit`, `except ModuleNotFoundError` — the clause phase 3 added — and `except Exception`) call `write_log(...)` (which does `LOG_PATH.open("a", ...)`) or open `LOG_PATH` directly, with no guard around that call. If `LOG_PATH`'s directory is unwritable at that moment (disk full, read-only install location such as `Program Files` without elevation, a locked-down/network profile directory, antivirus lock, etc.), that `open()` call raises inside the except-clause itself. Because Python does not let a later `except` on the same `try` catch an exception raised while handling an earlier one (and there is no outer wrapper here), the exception propagates straight out of the whole module. Since this is a `.pyw` file (no console attached), the result is the process exiting with **zero visible symptom** — no `messagebox`, no console output, nothing — which is precisely the failure mode CR-01 (iteration 1) was written to eliminate, just triggered by a different precondition (log path unwritable) instead of the sibling repo being missing. This applies to the pre-existing `except Exception` clause too, not only the new `except ModuleNotFoundError` clause, but it is worth flagging now because phase 3's fix work specifically added a second code path (`except ModuleNotFoundError`) that inherits this same unguarded pattern rather than hardening it.

**Fix:** Wrap each except-clause's own `write_log`/log-file access in its own `try/except OSError: pass` (mirroring `write_log`'s own existing internal `except OSError: pass` at line 241 of `codex_balance_widget_chrome.py`, which already handles exactly this for its own logger), so a log-write failure can never suppress the user-facing `messagebox.showerror` call that follows it:

```python
except ModuleNotFoundError as exc:
    try:
        write_log(f"Widget exited during startup: {exc}")
    except OSError:
        pass
    messagebox.showerror("Codex Balance Widget", f"Widget failed to start:\n\n{exc}")
```

## Info

### IN-01: No regression test covers the bootstrap-missing-sibling code path (carried forward, still unaddressed)

**File:** `probe_wham_usage.py:36-54`, `json_usage_provider.py:33-45`, `codex_balance_widget_chrome.py:51-65`, `codex_balance_widget_launcher.pyw:26-41`

**Issue:** Flagged in iteration 2 as IN-01, explicitly left out of scope by the fixer (default critical+warning pass). Confirmed still true: `test_probe_wham_usage.py`, `test_json_usage_provider.py`, and `test_codex_balance_widget_chrome.py` contain no test that patches `Path.is_dir` (or equivalent) to exercise either the `SystemExit` or `ModuleNotFoundError` branch of any of the three bootstrap checks, nor a launcher-level test asserting `messagebox.showerror` fires for the `ModuleNotFoundError` case. A future edit to any of the three near-identical blocks (e.g. attempting IN-02 below) has nothing to catch a regression.

**Fix:** Add a `unittest.mock.patch("pathlib.Path.is_dir", return_value=False)` test around a fresh `importlib.reload` per module, asserting the expected exception type/message; add a launcher test mocking `runpy.run_path` with `side_effect=ModuleNotFoundError("usage_widget_common not found...")` asserting `messagebox.showerror` is called.

### IN-02: Duplicated sys.path-bootstrap block across 3 files remains unreconciled and has drifted into two non-identical variants

**File:** `probe_wham_usage.py:36-54`, `json_usage_provider.py:33-45`, `codex_balance_widget_chrome.py:51-65`

**Issue:** Originally flagged in iteration 1 (IN-01) and iteration 2 (IN-02). Still unaddressed (out of scope both times). Now additionally worth noting: the three copies are no longer even structurally identical — `probe_wham_usage.py`'s copy has the extra `__name__ == "__main__"` branch (7 lines of dual-behavior logic) while the other two are a plain 5-line unconditional-`ModuleNotFoundError` check. A future maintainer "fixing" one copy to match another (a natural instinct when de-duplicating copy-pasted code) could easily propagate the wrong variant to the wrong file.

**Fix:** Same as previously suggested: extract into one local helper (e.g. `_bootstrap.py` in `codex_balance_widget`, not in the shared package) that centralizes the existence check and exposes both the `ModuleNotFoundError`-raising import-time behavior and a `run_as_main()`-style helper for the one file (`probe_wham_usage.py`) that needs the `SystemExit` variant.

### IN-03: `ProbeError = FetchError` changes the exception's traceback identity (carried forward, still true)

**File:** `probe_wham_usage.py:79-83`

**Issue:** Unchanged since iteration 1 (IN-03). `ProbeError` is the literal `usage_widget_common.errors.FetchError` class object, so tracebacks/`type(exc)` inspection show `usage_widget_common.errors.FetchError`, not a `probe_wham_usage`-local class. Functionally inert; already has a partial explanatory comment.

**Fix:** No action required beyond the existing comment; still worth keeping in mind for future debugging sessions across the two repos.

### IN-04: Import statements after non-import statements (E402) still unsuppressed in all three bootstrap blocks

**File:** `probe_wham_usage.py:58-59`, `json_usage_provider.py:49`, `codex_balance_widget_chrome.py:69`

**Issue:** Unchanged since iteration 1 (IN-04). Grepped for `noqa` across all `.py` files in this repo — zero matches. Any standard flake8/ruff run over these files will still flag `E402` on the `from usage_widget_common...` import lines with no inline suppression or explanation for tooling.

**Fix:** Add `# noqa: E402` (or the ruff equivalent) on the affected import lines, or a top-of-block comment explicitly noting the intentional ordering.

### IN-05: Launcher's `except SystemExit` comment cites an example that cannot actually occur via the launcher's own invocation chain

**File:** `codex_balance_widget_launcher.pyw:26-30`

**Issue:** The comment reads: "...so only surface a dialog here when there is an actual message (e.g. `probe_wham_usage.py` raising `SystemExit` when run as `__main__`)." But the launcher always runs `runpy.run_path(str(SCRIPT_PATH), run_name="__main__")` where `SCRIPT_PATH` is `codex_balance_widget_chrome.py` — `probe_wham_usage.py` is only ever reached transitively (via `json_usage_provider.py`'s `import probe_wham_usage`), so its own `__name__` is always `"probe_wham_usage"`, never `"__main__"`, in this specific invocation chain. The cited example is therefore not a scenario that can actually happen through the launcher; the only `SystemExit`-with-message case the launcher can realistically observe today is a hypothetical future one deliberately raised at `codex_balance_widget_chrome.py`'s own module/`__main__` scope. Minor, but a misleading example in a comment that a future maintainer might rely on to reason about "when does this branch actually fire."

**Fix:** Reword the comment to avoid citing `probe_wham_usage.py` specifically, e.g. "...so only surface a dialog here when there is an actual message (e.g. a future `SystemExit(msg)` raised at `codex_balance_widget_chrome.py`'s own module scope; note `probe_wham_usage.py`'s own `SystemExit` branch never fires here since it only triggers when `probe_wham_usage.py` itself is `__main__`, which is not the case in this launcher's invocation chain)."

---

*Reviewed: 2026-07-22T22:15:00Z*
*Reviewer: Claude (gsd-code-reviewer)*
*Depth: standard*
*Iteration: 3 (FINAL — 3-iteration cap reached)*
