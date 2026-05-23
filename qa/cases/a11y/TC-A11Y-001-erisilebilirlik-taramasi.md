---
id: TC-A11Y-001
title: "WCAG 2.1 erişilebilirlik taraması"
suite: a11y
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/common/accessibility.feature:9
requirements: [REQ-A11Y-001]
pre_conditions: [PRE-002]
tags: [migrated-pr3]
---

# TC-A11Y-001 — Erişilebilirlik taraması

## Önkoşul

Taranacak URL erişilebilir

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/a11y/scan` ile URL gönder | HTTP 200, tarama sonuçları |
| 2 | İhlal listesini kontrol et | Seviye (A, AA, AAA) bilgisi mevcut |
| 3 | Toplam skor kontrol et | 0-100 arasında erişilebilirlik puanı |

---
_Section: Engine: Erişilebilirlik. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
