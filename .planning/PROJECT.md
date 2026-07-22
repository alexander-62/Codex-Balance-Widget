# Codex Balance Widget

## What This Is

Desktop Tk tray widget showing Codex usage limits (5h%, weekly%, resets, credits) without relying on Chrome scraping as the primary path. Sibling project `claude_balance_widget_v1` (d:/00_Projects/claude_balance_widget_v1) does the same for Claude Code usage — separate codebase, same shape of problem (poll an API/scrape a page, show tray icon, refresh loop).

## Core Value

Reliable, low-friction usage-limit visibility without opening a browser tab.

## Requirements

### Validated

- ✓ JSON-first usage fetch via `wham/usage` endpoint, Chrome scrape as fallback — v1.0
- ✓ Every successful update logs its source (json|chrome) — v1.0
- ✓ Standalone probe script proves endpoint viability before touching widget code — v1.0
- ✓ Phase 1 code-review debt (redaction post-check, malformed-payload crash, broad exception handling) closed — v1.0 (Phase 01.1)
- ✓ Shared stdlib-only retry/error-classification/redaction/fetch-decision library (`usage_widget_common`), proven against Codex's real usage — v1.1 (Phase 3)
- ✓ Claude widget adopts the same shared library; tooltip-truncation crash and slow post-401 retry fixed — v1.1 (Phase 4)

### Active

(Defined per milestone — see `.planning/REQUIREMENTS.md`, created fresh by `/gsd-new-milestone`)

### Out of Scope

- Merging Claude and Codex widgets into a single process/tray icon — considered, rejected for now: keeps failure domains isolated (a provider bug in one widget shouldn't crash the other). Confirmed again during v1.1 (shared *code*, not shared *runtime*, was the chosen path). Revisit only as a deliberate later step.

## Context

Three repos now make up this ecosystem:
- `codex_balance_widget_chrome.py` (this repo, `d:/00_Projects/codex_balance_widget`) — JSON-first with Chrome fallback, async refresh loop, consumes `usage_widget_common` for retry/error-classification/redaction/fetch-decision.
- `claude_balance_widget_v1/claude_balance_widget.py` (sibling dir, `d:/00_Projects/claude_balance_widget_v1`) — Claude Code usage widget, now also consumes `usage_widget_common`; both known bugs (tooltip truncation, slow 401 retry) fixed in v1.1.
- `usage_widget_common` (sibling dir, `d:/00_Projects/usage_widget_common`) — new in v1.1, stdlib-only shared package (`FetchError`, `redact`/`redaction_clean`, `fetch_with_retry_once`, `decide_fetch_source`), own git history, consumed read-only by both widgets via a hardened `sys.path` bootstrap.

Known residual backlog (non-blocking, documented in `.planning/milestones/v1.0-MILESTONE-AUDIT.md` and `v1.1-MILESTONE-AUDIT.md`): a handful of pre-existing/deferred INFO-level polish items in `probe_wham_usage.py` and both widgets (rounding, magic numbers, traceback-identity comments, unused `REDACTED_PLACEHOLDER` export), plus one deferred human-verification item — no live run of the Claude widget against real Claude Code credentials has occurred yet (this dev machine has none); all automated coverage passed.

One pending todo remains, re-triaged during v1.1: `codex-5h-none-partial-parse.md` — likely NOT a bug (the JSON endpoint itself confirms the account has no 5-hour limit, matching the widget's honest "not found" report); left open for a future session with real evidence of an actual parsing defect.

## Constraints

- **Isolation**: Codex and Claude widgets remain separate processes/repos — only the retry/redaction/error-classification *pattern* is shared, not a merged runtime. Why: crash isolation between two independent data sources.
- **Stdlib-first**: Existing provider code (`json_usage_provider.py`, `probe_wham_usage.py`) uses only Python stdlib, no third-party deps for the fetch/retry core. Why: matches established v1.0 pattern, keeps the shared library dependency-free.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| JSON-first with Chrome fallback (v1.0) | Chrome scraping is slow/fragile; JSON endpoint proven viable by standalone probe | ✓ Good |
| Keep Codex/Claude widgets as separate processes | Crash isolation; avoids one shared failure domain | ✓ Good — confirmed through v1.1, no shared-failure incidents |
| Extract shared retry/redaction library, don't merge widgets | User explicitly chose "shared code, separate processes" over full merge after discussing tradeoffs | ✓ Good — `usage_widget_common` proven against both widgets, 0 critical/warning remaining after review cycles |
| New shared package lives in its own third sibling repo (`usage_widget_common`), not nested in either widget repo | Keeps neither widget dependent on the other; genuinely independent location | ✓ Good — clean 3-repo E2E integration confirmed by v1.1 audit |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-22 after v1.1 milestone*
