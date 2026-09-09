---
quick_id: 260909-r1
slug: codex-reset-credits
status: complete
created: 2026-09-09
code_commit: f00613f
---

# Summary: Show Codex Reset Credits

## Completed

- Added extraction of `rate_limit_reset_credits.available_count` and `applicable_available_count` from the live `wham/usage` JSON payload.
- Added optional reset-credit expiry extraction for future JSON shapes and Chrome fallback text.
- Extended `Balance`, history save/restore, and the main widget UI.
- Added a second line below credits: `Resets: N`, with optional `applicable now` and `expires` details when available.
- Updated tests for JSON extraction, async provider propagation, Balance mapping, and Chrome fallback text parsing.

## Research Evidence

Live `python probe_wham_usage.py --no-fixture` on 2026-09-09 returned:

```json
"rate_limit_reset_credits": {
  "available_count": 2,
  "applicable_available_count": 0
}
```

No expiry field was present in the live API response. Expiry display is therefore conditional.

## Verification

- `python -m unittest test_probe_wham_usage.py test_json_usage_provider.py test_codex_balance_widget_chrome.py` -> 66 tests passed.
- `python -m py_compile probe_wham_usage.py json_usage_provider.py codex_balance_widget_chrome.py` -> passed.
- Live `probe_wham_usage.py --no-fixture` extracted:
  - `reset_credits_available: 2`
  - `reset_credits_applicable: 0`
  - `reset_credits_expiry_text: absent in response`
