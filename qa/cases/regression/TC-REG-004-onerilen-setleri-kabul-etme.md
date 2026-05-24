---
id: TC-REG-004
title: "AI önerilerini toplu kabul etme"
suite: regression
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-REG-002]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-010]
tags: [migrated-pr3]
---

# TC-REG-004 — Önerilen setleri kabul etme

## Önkoşul

AI önerisi alınmış

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../regression-sets/accept-suggestions` ile önerileri gönder | HTTP 201 |
| 2 | Oluşturulan set sayısını kontrol et | Gönderilen öneri sayısı kadar |

---
_Section: Regresyon Setleri (Regression Sets). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
