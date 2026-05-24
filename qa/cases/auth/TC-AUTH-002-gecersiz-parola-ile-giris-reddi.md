---
id: TC-AUTH-002
title: "Hatalı parola ile giriş denemesi reddedilmeli"
suite: auth
priority: P0
type: [functional, smoke]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/auth/login.feature:13
    - backend/tests/bdd/features/authentication.feature:22
requirements: [REQ-AUTH-001]
pre_conditions: [PRE-001, PRE-004]
tags: [migrated-pr3]
---

# TC-AUTH-002 — Geçersiz parola ile giriş reddi

## Önkoşul

Aktif kullanıcı hesabı mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/auth/login` ile yanlış parola gönder | HTTP 401 döner |
| 2 | Yanıt gövdesini kontrol et | `detail`: "E-posta veya parola hatalı" |
| 3 | Token alanını kontrol et | `access_token` alanı mevcut olmamalı |

---
_Section: Kimlik Doğrulama (Authentication). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
