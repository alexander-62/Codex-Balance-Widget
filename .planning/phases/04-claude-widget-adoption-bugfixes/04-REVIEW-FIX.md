---
phase: 04-claude-widget-adoption-bugfixes
fixed_at: 2026-07-22T00:00:00Z
review_path: .planning/phases/04-claude-widget-adoption-bugfixes/04-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 04: Code Review Fix Report

**Fixed at:** 2026-07-22T00:00:00Z
**Source review:** .planning/phases/04-claude-widget-adoption-bugfixes/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (WR-01, WR-02 — critical+warning pass; IN-01..03 out of scope per instructions)
- Fixed: 2
- Skipped: 0

**Note on repo location:** All fixes below apply to the sibling repo `d:/00_Projects/claude_balance_widget_v1` (not this repo). All git commands and commits were run there directly via `git -C d:/00_Projects/claude_balance_widget_v1`, since this repo's own commit tooling does not reach that sibling checkout.

## Fixed Issues

### WR-01: `_load_token()` can leak a raw `AttributeError` instead of a friendly `FetchError`

**Files modified:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py`, `d:/00_Projects/claude_balance_widget_v1/test_core.py`
**Commit:** `44da854` (sibling repo `claude_balance_widget_v1`, branch `master`)
**Applied fix:** Read `credentials_state()` (lines 286-294) first to confirm the file's existing guard style, then applied the review's suggested `isinstance` guard (rather than widening the `except` clause) since it keeps `_load_token()`'s existing three-way except-clause structure (`FileNotFoundError` / `OSError, json.JSONDecodeError` / fall-through validation) intact without conflating "file unreadable" and "file readable but malformed" under one except branch:
```python
oauth = data.get("claudeAiOauth") if isinstance(data, dict) else None
token = oauth.get("accessToken") if isinstance(oauth, dict) else None
```
Added test coverage in `test_core.py`: `_load_token()` invoked against temp `.credentials.json` files containing a top-level JSON array (`[]`), string, and number, plus a case where `claudeAiOauth` itself is a non-dict value — all asserted to raise `FetchError` (not `AttributeError`).

### WR-02: Non-429 HTTP error responses (including 5xx) are never classified as retryable

**Files modified:** `d:/00_Projects/claude_balance_widget_v1/claude_balance_widget.py`, `d:/00_Projects/claude_balance_widget_v1/test_core.py`
**Commit:** `5dfce97` (sibling repo `claude_balance_widget_v1`, branch `master`)
**Applied fix:** Applied the review's suggested fix verbatim in the fall-through branch of `fetch()`'s `except urllib.error.HTTPError as exc:` handler (after the existing 401/403/429 checks):
```python
raise FetchError(
    f"Anthropic вернул HTTP {exc.code}.", retryable=500 <= exc.code < 600
) from exc
```
Added test coverage in `test_core.py`: monkeypatched `urllib.request.urlopen` to raise `HTTPError` for codes 500/502/503/504 and asserted `FetchError.retryable is True` in each case, plus a sanity check that HTTP 404 still yields `retryable is False` (unchanged behavior for non-5xx/429 codes).

**Verification (both fixes):** `py -3 -m py_compile` on both modified files after each edit (Tier 2, pass); full suite `py -3 test_core.py` run after each commit's state (pass, including the pre-existing 13 assertions plus the new WR-01/WR-02 coverage) — `Core tests passed (incl. retry/error-classification, tooltip truncation, backoff schedule).`

## Skipped Issues

None — both in-scope findings were fixed and verified.

---

_Fixed: 2026-07-22T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
