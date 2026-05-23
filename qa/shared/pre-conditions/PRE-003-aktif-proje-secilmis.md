---
id: PRE-003
title: "Aktif proje seçilmiş"
description: "Senaryo, executions, flows, approvals, regression vb. domain'lerinin TC'leri için aktif (selected) bir proje gerekir."
setup_steps:
  - "PRE-002 (JWT token) uygulanmış olmalı"
  - "Test Projesi adında bir proje oluşturulmuş (`POST /api/v1/tspm/projects`)"
  - "Proje ID context'e set edilmiş (UI: localStorage.activeProjectId; API: X-Project-ID header veya path param)"
  - "Proje status = active, archived = false"
teardown_steps: []
---

# PRE-003 — Aktif proje seçilmiş

## Amaç

Tek-tenant Cortex projesinde tüm TC'ler bir proje context'inde çalışır. Manuel test koşumu öncesi seed bir test projesi olmalı.

## Setup

```bash
# Seed
curl -X POST http://127.0.0.1:8000/api/v1/tspm/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "content-type: application/json" \
  -d '{"name":"Test Projesi","description":"QA için seed proje"}'

# UI tarafı: ilk proje otomatik aktif olur veya kullanıcı seçer.
```

## Bağımlılık

- PRE-001, PRE-002
