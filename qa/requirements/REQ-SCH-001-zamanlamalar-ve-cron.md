---
id: REQ-SCH-001
title: "Zamanlamalar ve Cron"
domain: SCH
source: internal-spec
external: ""
covered_by: [TC-SCH-001, TC-SCH-002, TC-SCH-003]
status: active
---

# REQ-SCH-001 — Zamanlamalar ve Cron

## Tanım

Bu gereksinim SCH domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-SCH-001 → REQ-SCH-001 (login), REQ-SCH-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/schedules/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
