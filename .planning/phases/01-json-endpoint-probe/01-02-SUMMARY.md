---
phase: 01-json-endpoint-probe
plan: 02
subsystem: infra
tags: [urllib, wham-usage, codex-cli, fixture, redaction]

# Dependency graph
requires:
  - phase: 01-json-endpoint-probe (plan 01)
    provides: "probe_wham_usage.py stdlib probe with tested fetch_usage/write_fixture/extract_fields/redact functions"
provides:
  - "wham_usage_fixture.json: live-captured, redacted response from GET https://chatgpt.com/backend-api/wham/usage (plan_type=plus, weekly window only, no 5h window present)"
  - "Confirmed zero schema drift vs 01-RESEARCH.md Endpoint Contract on a second live run"
  - "Confirmed git cleanliness of all six locked widget files after a live probe run"
affects: ["phase 2 (widget JSON provider integration) will use wham_usage_fixture.json as the reference fixture for parser tests"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live fixture capture followed immediately by three automated gates (redaction post-check, locked-file git-porcelain check, schema-shape comparison against RESEARCH) before any human review"

key-files:
  created: [wham_usage_fixture.json]
  modified: []

key-decisions:
  - "Fixture content matches the 01-RESEARCH.md Endpoint Contract example byte-for-byte in structure (same keys, same primary_window/secondary_window nullability, same credits/spend_control/rate_limit_reset_credits shape) — documented as zero drift rather than re-deriving a new schema"

requirements-completed: [PROBE-01, PROBE-03]

# Metrics
duration: ~10min
completed: 2026-07-20
---

# Phase 1 Plan 2: Live probe run, fixture capture, and human review Summary

**Live `GET https://chatgpt.com/backend-api/wham/usage` returned HTTP 200; redacted fixture `wham_usage_fixture.json` captured with zero schema drift from RESEARCH; user confirmed a second independent live run's extracted fields (weekly 80%, credits 0, five_hour absent) match the Codex balance widget exactly — Task 2 approved.**

## Performance

- **Duration:** ~10 min (Task 1 automated run + Task 2 human verification round-trip)
- **Started:** 2026-07-17T18:01:44+03:00 (after 01-01 completion commit)
- **Completed (Task 1):** 2026-07-17T18:03:54+03:00
- **Completed (Task 2, user approval received):** 2026-07-20
- **Tasks:** 2/2
- **Files modified:** 1 (new)

## Accomplishments

- Ran `py -3 probe_wham_usage.py --fixture wham_usage_fixture.json` from repo root with the live token in `~/.codex/auth.json` (auth_mode=chatgpt) — exit 0, `HTTP status: 200`, pretty redacted JSON, and an `Extracted fields (Balance)` block printed to stdout.
- Extracted fields on this run: `five_hour_percent` absent (expected on plan=plus — no 5h window in the response, per RESEARCH Pitfall 1), `weekly_percent: 69` (used_percent 31, remaining 69), `credits: 0`, `weekly_reset_text: 2026-07-23 10:39`.
- Fixture `wham_usage_fixture.json` written, valid JSON, contains `rate_limit`, and passes the redaction post-check (`json.loads` succeeds; no `eyJ` or `@` substrings anywhere in the file) — `user_id`/`account_id`/`email`/`spend_control.individual_limit` all show `<redacted>`.
- `git status --porcelain` on the six locked widget files (`codex_balance_widget_chrome.py`, `codex_balance_widget_launcher.pyw`, `install.bat`, `run.bat`, `run_hidden.vbs`, `requirements.txt`) returned empty — confirmed untouched.
- Overall `git status --porcelain` showed only `?? wham_usage_fixture.json` — no modified files outside `.planning/`.
- Schema comparison against `01-RESEARCH.md` Endpoint Contract: **zero drift**. Same top-level keys, same `rate_limit.primary_window` (weekly, `limit_window_seconds: 604800`) / `secondary_window: null` shape, same `credits`/`spend_control`/`rate_limit_reset_credits` structure. Only the live numeric values differ (`used_percent: 31` this run vs `16` in RESEARCH's earlier capture, different `reset_after_seconds`) — expected, not drift.
- **Task 2 (human review) approved by the user.** The user ran `py -3 probe_wham_usage.py --no-fixture` directly (a third independent live run) and compared the printed `Extracted fields (Balance)` block against a screenshot of the current Chrome-scraping widget: weekly 80% remaining (used 20%), weekly reset `2026-07-26 14:45`, credits `0`, `five_hour` absent — all four fields matched the widget exactly. The user separately re-verified the fixture redaction (`rate_limit` present; `email`/`user_id`/`account_id`/`spend_control.individual_limit` all `<redacted>`; no `eyJ`/`@` substrings) and confirmed `git status` showed only the expected new files.

## Task Commits

1. **Task 1: Живой запуск пробы, фикстура и проверка чистоты git** - `500e8d9` (feat)
2. **Task 2: Ревью вывода пробы и фикстуры** - checkpoint, no file changes; approved by user (response: "approved")

**Plan metadata:** `e6b8b36` (docs: Task 1 interim summary), final commit below

## Files Created/Modified

- `wham_usage_fixture.json` - Redacted live capture of the `wham/usage` response: `rate_limit` (weekly window only), `credits`, `spend_control`, `rate_limit_reset_credits`; `user_id`/`account_id`/`email`/`individual_limit` replaced with `<redacted>`.

## Decisions Made

- Schema drift check: compared the fixture's key structure to the RESEARCH.md live-response example field-by-field; concluded no structural drift, only expected value differences (percentages, timestamps) between two independent live captures on the same account.

## Deviations from Plan

None - Task 1 executed exactly as written: single live GET, fixture write, and all three specified autochecks (redaction post-check, locked-file git-porcelain check, schema comparison) passed on the first attempt. No retry was needed (no non-200 response encountered).

## Issues Encountered

None.

## User Setup Required

None - the probe used the existing `~/.codex/auth.json` maintained by Codex CLI; no new credentials or services were introduced.

## Next Phase Readiness

Both tasks complete. Live endpoint access, field extraction, and fixture redaction are proven end-to-end and independently confirmed by the user against the actual widget UI. All five phase Success Criteria are closed:

1. Live status + pretty JSON — `HTTP status: 200` printed on every run (Task 1, and the user's independent Task 2 run).
2. Extracted fields / honest list of missing ones — weekly %, credits, weekly reset printed and matched to the widget; `five_hour` correctly reported as absent (not an error) on this plus-plan account.
3. Redacted fixture — `wham_usage_fixture.json` committed, passes automated post-check and manual user inspection.
4. Diagnostics without traceback — covered by plan 01-01 (`ProbeError` branches), re-confirmed indirectly by the clean live runs in this plan.
5. Git shows only new files — verified twice (Task 1 automated check + user's own `git status` in Task 2).

`wham_usage_fixture.json` is ready to serve as the reference fixture for Phase 2's widget JSON-provider integration and parser tests. No blockers.

## Self-Check: PASSED

- FOUND: wham_usage_fixture.json
- FOUND commit: 500e8d9 (feat: Task 1 live fixture capture)
- FOUND commit: e6b8b36 (docs: Task 1 interim summary)

---
*Phase: 01-json-endpoint-probe*
*Completed: 2026-07-20 (both tasks complete, Task 2 approved by user)*
