---
id: REQ-INF-001
title: "Altyapı ve Sağlık Kontrolleri"
domain: INF
source: internal-spec
external: ""
covered_by: [TC-INF-001, TC-INF-002, TC-INF-003]
status: active
---

# REQ-INF-001 — Altyapı ve Sağlık Kontrolleri

## Tanım

Bu gereksinim INF domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-INF-001 → REQ-INF-001 (login), REQ-INF-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/infrastructure/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
