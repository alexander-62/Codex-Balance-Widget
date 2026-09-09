---
quick_id: 260909-r1
slug: codex-reset-credits
status: complete
created: 2026-09-09
---

# Research: Codex Usage Limit Resets

## Goal

Add usage limit reset credits to the Codex balance widget below the existing credits row, including expiry text when available.

## Findings

- The widget's primary data source is `GET https://chatgpt.com/backend-api/wham/usage`, called by `probe_wham_usage.fetch_usage()`.
- The local auth source is `$CODEX_HOME/auth.json` via `probe_wham_usage.load_tokens()`.
- The existing JSON path maps API response data through `probe_wham_usage.extract_fields()`, `JsonUsageProvider.fetch()`, and `build_balance_from_json_fields()`.
- A live redacted API response on 2026-09-09 returned:

```json
"rate_limit_reset_credits": {
  "available_count": 2,
  "applicable_available_count": 0
}
```

- The same live JSON did not include per-reset expiry timestamps or labels. The browser page does show expiry rows, so expiry support should be optional and tolerant:
  - JSON: read `available_count` and `applicable_available_count` now.
  - JSON future-proofing: accept common expiry keys if OpenAI later adds them.
  - Chrome fallback: parse `Usage limit resets` text and `Expires ...` rows when text fallback is used.

## Decision

Implement count display from JSON as the reliable path. Show expiry text only when present in a future JSON schema or when Chrome fallback text provides it. Do not force a hidden Chrome scrape just to get expiry because that would slow the currently-working JSON refresh path.
