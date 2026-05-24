---
id: REQ-SCN-002
title: "Senaryo otomatik versiyonlama ve diff"
domain: SCN
source: internal-spec
external: ""
covered_by: [TC-SCN-002, TC-SCN-007, TC-SCN-008]
status: active
---

# REQ-SCN-002 — Senaryo versiyonlama

## Tanım

Her senaryo güncellemesinde mevcut versiyonun snapshot'ı tutulur ve `current_version` artar. Versiyonlar arasında diff alınabilir (başlık, adım, metadata değişiklikleri).

## Kabul Kriterleri

- [ ] Senaryo güncelleme → `current_version` 1 artar
- [ ] Eski versiyon snapshot olarak korunur (read-only)
- [ ] `GET /scenarios/{id}/versions` tüm versiyonları döner (newest first)
- [ ] `GET /scenarios/{id}/versions/{v1}/diff/{v2}` field-by-field karşılaştırma
- [ ] Diff response: `title_changed`, `steps_changed`, `v1_snapshot`, `v2_snapshot`
- [ ] Versiyon snapshot'ları immutable (PUT/DELETE 405)

## Bağımlılık

- REQ-SCN-001 (senaryo CRUD)
