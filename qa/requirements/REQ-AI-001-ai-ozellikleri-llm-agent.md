---
id: REQ-AI-001
title: "AI Özellikleri (LLM Agent)"
domain: AI
source: internal-spec
external: ""
covered_by: [TC-AI-001]
status: active
---

# REQ-AI-001 — AI Özellikleri (LLM Agent)

## Tanım

Bu gereksinim AI domain'inin temel işlevsel ve davranışsal beklentilerini kapsar. PR 9'da
umbrella requirement olarak yaratıldı; ilerleyen PR'larda alt-gereksinimlere parçalanabilir
(örn. REQ-AI-001 → REQ-AI-001 (login), REQ-AI-002 (logout), ...).

## Kapsadığı TC'ler

Bu dosya frontmatter'ındaki `covered_by` listesi otomatik üretildi; `qa/tools/trace.mjs`
`coverage/traceability.csv` çıktısı kanonik kaynaktır.

## Kabul kriterleri

- [ ] Tüm P0 TC'ler pass durumda
- [ ] Domain spec dokümanları güncel
- [ ] Otomasyon oranı en az %50

## İlgili

- Suite: `qa/cases/ai/_suite.yml`
- Tasarım dokümanları: `qa/test-design/`
