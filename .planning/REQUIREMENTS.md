# Requirements: v1.2 Unify tray/UI layer

## v1 Requirements

### Shared Tray/UI Layer (usage_widget_common)

- [ ] **TRAYUI-01**: `usage_widget_common` exposes a shared `create_tray_image(percent)` function (icon rendering: colored rounded rect + percent digit or `?`/`✓`) that both widgets consume instead of their own local copy.
- [ ] **TRAYUI-02**: `usage_widget_common` exposes shared `usage_color(percent)` and `load_tray_font(size)` helpers, consumed by both widgets.
- [ ] **TRAYUI-03**: `usage_widget_common` exposes a shared `format_percent(value)` and `format_tray_reset(reset_text, language)` formatting helper, consumed by both widgets.
- [ ] **TRAYUI-04**: `usage_widget_common` exposes a shared, parameterized `build_tray_tooltip(...)` template — parameterized so Codex's extra "credits" line and Claude's simpler 2-line usage block both render correctly from the same shared function, truncated to 127 chars.

### Codex Widget Migration

- [ ] **CODEXUI-01**: `codex_balance_widget_chrome.py` consumes the shared tray/UI functions instead of its local `create_tray_image`/`build_tray_tooltip`/`usage_color`/`load_tray_font`/`format_tray_reset`, with no visual/behavior change (same icon, same tooltip text, same colors).

### Claude Widget Migration

- [ ] **CLAUDEUI-01**: `claude_balance_widget.py` consumes the same shared tray/UI functions instead of its local duplicates, with no visual/behavior change.

## Future Requirements (Deferred)

- Unifying tray-menu command structure (`_tray_toggle`/`_tray_refresh`/`_tray_open_site` naming/wiring parity) — noted as a smaller, lower-value follow-up; not required for this milestone's goal (visual/formatting unification is the priority).
- Live verification of Phase 4 (v1.1) Claude widget against real credentials — still outstanding from v1.1, unrelated to this milestone's scope, tracked separately in STATE.md Deferred Items.

## Out of Scope

- Merging the two widgets into one process — see PROJECT.md Constraints (crash-isolation rationale), still holds.
- Changing the actual data/fetch logic — this milestone touches only the tray/UI rendering layer, not `usage_widget_common.retry`/`errors`/`redaction`/`fetch_decision` (v1.1's deliverables, untouched here).
- New third-party UI dependencies — stays within the existing `pystray`/`Pillow` stack already used by both widgets.

## Traceability

(Filled by roadmapper)

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRAYUI-01 | — | Pending |
| TRAYUI-02 | — | Pending |
| TRAYUI-03 | — | Pending |
| TRAYUI-04 | — | Pending |
| CODEXUI-01 | — | Pending |
| CLAUDEUI-01 | — | Pending |
