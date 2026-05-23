---
id: TC-REG-001
title: "Yeni regresyon seti oluşturma"
suite: regression
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/regression/regression_sets.feature:14
requirements: [REQ-REG-001]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-010]
tags: [migrated-pr3]
---

# TC-REG-001 — Regresyon seti oluşturma

## Önkoşul

Proje mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/regression-sets` ile set oluştur | HTTP 201 |
| 2 | `scenario_count` kontrol et | `0` (boş set) |

---
_Section: Regresyon Setleri (Regression Sets). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
