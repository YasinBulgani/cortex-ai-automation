---
id: TC-SYN-004
title: "Üretilen veri setini dışa aktarma"
suite: synthetic-data
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SYN-002]
pre_conditions: [PRE-002, PRE-003, PRE-006]
tags: [migrated-pr3]
---

# TC-SYN-004 — Veri seti dışa aktarma

## Önkoşul

Sentetik veri üretilmiş

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/export` ile dışa aktarma formatı seç (CSV/JSON) | İndirme bağlantısı döner |
| 2 | Dosyayı indir ve içeriği kontrol et | Doğru format ve veri sayısı |

---
_Section: Sentetik Veri ve Test Verisi (Synthetic Data). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
