---
id: TC-QA-003
title: "Rastgele tıklama/gezinme testi"
suite: qa-engine
priority: P3
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-QA-001]
pre_conditions: [PRE-002, PRE-004, PRE-007]
tags: [migrated-pr3]
---

# TC-QA-003 — Monkey test çalıştırma

## Önkoşul

Hedef URL erişilebilir

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/qa/monkey-test` ile URL ve süre gönder | HTTP 200 |
| 2 | Sonuç raporunu kontrol et | Bulunan hatalar ve crash bilgileri |

---
_Section: QA Engine (Backend QA Routes). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
