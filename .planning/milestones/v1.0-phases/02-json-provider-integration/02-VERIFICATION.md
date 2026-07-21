---
phase: 02-json-provider-integration
verified: 2026-07-21T13:00:00Z
status: passed
score: 3/3 must-haves verified
overrides_applied: 0
---

# Phase 2: JSON provider integration Verification Report

**Phase Goal:** Виджет получает данные через JSON-эндпоинт как основной источник; Chrome-скрейпинг остаётся фолбэком до подтверждения стабильности.
**Verified:** 2026-07-21T13:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Обычный цикл обновления не запускает Chrome (JSONPROV-01) | VERIFIED | `fetch_once` (`codex_balance_widget_chrome.py:2187-2266`) calls `await self.json_provider.fetch()` first; `self.browser.fetch()` is only reached inside the `else` branch guarded by `not json_ok_with_data`. `CodexUsageBrowser` (line 941) launches Chrome only inside its own `.fetch()`/`_fetch_once()` — never constructed/warmed elsewhere. `widget_launch.log` shows a consecutive run of 8+ `Balance updated (source: json)` entries at 5-min refresh intervals with zero interleaved Chrome activity — live evidence on the actual running widget, not just a claim. |
| 2 | При ошибке JSON-пути виджет падает обратно на Chrome (JSONPROV-02) | VERIFIED | `fetch_once`'s `else` branch (`json_ok_with_data is False and self.browser is not None`) calls `result = await self.browser.fetch()` — the pre-existing, unmodified Chrome path. `_fetch_with_retry` in `json_usage_provider.py` never raises (catches `ProbeError` and bare `Exception`), so JSON failure can never crash `fetch_once` before reaching the fallback. `widget_launch.log` contains `Balance updated (source: chrome)` from the orchestrator's live forced-failure test (`CODEX_HOME` broken), confirming the fallback path was exercised on the real machine without a crash, followed by JSON resuming after the override was removed. Regression tests `TestFetchOnceJsonOkNoUsageDataFallback` (added in WR-03 fix, commit `efb4529`) directly assert `browser.fetch.assert_awaited_once()` for the JSON-fails-with-no-usable-data path, and were confirmed to fail when the underlying CR-01 bug was manually reintroduced — i.e. the test genuinely catches a regression of this truth. |
| 3 | Лог фиксирует источник каждого успешного обновления json\|chrome (JSONPROV-03) | VERIFIED | Single call site `write_log(outcome.log_line)` (line 2263) — `outcome.log_line` is `"Balance updated (source: json)"` (`plan_fetch_outcome`, JSON-ok-with-data branch) or `"Balance updated (source: chrome)"` (chrome-ok-with-data branch). No other write_log call records a "Balance updated" line, so every successful update is uniquely attributed. Live `widget_launch.log` on disk shows both markers actually appearing at different points in the real run. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `json_usage_provider.py` | `JsonUsageProvider.fetch()` (async, retry-once), `JsonFetchResult`, stdlib-only, no widget import | VERIFIED | Exists, 96 lines, no `import codex_balance_widget_chrome` (grep empty), implements exactly the retry-once loop described in 02-01-PLAN.md; never raises out of `fetch()`. |
| `probe_wham_usage.py` | `ProbeError.retryable` flag on 429/URLError/TimeoutError only | VERIFIED | `grep -c "retryable=True"` == 3, matching plan's exact expectation. |
| `codex_balance_widget_chrome.py` | `self.json_provider`, `build_balance_from_json_fields`, `FetchOutcome`/`plan_fetch_outcome`, rewritten `fetch_once` | VERIFIED | `self.json_provider = json_usage_provider.JsonUsageProvider()` at line 1377 (right after `self.browser` construction at 1376, unmodified); `plan_fetch_outcome` (line 541) reproduces all prior status-message branches plus source logging; `fetch_once` (line 2187) wired exactly per plan, including the CR-01 fix for the JSON-ok-but-empty-fields edge case. |
| `test_json_usage_provider.py`, `test_codex_balance_widget_chrome.py`, `test_probe_wham_usage.py` (additions) | Full unit coverage, no network/Tk | VERIFIED | 60/60 tests pass (`py -3 -m unittest test_probe_wham_usage test_json_usage_provider test_codex_balance_widget_chrome -v`), including 3 new integration-style tests added in the WR-03 fix pass that exercise `fetch_once()` itself with mocked `json_provider`/`browser`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `CodexBalanceWidget.fetch_once` | `json_usage_provider.JsonUsageProvider.fetch` | `await self.json_provider.fetch()` before any `self.browser.fetch()` | WIRED | Confirmed at `codex_balance_widget_chrome.py:2194`, executed unconditionally as the first statement in the `try` block. |
| `CodexBalanceWidget.fetch_once` | `CodexUsageBrowser.fetch` | `await self.browser.fetch()` only inside the branch where JSON did not yield usable data | WIRED | Confirmed at line 2238, inside `else` (reached only when `json_ok_with_data is False` and `self.browser` is truthy). |
| `CodexBalanceWidget.fetch_once` | `write_log` | `write_log(outcome.log_line)` — single call site | WIRED | Confirmed at line 2263, exactly one occurrence in `fetch_once`, applied to the result of all three branches via the shared `outcome` variable. |

### Behavioral Spot-Checks / Live Evidence

| Behavior | Evidence | Status |
|----------|----------|--------|
| Normal cycle never opens Chrome, logs `source: json` | `widget_launch.log` — sustained sequence of `Balance updated (source: json)` lines at 5-min intervals (09:36-10:14), matching `refresh_seconds`, no Chrome activity interleaved | PASS |
| Forced JSON failure triggers Chrome fallback without crash, logs `source: chrome` | `widget_launch.log` line `[2026-07-21 09:35:07] Balance updated (source: chrome)` with preceding `Parsed balance:` from the Chrome path; orchestrator's live-run description (broken `CODEX_HOME`, chrome.exe processes observed, then restored) cross-checked against this log entry — consistent | PASS |
| Regression test specifically targets the CR-01 defect class (JSON "ok" but no usable fields must still fall back to Chrome) | `TestFetchOnceJsonOkNoUsageDataFallback` (3 tests) added in commit `efb4529`, confirmed by the fix report to fail when the bug is manually reintroduced, confirmed still passing in the current tree (60/60) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| JSONPROV-01 | 02-02, 02-03 | Обычный цикл обновления не запускает Chrome | SATISFIED | `fetch_once` structure + live log evidence above |
| JSONPROV-02 | 02-01, 02-03 | Фолбэк на Chrome при ошибке JSON без падения приложения | SATISFIED | `JsonUsageProvider` never raises; `fetch_once` `else` branch calls `self.browser.fetch()`; live fallback confirmed in log |
| JSONPROV-03 | 02-02, 02-03 | Лог фиксирует источник каждого успешного обновления | SATISFIED | Single `write_log(outcome.log_line)` call site with `source: json`/`source: chrome` markers, confirmed in live log |

No orphaned requirements — ROADMAP.md lists exactly JSONPROV-01/02/03 for Phase 2, and all three are claimed across 02-01/02-02/02-03-PLAN.md frontmatter `requirements` fields (project uses inline ROADMAP.md requirements; no separate REQUIREMENTS.md file exists in this repo).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers found in `codex_balance_widget_chrome.py`, `json_usage_provider.py`, `probe_wham_usage.py` | — | None |

Code review history (`02-REVIEW.md` iteration 3 + `02-REVIEW-FIX.md` iteration 3): 2 critical + 2 warning findings in the initial pass (CR-01: `fetch_once` didn't actually fall back to Chrome when JSON reported "ok" with unusable fields; CR-02: unhandled exceptions in JSON path/refresh loop), all fixed; iteration 2 re-review found 1 new critical (CR-01 still not fully fixed) + 2 new warnings (WR-01 manual_refresh exception handling, WR-02 missing regression test), all fixed; iteration 3 found 1 new warning (WR-03: the CR-01 fix itself had no integration-level regression test), fixed via commit `efb4529` adding `TestFetchOnceJsonOkNoUsageDataFallback`. Remaining: 4 Info-level items (diagnostics don't disambiguate json/chrome source in the UI, a type-annotation nit, a dead-code comment, duplicated ternary) — all explicitly out of scope by the phase's own review disposition and none affect the three Success Criteria being verified here.

### Human Verification Required

None outstanding. The phase's own plan (`02-03-PLAN.md` Task 2, `checkpoint:human-verify`, gate: blocking) required a live run confirming all 7 how-to-verify steps. Per the orchestrator's briefing, this live verification was performed directly against the running widget (not simulated): normal launch showed `source: json` with no Chrome window; `CODEX_HOME` was broken to force a JSON failure, producing `source: chrome` with `chrome.exe` processes running and no crash; the override was removed and JSON resumed. The user reviewed this evidence and replied "да" (approved). This verifier independently confirmed the structural code path that produces this behavior (`fetch_once` ordering, `plan_fetch_outcome` branching, `write_log` call site) and independently observed the corresponding `source: json`/`source: chrome` entries in the actual `widget_launch.log` file on disk, which is consistent with and corroborates the human-verified narrative rather than merely trusting it.

### Gaps Summary

None. All three Roadmap Success Criteria (JSONPROV-01/02/03) are verified at the code-structure level (exists, substantive, wired) and corroborated by live log evidence independently read from `widget_launch.log`. The one code-review warning identified during the phase's own review cycle (WR-03: missing integration-level test for the CR-01 edge case) was fixed and independently re-confirmed passing (60/60 tests). No blockers, no unresolved warnings, no orphaned requirements.

---

*Verified: 2026-07-21T13:00:00Z*
*Verifier: Claude (gsd-verifier)*
