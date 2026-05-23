---
id: TC-SYN-006
title: "Senaryoya parametrik test verisi bağlama"
suite: synthetic-data
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SYN-004]
pre_conditions: [PRE-002, PRE-003, PRE-006]
tags: [migrated-pr3]
---

# TC-SYN-006 — Senaryoya test verisi bağlama

## Önkoşul

Senaryo ve test veri seti mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../scenarios/{id}/bind-data` ile veri seti ve mapping gönder | HTTP 201 |
| 2 | `GET .../scenarios/{id}/expanded` ile genişletilmiş senaryoyu sorgula | `expanded_rows` dolu |
| 3 | Parametrelerin doğru değiştirildiğini kontrol et | Mapping'e göre değerler yerleşmiş |

---
_Section: Sentetik Veri ve Test Verisi (Synthetic Data). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
