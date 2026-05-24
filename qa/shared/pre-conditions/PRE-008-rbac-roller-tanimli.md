---
id: PRE-008
title: "RBAC roller tanımlı (admin, editor, viewer)"
description: "Yetki testleri (TC-RBAC-*, TC-APR-*, üye yönetimi) sistem rollerinin seed edilmiş olmasını gerektirir."
setup_steps:
  - "Backend seed: roles tablosunda admin, editor, viewer kayıtları"
  - "Her rol için en az 1 test kullanıcısı atanmış"
  - "Permission matrisi yüklü (qa/test-design/rbac-matrix.md referansı)"
teardown_steps: []
---

# PRE-008 — RBAC roller tanımlı

## Amaç

RBAC testleri farklı yetki seviyelerinden istek atmayı gerektirir. Her rol için bir test kullanıcısı hazır olmalı.

## Test kullanıcıları

| Rol | Email | Parola |
|---|---|---|
| admin | admin@example.com | admin123 |
| editor | editor@example.com | editor123 |
| viewer | viewer@example.com | viewer123 |

## Bağımlılık

- PRE-001 (admin)
- PRE-004 (backend)
