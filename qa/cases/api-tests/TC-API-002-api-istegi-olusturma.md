---
id: TC-API-002
title: "Koleksiyona API isteği ekleme"
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

# TC-API-002 — API isteği oluşturma

## Önkoşul

Koleksiyon mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../collections/{colId}/requests` ile istek oluştur | HTTP 201 |
| 2 | `method`, `path`, `headers`, `body` kontrol et | Gönderilen verilerle eşleşir |

---
_Section: API Test Koleksiyonları (API Testing). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
