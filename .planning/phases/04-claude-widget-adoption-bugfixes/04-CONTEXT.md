# Phase 4: Claude widget adoption + bugfixes - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary

`claude_balance_widget.py` (sibling repo `d:/00_Projects/claude_balance_widget_v1`) adopts the shared `usage_widget_common` package (built and proven in Phase 3, lives at `d:/00_Projects/usage_widget_common`) for its retry/error-classification logic. Two known bugs get fixed as a natural consequence of wiring in the new retry/backoff logic: tray tooltip truncation crash and slow post-401 retry. Pure infra/bugfix phase — no new user-facing features, discuss skipped per infra-detection rule.

</domain>

<decisions>
## Implementation Decisions

### Shared Package Location (already resolved in Phase 3, not re-litigated)
- `usage_widget_common` lives at `d:/00_Projects/usage_widget_common`, its own git repo, stdlib-only.
- Consumed via `sys.path` insertion bootstrap — see the exact pattern already proven in `codex_balance_widget_chrome.py`/`json_usage_provider.py`/`probe_wham_usage.py` (this repo) for the boilerplate to mirror, including the hardened error handling from Phase 3's 3-iteration code review (existence check raising `ModuleNotFoundError`/`SystemExit` split by entry point, not a bare unguarded import).

### Claude's Discretion
Everything else is at Claude's discretion — infra/bugfix phase:
- Exact call sites in `claude_balance_widget.py` where `usage_widget_common.retry.fetch_with_retry_once` and `usage_widget_common.errors.FetchError` replace whatever ad-hoc retry/error logic currently exists there (read the file first — this widget was NOT part of v1.0, so its current error handling shape is unknown going in).
- Whether `usage_widget_common.redaction` and `usage_widget_common.fetch_decision` are also adopted here, or whether this widget's needs don't call for them (Claude Code's `.credentials.json` auth model differs from Codex's `auth.json`; the widget may not need a JSON/fallback fetch-decision skeleton at all if it only has one data source — investigate during planning, don't assume the same 4 primitives all apply symmetrically).
- Exact backoff schedule tuning (30s → 60s → 120s per the original todo, or whatever `usage_widget_common.retry` actually implements — check Phase 3's `retry.py` for its real signature/behavior rather than assuming the todo's exact numbers are hardcoded into the shared function).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `usage_widget_common` package (Phase 3 deliverable): `errors.FetchError`, `redaction.redact`/`redaction_clean`, `retry.fetch_with_retry_once`, `fetch_decision.decide_fetch_source` — all stdlib-only, unit-tested (20 tests), proven against Codex's real usage in Phase 3.
- The exact `sys.path` bootstrap pattern (with existence-check hardening from Phase 3's code review) in any of the 3 Codex files — copy this pattern, don't reinvent it.

### Established Patterns (from the sibling todo `.planning/todos/pending/claude-widget-tooltip-and-401-retry.md`, now resolves_phase: 4)
- Tooltip bug: `build_tray_tooltip()` truncates to `tooltip[:160]` (~line 709) but pystray's actual limit is 128 — fix is `tooltip[:127]`.
- 401 bug: widget reads `accessToken` from `.credentials.json` but doesn't refresh it itself; on 401 it waits the full `refresh_seconds` (5 min) instead of retrying fast. Fix: fast retry with backoff (30 → 60 → 120s) after 401/network errors, then fall back to normal interval — this is exactly what `usage_widget_common.retry` should provide generically.

### Integration Points
- `claude_balance_widget.py` in sibling repo `d:/00_Projects/claude_balance_widget_v1` (freshly git-initialized this milestone, baseline commit `e1c240b`) is the sole file touched.
- Must NOT modify anything in `usage_widget_common` itself unless a genuine bug/gap is found (that would be an unplanned change to a Phase-3-delivered, already-reviewed artifact — flag it rather than silently patching if it comes up).

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond CLAUDE-01..03 exactly as defined in `.planning/REQUIREMENTS.md`. No new features, no scope beyond adoption + the 2 named bugfixes.

</specifics>

<deferred>
## Deferred Ideas

- Merging Claude and Codex widgets into one process — out of scope for this entire milestone (see PROJECT.md Out of Scope).
- Any further hardening of `usage_widget_common` beyond what Phase 3 already delivered — if a real gap is found while adopting it in Claude's widget, defer to a follow-up phase/todo rather than scope-creeping into Phase 3's already-closed, reviewed work.

</deferred>
