---
id: TC-SCN-005
title: "Analiz metninden BDD senaryosu üretme"
suite: scenarios
priority: P0
type: [functional, integration]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SCN-003]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-SCN-005 — BDD senaryo üretimi (AI)

## Önkoşul

Proje mevcut, AI servisi erişilebilir

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/scenarios/generate-bdd` ile analiz metni gönder | HTTP 200 döner |
| 2 | Yanıtta `scenarios` dizisini kontrol et | En az 1 senaryo üretilmiş |
| 3 | Her senaryoda `title`, `description`, `gherkin`, `steps` kontrol et | Tüm alanlar dolu |

---
_Section: Senaryo Yönetimi (Scenario Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
