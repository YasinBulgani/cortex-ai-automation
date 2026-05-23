---
id: PRE-002
title: "Kullanıcı oturum açmış ve geçerli JWT token'a sahip"
description: "Korunan endpoint'lere veya UI sayfalarına erişim gerektiren tüm TC'lerin temel önkoşulu."
setup_steps:
  - "PRE-001 (aktif admin hesabı) uygulanmış olmalı"
  - "POST /api/v1/auth/login → access_token alınmış"
  - "Token Authorization: Bearer header'ında kullanıma hazır"
  - "Token expiry > 30 dakika (test süresi boyunca geçerli kalmalı)"
teardown_steps:
  - "Token'ı /api/v1/auth/logout ile invalidate et (opsiyonel — testler arası izolasyon için)"
---

# PRE-002 — JWT token'lı kullanıcı oturumu

## Amaç

Korunan API endpoint'leri ve UI sayfaları JWT token gerektirir. Bu önkoşul, login akışını her TC'de tekrar etmek yerine token'ı hazır kabul eder.

## Setup

```bash
# Backend
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "content-type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | jq -r .access_token)

# UI (Playwright)
# storageState fixture'ı kullanılır → e2e/global-setup.ts
```

## Bağımlılık

- PRE-001 (aktif admin hesabı)

## Bunu kullanan TC'ler

Otomatik: `qa/tools/trace.mjs` `coverage/traceability.csv` ile çıkarılır.
