---
id: TC-REQ-002
title: "Senaryoyu gereksinime bağlama"
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

# TC-REQ-002 — Senaryo-gereksinim bağlama

## Önkoşul

Senaryo ve gereksinim mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../scenarios/{id}/requirements` ile gereksinim ID'leri gönder | HTTP 201 |
| 2 | Bağlantıyı doğrula | Senaryo gereksinimlere bağlı |

---
_Section: Gereksinimler ve Kapsam (Requirements & Coverage). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
