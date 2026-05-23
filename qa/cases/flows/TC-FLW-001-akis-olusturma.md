---
id: TC-FLW-001
title: "Yeni test akışı oluşturma"
suite: flows
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/flows/flow_management.feature:14
requirements: [REQ-FLW-001]
pre_conditions: [PRE-002, PRE-003]
tags: [migrated-pr3]
---

# TC-FLW-001 — Akış oluşturma

## Önkoşul

Proje mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../flows` ile akış oluştur | HTTP 201 |
| 2 | `name`, `description` kontrol et | Gönderilen verilerle eşleşir |

---
_Section: Akışlar (Flows). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
