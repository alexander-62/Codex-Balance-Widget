---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Shared usage-provider core
status: executing
last_updated: "2026-07-22T16:46:16.252Z"
last_activity: 2026-07-22 -- Phase 3 execution started
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 2
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/ROADMAP.md (updated 2026-07-22)

**Core value:** Reliable, low-friction usage-limit visibility without opening a browser tab.
**Current focus:** Phase 3 — shared-library-extraction-codex-migration

## Current Position

Phase: 3 (shared-library-extraction-codex-migration) — EXECUTING
Plan: 1 of 2
Status: Executing Phase 3
Last activity: 2026-07-22 -- Phase 3 execution started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 6 (v1.0)
- Average duration: see .planning/milestones/v1.0-MILESTONE-AUDIT.md
- Total execution time: see .planning/milestones/v1.0-MILESTONE-AUDIT.md

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 (v1.0) | 2 | - | - |
| 01.1 (v1.0) | 1 | - | - |
| 2 (v1.0) | 3 | - | - |
| 3 (v1.1) | 0 | - | - |
| 4 (v1.1) | 0 | - | - |

**Recent Trend:**

- Last 5 plans: v1.0 only — no v1.1 plans executed yet
- Trend: N/A (new milestone)

*Updated after each plan completion*

## Accumulated Context

### Roadmap Evolution

- Phase 01.1 inserted after Phase 1 (v1.0): Address Phase 1 code-review debt (CR-01/CR-02/WR-01) before completing milestone v1.0 (URGENT)
- v1.1 roadmap created: Phase 3 (shared library extraction + Codex migration, SHARED-01..04 + CODEX-01) and Phase 4 (Claude widget adoption + bugfixes, CLAUDE-01..03)

### Decisions

- Рабочий код виджета (Chrome-скрейпинг) в Phase 1 не изменяется — только новый тестовый скрипт.
- Источник данных: `GET https://chatgpt.com/backend-api/wham/usage`, Bearer-токен из `~/.codex/auth.json` (см. .planning/seeds/codex-json-endpoint.md).
- v1.1 grouping: extract shared library together with the Codex migration (Phase 3) rather than as a standalone untested abstraction, since Codex's existing code is the source pattern being extracted; Claude widget adoption + bugfixes deferred to Phase 4 once the library is proven.

### Pending Todos

See Deferred Items below — 2 tracked todos, both pre-date this milestone.

### Blockers/Concerns

- **Open question for Phase 3 planning**: exact filesystem location of the shared package (working name `usage_widget_common/`) is unresolved. This repo (`codex_balance_widget`) hosts `.planning/`, but Phase 4's consumer (`claude_balance_widget.py`) lives in the separate sibling repo `d:/00_Projects/claude_balance_widget_v1` (freshly git-initialized, no shared history). Options include: a new subdirectory in one of the two existing repos referenced cross-repo, a new third sibling repo/package, or another arrangement — must be resolved during Phase 3 planning/discussion, not assumed.
- Widgets remain separate processes/tray icons in both phases (explicit constraint carried from PROJECT.md, not revisited this milestone).
- Shared package must stay stdlib-only (no new third-party deps) — constraint applies to both phases.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| todo | claude-widget-tooltip-and-401-retry.md | now scheduled — addressed by v1.1 Phase 4 (CLAUDE-02, CLAUDE-03) | v1.0 close, 2026-07-21 |
| todo | codex-5h-none-partial-parse.md | still pending — re-triaged as likely not-a-bug; not pulled into v1.1 (see REQUIREMENTS.md Future Requirements) | v1.0 close, 2026-07-21 |

## Session Continuity

Last session: 2026-07-22
Stopped at: v1.1 ROADMAP.md and STATE.md written; REQUIREMENTS.md traceability table updated (8/8 requirements mapped to Phase 3 or Phase 4)
Resume file: None

## Operator Next Steps

- Run `/gsd-plan-phase 3` to begin planning Phase 3 (Shared library extraction + Codex migration). Resolve the shared-package-location open question (see Blockers/Concerns) during that planning/discussion step.
