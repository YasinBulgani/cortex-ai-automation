---
id: TC-SCN-004
title: "Birden fazla senaryonun toplu silinmesi"
suite: scenarios
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - backend/tests/bdd/features/scenario_management.feature:46
requirements: [REQ-SCN-001]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-SCN-004 — Senaryo toplu silme

## Önkoşul

Birden fazla senaryo mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | 3 senaryo oluştur, ID'leri kaydet | 3 senaryo mevcut |
| 2 | `POST /api/v1/tspm/projects/{id}/scenarios/bulk-delete` ile 3 ID gönder | HTTP 204 döner |
| 3 | Silinen senaryoları GET ile sorgula | HTTP 404 döner |

---
_Section: Senaryo Yönetimi (Scenario Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
