---
id: TC-REQ-001
title: "Yeni gereksinim oluşturma"
suite: requirements
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-REQ-001]
pre_conditions: [PRE-002, PRE-003]
tags: [migrated-pr3]
---

# TC-REQ-001 — Gereksinim oluşturma

## Önkoşul

Proje mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../requirements` ile gereksinim oluştur | HTTP 201 |
| 2 | `external_id`, `title`, `priority` kontrol et | Gönderilen verilerle eşleşir |

---
_Section: Gereksinimler ve Kapsam (Requirements & Coverage). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
