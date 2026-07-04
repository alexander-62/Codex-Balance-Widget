---
status: complete
---

# Summary

- Added `prune_chrome_profile_cache()` and cache size launch flags.
- Documented that cache cleanup preserves login state.
- Verification: `python -m py_compile codex_balance_widget_chrome.py codex_balance_widget_launcher.pyw`.
- Ran the prune function once; the local `Default` profile directory dropped from about 52.9 MB to about 9.2 MB.
