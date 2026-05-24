---
id: TC-SCH-003
title: "Boş zamanlamayı tetikleme hatası"
suite: schedules
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SCH-002]
pre_conditions: [PRE-002, PRE-003, PRE-005]
tags: [migrated-pr3]
---

# TC-SCH-003 — Senaryo olmadan zamanlama tetikleme hatası

## Önkoşul

Senaryo bağlanmamış zamanlama

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Senaryo ID'si olmayan zamanlamayı tetikle | HTTP 400, "Zamanlamada senaryo bulunamadı" |

---
_Section: Zamanlamalar (Schedules). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
