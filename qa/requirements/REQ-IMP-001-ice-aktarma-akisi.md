---
id: REQ-IMP-001
title: "İçe Aktarma Akışı"
domain: IMP
source: internal-spec
external: ""
covered_by: [TC-IMP-001, TC-IMP-002, TC-IMP-003]
status: active
---

# REQ-IMP-001 — İçe Aktarma Akışı

## Tanım

Bu gereksinim IMP domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-IMP-001 → REQ-IMP-001 (login), REQ-IMP-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/imports/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
