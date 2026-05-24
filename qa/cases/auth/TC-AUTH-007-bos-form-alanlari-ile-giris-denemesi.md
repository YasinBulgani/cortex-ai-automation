---
id: TC-AUTH-007
title: "Eksik alanlar ile giriş formu validasyonu"
suite: auth
priority: P1
type: [functional, ui]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/auth/login.feature:20
    - backend/tests/bdd/features/authentication.feature:46
requirements: [REQ-AUTH-001]
pre_conditions: [PRE-001, PRE-004]
tags: [migrated-pr3]
---

# TC-AUTH-007 — Boş form alanları ile giriş denemesi

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `/login` sayfasında e-posta boş bırakıp giriş butonuna tıkla | Validasyon hatası gösterilmeli |
| 2 | E-posta doldur, parola boş bırakıp giriş butonuna tıkla | Validasyon hatası gösterilmeli |
| 3 | `POST /api/v1/auth/login` ile boş body gönder | HTTP 422 (Validation Error) döner |

---
_Section: Kimlik Doğrulama (Authentication). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
