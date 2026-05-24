---
id: TC-SCN-003
title: "Senaryo listesinde arama filtrelemesi"
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
    - e2e/bdd/features/scenarios/scenario_management.feature:17
    - backend/tests/bdd/features/scenario_management.feature:35
requirements: [REQ-SCN-001]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-SCN-003 — Senaryo listeleme ve arama

## Önkoşul

Birden fazla senaryo mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/{id}/scenarios` ile tam liste al | Tüm senaryolar döner |
| 2 | `GET /api/v1/tspm/projects/{id}/scenarios?q=login` ile arama yap | Sadece başlığında "login" geçen senaryolar |
| 3 | Olmayan bir terimle arama yap | Boş dizi döner |

---
_Section: Senaryo Yönetimi (Scenario Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
