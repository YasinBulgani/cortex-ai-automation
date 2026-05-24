---
id: REQ-AUTH-001
title: "JWT tabanlı login + rate limiting"
domain: AUTH
source: internal-spec
external: ""
covered_by: [TC-AUTH-001, TC-AUTH-002]
status: active
---

# REQ-AUTH-001 — JWT tabanlı login + rate limiting

## Tanım

Platform kullanıcıları e-posta + parola ile login olur ve karşılığında JWT access token alır. Token tüm korumalı API endpoint'lerinde `Authorization: Bearer <token>` ile gönderilir. Brute-force koruması için aynı IP'den ardışık 10 başarısız denemede rate limit (HTTP 429) devreye girer.

## Kabul Kriterleri

- [ ] `POST /api/v1/auth/login` 200 + JWT access token (geçerli kred)
- [ ] HTTP 401 + generic error (geçersiz kred — user enumeration korumalı)
- [ ] HTTP 429 (rate limit aşıldığında)
- [ ] JWT formatı: `header.payload.signature`
- [ ] Token expiry: 1 saat (configurable)
- [ ] Refresh token endpoint: `POST /api/v1/auth/refresh`

## İlgili

- Spec: `docs/local-login-setup.md` (henüz mevcut)
- Backend BDD: `backend/tests/bdd/features/authentication.feature`
- UI BDD: `e2e/bdd/features/auth/login.feature`
