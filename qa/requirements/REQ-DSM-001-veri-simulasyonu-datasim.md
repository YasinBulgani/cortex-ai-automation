---
id: REQ-DSM-001
title: "Veri Simülasyonu (DataSim)"
domain: DSM
source: internal-spec
external: ""
covered_by: [TC-DSM-001]
status: active
---

# REQ-DSM-001 — Veri Simülasyonu (DataSim)

## Tanım

Bu gereksinim DSM domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-DSM-001 → REQ-DSM-001 (login), REQ-DSM-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/datasim/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
