---
id: TC-SYN-002
title: "Yüklenen veri setinden sentetik veri üretme"
suite: synthetic-data
priority: P1
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

# TC-SYN-002 — Sentetik veri üretimi

## Önkoşul

Veri seti yüklenmiş ve analiz edilmiş

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/generate` ile üretim parametreleri gönder | İş ID döner |
| 2 | `GET /api/v1/jobs/{jobId}` ile durumu sorgula | `status` alanı güncellenmeli |
| 3 | İş tamamlanınca sonuç verisi kontrol et | İstenilen sayıda satır üretilmiş |

---
_Section: Sentetik Veri ve Test Verisi (Synthetic Data). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
