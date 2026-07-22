# Requirements: v1.1 Shared usage-provider core

## v1 Requirements

### Shared Library (usage_widget_common)

- [ ] **SHARED-01**: New shared package provides an async retry-once wrapper for transient fetch errors (mirrors `json_usage_provider.py`'s `_fetch_with_retry` pattern), usable by both Codex and Claude widgets.
- [ ] **SHARED-02**: Shared package provides error classification (a `retryable` flag distinguishing transient errors — network timeout/429/connection reset — from permanent ones — 401/403/malformed response).
- [ ] **SHARED-03**: Shared package provides a redaction denylist + `redaction_clean()`-style post-check reusable by any widget that prints/logs API response fields, preventing token/PII leaks in stdout or log files.
- [ ] **SHARED-04**: Shared package provides a pure fetch-decision skeleton (mirrors `plan_fetch_outcome`) expressing "primary source ok" / "primary source failed → fallback" / "both failed → retain existing data" as a testable pure function, parameterized so each widget supplies its own primary/fallback semantics.

### Codex Widget Migration

- [ ] **CODEX-01**: `json_usage_provider.py` and `probe_wham_usage.py` consume the shared package's retry/error-classification/redaction logic instead of their own local copies, with no behavior change (all 64 existing tests still pass unmodified in intent, though import paths change).

### Claude Widget Adoption + Bugfixes

- [ ] **CLAUDE-01**: `claude_balance_widget.py` adopts the shared package's retry-once wrapper and error classification for its usage-fetch calls.
- [ ] **CLAUDE-02**: Tray tooltip is truncated to 127 characters (not 160), preventing the `ValueError: string too long (142, maximum length 128)` crash from `build_tray_tooltip()`.
- [ ] **CLAUDE-03**: After a 401 (or other transient/auth error), the widget retries quickly using the shared package's backoff (e.g. 30s → 60s → 120s) instead of waiting the full `refresh_seconds` interval before the next attempt.

## Future Requirements (Deferred)

- Merging Claude and Codex widgets into a single process/tray icon — deliberately deferred, see PROJECT.md Out of Scope.
- Fixing pre-existing `probe_wham_usage.py` warnings (rounding, UnicodeDecodeError, redact() case-sensitivity) — tracked as backlog from v1.0 audit, not required for this milestone's goal.
- Codex widget's `codex-5h-none-partial-parse.md` todo — re-triaged during this session: JSON endpoint itself confirms no 5h limit exists on this account (matches widget's "not found" report), so this may not be a bug at all. Left in `.planning/todos/pending/` for a future session to close or re-open with real evidence, not pulled into this milestone.

## Out of Scope

- Single merged widget process — see PROJECT.md Constraints (crash-isolation rationale).
- New third-party dependencies for the shared package — must stay stdlib-only, matching v1.0's established pattern.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SHARED-01 | Phase 3 | Pending |
| SHARED-02 | Phase 3 | Pending |
| SHARED-03 | Phase 3 | Pending |
| SHARED-04 | Phase 3 | Pending |
| CODEX-01 | Phase 3 | Pending |
| CLAUDE-01 | Phase 4 | Pending |
| CLAUDE-02 | Phase 4 | Pending |
| CLAUDE-03 | Phase 4 | Pending |
