# Requirements: v1.2 Unify tray/UI layer

## v1 Requirements

### Shared Tray/UI Layer (usage_widget_common)

- [ ] **TRAYUI-01**: `usage_widget_common` exposes a shared `create_tray_image(percent, *, border_color=None, metric_badge=None)` function (icon rendering: colored rounded rect + percent digit or `?`/`✓`) that both widgets consume instead of their own local copy.
- [ ] **TRAYUI-02**: `usage_widget_common` exposes shared `usage_color(percent)` and `load_tray_font(size)` helpers, consumed by both widgets.
- [ ] **TRAYUI-03**: `usage_widget_common` exposes a shared `format_percent(value)` and `format_tray_reset(reset_text, language)` formatting helper, consumed by both widgets.
- [ ] **TRAYUI-04**: `usage_widget_common` exposes a shared, parameterized `build_tray_tooltip(...)` template — parameterized so Codex's extra "credits" line and Claude's simpler 2-line usage block both render correctly from the same shared function, truncated to 127 chars.
- [ ] **TRAYUI-05**: `create_tray_image`'s `border_color` param draws a 3px brand-accent outline around the icon so the two widgets are visually distinguishable at a glance — Codex passes its blue (`#1E88E5`), Claude passes its terracotta (`#CC785C`). Already implemented directly in both widgets (commits `accdf0e` Codex, `d5271f0` Claude) as the proof-before-extraction step; Phase 5 generalizes this into the shared module, Phase 6 removes the local duplicates.
- [ ] **TRAYUI-06**: `create_tray_image`'s `metric_badge` param draws a small letter "W" in a corner whenever the displayed percent is the weekly value rather than the 5-hour value. Already implemented directly in both widgets (same commits as TRAYUI-05) — Codex's `effective_codex_metric()` falls back to weekly when 5h is absent from the API; Claude's `Balance.effective_metric` reports whichever of 5h/weekly is the binding (lower) constraint. Phase 5/6 extract and migrate this the same way as TRAYUI-05.

### Shared Single-Instance Activation (usage_widget_common)

- [ ] **INSTANCE-01**: `usage_widget_common` exposes shared `start_single_instance_listener(port, on_activate)` and `notify_running_instance(port)` helpers (local-loopback TCP socket signal), extracted from both widgets' now-duplicated implementations (already implemented directly, same commits as TRAYUI-05/06) — a second launch attempt raises the running instance's window instead of showing an "already running" error, falling back to the error only if the signal can't be delivered. Each widget keeps its own fixed port (Codex 47850, Claude 47851).

## Already Delivered (not requiring shared extraction)

- Window shows only a close button (no minimize/maximize); closing minimizes to tray. Implemented directly in both widgets via `resizable(False, False)` + `-toolwindow` attribute (same commits as above) — trivial 3-line pattern, not worth a shared abstraction, no further phase work needed.

## Codex Widget Migration

- [ ] **CODEXUI-01**: `codex_balance_widget_chrome.py` consumes the shared tray/UI functions (TRAYUI-01..06) and the shared single-instance helpers (INSTANCE-01) instead of its own local copies, with no visual/behavioral change from what's already shipped in commit `accdf0e`.

## Claude Widget Migration

- [ ] **CLAUDEUI-01**: `claude_balance_widget.py` consumes the same shared tray/UI functions and single-instance helpers instead of its local copies, with no visual/behavioral change from what's already shipped in commit `d5271f0`.

## Future Requirements (Deferred)

- Unifying tray-menu command structure (`_tray_toggle`/`_tray_refresh`/`_tray_open_site` naming/wiring parity) — noted as a smaller, lower-value follow-up; not required for this milestone's goal.
- Live verification of Phase 4 (v1.1) Claude widget against real credentials — still outstanding from v1.1, unrelated to this milestone's scope, tracked separately in STATE.md Deferred Items.

## Out of Scope

- Merging the two widgets into one process — see PROJECT.md Constraints (crash-isolation rationale), still holds.
- Changing the actual data/fetch logic — this milestone touches only the tray/UI/window-activation rendering layer, not `usage_widget_common.retry`/`errors`/`redaction`/`fetch_decision` (v1.1's deliverables, untouched here).
- New third-party UI dependencies — stays within the existing `pystray`/`Pillow`/stdlib `socket` stack already used by both widgets.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRAYUI-01 | Phase 5 | Pending |
| TRAYUI-02 | Phase 5 | Pending |
| TRAYUI-03 | Phase 5 | Pending |
| TRAYUI-04 | Phase 5 | Pending |
| TRAYUI-05 | Phase 5 | Pending |
| TRAYUI-06 | Phase 5 | Pending |
| INSTANCE-01 | Phase 5 | Pending |
| CODEXUI-01 | Phase 6 | Pending |
| CLAUDEUI-01 | Phase 6 | Pending |
