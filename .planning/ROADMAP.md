# Roadmap: Codex Balance Widget — переход на JSON-источник данных

## Milestones

- ✅ **v1.0 JSON provider integration MVP** — Phases 1, 01.1, 2 (shipped 2026-07-21)
- ✅ **v1.1 Shared usage-provider core** — Phases 3-4 (shipped 2026-07-22)
- 🚧 **v1.2 Unify tray/UI layer** — Phases 5-6 (in progress)

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

<details>
<summary>✅ v1.0 JSON provider integration MVP (Phases 1, 01.1, 2) — SHIPPED 2026-07-21</summary>

- [x] Phase 1: JSON endpoint probe (2/2 plans) — completed 2026-07-20
- [x] Phase 01.1: Address Phase 1 tech debt (INSERTED) (1/1 plans) — completed 2026-07-21
- [x] Phase 2: JSON provider integration (3/3 plans) — completed 2026-07-21

Full details: [.planning/milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

<details>
<summary>✅ v1.1 Shared usage-provider core (Phases 3-4) — SHIPPED 2026-07-22</summary>

- [x] Phase 3: Shared library extraction + Codex migration (2/2 plans) — completed 2026-07-22
- [x] Phase 4: Claude widget adoption + bugfixes (1/1 plans) — completed 2026-07-22

Full details: [.planning/milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

</details>

### 🚧 v1.2 Unify tray/UI layer (In Progress)

**Milestone Goal:** Extract the duplicated tray/UI logic (icon drawing with brand border + metric badge, tooltip formatting, color/font helpers, single-instance activation) from both widgets into `usage_widget_common`, eliminating the copy-paste between `codex_balance_widget_chrome.py` and `claude_balance_widget_v1/claude_balance_widget.py`.

- [ ] **Phase 5: Shared tray/UI + single-instance library extraction** - Build `usage_widget_common.tray` (icon rendering incl. border/badge, color/font helpers, formatting, parameterized tooltip template) and `usage_widget_common.instance` (single-instance listener/notify) from the two widgets' already-shipped, proven near-duplicate implementations (Codex `accdf0e`, Claude `d5271f0`).
- [ ] **Phase 6: Widget migration to shared modules** - Migrate both `codex_balance_widget_chrome.py` and `claude_balance_widget.py` onto the shared tray/UI and single-instance modules, removing local duplicates, with no visual/behavioral change from what's already shipped.

## Phase Details

### Phase 5: Shared tray/UI + single-instance library extraction

**Goal**: New `usage_widget_common.tray` and `usage_widget_common.instance` modules expose shared icon rendering (including brand-accent border and weekly-metric badge), color/font helpers, formatting helpers, a parameterized tooltip template, and single-instance listener/notify helpers — extracted and generalized from Codex's and Claude's near-identical, already-shipped local implementations (commits `accdf0e` and `d5271f0`) — proven correct against both widgets' real field sets and ports before either widget migrates onto them.
**Depends on**: v1.1 Phase 3 (the `usage_widget_common` package must already exist)
**Requirements**: TRAYUI-01, TRAYUI-02, TRAYUI-03, TRAYUI-04, TRAYUI-05, TRAYUI-06, INSTANCE-01
**Success Criteria** (what must be TRUE):

  1. `usage_widget_common.tray.create_tray_image(percent, *, border_color=None, metric_badge=None)` renders the same colored rounded-rect icon with percent digit or `?`/`✓` overlay that both widgets currently draw, plus a 3px brand-accent border when `border_color` is supplied (Codex `#1E88E5`, Claude `#CC785C`) and a small "W" corner badge when `metric_badge` is set — the function renders from caller-supplied parameters only, it does not decide which metric is "effective" (that stays in each widget's own `effective_codex_metric()` / `Balance.effective_metric` logic).
  2. `usage_widget_common.tray.usage_color(percent)` and `load_tray_font(size)` are importable from the shared package and reproduce the existing color-threshold and font-loading-fallback behavior of both widgets' local versions.
  3. `usage_widget_common.tray.format_percent(value)` and `format_tray_reset(reset_text, language)` reproduce the existing formatting output for both widgets' reset-text inputs.
  4. `usage_widget_common.tray.build_tray_tooltip(...)` is parameterized so Codex's 3-line tooltip (5h + weekly + credits) and Claude's simpler 2-line tooltip (5h + weekly) both render correctly from the same function, each truncated to 127 chars.
  5. `usage_widget_common.instance.start_single_instance_listener(port, on_activate)` and `notify_running_instance(port)` are importable from the shared package and reproduce both widgets' existing local-loopback-socket behavior — a second launch attempt on the same port raises the running instance's window via `on_activate`, falling back to an "already running" error only if the signal can't be delivered — proven against both widgets' fixed ports (Codex 47850, Claude 47851).

**Plans**: TBD
**UI hint**: yes

### Phase 6: Widget migration to shared modules

**Goal**: Both `codex_balance_widget_chrome.py` and `claude_balance_widget.py` consume `usage_widget_common.tray` and `usage_widget_common.instance` instead of their local duplicate `create_tray_image`/`build_tray_tooltip`/`usage_color`/`load_tray_font`/`format_tray_reset`/single-instance-listener implementations, with no visual or behavioral change from what's already shipped in commits `accdf0e` (Codex) and `d5271f0` (Claude) — same icons (incl. border color and W badge), same tooltip text, same colors, same single-instance activation behavior.
**Depends on**: Phase 5 (shared tray/UI and single-instance modules must exist and be proven)
**Requirements**: CODEXUI-01, CLAUDEUI-01
**Success Criteria** (what must be TRUE):

  1. `codex_balance_widget_chrome.py` calls the shared tray/UI functions (with its blue `#1E88E5` border and its own `effective_codex_metric()`-driven badge flag) and the shared single-instance helpers (port 47850) instead of its local copies; the local duplicate functions are removed from the file.
  2. `claude_balance_widget.py` calls the same shared tray/UI functions (with its terracotta `#CC785C` border and its own `Balance.effective_metric`-driven badge flag) and the shared single-instance helpers (port 47851) instead of its local duplicates; the local duplicate functions are removed from the file.
  3. Running both widgets shows identical tray icons (border color, weekly badge), colors, and tooltip text/formatting, and identical single-instance activation behavior, to their pre-migration (already-shipped) behavior — manual/visual verification.
  4. All existing automated tests for both widgets still pass after the migration.

**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|-----------------|--------|-----------|
| 1. JSON endpoint probe | v1.0 | 2/2 | Complete | 2026-07-20 |
| 01.1. Address Phase 1 tech debt (INSERTED) | v1.0 | 1/1 | Complete | 2026-07-21 |
| 2. JSON provider integration | v1.0 | 3/3 | Complete | 2026-07-21 |
| 3. Shared library extraction + Codex migration | v1.1 | 2/2 | Complete | 2026-07-22 |
| 4. Claude widget adoption + bugfixes | v1.1 | 1/1 | Complete | 2026-07-22 |
| 5. Shared tray/UI + single-instance library extraction | v1.2 | 0/TBD | Not started | - |
| 6. Widget migration to shared modules | v1.2 | 0/TBD | Not started | - |

*For full milestone details, see [.planning/milestones/](milestones/)*
