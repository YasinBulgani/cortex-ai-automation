---
id: TC-APR-002
title: "Bekleyen onayı onaylama"
suite: approvals
priority: P0
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/approvals/approval_queue.feature:14
requirements: [REQ-APR-002]
pre_conditions: [PRE-002, PRE-003, PRE-009]
tags: [migrated-pr3]
---

# TC-APR-002 — Onay kararı — Onayla

## Önkoşul

`status=pending` olan onay kaydı

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/approvals/{approvalId}/decide` ile `{"decision": "approved"}` gönder | HTTP 200, `{"ok": true}` |
| 2 | Onayı tekrar sorgula | `status` = `"approved"` |
| 3 | `decided_at` alanını kontrol et | Null değil, güncel zaman damgası |

---
_Section: Onay İş Akışı (Approval Workflow). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
