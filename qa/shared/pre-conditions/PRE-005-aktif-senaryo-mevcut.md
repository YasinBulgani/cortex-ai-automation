---
id: PRE-005
title: "Projede en az 1 senaryo mevcut"
description: "Senaryo CRUD dışındaki TC'ler (run, regression, schedules, flows) en az 1 mevcut senaryoya ihtiyaç duyar."
setup_steps:
  - "PRE-003 (aktif proje) uygulanmış olmalı"
  - "Proje altında 'Login Testi' veya benzer bir senaryo oluşturulmuş"
  - "Senaryo status = active, current_version >= 1"
  - "En az 3 adım içeriyor (Given/When/Then)"
teardown_steps: []
---

# PRE-005 — Projede en az 1 senaryo mevcut

## Amaç

Run, regression set, schedule TC'leri var olan senaryolar üzerinden çalışır. Boş projede bu TC'ler çalıştırılamaz.

## Setup

```bash
PROJECT_ID=...
curl -X POST http://127.0.0.1:8000/api/v1/tspm/projects/$PROJECT_ID/scenarios \
  -H "Authorization: Bearer $TOKEN" \
  -H "content-type: application/json" \
  -d '{"title":"Login Testi","steps":[{"order":1,"keyword":"Given","text":"Kullanici login sayfasinda"}]}'
```

## Bağımlılık

- PRE-003
