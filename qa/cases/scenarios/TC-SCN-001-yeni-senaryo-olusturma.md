---
id: TC-SCN-001
title: "Projeye yeni test senaryosu ekleme"
suite: scenarios
priority: P0
type: [functional, smoke]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/scenarios/scenario_management.feature:10
    - backend/tests/bdd/features/scenario_management.feature:11
requirements: [REQ-SCN-001]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-SCN-001 — Yeni senaryo oluşturma

## Önkoşul

Proje mevcut, geçerli JWT

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/scenarios` ile senaryo verisi gönder | HTTP 201 döner |
| 2 | Yanıtta `id`, `title`, `status`, `current_version` kontrol et | Tüm alanlar dolu, `current_version=1` |
| 3 | Oluşturulan senaryoyu `GET` ile sorgula | Aynı veri döner |

---
_Section: Senaryo Yönetimi (Scenario Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
