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
duration: 3min
completed: 2026-07-17
---

# Phase 1 Plan 2: Live probe run, fixture capture, and human review Summary

**Live `GET https://chatgpt.com/backend-api/wham/usage` returned HTTP 200; redacted fixture `wham_usage_fixture.json` captured with zero schema drift from RESEARCH; Task 2 human-verify checkpoint reached and awaiting user confirmation.**

## Performance

- **Duration:** ~3 min (Task 1 only; Task 2 is a pending human checkpoint)
- **Started:** 2026-07-17T18:01:44+03:00 (after 01-01 completion commit)
- **Completed (Task 1):** 2026-07-17T18:03:54+03:00
- **Tasks:** 1/2 (Task 2 is `checkpoint:human-verify`, awaiting user response)
- **Files modified:** 1 (new)

## Accomplishments

- Ran `py -3 probe_wham_usage.py --fixture wham_usage_fixture.json` from repo root with the live token in `~/.codex/auth.json` (auth_mode=chatgpt) — exit 0, `HTTP status: 200`, pretty redacted JSON, and an `Extracted fields (Balance)` block printed to stdout.
- Extracted fields on this run: `five_hour_percent` absent (expected on plan=plus — no 5h window in the response, per RESEARCH Pitfall 1), `weekly_percent: 69` (used_percent 31, remaining 69), `credits: 0`, `weekly_reset_text: 2026-07-23 10:39`.
- Fixture `wham_usage_fixture.json` written, valid JSON, contains `rate_limit`, and passes the redaction post-check (`json.loads` succeeds; no `eyJ` or `@` substrings anywhere in the file) — `user_id`/`account_id`/`email`/`spend_control.individual_limit` all show `<redacted>`.
- `git status --porcelain` on the six locked widget files (`codex_balance_widget_chrome.py`, `codex_balance_widget_launcher.pyw`, `install.bat`, `run.bat`, `run_hidden.vbs`, `requirements.txt`) returned empty — confirmed untouched.
- Overall `git status --porcelain` showed only `?? wham_usage_fixture.json` — no modified files outside `.planning/`.
- Schema comparison against `01-RESEARCH.md` Endpoint Contract: **zero drift**. Same top-level keys, same `rate_limit.primary_window` (weekly, `limit_window_seconds: 604800`) / `secondary_window: null` shape, same `credits`/`spend_control`/`rate_limit_reset_credits` structure. Only the live numeric values differ (`used_percent: 31` this run vs `16` in RESEARCH's earlier capture, different `reset_after_seconds`) — expected, not drift.

## Task Commits

1. **Task 1: Живой запуск пробы, фикстура и проверка чистоты git** - `500e8d9` (feat)

**Plan metadata:** (pending — will be added after Task 2 checkpoint resolves)

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

Task 1 (the only automatable/auto task in this plan) is complete and committed (`500e8d9`). Task 2 is a `checkpoint:human-verify` gate (`gate="blocking"`) — it does not modify files and cannot be auto-approved by an executor agent; it requires the actual user to run `py -3 probe_wham_usage.py --no-fixture`, review the printed fields against the current widget, inspect `wham_usage_fixture.json` for redaction, and confirm `git status` cleanliness, then respond "approved" (or describe issues).

This plan is paused at the Task 2 checkpoint pending that human response; the orchestrator must present the checkpoint to the real user and resume/re-invoke to close out the plan (mark requirement PROBE-03 complete, add the final `docs` metadata commit) once approval is received.

## Self-Check: PASSED

- FOUND: wham_usage_fixture.json
- FOUND commit: 500e8d9 (feat: Task 1 live fixture capture)

---
*Phase: 01-json-endpoint-probe*
*Completed: 2026-07-17 (Task 1 only; Task 2 checkpoint pending)*
