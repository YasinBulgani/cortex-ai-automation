---
id: REQ-INT-001
title: "Dış Sistem Entegrasyonları"
domain: INT
source: internal-spec
external: ""
covered_by: [TC-INT-001, TC-INT-002]
status: active
---

# REQ-INT-001 — Dış Sistem Entegrasyonları

## Tanım

Bu gereksinim INT domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-INT-001 → REQ-INT-001 (login), REQ-INT-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/integrations/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
