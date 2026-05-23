---
id: TC-AUTH-001
title: "Geçerli kimlik bilgileri ile başarılı giriş"
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
    - e2e/bdd/features/auth/login.feature:6
    - backend/tests/bdd/features/authentication.feature:11
requirements: [REQ-AUTH-001]
pre_conditions: [PRE-001, PRE-004]
tags: [migrated-pr3]
---

# TC-AUTH-001 — Başarılı kullanıcı girişi

## Önkoşul

Aktif kullanıcı hesabı mevcut (email: test@bgts.com, parola: Test1234!)

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/auth/login` endpoint'ine `{"email": "test@bgts.com", "password": "Test1234!"}` gönder | HTTP 200 döner |
| 2 | Yanıt gövdesini kontrol et | `access_token` alanı mevcut ve boş değil |
| 3 | Token formatını doğrula | JWT formatında (header.payload.signature) |
| 4 | `/login` sayfasında form alanlarını doldur ve giriş butonuna tıkla | `/projects` sayfasına yönlendirme |

---
_Section: Kimlik Doğrulama (Authentication). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
