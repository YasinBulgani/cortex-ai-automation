---
id: TC-APR-001
title: "Proje onay kuyruğunu listeleme"
suite: approvals
priority: P1
type: [functional, smoke]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/approvals/approval_queue.feature:10
requirements: [REQ-APR-001]
pre_conditions: [PRE-002, PRE-003, PRE-009]
tags: [migrated-pr3]
---

# TC-APR-001 — Onay listesi sorgulama

## Önkoşul

Projede onay kayıtları mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/{id}/approvals` isteği gönder | HTTP 200, onay listesi |
| 2 | Sıralamayı kontrol et | `created_at` azalan sırada |
| 3 | Her onay kaydında `status`, `project_id` kontrol et | Doğru proje ID'sine ait |

---
_Section: Onay İş Akışı (Approval Workflow). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
