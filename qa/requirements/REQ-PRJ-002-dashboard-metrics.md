---
id: REQ-PRJ-002
title: "Proje dashboard ve metrik endpoint'leri"
domain: PRJ
source: internal-spec
external: ""
covered_by: [TC-PRJ-003]
status: active
---

# REQ-PRJ-002 — Proje dashboard ve metrikler

## Tanım

Her proje için özet metrikler (senaryo sayısı, bekleyen onay, koşum geçmişi, son koşumun pass rate'i) tek bir dashboard endpoint'i ile sunulur. UI dashboard sayfası bu endpoint'ten beslenir.

## Kabul Kriterleri

- [ ] `GET /api/v1/tspm/projects/{id}/dashboard` → 200
- [ ] Boş proje için tüm sayılar 0, `latest_run_pass_rate: null`
- [ ] Aktif proje için doğru sayılar (`scenario_count`, `pending_approvals`, `execution_count`)
- [ ] Cache: 30 saniye (yüksek trafik için)
- [ ] UI dashboard endpoint'i 200ms altında cevap vermeli (P95)

## İlgili

- Bağımlı: REQ-PRJ-001 (proje var olmalı)
- Backend BDD: `backend/tests/bdd/features/project_management.feature` (Scenario 48+)
