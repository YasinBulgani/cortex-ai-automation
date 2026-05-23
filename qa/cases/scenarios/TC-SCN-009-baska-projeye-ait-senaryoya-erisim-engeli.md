---
id: TC-SCN-009
title: "Farklı projeye ait senaryo erişim kontrolü"
suite: scenarios
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - backend/tests/bdd/features/scenario_management.feature:54
requirements: [REQ-SCN-004]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-SCN-009 — Başka projeye ait senaryoya erişim engeli

## Önkoşul

İki farklı proje, A projesinin senaryosu

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Proje B ID ile Proje A senaryosunu sorgula | HTTP 404 döner |
| 2 | Yanıt mesajını kontrol et | "Senaryo bulunamadı" |

---
_Section: Senaryo Yönetimi (Scenario Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
