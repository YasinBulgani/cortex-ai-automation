---
id: REQ-SYN-001
title: "Sentetik Veri"
domain: SYN
source: internal-spec
external: ""
covered_by: [TC-SYN-001, TC-SYN-002, TC-SYN-003, TC-SYN-004, TC-SYN-005, TC-SYN-006]
status: active
---

# REQ-SYN-001 — Sentetik Veri

## Tanım

Bu gereksinim SYN domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-SYN-001 → REQ-SYN-001 (login), REQ-SYN-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/synthetic-data/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
