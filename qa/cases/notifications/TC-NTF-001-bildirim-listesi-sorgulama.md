---
id: TC-NTF-001
title: "Kullanıcı bildirimlerini listeleme"
suite: notifications
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-NTF-001]
pre_conditions: [PRE-002]
tags: [migrated-pr3]
---

# TC-NTF-001 — Bildirim listesi sorgulama

## Önkoşul

Bildirim kaydı mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/notifications/` isteği gönder | HTTP 200, bildirim listesi |

---
_Section: Bildirimler (Notifications). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
