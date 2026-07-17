---
phase: 1
slug: json-endpoint-probe
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-17
updated: 2026-07-17
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | python stdlib `unittest` (репо без pytest; зависимостей не добавляем) |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `py -3 -m unittest test_probe_wham_usage -v` |
| **Full suite command** | `py -3 -m unittest test_probe_wham_usage -v` + live run `py -3 probe_wham_usage.py` |
| **Estimated runtime** | ~5 seconds (unit) / ~10 seconds (live) |

---

## Sampling Rate

- **After every task commit:** Run `py -3 -m unittest test_probe_wham_usage -v`
- **After every plan wave:** Run full suite + live probe
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | PROBE-02 | T-1-02 | redact()/redaction_clean покрыты unit-тестами; тесты без сети и без реального auth.json | unit | `py -3 -m unittest test_probe_wham_usage -v` | создаётся задачей | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | PROBE-04 | T-1-01 | токен только в build_headers; ошибки — русская строка + exit 1, без traceback | unit + CLI | `py -3 -m unittest test_probe_wham_usage -v` + `CODEX_HOME=<пустая папка> py -3 probe_wham_usage.py --no-fixture` → exit 1, вывод содержит "auth.json", без "Traceback" | создаётся задачей | ⬜ pending |
| 01-02-T1 | 01-02 | 2 | PROBE-01, PROBE-03 | T-1-05, T-1-07 | фикстура пишется только после redact(); пост-проверка "eyJ"/"@"; git-чистота рабочего кода | live smoke + автопроверка | `py -3 probe_wham_usage.py --fixture wham_usage_fixture.json` && python-проверка фикстуры (нет eyJ/@, есть rate_limit) && `git status --porcelain <6 файлов рабочего кода>` пуст | создаётся задачей | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | Success Criteria 1-2 | T-1-06 | ревьюер подтверждает отсутствие email/JWT в stdout и фикстуре | human-verify (checkpoint) | — (manual, см. how-to-verify плана 01-02) | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `test_probe_wham_usage.py` — stubs: классификация окон по limit_window_seconds, редакция фикстуры (нет `eyJ`, нет `@`), парсинг auth.json
  - Покрывается задачей 01-01-T1 (tdd="true": тесты пишутся до реализации внутри той же задачи; отдельная Wave 0 не требуется)
- [x] нет conftest/framework install — stdlib unittest

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Живой HTTP 200 от wham/usage с реальным токеном | Success Criteria 1 | Требует живого токена/сети | `py -3 probe_wham_usage.py` — статус 200, pretty JSON, извлечённые окна (частично автоматизировано в 01-02-T1: exit 0 + проверки) |
| 401-диагностика без traceback | Success Criteria 4 | Требует битого/протухшего токена — реальный auth.json портить нельзя | ветка «нет файла» автоматизирована (`CODEX_HOME=<пустая папка>`); полная 401-ветка — при случайном протухании токена, поведение задано таблицей «Семантика ошибок» RESEARCH |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (нет MISSING — тесты создаются первой задачей)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned 2026-07-17 (planner)
