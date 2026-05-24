---
id: REQ-ENG-001
title: "Engine (Flask Test Runner)"
domain: ENG
source: internal-spec
external: ""
covered_by: [TC-ENG-001, TC-ENG-002]
status: active
---

# REQ-ENG-001 — Engine (Flask Test Runner)

## Tanım

Bu gereksinim ENG domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-ENG-001 → REQ-ENG-001 (login), REQ-ENG-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/engine/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
