---
id: TC-API-004
title: "API test koşu geçmişini sorgulama"
suite: api-tests
priority: P2
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

# TC-API-004 — API test koşu geçmişi

## Önkoşul

En az 1 API test koşusu

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../api-tests/runs` isteği gönder | HTTP 200, koşu listesi |
| 2 | Sıralamayı kontrol et | Azalan tarih sırası |

---
_Section: API Test Koleksiyonları (API Testing). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
