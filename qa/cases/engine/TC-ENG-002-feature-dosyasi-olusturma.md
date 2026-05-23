---
id: TC-ENG-002
title: "Yeni Gherkin feature dosyası oluşturma"
suite: engine
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-ENG-001]
pre_conditions: [PRE-004, PRE-007]
tags: [migrated-pr3]
---

# TC-ENG-002 — Feature dosyası oluşturma

## Önkoşul

Engine çalışır durumda

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/features/` ile feature içeriği gönder | HTTP 201 |
| 2 | Oluşturulan dosyayı sorgula | Gönderilen Gherkin içeriği mevcut |

---
_Section: Engine: Feature Dosyaları. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
