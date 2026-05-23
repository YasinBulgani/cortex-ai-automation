---
id: TC-IMP-001
title: "Dosya ile içe aktarma başlatma"
suite: imports
priority: P0
type: [functional, smoke]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/import/import_tests.feature:14
requirements: [REQ-IMP-001]
pre_conditions: [PRE-002, PRE-003]
tags: [migrated-pr3]
---

# TC-IMP-001 — Dosya içe aktarma oluşturma

## Önkoşul

Proje mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/imports` ile `{"filename": "test.xlsx", "raw_text": "..."}` gönder | HTTP 201 döner |
| 2 | Yanıtta `id`, `filename`, `status` kontrol et | `status` = `"completed"` |
| 3 | `scenario_count` kontrol et | 0 veya pozitif sayı |

---
_Section: İçe Aktarma Akışı (Import Flow). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
