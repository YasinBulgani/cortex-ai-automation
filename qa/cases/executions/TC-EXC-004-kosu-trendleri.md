---
id: TC-EXC-004
title: "Koşu trend verilerini sorgulama"
suite: executions
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-EXC-003]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-007]
tags: [migrated-pr3]
---

# TC-EXC-004 — Koşu trendleri

## Önkoşul

Birden fazla koşu mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../execution-trends?days=30` isteği gönder | HTTP 200 |
| 2 | `data_points` dizisini kontrol et | Tarih sıralı veri noktaları |
| 3 | Her noktada `total`, `passed`, `failed`, `pass_rate` kontrol et | Tutarlı hesaplama |

---
_Section: Test Koşusu ve Sonuçlar (Executions). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
