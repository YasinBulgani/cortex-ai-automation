---
id: TC-SCH-001
title: "Yeni zamanlama oluşturma"
suite: schedules
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SCH-001]
pre_conditions: [PRE-002, PRE-003, PRE-005]
tags: [migrated-pr3]
---

# TC-SCH-001 — Zamanlama oluşturma

## Önkoşul

Proje ve senaryolar mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../schedules` ile cron ifadesi ve senaryo ID'leri gönder | HTTP 201 |
| 2 | `cron_expression`, `is_active` kontrol et | Gönderilen değerlerle eşleşir |

---
_Section: Zamanlamalar (Schedules). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
