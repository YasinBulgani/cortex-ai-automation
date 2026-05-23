---
id: TC-REQ-003
title: "Gereksinim-senaryo kapsam matrisini sorgulama"
suite: requirements
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-REQ-001]
pre_conditions: [PRE-002, PRE-003]
tags: [migrated-pr3]
---

# TC-REQ-003 — Kapsam matrisi

## Önkoşul

Gereksinimler ve senaryolar bağlanmış

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../coverage-matrix` isteği gönder | HTTP 200 |
| 2 | `coverage_percent` kontrol et | 0-100 arasında doğru hesaplanmış |
| 3 | `rows` içinde her gereksinim için bağlı senaryo ID'leri | Doğru bağlantılar |

---
_Section: Gereksinimler ve Kapsam (Requirements & Coverage). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
