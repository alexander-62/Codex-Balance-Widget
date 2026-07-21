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

### Active

(Defined per milestone — see `.planning/REQUIREMENTS.md`)

### Out of Scope

- Merging Claude and Codex widgets into a single process/tray icon — considered, rejected for now: keeps failure domains isolated (a provider bug in one widget shouldn't crash the other). Revisit only as a deliberate later step.

## Context

Two independent desktop widgets exist:
- `codex_balance_widget_chrome.py` (this repo) — JSON-first with Chrome fallback, async refresh loop, `JsonUsageProvider` retry-once pattern, redaction-guarded diagnostics.
- `claude_balance_widget_v1/claude_balance_widget.py` (sibling dir, `d:/00_Projects/claude_balance_widget_v1`, freshly git-initialized) — Claude Code usage widget, currently has 2 known bugs: tray tooltip truncation crash (160 vs pystray's 128 limit) and no fast-retry after 401 (waits full refresh interval).

Known residual backlog from v1.0 (non-blocking, documented in `.planning/milestones/v1.0-MILESTONE-AUDIT.md`): 4 minor pre-existing warnings in `probe_wham_usage.py` (rounding, UnicodeDecodeError, truthiness guard, redact() case-sensitivity), 3 info items in Phase 2 code (UI diagnostics, type annotation, dead code).

## Constraints

- **Isolation**: Codex and Claude widgets remain separate processes/repos — only the retry/redaction/error-classification *pattern* is shared, not a merged runtime. Why: crash isolation between two independent data sources.
- **Stdlib-first**: Existing provider code (`json_usage_provider.py`, `probe_wham_usage.py`) uses only Python stdlib, no third-party deps for the fetch/retry core. Why: matches established v1.0 pattern, keeps the shared library dependency-free.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| JSON-first with Chrome fallback (v1.0) | Chrome scraping is slow/fragile; JSON endpoint proven viable by standalone probe | ✓ Good |
| Keep Codex/Claude widgets as separate processes | Crash isolation; avoids one shared failure domain | — Pending |
| Extract shared retry/redaction library, don't merge widgets | User explicitly chose "shared code, separate processes" over full merge after discussing tradeoffs | — Pending |

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
*Last updated: 2026-07-21 after v1.0 milestone, before v1.1 kickoff*
