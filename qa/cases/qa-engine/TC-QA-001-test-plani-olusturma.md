---
id: TC-QA-001
title: "Otomatik test planı oluşturma"
suite: qa-engine
priority: P2
type: [functional, api]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-QA-001]
pre_conditions: [PRE-002, PRE-004, PRE-007]
tags: [migrated-pr3]
---

# TC-QA-001 — Test planı oluşturma

## Önkoşul

Geçerli JWT

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/qa/test-plan` ile test planı parametreleri gönder | HTTP 200, test planı |
| 2 | Planın kapsamını kontrol et | Modüller, öncelikler, test tipleri |

---
_Section: QA Engine (Backend QA Routes). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
