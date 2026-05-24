---
id: REQ-SYN-004
title: "TSPM test verisi yönetimi (proje içi)"
domain: SYN
source: internal-spec
external: ""
covered_by: [TC-SYN-005, TC-SYN-006]
status: active
---

# REQ-SYN-004 — Test verisi yönetimi

## Tanım

Proje içinde, senaryoya bağlanabilen test veri setleri yönetilir. Senaryolar parametrik koşumda bu veri setlerini kullanır.

## Kabul Kriterleri

- [ ] `POST /tspm/projects/{id}/test-data` → veri seti oluştur (CSV/JSON inline veya syndata reference)
- [ ] `PATCH /scenarios/{id}/test-data` → senaryoya veri seti bağla
- [ ] Senaryo koşumunda her satır için ayrı result kaydedilir (`TC-XXX-NNN#1`, `#2`, ...)
- [ ] Veri seti versiyonlanır (data set güncellense bile eski run reproducible)

## Bağımlılık

- REQ-SCN-001 (senaryo var olmalı)
- REQ-SYN-001 veya REQ-SYN-002 (kaynak veri)
