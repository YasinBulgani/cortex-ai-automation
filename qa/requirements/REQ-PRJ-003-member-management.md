---
id: REQ-PRJ-003
title: "Proje üye yönetimi (ekle/çıkar/rol değiştir)"
domain: PRJ
source: internal-spec
external: ""
covered_by: [TC-PRJ-005, TC-PRJ-006]
status: active
---

# REQ-PRJ-003 — Proje üye yönetimi

## Tanım

Proje sahibi (owner/admin) projelerine üye ekleyebilir, çıkarabilir ve rollerini değiştirebilir. RBAC entegrasyonu ile editor/viewer/admin rolleri proje-spesifik atanabilir.

## Kabul Kriterleri

- [ ] `POST /api/v1/tspm/projects/{id}/members` ile üye ekleme
- [ ] `DELETE /api/v1/tspm/projects/{id}/members/{userId}` ile üye çıkarma
- [ ] Eklenen üye `GET /members` listesinde görünür
- [ ] Çıkarılan üye projeye erişimini kaybeder (sonraki istek 403)
- [ ] Owner kendi kendini çıkaramaz (400 + "Owner cannot remove self")
- [ ] Üye değişikliği audit log'lara düşer

## Bağımlılık

- REQ-PRJ-001 (proje var olmalı)
- REQ-RBAC-001 (RBAC rolleri tanımlı)

## İlgili

- engine/features/api/members.feature (eski automation, PR 23 envanterde)
