---
id: REQ-AUTH-003
title: "Input validation ve güvenlik (SQL injection, XSS, rate limit)"
domain: AUTH
source: internal-spec
external: ""
covered_by: [TC-AUTH-008]
status: active
---

# REQ-AUTH-003 — Auth endpoint'lerinin güvenlik gereksinimleri

## Tanım

Login ve diğer auth endpoint'leri input validation ile saldırılara karşı korumalı olmalıdır. SQL injection, XSS, parameter pollution, brute force, user enumeration gibi yaygın saldırı vektörleri kapatılmalı.

## Kabul Kriterleri

### Input validation (HTTP 422)
- [ ] Email format geçersizse → 422
- [ ] Email boşsa → 422
- [ ] Parola boşsa → 422
- [ ] Parola uzunluğu 8 karakterden azsa → 422 (signup için)
- [ ] Email > 254 karakter → 422 (RFC 5321)
- [ ] Parola > 128 karakter → 422 (DoS koruması)

### SQL injection
- [ ] `email: "' OR '1'='1"` payload → 401 (giriş başarısız), DB error sızmaz
- [ ] Stack trace response'a düşmez
- [ ] Parameterized queries kullanılır (SQLAlchemy ORM seviyesinde)

### XSS
- [ ] Email alanında `<script>` payload → 401, response sanitize edilmiş
- [ ] Error message'larda kullanıcı input'u escape edilir

### Rate limiting
- [ ] Aynı IP'den 10 ardışık başarısız login → 429 (Too Many Requests)
- [ ] Rate limit reset süresi: 5 dakika
- [ ] Başarılı login rate limit'i resetler
- [ ] `Retry-After` header response'ta dolu

### User enumeration koruması
- [ ] Var olmayan email + yanlış parola → aynı 401 + generic mesaj
- [ ] Response timing fark etmemeli (constant-time comparison)

## İlgili

- Spec: `qa/test-design/security.md`, `qa/strategy/risk-register.md` (R-001 auth token leak)
- OWASP: A02 (Cryptographic Failures), A03 (Injection), A07 (Identification Failures)
- Bağımlı: REQ-AUTH-001 (login endpoint)
