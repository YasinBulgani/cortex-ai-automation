---
id: REQ-APR-002
title: "Onay kararı akışı (onayla / reddet)"
domain: APR
source: internal-spec
external: ""
covered_by: [TC-APR-002, TC-APR-003, TC-APR-004]
status: active
---

# REQ-APR-002 — Onay kararı akışı

## Tanım

Onay listesindeki pending kayıtlar için kullanıcı onayla veya reddet kararı verebilir. Karar verildikten sonra kayıt history'e düşer ve ilgili artifact (senaryo, regression set vb.) state değişir.

## Kabul Kriterleri

- [ ] `POST /approvals/{id}/approve` → 200, `status: approved`
- [ ] `POST /approvals/{id}/reject` → 200, `status: rejected` (gerekçe opsiyonel)
- [ ] Olmayan ID → 404
- [ ] Zaten karar verilmiş kayıt → 409 Conflict
- [ ] Onaylanan senaryo `status: active` olur
- [ ] Reddedilen senaryo `status: draft` kalır + rejected mark
- [ ] Karar audit log'a düşer (kim, ne zaman, gerekçe)

## Bağımlılık

- REQ-APR-001 (onay listesi var)
- REQ-RBAC-001 (approver yetkisi)
