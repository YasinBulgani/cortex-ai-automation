---
id: TC-AUTH-003
title: "Sistemde olmayan e-posta ile giriş denemesi"
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
    - backend/tests/bdd/features/authentication.feature:31
requirements: [REQ-AUTH-001]
pre_conditions: [PRE-001, PRE-004]
tags: [migrated-pr3]
---

# TC-AUTH-003 — Geçersiz e-posta ile giriş reddi

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/auth/login` ile olmayan e-posta gönder | HTTP 401 döner |
| 2 | Yanıt mesajını kontrol et | "E-posta veya parola hatalı" (bilgi sızdırmaz) |

---
_Section: Kimlik Doğrulama (Authentication). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
