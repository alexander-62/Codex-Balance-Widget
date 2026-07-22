# Phase 5: Shared tray/UI + single-instance library extraction - Context

**Gathered:** 2026-07-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract already-proven, already-shipped tray/UI rendering and single-instance-activation code from both widgets into new `usage_widget_common.tray` and `usage_widget_common.instance` modules. Pure infra/extraction phase — the actual user-facing behavior (border colors, weekly badge, close-to-tray, instant re-launch activation) already shipped in Codex commit `accdf0e` and Claude commit `d5271f0`; this phase only generalizes the already-working code into the shared package. No new behavior, no design choices, discuss skipped per infra-detection rule.

</domain>

<decisions>
## Implementation Decisions

### Exact extraction source (Claude's Discretion for module layout, but the function bodies to generalize are locked — mirror what's already shipped, don't redesign)

**`usage_widget_common.tray` — extract from:**
- Codex `codex_balance_widget_chrome.py` (commit `accdf0e`): `create_tray_image(percent, *, border_color=None, metric_badge=None)`, `usage_color(percent)`, `load_tray_font(size)`, `hex_to_rgb(color)`, `format_tray_reset(reset_text, language)`, `build_tray_tooltip(...)`.
- Claude `claude_balance_widget.py` (commit `d5271f0`): the same function set, near-identical implementation, minor differences: Claude's `usage_color` treats low-percent as RED/high as GREEN (remaining-based semantics) while Codex's likely treats it the same way — verify both during extraction and do NOT silently unify differing color-threshold semantics without flagging it; Claude's tooltip has no "credits" line, Codex's does — `build_tray_tooltip` must stay parameterized to handle both (already true directionally per TRAYUI-04's phrasing prior to this session, now also carries border/badge related fields through unchanged since those are icon-only concerns, not tooltip text).
- `create_tray_image`'s `border_color`/`metric_badge` params are pure rendering — the function must NOT decide which color or badge to show (that stays a per-widget decision: Codex's `effective_codex_metric()`, Claude's `Balance.effective_metric` — do NOT extract or unify these two decision functions, they encode genuinely different "which metric is binding" semantics per widget's data shape).

**`usage_widget_common.instance` — extract from:**
- Both widgets' `_start_single_instance_listener()` method (near-identical: bind local TCP socket, accept loop, close connection, call `self._run_on_ui(self.show_window_from_tray)`/equivalent) and module-level `notify_running_instance()` function (connect-with-timeout, return bool).
- Generalize to `start_single_instance_listener(port: int, on_activate: Callable[[], None]) -> None` (spawns its own daemon thread internally, takes an `on_activate` callback instead of hardcoding `self.show_window_from_tray`) and `notify_running_instance(port: int, timeout: float = 1.0) -> bool`.
- Each widget keeps calling with its own fixed port (Codex 47850, Claude 47851) and its own `is_exiting`/`show_window_from_tray`-equivalent callback — the port number and activation callback are NOT hardcoded in the shared module.

### Claude's Discretion
- Whether `tray.py`/`instance.py` are separate files or one combined module in `usage_widget_common` — mirror the granularity of the existing 4 modules (`errors.py`/`redaction.py`/`retry.py`/`fetch_decision.py`), i.e. prefer separate files matching this project's established one-concern-per-module convention.
- Exact internal structure of the listener's accept-loop thread management (already a settled ~20-line pattern in both widgets — copy it, don't redesign it).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (the extraction source, already working)
- `codex_balance_widget_chrome.py` commit `accdf0e` — full working reference implementation for Codex's usage.
- `claude_balance_widget.py` commit `d5271f0` — full working reference implementation for Claude's usage.
- Both already have 64/64 (Codex) and passing (Claude `test_core.py`) test suites that exercise the current (pre-extraction) local implementations — Phase 6 must keep these green after migration.

### Established Patterns
- Same sys.path bootstrap pattern from v1.1 (existence-check, ModuleNotFoundError/SystemExit split) — this phase's new shared modules don't need their own bootstrap, they're imported the same way `errors`/`redaction`/`retry`/`fetch_decision` already are.
- Stdlib-only + Pillow/pystray only (already the case for both widgets' tray code) — `usage_widget_common` stays dependency-free beyond what's already implied by consumers needing Pillow/pystray themselves (the shared module can assume `Image`/`ImageDraw`/`ImageFont` are available since only tray-code callers import it, matching how the local versions already guard with `if Image is None or ImageDraw is None: return None`).

### Integration Points
- `usage_widget_common/__init__.py` (v1.1) currently re-exports the 4 existing modules' public API — this phase's new `tray`/`instance` modules should follow the same re-export convention for consistency.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond TRAYUI-01..06 and INSTANCE-01 exactly as defined in `.planning/REQUIREMENTS.md`. The visual/behavioral design (border colors, badge letter, close-to-tray, activation-on-relaunch) is already locked from direct conversation with the user this session — this phase is pure code reorganization, not a design phase.

</specifics>

<deferred>
## Deferred Ideas

- Unifying the two widgets' "which metric is effective" decision functions (`effective_codex_metric` vs `Balance.effective_metric`) — deliberately NOT in scope, these encode different semantics per widget's data availability shape.
- Window-chrome (`resizable`/`-toolwindow`) — explicitly excluded from shared extraction per REQUIREMENTS.md "Already Delivered", trivial 3-line duplication, not worth abstracting.
- Tray-menu command structure unification — deferred to a future milestone if ever prioritized.

</deferred>
