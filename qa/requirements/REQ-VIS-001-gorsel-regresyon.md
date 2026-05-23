---
id: REQ-VIS-001
title: "Görsel Regresyon"
domain: VIS
source: internal-spec
external: ""
covered_by: [TC-VIS-001]
status: active
---

# REQ-VIS-001 — Görsel Regresyon

## Tanım

Bu gereksinim VIS domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-VIS-001 → REQ-VIS-001 (login), REQ-VIS-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/visual-regression/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
