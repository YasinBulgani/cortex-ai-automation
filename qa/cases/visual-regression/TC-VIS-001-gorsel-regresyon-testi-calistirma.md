---
id: TC-VIS-001
title: "İki ekran görüntüsü arasında SSIM karşılaştırma"
suite: visual-regression
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-VIS-001]
pre_conditions: [PRE-002, PRE-003, PRE-005]
tags: [migrated-pr3]
---

# TC-VIS-001 — Görsel regresyon testi çalıştırma

## Önkoşul

Baseline ekran görüntüsü mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/visual/compare` ile baseline ve test görüntüsü gönder | HTTP 200 |
| 2 | SSIM skorunu kontrol et | 0-1 arasında değer |
| 3 | Fark haritasını kontrol et | Farklılıklar vurgulanmış |

---
_Section: Engine: Görsel Regresyon. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
