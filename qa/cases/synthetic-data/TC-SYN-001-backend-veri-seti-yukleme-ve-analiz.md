---
id: TC-SYN-001
title: "CSV/JSON dosyası yükleme ve yapı analizi"
suite: synthetic-data
priority: P1
type: [functional, api]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SYN-001]
pre_conditions: [PRE-002, PRE-003, PRE-006]
tags: [migrated-pr3]
---

# TC-SYN-001 — Backend veri seti yükleme ve analiz

## Önkoşul

Geçerli JWT

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/upload` ile CSV dosyası yükle | HTTP 200, dosya ID döner |
| 2 | `POST /api/v1/analyze` ile dosya ID gönder | Sütun tipleri, istatistikler döner |
| 3 | `POST /api/v1/classify` ile dosyayı sınıflandır | Veri sınıflandırma sonuçları |

---
_Section: Sentetik Veri ve Test Verisi (Synthetic Data). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
