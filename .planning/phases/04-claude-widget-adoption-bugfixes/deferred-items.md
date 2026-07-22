# Deferred Items — Phase 04, Plan 01

Items discovered during execution that are out of scope for this plan's task changes (pre-existing, not caused by this plan's edits).

## README_RU.md — markdownlint MD029 (ordered list prefix)

- **File:** `d:/00_Projects/claude_balance_widget_v1/README_RU.md`
- **Line:** ~54 (the `3. Запустите виджет:` item under `## Установка`)
- **Issue:** markdownlint flags `Expected: 1; Actual: 3` because the numbered list (`1.`/`2.`/`3.`) is interrupted by a fenced code block, which some linters treat as breaking list continuity.
- **Pre-existing:** Yes — this exact list structure existed in the original `README_RU.md` before Task 3's edit; Task 3 only inserted a new `## Требования` section before `## Установка` and did not touch the numbered list itself.
- **Action taken:** None (out of scope per SCOPE BOUNDARY — only auto-fix issues directly caused by the current task's changes).
