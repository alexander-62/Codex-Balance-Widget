---
phase: 03-shared-library-extraction-codex-migration
reviewed: 2026-07-22T21:30:00Z
depth: standard
iteration: 2
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
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 03: Code Review Report (Re-review, Iteration 2)

**Reviewed:** 2026-07-22T21:30:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

This is a re-review after a fixer pass (`03-REVIEW-FIX.md`) that claimed to close all 3 in-scope findings from iteration 1 (`03-REVIEW.iter1.md`): CR-01 (unhandled hard dependency on the sibling `usage_widget_common` repo), WR-01 (stale "stdlib-only" docstrings), and WR-02 (unsafe `redact()` default).

I did not trust the fix report's claims at face value. For each of the 3 claimed fixes I re-read the actual current file contents, inspected the exact fix commits (`9a1b4c2`, `4919353`, `3d5a24b` in this repo; `08acaf0` in the sibling `usage_widget_common` repo), grepped both repos (and `claude_balance_widget_v1`, the other stated consumer of the shared package) for every remaining call site of the changed API, byte-compiled all touched `.py`/`.pyw` files, and re-ran both full test suites from scratch (`usage_widget_common`: 20/20 passing; `codex_balance_widget`: 64/64 passing).

**Verdict: all 3 claimed fixes are real, correctly implemented, and complete for their stated scope.** See "Fix Verification" below for details. However, the CR-01 fix pass itself introduces two new, provable gaps of its own (one behavioral, one documentation), written up as WR-01/WR-02 below, plus two Info-level follow-ups.

## Fix Verification (Iteration 1 Findings)

### CR-01 — Unhandled hard dependency on sibling repo: **FIXED** (with caveats, see WR-01/WR-02 below)

Confirmed present in all three files, with byte-identical logic:
- `probe_wham_usage.py:36-44`
- `json_usage_provider.py:33-41`
- `codex_balance_widget_chrome.py:51-59`

```python
_SIBLING_COMMON = Path(__file__).resolve().parent.parent / "usage_widget_common"
if not _SIBLING_COMMON.is_dir():
    raise SystemExit(
        f"usage_widget_common not found at {_SIBLING_COMMON}.\n"
        "Clone it as a sibling of this repo (see README) before running "
        "probe_wham_usage.py / the widget."
    )
if str(_SIBLING_COMMON) not in sys.path:
    sys.path.insert(0, str(_SIBLING_COMMON))
```

`codex_balance_widget_launcher.pyw:26-33` now imports `tkinter.messagebox` and catches `SystemExit` explicitly, showing `messagebox.showerror(...)` only when `exc.code not in (None, 0)` — correctly distinguishing the new missing-sibling `SystemExit(message)` case from the pre-existing bare `raise SystemExit` "already running" app-lock case (which already shows its own `messagebox.showinfo` in `codex_balance_widget_chrome.py`'s `__main__` block, and would double-dialog the user if not excluded here). Traced this exclusion logic by hand — correct. The generic `except Exception:` branch in the launcher now also shows a `messagebox.showerror`, closing the original "no messagebox, no console, no visible symptom at all" gap for real. `README.md`, `README.ru.md`, and `install.bat` were all updated to state the sibling-repo requirement.

For the two documented usage paths this fixes cleanly:
- Launcher path (`run.bat` → `run_hidden.vbs` → `codex_balance_widget_launcher.pyw`): missing sibling now surfaces a clean `messagebox.showerror` dialog. Confirmed by tracing the exception-propagation chain (`import json_usage_provider` at `codex_balance_widget_chrome.py:49` transitively triggers `probe_wham_usage.py`'s bootstrap check first, since `json_usage_provider.py:31` imports it; `SystemExit` propagates cleanly up through `runpy.run_path` to the launcher's `except SystemExit` handler).
- Direct debugging path (`py -3 codex_balance_widget_chrome.py`, per README): an uncaught `SystemExit("...")` at module scope prints only the message string to stderr and exits 1 — a clean diagnostic instead of a raw traceback. Confirmed this is standard CPython behavior for uncaught `SystemExit` with a non-integer argument.

Both test suites pass after the fix (re-run independently here, not just trusting the fix report's stated numbers): `usage_widget_common` 20/20, `codex_balance_widget` 64/64.

**However**, this fix pass introduces two new gaps of its own — see **WR-01** and **WR-02** below — that mean CR-01 is not fully closed for two secondary audiences (test/dev tooling, and external contributors following the README from a fresh GitHub clone), even though it is fully closed for the primary Windows-GUI-user audience it targeted.

### WR-01 (iter1) — Stale docstrings: **FIXED**

`probe_wham_usage.py:15-19` and `json_usage_provider.py:15-21` both now accurately describe the `usage_widget_common` sibling dependency, the `sys.path` bootstrap side effect, and the possibility of `SystemExit` on a missing sibling. The old "only stdlib" / "no side effects on import" claims are gone. Confirmed via `git show 4919353`.

### WR-02 (iter1) — Unsafe `redact()` default: **FIXED**

`d:/00_Projects/usage_widget_common/usage_widget_common/redaction.py:9` is now `def redact(obj: Any, *, keys: frozenset[str]) -> Any:` — no default, keyword-only. Grepped **both** `codex_balance_widget` and `claude_balance_widget_v1` (the other stated consumer of this shared package, per `usage_widget_common/__init__.py`'s own docstring) for every call site of `redact(`:
- `probe_wham_usage.py:254` — updated to `_redact_generic(obj, keys=REDACT_KEYS)` (was positional; would have raised `TypeError` under the new signature if left unchanged — correctly fixed).
- `usage_widget_common/tests/test_redaction.py:38-40` — updated to pass `keys=frozenset()` explicitly.
- `claude_balance_widget_v1` — no call sites exist yet (Phase 4 has not started), so there was nothing there to break.

No missed call sites found. Both test suites re-run and pass.

## Warnings

### WR-01: CR-01's `SystemExit`-at-import swap breaks clean `unittest` failure reporting when the sibling repo is absent

**File:** `probe_wham_usage.py:37-42`, `json_usage_provider.py:34-39`, `codex_balance_widget_chrome.py:52-57`

**Issue:** The CR-01 fix replaces a plain `ModuleNotFoundError` (an `Exception` subclass) with `raise SystemExit(...)` (a `BaseException` subclass, deliberately *not* caught by bare `except Exception:`) at module-import time. This is the right call for the interactive Windows-GUI and direct-`py -3` paths (verified above), but it silently degrades the failure mode for this project's own test tooling (`unittest`, per `03-CONTEXT.md`: *"Tests use `unittest`"*).

I reproduced this concretely in an isolated scratch directory (not touching this repo): a module that does `raise SystemExit("msg")` at import time, imported by a test file at module scope (mirroring `import probe_wham_usage` at the top of `test_probe_wham_usage.py`), behaves differently depending on invocation style:
- `python -m unittest discover -s . -p "test_*.py"` → `unittest`'s discovery loader *does* catch it and reports a normal `ERROR` with a full traceback and a `Ran N tests` / `FAILED (errors=1)` summary.
- `python -m unittest test_mod2` (naming the module directly — **the exact invocation style the fix report itself describes using**: *"full test suite (`test_probe_wham_usage`, `test_json_usage_provider`, `test_codex_balance_widget_chrome`) re-run and passing (64/64)"*) → the `SystemExit` is **not** caught anywhere in `unittest`'s direct-name-loading path; it propagates all the way out, printing only the bare message with **no test summary at all** — no indication of which module failed, or that 0 of 64 tests actually ran.

By contrast, the pre-fix `ModuleNotFoundError` produced a clean `ERROR: ... FAILED (errors=1)` report under the exact same direct-name invocation style (confirmed side-by-side in the same repro). The process exit code is still non-zero (`1`) in both cases, so a CI gate keyed purely on exit code wouldn't be fooled — there is currently no CI workflow in either repo, though, so a human reading local terminal/log output is the actual audience today, and that audience gets dramatically less diagnostic information after this fix than before it, in exactly the scenario (sibling repo missing/misconfigured) this fix pass was supposed to make *more* diagnosable, not less.

**Fix:** Keep the fail-loud `SystemExit` behavior for actual end-user entry points, but don't let it leak into library/import-time code that test tooling also imports. For example, raise a plain, catchable exception from the bootstrap check itself, and only convert it to `SystemExit`/a messagebox at the real entry points:

```python
class _SiblingRepoMissing(ImportError):
    pass

_SIBLING_COMMON = Path(__file__).resolve().parent.parent / "usage_widget_common"
if not _SIBLING_COMMON.is_dir():
    raise _SiblingRepoMissing(
        f"usage_widget_common not found at {_SIBLING_COMMON}.\n"
        "Clone it as a sibling of this repo (see README) before running "
        "probe_wham_usage.py / the widget."
    )
```

with each file's own `if __name__ == "__main__":` block (and the launcher) catching `_SiblingRepoMissing` and re-raising it as `SystemExit` / showing the messagebox. `ImportError` is an `Exception` subclass, so `unittest`'s loader (and any other Exception-based tooling) handles it the same clean way it always has. At minimum, if the `SystemExit`-at-import design is kept as-is, document this test-runner caveat (e.g. a code comment near the check, or in the test files) so a future contributor doesn't waste time debugging a mysteriously silent/truncated `python -m unittest <module>` run.

### WR-02: README/install.bat's new "clone `usage_widget_common`" instructions give no clone source — CR-01's fix is incomplete for anyone but the original developer's machine

**File:** `README.md:25,31`; `README.ru.md:24,30`; `install.bat:6-12`

**Issue:** The CR-01 fix commit (`9a1b4c2`) added, verbatim:

> "Clone `usage_widget_common` next to this repo (same parent folder), if you have not already."

to both READMEs, plus a matching warning in `install.bat`. None of the three says *where* to clone it *from* — no git URL, no host, nothing. I checked: `codex_balance_widget` (this repo) has a real public remote (`git remote -v` → `origin https://github.com/alexander-62/Codex-Balance-Widget.git`), but `usage_widget_common` has **zero** remotes configured (`git remote -v` in that repo returns nothing) — it exists only as a local, un-pushed git repo on this one machine.

`README.md` is written as a general public-facing document (it has a "Disclaimer" section explicitly framing this as "an unofficial community tool," an MIT license link, and step-by-step install instructions aimed at a general user, not just the original author). Iteration 1's CR-01 finding was specifically titled *"fresh installs following the README will crash"* — this fix pass stops the raw crash and replaces it with a clean `SystemExit`/messagebox message, which is real progress, but literally following the current README's own new step 1 from a fresh `git clone` of the public GitHub repo is a dead end: there is nowhere the instructions point to actually obtain `usage_widget_common`. The net result for that audience is still a fully blocked install — just with a nicer error message instead of a traceback.

**Fix:** Either publish `usage_widget_common` somewhere (even a personal/private remote) and put the actual clone URL in both READMEs and `install.bat`'s warning text, e.g.:

```markdown
- the `usage_widget_common` repo cloned as a sibling directory of this repo
  (same parent folder): `git clone <actual-url-here> ../usage_widget_common`
```

or, if this pairing is intentionally a single-developer, non-distributed setup for now, say so explicitly in the README (e.g. "this repo currently depends on a private, unpublished sibling package and is not yet installable by external users") so the gap is honest rather than silently unusable.

## Info

### IN-01: No regression test covers the new bootstrap-failure code path CR-01 itself introduced

**File:** `probe_wham_usage.py:37-42`, `json_usage_provider.py:34-39`, `codex_balance_widget_chrome.py:52-57`, `codex_balance_widget_launcher.pyw:26-33`

**Issue:** The fix report's own verification for CR-01 was "`python -m ast.parse` on all four modified files; full test suite ... re-run and passing (64/64) both before and after this commit" — i.e. it confirmed the change didn't *break* anything already tested, but no new test exercises the actual new behavior this fix added (missing-directory → `SystemExit` with the expected message text; launcher's `except SystemExit` → `messagebox.showerror` called with the right args; bare `raise SystemExit` → messagebox correctly *not* shown a second time). A future edit to this block (e.g. someone "simplifying" the duplicated check per IN-02 below) could silently regress the fail-loud behavior with nothing to catch it.

**Fix:** Add a small test per file, e.g. `unittest.mock.patch("pathlib.Path.is_dir", return_value=False)` around a fresh `importlib.reload` of the module under test, asserting `SystemExit` is raised with the expected substring; and a launcher-level test using `unittest.mock.patch("runpy.run_path", side_effect=SystemExit("usage_widget_common not found..."))` asserting `messagebox.showerror` is called, plus a second case with `side_effect=SystemExit()` (bare) asserting it is *not* called.

### IN-02: The duplicated sys.path-bootstrap block (iteration 1's IN-01, left out of scope) grew from 3 lines to 7 lines per file

**File:** `probe_wham_usage.py:36-44`, `json_usage_provider.py:33-41`, `codex_balance_widget_chrome.py:51-59`

**Issue:** Iteration 1 already flagged (as an out-of-scope Info item) that the `_SIBLING_COMMON` / `sys.path.insert` block is copy-pasted identically across all three files. This fix pass — correctly, since fixing it once wouldn't have addressed CR-01 in the other two copies — added the new `is_dir()` check to all three copies too, more than doubling the size of the duplicated block (3 lines → 7 lines) without deduplicating it. This isn't a regression against this fix pass's stated mandate (CR-01/WR-01/WR-02 only), but the maintenance cost the original IN-01 called out ("any future change ... now needs to be made in three places") is measurably larger now than when it was first flagged.

**Fix:** Same suggestion as iteration 1's IN-01: extract this block into one local helper (e.g. a small `_bootstrap.py` in `codex_balance_widget`, not in the shared package itself, since the shared package is the thing being bootstrapped) that all three files import first, so the existence-check-plus-path-insertion logic lives in exactly one place.

---

_Reviewed: 2026-07-22T21:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2 (re-review after fix pass)_
