# Milestones

## v1.0 JSON provider integration MVP (Shipped: 2026-07-21)

**Phases completed:** 3 phases, 6 plans, 12 tasks

**Key accomplishments:**

- Standalone stdlib probe (`probe_wham_usage.py`) proving `wham/usage` field extraction and window classification, backed by 23 network-free unittest cases; live-run diagnostics confirmed for the missing-auth.json branch.
- Live `GET https://chatgpt.com/backend-api/wham/usage` returned HTTP 200; redacted fixture `wham_usage_fixture.json` captured with zero schema drift from RESEARCH; user confirmed a second independent live run's extracted fields (weekly 80%, credits 0, five_hour absent) match the Codex balance widget exactly — Task 2 approved.
- Hardened `probe_wham_usage.py`'s malformed-payload tolerance, stdout redaction post-check, and exception handling contract with 4 new regression tests proving each fix.
- Extended `probe_wham_usage.ProbeError` with a `retryable` flag (429/URLError/TimeoutError = True, all else False) and built `json_usage_provider.py` — a new stdlib-only async wrapper (`JsonUsageProvider.fetch()` / `JsonFetchResult`) implementing exactly one retry on transient errors and immediate fallback-signal on 401/403, fully unit-tested without network access.
- Added ISO reset-date parsing, a JSON-fields-to-Balance mapper, and a pure `plan_fetch_outcome` decision function that reproduces every status message currently in `fetch_once`, all covered by 17 new unit tests — `fetch_once` itself is untouched, ready for Plan 02-03 to wire it in.
- `fetch_once` now tries the JSON usage endpoint first via `JsonUsageProvider`, falling back to the existing `CodexUsageBrowser` (Chrome) only on JSON failure, with a single logging point recording `source: json`/`source: chrome` — confirmed working live on the running widget by the user, including a forced JSON-path failure that correctly triggered the Chrome fallback without crashing.

---
