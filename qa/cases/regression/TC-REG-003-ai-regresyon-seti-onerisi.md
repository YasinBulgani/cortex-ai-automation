---
id: TC-REG-003
title: "AI destekli regresyon set önerisi"
suite: regression
priority: P2
type: [functional, integration]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/regression/regression_sets.feature:22
requirements: [REQ-REG-002]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-010]
tags: [migrated-pr3]
---

# TC-REG-003 — AI regresyon seti önerisi

## Önkoşul

Projede senaryolar mevcut, AI servisi erişilebilir

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../regression-sets/suggest` ile istek gönder | HTTP 200 |
| 2 | `sets` dizisini kontrol et | En az 1 set önerisi |
| 3 | Her öneride `name`, `description`, `scenario_ids` kontrol et | Alanlar dolu |

---
_Section: Regresyon Setleri (Regression Sets). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
