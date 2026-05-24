---
id: TC-QA-002
title: "Test otomasyonu kodu üretme"
suite: qa-engine
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-QA-001]
pre_conditions: [PRE-002, PRE-004, PRE-007]
tags: [migrated-pr3]
---

# TC-QA-002 — Otomasyon kodu üretimi

## Önkoşul

Geçerli JWT

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/qa/generate-automation` ile senaryo gönder | HTTP 200, otomasyon kodu |
| 2 | Üretilen kodun formatını kontrol et | Geçerli Playwright/pytest kodu |

---
_Section: QA Engine (Backend QA Routes). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
