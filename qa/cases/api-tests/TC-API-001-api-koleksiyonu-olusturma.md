---
id: TC-API-001
title: "Yeni API test koleksiyonu oluşturma"
suite: api-tests
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-API-001]
pre_conditions: [PRE-002, PRE-004]
tags: [migrated-pr3]
---

# TC-API-001 — API koleksiyonu oluşturma

## Önkoşul

Proje mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../api-tests/collections` ile koleksiyon oluştur | HTTP 201 |
| 2 | `name`, `base_url`, `request_count` kontrol et | `request_count = 0` |

---
_Section: API Test Koleksiyonları (API Testing). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
