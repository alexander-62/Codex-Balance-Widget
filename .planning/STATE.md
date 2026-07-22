---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Unify tray/UI layer
status: planning
last_updated: "2026-07-23T00:00:00.000Z"
last_activity: 2026-07-23
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/ROADMAP.md (updated 2026-07-23)

**Core value:** Reliable, low-friction usage-limit visibility without opening a browser tab.
**Current focus:** Phase 5 — Shared tray/UI + single-instance library extraction (ready to plan)

## Current Position

Phase: 5 of 6 overall (v1.2 Phase 1 of 2) — Shared tray/UI + single-instance library extraction
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-07-23 — v1.2 ROADMAP.md re-created to cover all 9 current requirements (previous draft only covered 6); Phase 5 now TRAYUI-01..06 + INSTANCE-01, Phase 6 now CODEXUI-01/CLAUDEUI-01; REQUIREMENTS.md traceability updated, 9/9 mapped

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 9 (v1.0: 6, v1.1: 3)
- Average duration: see .planning/milestones/v1.0-MILESTONE-AUDIT.md and v1.1 audit
- Total execution time: see milestone audits

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 (v1.0) | 2 | - | - |
| 01.1 (v1.0) | 1 | - | - |
| 2 (v1.0) | 3 | - | - |
| 3 (v1.1) | 2 | - | - |
| 4 (v1.1) | 1 | - | - |
| 5 (v1.2) | 0 (TBD) | - | - |
| 6 (v1.2) | 0 (TBD) | - | - |

**Recent Trend:**

- Last 5 plans: v1.0/v1.1 only — no v1.2 plans executed yet
- Trend: N/A (roadmap just re-created, no execution yet)

*Updated after each plan completion*

## Accumulated Context

### Roadmap Evolution

- Phase 01.1 inserted after Phase 1 (v1.0): Address Phase 1 code-review debt (CR-01/CR-02/WR-01) before completing milestone v1.0 (URGENT)
- v1.1 roadmap created: Phase 3 (shared library extraction + Codex migration, SHARED-01..04 + CODEX-01) and Phase 4 (Claude widget adoption + bugfixes, CLAUDE-01..03)
- v1.2 roadmap first drafted (superseded): Phase 5 (TRAYUI-01..04) and Phase 6 (CODEXUI-01, CLAUDEUI-01) — only covered 6/9 requirements, written before TRAYUI-05/06 and INSTANCE-01 existed.
- v1.2 roadmap RE-CREATED 2026-07-23: REQUIREMENTS.md expanded to 9 requirements (added TRAYUI-05 border-color outline, TRAYUI-06 metric badge, INSTANCE-01 single-instance listener/notify; CODEXUI-01/CLAUDEUI-01 descriptions updated to reference the new commits). Phase 5 now covers TRAYUI-01..06 + INSTANCE-01 (extraction of `usage_widget_common.tray` + new `usage_widget_common.instance`, generalizing the already-shipped, already-duplicated implementations proven in Codex commit `accdf0e` and Claude commit `d5271f0`). Phase 6 unchanged in shape (CODEXUI-01, CLAUDEUI-01 migration) but now also covers single-instance-helper migration, not just tray/UI. Same 2-phase "prove in both real widgets first, then extract, then migrate" shape as v1.1 Phase 3/4 and the original v1.2 draft — only the requirement set inside each phase grew.

### Decisions

- Рабочий код виджета (Chrome-скрейпинг) в Phase 1 не изменяется — только новый тестовый скрипт.
- Источник данных: `GET https://chatgpt.com/backend-api/wham/usage`, Bearer-токен из `~/.codex/auth.json` (см. .planning/seeds/codex-json-endpoint.md).
- v1.1 grouping: extract shared library together with the Codex migration (Phase 3) rather than as a standalone untested abstraction; Claude widget adoption deferred to Phase 4.
- v1.2 grouping: build the shared `usage_widget_common.tray` (+ new `usage_widget_common.instance`) modules as their own phase (Phase 5, single wave — building the modules IS the deliverable), then migrate both widgets in Phase 6 as two small, symmetric, mechanical swaps with no cross-dependency between them.
- v1.2 border/badge semantics (TRAYUI-05/06): the shared `create_tray_image` only renders what it's told (a `border_color` and a `metric_badge` flag) — it does NOT unify each widget's "which metric is effective" decision logic. Codex's `effective_codex_metric()` (falls back to weekly when 5h absent) and Claude's `Balance.effective_metric` (picks whichever of 5h/weekly is more restrictive) remain separate, widget-owned decisions; only their boolean/flag output crosses into the shared rendering function.
- v1.2 already-shipped-then-extract pattern: TRAYUI-05, TRAYUI-06, and INSTANCE-01's underlying behavior is already implemented ad-hoc in both widgets (Codex `accdf0e`, Claude `d5271f0`) as a deliberate proof-before-extraction step, same pattern that worked in v1.0→v1.1 (Phase 1 proved the JSON provider standalone before Phase 2 integrated it). Phase 5 extracts/generalizes; Phase 6 migrates both widgets onto the extracted modules with zero visual/behavioral regression from what's already shipped.
- Window-chrome (single-close-button via `resizable(False, False)` + `-toolwindow`) explicitly excluded from shared extraction — trivial 3-line pattern already implemented identically in both widgets; not worth a shared abstraction, no phase/requirement created for it (see REQUIREMENTS.md "Already Delivered").

### Pending Todos

See Deferred Items below — 2 tracked todos, both pre-date this milestone.

### Blockers/Concerns

- Widgets remain separate processes/tray icons in both phases (explicit constraint carried from PROJECT.md, not revisited this milestone).
- Shared package must stay stdlib-only aside from the existing Pillow/pystray stack — no new third-party deps, per PROJECT.md constraints and REQUIREMENTS.md Out of Scope.
- v1.1 Phase 3/4 directories (`.planning/phases/03-*`, `04-*`) remain unarchived intentionally, pending a live-credentials verification the user is holding off on — do not move/touch them; not a blocker for v1.2 phase numbering (v1.2 starts fresh at Phase 5).

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| todo | claude-widget-tooltip-and-401-retry.md | RESOLVED — fixed and closed by v1.1 Phase 4 (CLAUDE-02, CLAUDE-03), todo file removed 2026-07-22 | v1.0 close, 2026-07-21 |
| todo | codex-5h-none-partial-parse.md | still pending — re-triaged as likely not-a-bug (JSON endpoint confirms no 5h limit on this account, matches widget's honest report); not pulled into v1.1 or v1.2, remains for a future session with real evidence of an actual bug | v1.0 close, 2026-07-21 |
| verification_gap | Phase 04 (04-VERIFICATION.md) — human_needed | acknowledged and deferred at v1.1 close — no live run against real Claude Code credentials occurred this session (machine has no .credentials.json); all automated evidence passed; user explicitly chose to continue without live validation rather than block; still outstanding, unrelated to v1.2 scope | v1.1 close, 2026-07-22 |
| requirement (deferred) | Unifying tray-menu command structure (`_tray_toggle`/`_tray_refresh`/`_tray_open_site` naming/wiring parity) | deferred out of v1.2 — smaller, lower-value follow-up; visual/formatting unification is this milestone's priority | v1.2 requirements, 2026-07-22 |

## Session Continuity

Last session: 2026-07-23
Stopped at: v1.2 ROADMAP.md re-created to cover all 9 current requirements (was 6); STATE.md updated; REQUIREMENTS.md traceability table updated (9/9 requirements mapped to Phase 5 or Phase 6)
Resume file: None

## Operator Next Steps

- Plan Phase 5 with `/gsd-plan-phase 5`
