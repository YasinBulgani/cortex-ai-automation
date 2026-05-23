---
id: REQ-SCN-003
title: "AI ile BDD senaryo üretimi ve toplu kayıt"
domain: SCN
source: internal-spec
external: ""
covered_by: [TC-SCN-005, TC-SCN-006]
status: active
---

# REQ-SCN-003 — AI senaryo üretimi

## Tanım

Kullanıcı doğal dilde test ihtiyacını yazar, AI BDD formatında senaryo taslakları üretir. Üretilen senaryolar onay kuyruğuna düşer; kullanıcı onayladıklarını toplu kaydedebilir.

## Kabul Kriterleri

- [ ] `POST /api/v1/scenarios/ai-generate` → N taslak senaryo (default N=5)
- [ ] Taslaklar `status: draft`, `source: ai-generated` tag'li
- [ ] Onay kuyruğunda görünür (`/approvals?source=ai`)
- [ ] `POST /scenarios/bulk-save` ile toplu kayıt (200 + saved_ids)
- [ ] AI üretim budget: günlük max 100 senaryo per proje (cost rails)
- [ ] AI üretim audit log'lara düşer (prompt + response özeti)

## Bağımlılık

- REQ-SCN-001 (senaryo CRUD)
- REQ-APR-002 (onay akışı)
- Cortex AI gateway (`ai-gateway`)

## Notlar

Bu özellik Cortex AI Automation'ın temel diferansiyel özelliği — kalite + cost rails kritik.
