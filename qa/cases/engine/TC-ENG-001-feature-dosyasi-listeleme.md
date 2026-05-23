---
id: TC-ENG-001
title: "Gherkin feature dosyalarını listeleme"
suite: engine
priority: P1
type: [functional, integration]
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

# TC-ENG-001 — Feature dosyası listeleme

## Önkoşul

Engine çalışır durumda

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/features/` isteği gönder (Engine :5001) | HTTP 200, feature listesi |
| 2 | Listedeki dosya isimlerini kontrol et | `.feature` uzantılı dosyalar |

---
_Section: Engine: Feature Dosyaları. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
