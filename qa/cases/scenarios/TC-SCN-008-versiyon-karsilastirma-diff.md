---
id: TC-SCN-008
title: "İki versiyon arasındaki farkları görüntüleme"
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
    - backend/tests/bdd/features/scenario_management.feature:69
requirements: [REQ-SCN-002]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-SCN-008 — Versiyon karşılaştırma (diff)

## Önkoşul

Senaryo en az 2 versiyonlu

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../versions/1/diff/2` ile diff isteği gönder | HTTP 200 döner |
| 2 | `title_changed`, `steps_changed` gibi boolean alanları kontrol et | Değişen alanlar `true` |
| 3 | `v1_snapshot` ve `v2_snapshot` kontrol et | Her iki versiyon snapshot'ı mevcut |

---
_Section: Senaryo Yönetimi (Scenario Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
