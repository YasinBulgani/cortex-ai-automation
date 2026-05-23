---
id: TC-SCN-006
title: "Üretilen BDD senaryolarını veritabanına kaydetme"
suite: scenarios
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SCN-003]
pre_conditions: [PRE-002, PRE-003, PRE-004]
tags: [migrated-pr3]
---

# TC-SCN-006 — BDD senaryoları toplu kaydetme

## Önkoşul

BDD üretimi yapılmış

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/scenarios/save-bdd` ile senaryo listesi gönder | HTTP 201 döner |
| 2 | Yanıttaki senaryo sayısını kontrol et | Gönderilen sayı ile eşleşmeli |
| 3 | Her senaryonun `status` alanını kontrol et | `"draft"` olmalı |

---
_Section: Senaryo Yönetimi (Scenario Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
