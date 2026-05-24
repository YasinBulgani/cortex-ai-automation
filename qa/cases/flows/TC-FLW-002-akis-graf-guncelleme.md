---
id: TC-FLW-002
title: "Akış diyagramını (node/edge) güncelleme"
suite: flows
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-FLW-001]
pre_conditions: [PRE-002, PRE-003]
tags: [migrated-pr3]
---

# TC-FLW-002 — Akış graf güncelleme

## Önkoşul

Akış mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `PUT .../flows/{flowId}/graph` ile nodes ve edges gönder | HTTP 200 |
| 2 | Güncellenen akışın `nodes`, `edges` kontrol et | Gönderilen verilerle eşleşir |

---
_Section: Akışlar (Flows). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
