---
id: REQ-APR-001
title: "Onay İş Akışı"
domain: APR
source: internal-spec
external: ""
covered_by: [TC-APR-001, TC-APR-002, TC-APR-003, TC-APR-004, TC-APR-005]
status: active
---

# REQ-APR-001 — Onay İş Akışı

## Tanım

Bu gereksinim APR domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-APR-001 → REQ-APR-001 (login), REQ-APR-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/approvals/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
