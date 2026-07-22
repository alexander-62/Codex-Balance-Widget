# Phase 3: Shared library extraction + Codex migration - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract retry-once, error-classification, redaction, and fetch-decision primitives from Codex's proven `json_usage_provider.py` / `probe_wham_usage.py` into a new standalone package `usage_widget_common`, then migrate the Codex widget onto it with no behavior change. Pure infra/refactor phase — no new user-facing behavior, no design choices, discuss skipped per infra-detection rule.

</domain>

<decisions>
## Implementation Decisions

### Shared Package Location (resolved via direct user question — not Claude's Discretion)
- New sibling repo: `d:/00_Projects/usage_widget_common`, own git repo, own history.
- Both Codex and Claude widgets consume it via relative path / `sys.path` insertion (or local `pip install -e`) — no PyPI publish, no vendoring/copying.
- Rationale (user-confirmed): keeps neither widget repo dependent on the other; a genuinely third, independent location.

### Claude's Discretion
Everything else is at Claude's discretion — infra phase, technical fixes/extraction only:
- Exact module/file layout inside `usage_widget_common` (e.g. `retry.py`, `redaction.py`, `errors.py`, `fetch_decision.py` vs one flat module) — mirror the granularity of what's being extracted.
- Exact import mechanism the Codex widget uses to reach the sibling package (`sys.path.insert` at top of `json_usage_provider.py`/`probe_wham_usage.py`, or a `pip install -e ../usage_widget_common` into the venv) — pick whichever is simplest given this project has no existing packaging/venv infrastructure (stdlib-only, no requirements.txt-managed venv observed for Codex widget).
- Naming of shared primitives (can keep `ProbeError`-style names or rename now that they're generic — prefer renaming to something source-agnostic like `FetchError`/`RetryableFetcher` since Claude widget will use them for a different API, not "probe").

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (the extraction source)
- `json_usage_provider.py`'s `_fetch_with_retry` — the retry-once loop to generalize.
- `probe_wham_usage.py`'s `ProbeError` (with `retryable` flag) — the error-classification pattern to generalize.
- `probe_wham_usage.py`'s `redact()` / `redaction_clean()` — the redaction denylist + post-check pattern to generalize.
- `codex_balance_widget_chrome.py`'s `plan_fetch_outcome` — the pure fetch-decision function to generalize (currently hardcoded to json/chrome sources; must become parameterized).

### Established Patterns
- Stdlib-only, no third-party deps (matches v1.0 pattern, carried as an explicit v1.1 constraint).
- Single-diagnostic-string error contract (one clean message, not multiple exception types leaking to caller).
- Tests use `unittest`, no network, extensive mocking via `unittest.mock.patch`.

### Integration Points
- `json_usage_provider.py` and `probe_wham_usage.py` (Codex repo) become the first consumers — this phase's acceptance bar.
- `claude_balance_widget.py` (sibling repo) is NOT touched in this phase — it's Phase 4's job, but the shared package's API must be generic enough that Phase 4 doesn't need to reshape it.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond SHARED-01..04 and CODEX-01 exactly as defined in `.planning/REQUIREMENTS.md`. No new features, no scope beyond extraction + migration.

</specifics>

<deferred>
## Deferred Ideas

- Claude widget adoption itself — deferred to Phase 4 (already scoped there).
- Publishing `usage_widget_common` anywhere beyond local sibling-repo consumption (PyPI, private index) — not needed for 2 local widgets, out of scope entirely unless raised later.

</deferred>
