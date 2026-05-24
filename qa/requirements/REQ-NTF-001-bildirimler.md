---
id: REQ-NTF-001
title: "Bildirimler"
domain: NTF
source: internal-spec
external: ""
covered_by: [TC-NTF-001]
status: active
---

# REQ-NTF-001 — Bildirimler

## Tanım

Bu gereksinim NTF domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-NTF-001 → REQ-NTF-001 (login), REQ-NTF-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/notifications/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
