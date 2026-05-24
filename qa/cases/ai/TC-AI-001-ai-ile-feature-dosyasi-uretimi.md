---
id: TC-AI-001
title: "AI ile otomatik Gherkin feature üretimi"
suite: ai
priority: P2
type: [functional, integration]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-AI-001]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-AI-001 — AI ile feature dosyası üretimi

## Önkoşul

Engine çalışır, AI servisi erişilebilir

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/generate-feature/` ile URL veya açıklama gönder | HTTP 200 |
| 2 | Üretilen feature içeriğini kontrol et | Geçerli Gherkin formatında |
| 3 | Given/When/Then adımları kontrol et | Mantıklı test senaryosu |

---
_Section: Engine: AI Test Üretimi. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
