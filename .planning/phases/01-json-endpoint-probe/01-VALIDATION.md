---
phase: 1
slug: json-endpoint-probe
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-17
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
| (планировщик заполнит) | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `test_probe_wham_usage.py` — stubs: классификация окон по limit_window_seconds, редакция фикстуры (нет `eyJ`, нет `@`), парсинг auth.json
- [ ] нет conftest/framework install — stdlib unittest

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Живой HTTP 200 от wham/usage с реальным токеном | Success Criteria 1 | Требует живого токена/сети | `py -3 probe_wham_usage.py` — статус 200, pretty JSON, извлечённые окна |
| 401-диагностика без traceback | Success Criteria 4 | Требует битого токена | подменить токен env-переменной/флагом и убедиться в человекочитаемой ошибке |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
