---
id: TC-EXC-002
title: "Test sonucu durumunu güncelleme"
suite: executions
priority: P0
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-EXC-002]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-007]
tags: [migrated-pr3]
---

# TC-EXC-002 — Koşu sonucu güncelleme

## Önkoşul

Koşu mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `PATCH .../executions/{runId}/results/{resultId}` ile `{"status": "passed"}` gönder | HTTP 200 |
| 2 | Koşu detayını sorgula | İlgili sonucun durumu `"passed"` |

---
_Section: Test Koşusu ve Sonuçlar (Executions). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
