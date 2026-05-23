---
id: TC-API-003
title: "Koleksiyondaki tüm istekleri çalıştırma"
suite: api-tests
priority: P1
type: [functional, integration]
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

# TC-API-003 — API koleksiyonu çalıştırma

## Önkoşul

Koleksiyon ve istekler mevcut, hedef API erişilebilir

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../collections/{colId}/run` ile çalıştır | HTTP 200 |
| 2 | `status` kontrol et | `"completed"` |
| 3 | `results` dizisini kontrol et | Her istek için sonuç mevcut |
| 4 | Her sonuçta `status_code`, `duration_ms`, `passed` kontrol et | Doğru HTTP kodları |

---
_Section: API Test Koleksiyonları (API Testing). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
