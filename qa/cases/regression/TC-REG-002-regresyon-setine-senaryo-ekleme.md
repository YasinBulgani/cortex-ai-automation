---
id: TC-REG-002
title: "Mevcut sete senaryo ekleme"
suite: regression
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-REG-001]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-010]
tags: [migrated-pr3]
---

# TC-REG-002 — Regresyon setine senaryo ekleme

## Önkoşul

Regresyon seti ve senaryolar mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../regression-sets/{setId}/add` ile senaryo ID'leri gönder | HTTP 200 |
| 2 | `count` değerini kontrol et | Eklenen senaryo sayısı |
| 3 | Set detayını sorgula | Eklenen senaryolar listede |

---
_Section: Regresyon Setleri (Regression Sets). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
