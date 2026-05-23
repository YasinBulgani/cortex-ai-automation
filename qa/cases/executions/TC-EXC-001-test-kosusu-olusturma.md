---
id: TC-EXC-001
title: "Yeni test koşusu başlatma"
suite: executions
priority: P0
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/executions/execution_management.feature:15
requirements: [REQ-EXC-001]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-007]
tags: [migrated-pr3]
---

# TC-EXC-001 — Test koşusu oluşturma

## Önkoşul

Senaryolar mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/executions` ile koşu oluştur | HTTP 201 |
| 2 | `status` kontrol et | `"running"` |
| 3 | `scenario_total` kontrol et | Gönderilen senaryo sayısı |

---
_Section: Test Koşusu ve Sonuçlar (Executions). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
