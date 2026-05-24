---
id: TC-AUTH-006
title: "Geçersiz token ile korumalı endpoint erişimi engellenmeli"
suite: auth
priority: P0
type: [functional, api]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - backend/tests/bdd/features/authentication.feature:69
requirements: [REQ-AUTH-002]
pre_conditions: [PRE-001, PRE-004]
tags: [migrated-pr3]
---

# TC-AUTH-006 — Geçersiz/süresi dolmuş token ile erişim reddi

## Önkoşul

Geçersiz veya süresi dolmuş token

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/auth/me` ile geçersiz token gönder | HTTP 401 döner |
| 2 | `GET /api/v1/tspm/projects` ile token olmadan gönder | HTTP 401 döner |

---
_Section: Kimlik Doğrulama (Authentication). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
