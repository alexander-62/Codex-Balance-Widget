---
phase: 03-shared-library-extraction-codex-migration
fixed_at: 2026-07-22T18:05:00Z
review_path: .planning/phases/03-shared-library-extraction-codex-migration/03-REVIEW.md
iteration: 3
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-07-22T18:05:00Z
**Source review:** .planning/phases/03-shared-library-extraction-codex-migration/03-REVIEW.md
**Iteration:** 3 (FINAL — 3-iteration auto-fix cap reached after this pass)

**Summary:**

- Findings in scope: 3 (WR-01, WR-02, WR-03 — default critical+warning scope; the 5 Info findings IN-01 through IN-05 were explicitly out of scope for this pass and were not touched)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: Iteration 2's own `ModuleNotFoundError` fix silently re-broke the docstring accuracy that iteration 1's WR-01 fix established

**Files modified:** `probe_wham_usage.py`, `json_usage_provider.py`
**Commit:** `0edabd8`
**Applied fix:**

- `probe_wham_usage.py`'s module docstring now states that a missing sibling repo raises `SystemExit` when run directly as a script (`py -3 probe_wham_usage.py`) or `ModuleNotFoundError` when imported (by `unittest`, `json_usage_provider.py`, or `codex_balance_widget_chrome.py`), and explicitly notes `git clone <url>` will not work for the unpublished sibling package — matching the corrected README wording from iteration-2's WR-02.
- `json_usage_provider.py`'s module docstring was corrected to remove the unconditionally-false "will raise SystemExit if usage_widget_common is missing" claim. It now correctly states this module has no `__main__` case of its own, so a missing sibling always raises `ModuleNotFoundError` regardless of invocation path, and likewise notes the sibling cannot be obtained via `git clone <url>`.
- Verified both docstrings against the actual current bootstrap code (`probe_wham_usage.py:36-54`, `json_usage_provider.py:34-47`) before editing — the dual-behavior/unconditional-behavior split described matches the real code exactly.

**Verification performed:**

- Re-read both modified docstring blocks in full — text is accurate and complete, no corruption to surrounding code.
- `python -c "import ast; ast.parse(...)"` passed on both files.
- Full suite re-run after this fix alone: 64/64 passing (no functional code was touched, docstrings only).

### WR-02: The CR-01 (iteration 1) "raw traceback on direct invocation" regression, still live for `codex_balance_widget_chrome.py`

**Files modified:** `codex_balance_widget_chrome.py`
**Commit:** `631da5b`
**Applied fix:**

- Restructured `codex_balance_widget_chrome.py`'s bootstrap block: the `import json_usage_provider` statement, its own `_SIBLING_COMMON.is_dir()` check, and the `from usage_widget_common.fetch_decision import decide_fetch_source` import are now wrapped in a `try/except ModuleNotFoundError`. This is necessary (not merely "wrap the `__main__` block") because the actual failure happens at import time — line 49 of the original file, long before the `if __name__ == "__main__":` block at the bottom of the file (line 2346) is ever reached; wrapping only that block cannot catch an import-time failure.
- When caught with `__name__ == "__main__"` (both `py -3 codex_balance_widget_chrome.py` directly, and the launcher's `runpy.run_path(..., run_name="__main__")` invocation), the handler re-raises `SystemExit(str(exc)) from None`, giving a clean one-line diagnostic instead of a multi-frame traceback.
- When caught with `__name__ != "__main__"` (e.g. `test_codex_balance_widget_chrome.py`'s `from codex_balance_widget_chrome import (...)`), the handler re-raises the original `ModuleNotFoundError` unchanged, preserving normal unittest error reporting — this path is inert in the actual test suite since the sibling is present during test runs, but was confirmed to not alter any existing passing-case behavior.
- Confirmed the launcher (`codex_balance_widget_launcher.pyw`) is unaffected functionally: since it invokes `runpy.run_path(..., run_name="__main__")`, the newly-raised `SystemExit` is caught by the launcher's existing `except SystemExit as exc:` clause (a non-`None`/non-`0` `exc.code`), which shows the same user-facing `messagebox.showerror` as before — the launcher previously caught this case via its `except ModuleNotFoundError` clause with an equivalent message; the user-visible outcome is unchanged, only which except-clause on the launcher's side handles it.

**`json_usage_provider.py`'s residual WR-02 concern:** Confirmed `json_usage_provider.py` has no `if __name__ == "__main__":` block or other direct-invocation entry point of its own (grepped the file: the only `__main__` occurrence is now in its docstring, added by the WR-01 fix above, describing its own lack of a main-guard). It is only ever imported by `codex_balance_widget_chrome.py` (fixed above) or by `test_json_usage_provider.py` (where a raw, uncaught exception is the correct `unittest` behavior — not something to "fix"). **This finding's residual concern for `json_usage_provider.py` is resolved transitively by the `codex_balance_widget_chrome.py` fix above** — there is no other user-facing path that reaches `json_usage_provider.py`'s bootstrap check with a raw traceback.

**Verification performed:**

- `python -c "import ast; ast.parse(...)"` passed on `codex_balance_widget_chrome.py`.
- Independent reproduction (scratchpad script, real repo/sibling untouched): monkeypatched `pathlib.Path.is_dir` to simulate the sibling missing, then ran `runpy.run_path("codex_balance_widget_chrome.py", run_name="__main__")` in a subprocess. **Before this fix** this scenario produced a multi-frame traceback (confirmed by the iteration-3 review's own repro, reproduced independently here). **After this fix**, stderr shows exactly:

  ```text
  usage_widget_common not found at <path>.
  Clone it as a sibling of this repo (see README) before running probe_wham_usage.py / the widget.
  ```

  with return code 1 and no traceback frames — matching the standalone-CLI contract already established for `probe_wham_usage.py`.
- Full suite re-run after this fix: 64/64 passing (sibling repo present, normal case unaffected).

### WR-03: The launcher's except-clauses had no fallback if `write_log`/log-file access itself failed

**Files modified:** `codex_balance_widget_launcher.pyw`
**Commit:** `42c2e3d`
**Applied fix:**

- Wrapped the `write_log(...)` call in the `except SystemExit as exc:` clause's `if exc.code not in (None, 0):` branch in its own `try/except OSError: pass`.
- Wrapped the `write_log(...)` call in the `except ModuleNotFoundError as exc:` clause in its own `try/except OSError: pass` (this is the clause phase 3/iteration-2 added, called out specifically in the finding).
- Wrapped both the `write_log(...)` call and the `LOG_PATH.open("a", ...)` / `traceback.print_exc(...)` block in the pre-existing `except Exception:` clause in a single `try/except OSError: pass` (the finding explicitly noted this pre-existing clause has the same unguarded pattern, not only the new `ModuleNotFoundError` clause).
- In all three clauses, the `messagebox.showerror(...)` call remains outside and after the guarded log-write block, so it always executes regardless of whether the log write succeeded.

**Verification performed:**

- `python -c "import ast; ast.parse(...)"` passed on `codex_balance_widget_launcher.pyw`.
- Independent reproduction (scratchpad scripts, real repo untouched): monkeypatched `pathlib.Path.open` so the first write to `widget_launch.log` succeeds and every subsequent write raises `OSError` (simulating a log path that becomes unwritable mid-run — e.g. disk full), and mocked `tkinter.messagebox.showerror` to record calls without popping a real dialog.
  - Scenario A — sibling missing (triggers the `except ModuleNotFoundError` clause after this pass's WR-02 fix converts the deeper `ModuleNotFoundError` back through, or directly if reached that way): confirmed the launcher script completes without any exception escaping, and `messagebox.showerror` is called once with the expected `"Widget failed to start:\n\n..."` message.
  - Scenario B — a generic unexpected crash (simulated via a patched `runpy.run_path` raising `RuntimeError`), forcing the `except Exception:` clause: confirmed the launcher completes without any exception escaping, and `messagebox.showerror` is called once with the expected `"Widget crashed before startup..."` message.
  - In both scenarios, the log-file `open()` call count was 2 (first write succeeds, second — the except-clause's own write — fails and is swallowed), and in both cases `messagebox.showerror` still fired. Confirmed this precisely matches the failure mode WR-03 described: only the except-clause's own log write fails, and the guard successfully prevents that from suppressing the user-facing dialog.
- Full suite re-run after this fix: 64/64 passing (this file has no direct unit test coverage in the existing suite — `codex_balance_widget_launcher.pyw` is not imported by any of the three test modules — so the scratchpad reproduction above is the only verification available for this specific change; this is consistent with IN-01's carried-forward finding that no regression test exists for any of the bootstrap/launcher error paths).

## Full Suite Re-Verification (after all three fixes)

- This repo (`codex_balance_widget`): `py -3 -m unittest test_probe_wham_usage test_json_usage_provider test_codex_balance_widget_chrome` → **64/64 passing**, run both inside the isolated fix worktree and again in the main repo after the worktree's commits were fast-forwarded onto `main`.
- No sibling-repo (`usage_widget_common`) files were modified this iteration (out of scope per the task instructions), so no re-run of its test suite was required or performed.
- Note on verification environment: this iteration's fixes were made inside an isolated git worktree under a temp directory whose parent differs from the real repo's parent (`D:/tmp/sv-03-reviewfix-*` vs. `D:/00_Projects/codex_balance_widget`), which broke the three files' relative sibling-repo lookup (`Path(__file__).resolve().parent.parent / "usage_widget_common"`) purely as an artifact of the worktree's location on disk. A temporary Windows directory junction (`D:\tmp\usage_widget_common` → `D:\00_Projects\usage_widget_common`) was created before running the test suite inside the worktree, and removed immediately after — mirroring the exact same workaround iteration-2's fix report documented for the same reason. This junction was never part of any commit and was fully cleaned up before the worktree itself was removed.

## Skipped Issues

None — all three in-scope findings (WR-01, WR-02, WR-03) were fixed and independently verified.

## Notes on Findings Not Fully Resolved (required disclosure — final iteration)

All three in-scope Warnings are considered fully resolved by this pass. For full transparency going into the 3-iteration cap:

- **WR-02's fix for `codex_balance_widget_chrome.py` is a real behavioral fix**, not a documentation-only change: it changes what exception type propagates out of the module at import time depending on `__name__`. This was verified both by independent reproduction (clean `SystemExit`, no traceback, exit code 1) and by re-running the full test suite to confirm no regression for the normal (sibling-present) import path used by `test_codex_balance_widget_chrome.py`. Because this changes control flow (not just strings/comments), per the fix-agent's own verification-strategy guidance this is flagged here as a logic-adjacent change: **human spot-check of the reasoning is recommended** (specifically: confirming that `__name__ == "__main__"` is indeed true in the launcher's `runpy.run_path(..., run_name="__main__")` context, which this report verified via reproduction but is worth a second look given it is somewhat non-obvious).
- The 5 Info findings from `03-REVIEW.md` iteration 3 (IN-01 through IN-05) remain **unaddressed by design** — out of scope for this critical+warning-only fix pass, exactly as instructed. In particular, IN-01 (no regression test covers any of the bootstrap/launcher error paths touched by WR-01/WR-02/WR-03 across all three iterations) remains the most relevant follow-up: none of this iteration's three fixes have dedicated automated test coverage; all verification was performed via scratchpad reproduction scripts run against the isolated fix worktree, not via additions to the checked-in test suite. If a future maintainer edits any of the three near-identical bootstrap blocks or the launcher's except-clauses again, nothing in the existing 64-test suite will catch a regression in this specific area.
- Since this is the final allowed auto-fix iteration for this phase, no further automated review/fix passes will run. Any future changes to `probe_wham_usage.py`, `json_usage_provider.py`, `codex_balance_widget_chrome.py`, or `codex_balance_widget_launcher.pyw` around this bootstrap/error-handling logic should be manually re-verified against the reproduction scenarios described above (sibling-missing via `Path.is_dir` monkeypatch, log-write failure via `Path.open` monkeypatch), since there is no automated test guarding them.

---

_Fixed: 2026-07-22T18:05:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3_
