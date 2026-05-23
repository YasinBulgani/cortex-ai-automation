---
id: TC-RUN-001
title: "Engine üzerinden test koşusu başlatma"
suite: runs
priority: P1
type: [functional, integration]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-RUN-001]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-007]
tags: [migrated-pr3]
---

# TC-RUN-001 — Test koşusu başlatma

## Önkoşul

Feature dosyası mevcut, Engine çalışır

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/run/` ile feature dosyası ve parametreler gönder | HTTP 200, koşu başlar |
| 2 | SSE stream üzerinden ilerlemeyi takip et | Gerçek zamanlı güncelleme |
| 3 | Koşu tamamlanınca raporu kontrol et | Allure veya JSON rapor |

---
_Section: Engine: Test Çalıştırma. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
