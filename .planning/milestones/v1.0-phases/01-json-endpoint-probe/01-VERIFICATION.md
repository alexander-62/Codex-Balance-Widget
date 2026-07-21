---
phase: 01-json-endpoint-probe
verified: 2026-07-20T16:43:28Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
---

# Phase 1: JSON endpoint probe Verification Report

**Phase Goal:** Отдельный тестовый скрипт: auth.json → wham/usage → структура ответа. Рабочий код виджета не изменяется.
**Verified:** 2026-07-20T16:43:28Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Merged from ROADMAP.md Success Criteria (5) and PLAN frontmatter `must_haves.truths` (01-01: 4, 01-02: 4), deduplicated.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `py -3 probe_wham_usage.py` prints HTTP status + pretty JSON (ROADMAP SC1 / PROBE-01) | VERIFIED | Independently re-ran `py -3 probe_wham_usage.py --no-fixture` live: stdout printed `HTTP status: 200` followed by pretty-printed, redacted JSON (email/user_id/account_id/individual_limit all `<redacted>`, no raw PII) |
| 2 | Script extracts and prints Balance-equivalent fields (5h %, weekly %, resets, credits) or honestly reports absence (ROADMAP SC2 / PROBE-02) | VERIFIED | Same live run printed `Extracted fields (Balance)` block: `five_hour_percent: отсутствует в ответе`, `weekly_percent: 80`, `credits: 0`, `weekly_reset_text: 2026-07-26 14:45`, plus a `window 604800s: ...` line — matches `extract_fields()` unit test (`test_extract_fields_live_fixture`, weekly_percent==84 on the RESEARCH fixture) |
| 3 | Script saves the raw response to a redacted fixture file for future parser tests (ROADMAP SC3 / PROBE-03) | VERIFIED | `wham_usage_fixture.json` exists, tracked in git (`git ls-files`), `json.loads()` succeeds, contains `rate_limit` key; independently re-checked with `'eyJ' in s`→False, `'@' in s`→False |
| 4 | Missing/expired token produces a clear diagnostic (which file/field/HTTP code), not a traceback (ROADMAP SC4 / PROBE-04) | VERIFIED | Independently reproduced: `CODEX_HOME=<empty tmp dir> py -3 probe_wham_usage.py --no-fixture` → exit 1, stdout = `Не найден файл auth.json (<path>). Установите/запустите Codex CLI и выполните codex login.` — contains "auth.json", no "Traceback" |
| 5 | `git status` shows only new files — not one line of `codex_balance_widget_chrome.py` or the launchers is changed (ROADMAP SC5, [LOCKED]) | VERIFIED | `git status --porcelain codex_balance_widget_chrome.py codex_balance_widget_launcher.pyw install.bat run.bat run_hidden.vbs requirements.txt` → empty; `git log --oneline 3b5b8bf..HEAD -- <same 6 files>` → empty (no commits touched them since phase start) |
| 6 | Unit test suite passes without network (23+ tests, exit 0) — PLAN 01-01 must_have | VERIFIED | `py -3 -m unittest test_probe_wham_usage -v` → 23 tests, `OK`, exit 0. No `urllib.request.urlopen` or `Path.home()` calls in the test file (`grep` empty) |
| 7 | Windows classified strictly by `limit_window_seconds`, never by primary/secondary position — PLAN 01-01 must_have | VERIFIED | `pick_window()`/`collect_windows()` implementation keys exclusively on `window.get("limit_window_seconds")`; `TestWindows` (7 tests) cover both-present, null, missing-key, additional_rate_limits, found/not-found/tolerance cases, all passing |
| 8 | Access token and PII never printed to stdout, in any mode including `--debug` — PLAN 01-01 must_have | VERIFIED | `grep -n "print" probe_wham_usage.py \| grep -i token` → empty (T-1-01 acceptance grep); token lives only inside `build_headers()`; independently confirmed across 2 live runs that stdout only shows `<redacted>` for email/user_id/account_id/individual_limit. **See WARNING below (CR-01)**: the stdout path lacks the same `redaction_clean()` post-check that `write_fixture()` has, so this guarantee currently holds empirically but is not defense-in-depth verified for unknown future field names |
| 9 | User confirmed extracted fields match the current widget's Balance display — PLAN 01-02 must_have | VERIFIED | 01-02-SUMMARY.md documents the Task 2 human-verify checkpoint response "approved": user independently ran `--no-fixture`, compared weekly %, weekly reset, credits, and absent-`five_hour` against the Chrome-scraping widget screenshot — all four matched |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `probe_wham_usage.py` | stdlib probe: load_tokens, jwt_exp, collect_windows, pick_window, extract_fields, redact, redaction_clean, build_headers, fetch_usage, write_fixture, main; min 150 lines | VERIFIED | 399 lines; all 11 named functions present with matching signatures; stdlib-only imports (`argparse, base64, json, os, sys, traceback, urllib.error, urllib.request, datetime, pathlib, typing`) — no `requests` or third-party import |
| `test_probe_wham_usage.py` | unittest suite on pure functions, no network, no real auth.json | VERIFIED | 247 lines, 23 tests across 6 classes, `import probe_wham_usage` present, no `urlopen`/`Path.home()` calls |
| `wham_usage_fixture.json` | redacted raw wham/usage response, contains `rate_limit` | VERIFIED | Committed (`git ls-files`), valid JSON, `rate_limit.primary_window.limit_window_seconds=604800` present, `secondary_window: null`; PII fields redacted |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `test_probe_wham_usage.py` | `probe_wham_usage.py` | direct module import | WIRED | `import probe_wham_usage` at line 17; all 23 tests call functions on the imported module and pass |
| `probe_wham_usage.py` | `$CODEX_HOME/auth.json` | `os.environ.get('CODEX_HOME')` with `Path.home()/'.codex'` fallback | WIRED | `auth_json_path()` implements exactly this; empirically exercised (empty-CODEX_HOME diagnostic run + live run against real `~/.codex/auth.json`) |
| `probe_wham_usage.py` | `https://chatgpt.com/backend-api/wham/usage` | `urllib.request.Request` with `Authorization: Bearer` header | WIRED | `USAGE_URL` constant + `build_headers()` + `fetch_usage()`; live run returned `HTTP status: 200` with real Bearer token |
| `wham_usage_fixture.json` | `probe_wham_usage.py` | generated by `write_fixture()` on live run | WIRED | `write_fixture()` implementation redacts, post-checks (`redaction_clean`), then writes; committed fixture content is structurally consistent with `redact()`'s denylist output |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Unit suite green, no network | `py -3 -m unittest test_probe_wham_usage -v` | 23 tests, OK, exit 0 | PASS |
| Missing-auth.json diagnostic, no traceback | `CODEX_HOME=<empty tmp> py -3 probe_wham_usage.py --no-fixture` | exit 1, "Не найден файл auth.json (...)"; no "Traceback" | PASS |
| Live HTTP 200 + redacted output (independent re-run #1) | `py -3 probe_wham_usage.py --no-fixture` | `HTTP status: 200`, redacted JSON, `Extracted fields` block printed, no PII | PASS |
| Live HTTP 200 + redacted output (independent re-run #2) | `py -3 probe_wham_usage.py --no-fixture` | `HTTP status: 200`, weekly_percent 80, git status unchanged after run | PASS |
| Token never appears in `print(...)` statements | `grep -n "print" probe_wham_usage.py \| grep -i token` | empty output | PASS |
| Locked widget files untouched since phase start | `git log --oneline 3b5b8bf..HEAD -- codex_balance_widget_chrome.py codex_balance_widget_launcher.pyw install.bat run.bat run_hidden.vbs requirements.txt` | empty | PASS |
| Fixture contains no token/email substrings | `py -3 -c "..."` on `wham_usage_fixture.json` | `eyJ`→False, `@`→False, `rate_limit`→True | PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh`-style conventional probes exist in this repo (this phase's "probe" is the deliverable itself, `probe_wham_usage.py`, not a verification harness script). Its unittest suite and live-run behavior are covered under Behavioral Spot-Checks above. Step 7c: SKIPPED (no `scripts/*/tests/probe-*.sh` files found).

### Requirements Coverage

No `.planning/REQUIREMENTS.md` file exists in this project — requirement descriptions are only defined inline in `ROADMAP.md`'s Phase 1 section (`**Requirements**: PROBE-01, PROBE-02, PROBE-03, PROBE-04`). Cross-referenced against plan frontmatter:

| Requirement | Source Plan | Description (from ROADMAP/PLAN context) | Status | Evidence |
|-------------|-------------|------------------------------------------|--------|----------|
| PROBE-01 | 01-02-PLAN.md | Live run reaches wham/usage, exit 0, "HTTP status: 200" printed | SATISFIED | Live run confirmed twice independently by verifier + once by executor (01-02-SUMMARY) |
| PROBE-02 | 01-01-PLAN.md | Redaction (`redact`/`redaction_clean`) covered by unit tests, no network, no real auth.json | SATISFIED | `TestRedact` (4 tests) + `TestFixtureAndHeaders` (4 tests) all green |
| PROBE-03 | 01-02-PLAN.md | Fixture written, valid JSON, contains `rate_limit`, no `eyJ`/`@` substrings | SATISFIED | `wham_usage_fixture.json` verified directly |
| PROBE-04 | 01-01-PLAN.md | Token isolated to `build_headers`; all error branches produce one Russian diagnostic string + exit 1, no traceback | SATISFIED | grep + live empty-CODEX_HOME reproduction |

No orphaned requirements — all 4 IDs declared in ROADMAP.md Phase 1 are claimed by exactly one plan each (01-01: PROBE-02, PROBE-04; 01-02: PROBE-01, PROBE-03), matching `requirements-completed` in both SUMMARY.md files.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `probe_wham_usage.py` | 365-366 | (from `.planning/phases/01-json-endpoint-probe/01-REVIEW.md`, CR-01) stdout print of `redact()`ed payload has no `redaction_clean()` post-check, unlike `write_fixture()` which has one | WARNING | Currently no observed leak (empirically verified twice live in this session) — `redact()`'s key-based denylist caught all PII in the actual response shape. But the guarantee is not defense-in-depth: an unanticipated PII-bearing key name in a future API response would print unredacted to stdout with no safety net, unlike the fixture path |
| `probe_wham_usage.py` | 129, 134-139 | (01-REVIEW.md, CR-02) `collect_windows()` assumes `rate_limit` / `additional_rate_limits[]` entries are dicts once truthy; a non-dict value raises an uncaught `AttributeError` that escapes the single `except ProbeError` handler in `main()` | WARNING | Only reachable on a malformed/unexpected payload shape from the live API — not exercised by any of this phase's declared success criteria (which cover missing-token, not malformed-response, diagnostics). No traceback observed in any test performed for this verification |
| `probe_wham_usage.py` | 391-395 | (01-REVIEW.md, WR-01) `main()` only catches `ProbeError`; any other exception type (including CR-02's `AttributeError`) bypasses the single-diagnostic contract | WARNING | Same root cause as CR-02; not exercised in this phase's tested scenarios |
| `test_probe_wham_usage.py` | 117 | (01-REVIEW.md, WR-02) `self.assertIn("20", fields["weekly_reset_text"])` is a weak assertion that would pass even on a formatting regression | INFO | Test-quality gap, not a functional gap — `extract_fields` itself was independently verified via live runs to produce a correctly formatted `YYYY-MM-DD HH:MM` string |
| `test_probe_wham_usage.py` | whole file | (01-REVIEW.md, WR-03) No test coverage for `fetch_usage()` HTTP-error branches (401/403/429/HTML) or `main()` end-to-end | INFO | Error-branch behavior was validated for one branch (missing auth.json) via live reproduction in this verification; the other HTTP-error branches (401/403/429) remain unit-untested, relying on manual code inspection and the RESEARCH.md error-semantics table |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in either file (`grep` empty). No hardcoded-empty-data or stub-return patterns found — these are runtime-behavior gaps identified by a formal code review (`01-REVIEW.md`, same-day, status `issues_found`), not incomplete/placeholder implementations.

**Assessment:** None of these findings invalidate a phase must-have. All 9 observable truths and 5 ROADMAP success criteria are demonstrated working against the live endpoint, with real tokens, in this verification session. CR-01/CR-02/WR-01 are legitimate robustness gaps for defense-in-depth against *future* schema drift and *unknown* field names — worth fixing before Phase 2 hardens this probe into the widget's production JSON provider, but they do not block Phase 1's stated goal ("standalone test script proves the field-extraction concept; widget code untouched"), which this probe demonstrably achieves today.

### Human Verification Required

None outstanding. The phase's designated human-verify checkpoint (01-02 Task 2, gate="blocking") was already executed and approved during phase execution — documented in `01-02-SUMMARY.md` with the user's independent live run and field-by-field comparison against the widget UI, response "approved". No new human verification items were identified during this re-check.

### Gaps Summary

No gaps block Phase 1's goal. All 5 ROADMAP Success Criteria and all 4 requirement IDs (PROBE-01..04) are independently reproduced and verified in this session (live HTTP 200, extracted-fields printout, redacted fixture, missing-auth.json diagnostic without traceback, and a fully clean `git status` on all six locked widget files across the phase's full commit range). Three WARNING-level and two INFO-level findings carried over from the same-day code review (`01-REVIEW.md`) remain unresolved (no fix commits found after `c625aae`) — these are robustness/defense-in-depth gaps for hypothetical future/malformed inputs, not failures of any demonstrated behavior. Recommend the developer decide whether to open a small follow-up plan to close CR-01/CR-02/WR-01 before Phase 2 builds the production JSON provider on top of `probe_wham_usage.py`, or explicitly accept them as known probe-only debt.

---

*Verified: 2026-07-20T16:43:28Z*
*Verifier: Claude (gsd-verifier)*
