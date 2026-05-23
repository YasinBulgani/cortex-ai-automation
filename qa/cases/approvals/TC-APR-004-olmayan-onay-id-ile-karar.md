---
id: TC-APR-004
title: "Geçersiz onay ID ile karar verme hatası"
suite: approvals
priority: P1
type: [functional, api]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-APR-002]
pre_conditions: [PRE-002, PRE-003, PRE-009]
tags: [migrated-pr3]
---

# TC-APR-004 — Olmayan onay ID ile karar

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Olmayan `approvalId` ile decide isteği gönder | HTTP 404, "Onay bulunamadı" |

---
_Section: Onay İş Akışı (Approval Workflow). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
