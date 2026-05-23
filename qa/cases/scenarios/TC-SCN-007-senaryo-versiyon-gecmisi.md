---
id: TC-SCN-007
title: "Senaryo versiyon geçmişi sorgulama"
suite: scenarios
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SCN-002]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-SCN-007 — Senaryo versiyon geçmişi

## Önkoşul

Senaryo en az 2 kez güncellenmiş

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/{id}/scenarios/{scenarioId}/versions` | HTTP 200, versiyon listesi |
| 2 | Versiyon sırasını kontrol et | Azalan sırada (en yeni en üstte) |
| 3 | Her versiyonda `title`, `description`, `steps`, `status` kontrol et | Tüm snapshot alanları mevcut |

---
_Section: Senaryo Yönetimi (Scenario Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
