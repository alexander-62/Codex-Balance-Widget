# Roadmap: Codex Balance Widget — переход на JSON-источник данных

## Milestones

- ✅ **v1.0 JSON provider integration MVP** — Phases 1, 01.1, 2 (shipped 2026-07-21)
- 🚧 **v1.1 Shared usage-provider core** — Phases 3-4 (in progress)

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

### 🚧 v1.1 Shared usage-provider core (In Progress)

**Milestone Goal:** Extract the retry/error-classification/redaction/fetch-decision logic proven in the Codex widget into a shared, stdlib-only library, then adopt it in both widgets — fixing the Claude widget's two known bugs along the way.

- [x] **Phase 3: Shared library extraction + Codex migration** - Extract `usage_widget_common` from Codex's existing, tested patterns and migrate the Codex widget onto it with no behavior change. (completed 2026-07-22)
- [x] **Phase 4: Claude widget adoption + bugfixes** - Wire the Claude widget onto the shared library, fixing its tooltip-truncation crash and slow 401 retry as part of the rewiring. (completed 2026-07-22)

## Phase Details

### Phase 3: Shared library extraction + Codex migration

**Goal**: A new stdlib-only shared package (`usage_widget_common`, hosted in its own sibling repo at `d:/00_Projects/usage_widget_common` — location resolved via 03-CONTEXT.md) exposes retry-once, error-classification, redaction, and fetch-decision primitives extracted from Codex's already-proven `json_usage_provider.py` / `probe_wham_usage.py` patterns. The Codex widget consumes these from the shared package instead of its local copies, with no behavior change — proving the abstraction against real, tested code before the Claude widget (Phase 4) depends on it.
**Depends on**: v1.0 Phase 2 (JSON provider integration) — extracts the patterns that phase built
**Requirements**: SHARED-01, SHARED-02, SHARED-03, SHARED-04, CODEX-01
**Success Criteria** (what must be TRUE):

  1. A shared package exists exposing public retry-once, error-classification (`retryable` flag), redaction-denylist/`redaction_clean()`-style, and pure fetch-decision (`plan_fetch_outcome`-style) primitives, importable independently of any single widget.
  2. `json_usage_provider.py` and `probe_wham_usage.py` import their retry/classification/redaction logic from the shared package instead of local copies.
  3. All existing Codex widget/provider tests still pass unmodified in intent (import paths may change, behavior does not).
  4. Inspecting the shared package's imports shows stdlib only — no third-party dependencies introduced.
  5. The shared fetch-decision function is parameterized by primary/fallback semantics rather than hardcoded to Codex's JSON/Chrome sources, so a different widget can supply its own.

**Plans:** 2/2 plans complete

Plans:
- [x] 03-01-PLAN.md — Bootstrap `usage_widget_common` sibling repo; implement FetchError, redact/redaction_clean, fetch_with_retry_once, decide_fetch_source (SHARED-01..04)
- [x] 03-02-PLAN.md — Migrate `probe_wham_usage.py`, `json_usage_provider.py`, `codex_balance_widget_chrome.py` onto the shared package with no behavior change (CODEX-01)

### Phase 4: Claude widget adoption + bugfixes

**Goal**: `claude_balance_widget.py` (sibling repo `d:/00_Projects/claude_balance_widget_v1`) consumes the shared package for its retry/error-classification logic, and its two known bugs — tooltip-truncation crash and slow post-401 retry — are fixed as a natural consequence of wiring in the new retry/backoff logic.
**Depends on**: Phase 3 (shared package must exist and be importable from the sibling repo)
**Requirements**: CLAUDE-01, CLAUDE-02, CLAUDE-03
**Success Criteria** (what must be TRUE):

  1. `claude_balance_widget.py` calls the shared package's retry-once wrapper and error classification for its usage-fetch calls instead of any local duplicate logic.
  2. Tray tooltip text is truncated to 127 characters (not 160); the widget no longer raises `ValueError: string too long` for long tooltip content.
  3. After a 401 (or other transient/auth) error, the widget retries using the shared backoff schedule (e.g. 30s → 60s → 120s) instead of waiting the full `refresh_seconds` interval before the next attempt.
  4. The widget runs end-to-end with the new wiring (manual verification), showing usage updates via the shared retry path with no behavioral regression versus prior behavior.

**Plans:** 1/1 plans complete

Plans:
- [x] 04-01-PLAN.md — Adopt usage_widget_common retry/error-classification; fix tooltip truncation and post-failure backoff; harden sibling-repo bootstrap (launcher/install-script/README parity)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|-----------------|--------|-----------|
| 1. JSON endpoint probe | v1.0 | 2/2 | Complete | 2026-07-20 |
| 01.1. Address Phase 1 tech debt (INSERTED) | v1.0 | 1/1 | Complete | 2026-07-21 |
| 2. JSON provider integration | v1.0 | 3/3 | Complete | 2026-07-21 |
| 3. Shared library extraction + Codex migration | v1.1 | 2/2 | Complete    | 2026-07-22 |
| 4. Claude widget adoption + bugfixes | v1.1 | 1/1 | Complete    | 2026-07-22 |

*For full v1.0 details, see [.planning/milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)*
