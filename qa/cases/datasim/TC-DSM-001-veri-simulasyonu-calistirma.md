---
id: TC-DSM-001
title: "Test verisi simülasyonu oluşturma"
suite: datasim
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-DSM-001]
pre_conditions: [PRE-002, PRE-003, PRE-006]
tags: [migrated-pr3]
---

# TC-DSM-001 — Veri simülasyonu çalıştırma

## Önkoşul

Engine çalışır

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/datasim/generate` ile simülasyon parametreleri gönder | HTTP 200 |
| 2 | Üretilen veriyi kontrol et | Belirtilen format ve sayıda veri |

---
_Section: Engine: Veri Simülasyonu (DataSim). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
