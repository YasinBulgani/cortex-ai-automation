---
id: REQ-SCN-001
title: "Senaryo Yönetimi"
domain: SCN
source: internal-spec
external: ""
covered_by: [TC-SCN-001, TC-SCN-002, TC-SCN-003, TC-SCN-004, TC-SCN-005, TC-SCN-006, TC-SCN-007, TC-SCN-008, TC-SCN-009]
status: active
---

# REQ-SCN-001 — Senaryo Yönetimi

## Tanım

Bu gereksinim SCN domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-SCN-001 → REQ-SCN-001 (login), REQ-SCN-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/scenarios/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
