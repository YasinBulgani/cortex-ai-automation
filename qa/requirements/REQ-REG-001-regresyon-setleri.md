---
id: REQ-REG-001
title: "Regresyon Setleri"
domain: REG
source: internal-spec
external: ""
covered_by: [TC-REG-001, TC-REG-002, TC-REG-003, TC-REG-004]
status: active
---

# REQ-REG-001 — Regresyon Setleri

## Tanım

Bu gereksinim REG domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-REG-001 → REQ-REG-001 (login), REQ-REG-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/regression/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
