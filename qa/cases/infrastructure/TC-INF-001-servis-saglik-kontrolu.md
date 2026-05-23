---
id: TC-INF-001
title: "Backend sağlık endpoint kontrolü"
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

# TC-INF-001 — Servis sağlık kontrolü

## Önkoşul

Backend çalışır

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /health` isteği gönder | HTTP 200, `{"status": "ok"}` |

---
_Section: Altyapı ve Sağlık Kontrolleri. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
