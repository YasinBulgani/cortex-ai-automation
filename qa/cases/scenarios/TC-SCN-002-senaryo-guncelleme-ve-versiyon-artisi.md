---
id: TC-SCN-002
title: "Senaryo güncellenince versiyon numarası artmalı"
suite: scenarios
priority: P0
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - backend/tests/bdd/features/scenario_management.feature:26
requirements: [REQ-SCN-001, REQ-SCN-002]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-SCN-002 — Senaryo güncelleme ve versiyon artışı

## Önkoşul

Mevcut senaryo

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Mevcut senaryo `current_version` değerini not al | Örneğin `1` |
| 2 | `PUT /api/v1/tspm/projects/{id}/scenarios/{scenarioId}` ile güncelleme gönder | HTTP 200 döner |
| 3 | `current_version` kontrol et | `2` (bir artmış) |
| 4 | Versiyon geçmişini sorgula | Önceki versiyon kaydedilmiş olmalı |

---
_Section: Senaryo Yönetimi (Scenario Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
