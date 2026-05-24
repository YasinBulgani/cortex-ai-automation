---
id: TC-AUTH-005
title: "/me endpoint'i ile oturum sahibi bilgileri"
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
    - backend/tests/bdd/features/authentication.feature:60
requirements: [REQ-AUTH-002]
pre_conditions: [PRE-001, PRE-004]
tags: [migrated-pr3]
---

# TC-AUTH-005 — JWT token ile kullanıcı bilgisi sorgulama

## Önkoşul

Geçerli JWT token

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/auth/me` ile geçerli token gönder | HTTP 200 döner |
| 2 | Yanıt gövdesini kontrol et | `id`, `email`, `roles`, `permissions` alanları mevcut |
| 3 | `roles` alanını kontrol et | Kullanıcının atanmış rolleri listelenmeli |

---
_Section: Kimlik Doğrulama (Authentication). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
