---
id: REQ-A11Y-001
title: "Erişilebilirlik (WCAG 2.1)"
domain: A11Y
source: internal-spec
external: ""
covered_by: [TC-A11Y-001]
status: active
---

# REQ-A11Y-001 — Erişilebilirlik (WCAG 2.1)

## Tanım

Bu gereksinim A11Y domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-A11Y-001 → REQ-A11Y-001 (login), REQ-A11Y-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/a11y/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
