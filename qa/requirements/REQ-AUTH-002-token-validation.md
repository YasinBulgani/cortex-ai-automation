---
id: REQ-AUTH-002
title: "Token doğrulama ve oturum bilgisi (/me endpoint)"
domain: AUTH
source: internal-spec
external: ""
covered_by: [TC-AUTH-005, TC-AUTH-006]
status: active
---

# REQ-AUTH-002 — Token doğrulama ve oturum bilgisi

## Tanım

Geçerli JWT token ile `/api/v1/auth/me` endpoint'i kullanıcının kendi bilgilerini (id, email, roles) döndürür. Geçersiz/süresi dolmuş/manipüle edilmiş token ile korumalı endpoint'ler 401 veya 403 ile reddedilir.

## Kabul Kriterleri

- [ ] `GET /api/v1/auth/me` + valid token → 200 + `{id, email, roles, ...}`
- [ ] Token expired → 401 + `{detail: "Token expired"}`
- [ ] Token signature invalid → 401
- [ ] Token missing → 401 veya 403 (endpoint-spesifik)
- [ ] Token revoked (logout sonrası) → 401
- [ ] `roles` listesi boş olmamalı (her kullanıcının en az 1 rolü olmalı)

## İlgili

- Spec: `qa/test-design/security.md` (token security testleri)
- Backend BDD: `backend/tests/bdd/features/authentication.feature` (Scenario'lar 60+, 70+)
- Bağımlı: REQ-AUTH-001 (login endpoint — token issue eder)
