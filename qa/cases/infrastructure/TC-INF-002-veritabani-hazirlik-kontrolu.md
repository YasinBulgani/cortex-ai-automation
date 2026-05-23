---
id: TC-INF-002
title: "Veritabanı bağlantı ve hazırlık kontrolü"
suite: infrastructure
priority: P0
type: [smoke]
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

# TC-INF-002 — Veritabanı hazırlık kontrolü

## Önkoşul

Backend ve PostgreSQL çalışır

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /ready` isteği gönder | HTTP 200, `{"ready": true, "database": "ok"}` |

---
_Section: Altyapı ve Sağlık Kontrolleri. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
