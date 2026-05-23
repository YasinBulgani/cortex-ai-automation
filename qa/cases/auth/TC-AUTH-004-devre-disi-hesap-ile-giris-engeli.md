---
id: TC-AUTH-004
title: "Devre dışı bırakılmış hesap ile giriş engellenmeli"
suite: auth
priority: P0
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - backend/tests/bdd/features/authentication.feature:39
requirements: [REQ-AUTH-001]
pre_conditions: [PRE-001, PRE-004]
tags: [migrated-pr3]
---

# TC-AUTH-004 — Devre dışı hesap ile giriş engeli

## Önkoşul

`is_active=false` olan kullanıcı hesabı

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Devre dışı hesap ile login isteği gönder | HTTP 403 döner |
| 2 | Yanıt mesajını kontrol et | "Hesap devre dışı" |

---
_Section: Kimlik Doğrulama (Authentication). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
