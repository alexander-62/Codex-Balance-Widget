---
phase: 03-shared-library-extraction-codex-migration
reviewed: 2026-07-22T20:15:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - probe_wham_usage.py
  - json_usage_provider.py
  - codex_balance_widget_chrome.py
  - d:/00_Projects/usage_widget_common/usage_widget_common/errors.py
  - d:/00_Projects/usage_widget_common/usage_widget_common/redaction.py
  - d:/00_Projects/usage_widget_common/usage_widget_common/retry.py
  - d:/00_Projects/usage_widget_common/usage_widget_common/fetch_decision.py
  - d:/00_Projects/usage_widget_common/usage_widget_common/__init__.py
findings:
  critical: 1
  warning: 2
  info: 4
  total: 7
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-07-22T20:15:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

I reviewed both halves of this extraction phase: the four new `usage_widget_common` modules (`errors.py`, `redaction.py`, `retry.py`, `fetch_decision.py` + `__init__.py`) and the three migrated Codex files (`probe_wham_usage.py`, `json_usage_provider.py`, `codex_balance_widget_chrome.py`).

**Behavioral fidelity of the extraction itself is good.** I traced the pre-migration diff (`git show 02ecb0b`) line-by-line against the new shared implementations:
- `retry.fetch_with_retry_once` is a byte-for-byte transcription of the old hand-rolled `_fetch_with_retry` loop, with `FetchError` (aliased as `ProbeError`) substituted for the exception type.
- `redaction.redact`/`redaction_clean` are byte-for-byte transcriptions of the old module-level functions, with the domain-specific `REDACT_KEYS` denylist correctly kept local to `probe_wham_usage.py` (not centralized — matches the stated T-3-02 threat mitigation).
- `fetch_decision.decide_fetch_source`'s 4-way skeleton (`primary`/`fallback`/`retain_existing`/`none`) reproduces `plan_fetch_outcome`'s old nested-if chain exactly; I hand-traced all 4 branches against the pre-migration diff and confirmed the message/branch mapping is unchanged.
- Ran both test suites: `codex_balance_widget` (64 tests) and `usage_widget_common` (20 tests) — all pass, including the 10-case `TestPlanFetchOutcome` and 3-case `TestFetchOnceJsonOkNoUsageDataFallback` that specifically guard this migration's chrome-fallback branch.
- The `sys.path` bootstrap itself is sound: all three files compute the identical `_SIBLING_COMMON` path, the idempotency check (`if str(...) not in sys.path`) is correct, `import json_usage_provider` always runs before `codex_balance_widget_chrome.py`'s own bootstrap (so the path is already present by then), and Python's `sys.modules` cache means there's no diamond-import / duplicate-class-object risk across the three redundant bootstrap blocks.

**However, the migration introduces a real, unaddressed regression**: all three files now hard-fail at import time if the sibling `usage_widget_common` repo is absent, and nothing in this phase's plan, README, or install scripts accounts for that. That's this review's one Critical finding. I also found two Warnings (stale docstrings, an unsafe default in the shared `redact()` API) and four minor Info items.

## Critical Issues

### CR-01: Unhandled, undocumented hard dependency on a sibling repo — fresh installs following the README will crash

**File:** `probe_wham_usage.py:33-38`, `json_usage_provider.py:29-33`, `codex_balance_widget_chrome.py:51-55`

**Issue:** Before this phase, all three files were fully self-contained (stdlib + each other). This migration makes them require `d:/00_Projects/usage_widget_common` to exist as a sibling directory on disk at import time:

```python
_SIBLING_COMMON = Path(__file__).resolve().parent.parent / "usage_widget_common"
if str(_SIBLING_COMMON) not in sys.path:
    sys.path.insert(0, str(_SIBLING_COMMON))

from usage_widget_common.errors import FetchError
from usage_widget_common.redaction import redact as _redact_generic, redaction_clean
```

There is no existence check, no try/except, and no user-facing fallback. If `usage_widget_common` is missing (e.g. a fresh `git clone` of just this repo, a machine that only has `codex_balance_widget` checked out, or the sibling repo being moved/renamed), every one of the three files raises a bare `ModuleNotFoundError` the moment it's imported — before `main()`, before `if __name__ == "__main__":`, before any of this app's otherwise-careful error handling gets a chance to run.

The failure mode is worse than a normal crash because of how this app is actually launched:
- Via `run.bat` → `run_hidden.vbs` → `codex_balance_widget_launcher.pyw`: the launcher's `try/except Exception` catches the `ModuleNotFoundError` from `runpy.run_path(...)` and writes it to `widget_launch.log` only — **no messagebox, no console, no visible symptom at all**. The user just sees nothing happen when they double-click, with zero clue to check a log file they don't know exists.
- Via `py -3 codex_balance_widget_chrome.py` directly (the documented debugging path in README.md line 38): a raw, untranslated Python traceback prints to console, breaking this codebase's otherwise-consistent "every failure path shows a clean Russian/English diagnostic" design (see e.g. `probe_wham_usage.load_tokens`'s carefully worded `ProbeError` messages).

Nothing in this phase's deliverables addresses this:
- `README.md` / `README.ru.md` — neither mentions `usage_widget_common` or that a second repo must be cloned as a sibling before the app will run (confirmed via grep — zero matches in both files).
- `install.bat` — only runs `pip install -r requirements.txt`; does not clone, copy, or verify the sibling repo.
- `.planning/phases/03-shared-library-extraction-codex-migration/03-01-PLAN.md`'s threat model (T-3-01) explicitly "accepts" the `sys.path` insertion as a *tampering* risk (same-developer trust), but never considers the *availability* risk of the sibling simply not existing on a given machine.
- No CI workflow exists in either repo that would catch this on a fresh checkout.

This regresses a previously self-contained, stdlib-only, install.bat-installable tool into one with an undocumented, unenforced cross-repo filesystem dependency.

**Fix:** At minimum, fail loudly and helpfully instead of silently/raw. For example, in each of the three files:

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

And, ideally, wrap the launcher's import failure so it surfaces via `messagebox.showerror(...)` the same way `if not app_lock:` already does in `codex_balance_widget_chrome.py`'s `__main__` block, instead of only logging silently. Separately, update `README.md`/`README.ru.md`'s "Install and Run" section and `install.bat` to state the sibling-repo requirement (or, better, have `install.bat` `git clone`/verify it).

## Warnings

### WR-01: Stale "stdlib only, no import side effects" docstring claims

**File:** `probe_wham_usage.py:15-17`, `json_usage_provider.py:15-17`

**Issue:** Both module docstrings still make claims that this migration made false:

- `probe_wham_usage.py`: *"Only stdlib is used: json, os, sys, base64, argparse, urllib.request, urllib.error, datetime, pathlib."* — the module now also imports `usage_widget_common.errors` and `usage_widget_common.redaction`, a non-stdlib sibling package.
- `json_usage_provider.py`: *"Only stdlib is used (asyncio, dataclasses) plus probe_wham_usage itself... this module is safe to import from any caller, sync or async, **without side effects on import**."* — the module now performs `sys.path.insert(...)` at import time, which is precisely a side effect on import, and it also now depends on `usage_widget_common`.

These are exactly the kind of claims a future contributor (or a security-conscious user) would read and rely on without re-verifying against the actual import list.

**Fix:** Update both docstrings to mention the `usage_widget_common` sibling dependency and drop/qualify the "no side effects" and "only stdlib" claims, e.g.:

```
Only stdlib is used directly by this module, plus the sibling
`usage_widget_common` package (also stdlib-only) reached via a
sys.path bootstrap — see the top of this file.
```

### WR-02: `usage_widget_common.redaction.redact()`'s `keys` default silently produces near-no redaction

**File:** `d:/00_Projects/usage_widget_common/usage_widget_common/redaction.py:9`

**Issue:** `def redact(obj: Any, keys: frozenset[str] = frozenset()) -> Any:` — the docstring correctly explains that callers must supply their own domain-specific denylist, but nothing enforces that. A future caller (e.g. Phase 4's Claude widget, or any later maintainer) who calls `redact(payload)` without the `keys=` argument gets a function that silently redacts *only* keys containing the substring `"token"` — every other sensitive field (email, account/user IDs, etc.) passes through untouched, with no warning, no error, and a return value that looks like it did its job. Given this module's entire purpose is leak-prevention (per its own docstring and `redaction_clean`'s "post-check" framing), a silent-mostly-no-op default is a footgun in exactly the place where a fail-safe default matters most.

**Fix:** Make `keys` a required keyword argument (no default), forcing every call site to consciously decide its denylist:

```python
def redact(obj: Any, *, keys: frozenset[str]) -> Any:
    ...
```

If a truly-optional call site is ever needed, prefer `keys: frozenset[str] | None = None` and raise inside the function if `None` reaches recursion, rather than silently treating it as "redact nothing."

## Info

### IN-01: Sys.path bootstrap block duplicated verbatim across three files

**File:** `probe_wham_usage.py:33-35`, `json_usage_provider.py:29-31`, `codex_balance_widget_chrome.py:51-53`

**Issue:** The identical 3-line `_SIBLING_COMMON` / `sys.path.insert` block is copy-pasted into all three files. Functionally harmless today (idempotent, and `import json_usage_provider` always runs before `codex_balance_widget_chrome.py`'s own copy), but any future change to the sibling-resolution logic (e.g. supporting an env-var override, or fixing CR-01 above) now needs to be made in three places, and it would be easy to update two and forget the third.

**Fix:** Consider a tiny local helper (e.g. `_bootstrap.py` in this repo, not in the shared package, since the shared package is the thing being bootstrapped) that all three files import first, centralizing the path-resolution/insertion/existence-check logic once.

### IN-02: `sys.path.insert(0, ...)` adds the sibling repo's *root* (including its `tests/` namespace package) to global import path

**File:** `probe_wham_usage.py:33-35`

**Issue:** `_SIBLING_COMMON` resolves to `d:/00_Projects/usage_widget_common` (the repo root), not `.../usage_widget_common/usage_widget_common` (the actual package). Inserting the repo root at `sys.path[0]` is necessary for `import usage_widget_common.X` to resolve, but it also makes everything else at that repo's root importable process-wide for the remaining lifetime of the interpreter — including `tests/` (a directory with no `__init__.py`, so it's importable as a PEP 420 implicit namespace package). In an ordinary single-widget run this is inert, but it's a latent name-collision risk if this process ever imports another same-named top-level module/package from elsewhere on `sys.path`.

**Fix:** Low priority given current usage, but worth a comment noting the tradeoff, or resolving/inserting a more specific path if the package layout ever changes.

### IN-03: `ProbeError = FetchError` changes the exception's traceback identity

**File:** `probe_wham_usage.py:62`

**Issue:** `ProbeError` is now the literal `usage_widget_common.errors.FetchError` class object (not a subclass), so any traceback or `type(exc)` inspection will show `usage_widget_common.errors.FetchError` rather than `probe_wham_usage.ProbeError`. Functionally inert (confirmed via the full existing test suite), but worth calling out since it means future debugging of a Codex-specific stack trace will point at a class defined in a different repo, which can be momentarily confusing when the two repos are checked out at different revisions.

**Fix:** No action required; just worth a one-line comment where `ProbeError = FetchError` is defined (already partially covered by the existing comment) noting the traceback-identity implication explicitly, for future debugging sessions.

### IN-04: Import statements placed after non-import statements (E402-style) in all three bootstrap blocks

**File:** `probe_wham_usage.py:37-38`, `json_usage_provider.py:33`, `codex_balance_widget_chrome.py:55`

**Issue:** `from usage_widget_common... import ...` statements appear after the `_SIBLING_COMMON = ...` / `if ...: sys.path.insert(...)` statements, which is unavoidable given the sys.path technique, but will trigger `E402 module level import not at top of file` on any standard linter (flake8/ruff) run over these files, since none of them currently have an inline suppression.

**Fix:** Add `# noqa: E402` (or the ruff equivalent) on the affected `from usage_widget_common...` import lines, or a top-of-block comment noting the intentional ordering, to avoid this being repeatedly re-flagged by tooling as if it were an oversight.

---

_Reviewed: 2026-07-22T20:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
