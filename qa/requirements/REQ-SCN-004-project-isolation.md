---
id: REQ-SCN-004
title: "Senaryo proje izolasyonu (cross-project access engeli)"
domain: SCN
source: internal-spec
external: ""
covered_by: [TC-SCN-009]
status: active
---

# REQ-SCN-004 — Senaryo proje izolasyonu

## Tanım

Senaryolar projelerine bağlıdır. Bir kullanıcı kendi proje context'i dışındaki senaryolara erişemez (404 döndürülür, 403 değil — varlık ifşa edilmez).

## Kabul Kriterleri

- [ ] `GET /projects/{A}/scenarios/{B'ye-ait-id}` → 404 (403 değil)
- [ ] Toplu silme: farklı projeye ait ID gönderilirse o ID yok sayılır (silinmez)
- [ ] Cross-project search dönmemeli (filter zorunlu)
- [ ] Cache invalidation cross-project sızıntı yapmamalı

## Güvenlik gerekçesi

403 yerine 404: varlığın varlığını ifşa etmemek (security-by-obscurity değil, defense-in-depth). Saldırgan ID brute-force ile proje haritasını çıkaramaz.

## Bağımlılık

- REQ-AUTH-002 (token-based izolasyon)
- REQ-RBAC-001 (rol-bazlı izolasyon)
