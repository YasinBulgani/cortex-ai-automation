---
id: TC-INF-003
title: "PostgreSQL kapalıyken ready endpoint davranışı"
suite: infrastructure
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-INF-001]
pre_conditions: [PRE-004]
tags: [migrated-pr3]
---

# TC-INF-003 — Veritabanı bağlantı hatası durumu

## Önkoşul

PostgreSQL durdurulmuş

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | PostgreSQL'i durdur | — |
| 2 | `GET /ready` isteği gönder | `{"ready": false, "database": "...hata..."}` |

---
_Section: Altyapı ve Sağlık Kontrolleri. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
