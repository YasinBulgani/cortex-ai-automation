---
id: PRE-001
title: "Aktif admin kullanıcı hesabı"
description: "Admin yetkili, aktif (locked değil) bir kullanıcının varlığını garanti eder."
setup_steps:
  - "Backend seed script çalıştırıldı: `npm run seed:test`"
  - "admin@example.com / admin123 hesabı veritabanında mevcut"
  - "Hesap status = active, locked = false, mfa_enabled = false"
teardown_steps: []
---

# PRE-001 — Aktif admin kullanıcı hesabı

## Amaç

Auth TC'lerinin çoğu bir login için var olan, aktif bir admin hesaba ihtiyaç duyar. Bu önkoşul o garantiyi verir.

## Setup adımları

1. Backend seed: `npm run seed:test`
2. Kontrol: `admin@example.com / admin123` veritabanında mevcut
3. Hesap durumu: `status = active`, `locked = false`, `mfa_enabled = false`

## Bunu kullanan TC'ler

`tools/trace.mjs` otomatik üretir.
