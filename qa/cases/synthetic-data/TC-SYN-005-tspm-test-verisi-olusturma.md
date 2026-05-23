---
id: TC-SYN-005
title: "Proje içi test veri seti oluşturma"
suite: synthetic-data
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SYN-004]
pre_conditions: [PRE-002, PRE-003, PRE-006]
tags: [migrated-pr3]
---

# TC-SYN-005 — TSPM test verisi oluşturma

## Önkoşul

Proje mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/test-data` ile veri seti oluştur | HTTP 201 |
| 2 | `columns` ve `rows` alanlarını kontrol et | Gönderilen verilerle eşleşmeli |

---
_Section: Sentetik Veri ve Test Verisi (Synthetic Data). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
