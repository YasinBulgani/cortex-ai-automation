---
id: TC-APR-003
title: "Bekleyen onayı reddetme"
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
    - e2e/bdd/features/approvals/approval_queue.feature:22
requirements: [REQ-APR-002]
pre_conditions: [PRE-002, PRE-003, PRE-009]
tags: [migrated-pr3]
---

# TC-APR-003 — Onay kararı — Reddet

## Önkoşul

`status=pending` olan onay kaydı

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../approvals/{approvalId}/decide` ile `{"decision": "rejected"}` gönder | HTTP 200 |
| 2 | Onay durumunu kontrol et | `status` = `"rejected"` |

---
_Section: Onay İş Akışı (Approval Workflow). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
