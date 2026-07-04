---
status: complete
---

# Prune Chrome Profile Cache

Add a small, safe cache-pruning path for the dedicated Chrome profile so the widget keeps authentication state but removes bulky generated cache folders before browser refreshes.

## Scope

- Prune known Chrome cache directories under `codex_chrome_profile`.
- Preserve cookies, login storage, settings, and usage history.
- Document the behavior.
- Verify Python syntax and run the prune function once.
