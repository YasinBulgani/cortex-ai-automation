---
id: TC-EXC-003
title: "Önceki koşuyu yeniden çalıştırma"
suite: executions
priority: P1
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

# TC-EXC-003 — Koşu yeniden çalıştırma

## Önkoşul

Tamamlanmış koşu mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/executions/{runId}` ile re-run | HTTP 201, yeni koşu |
| 2 | Yeni koşunun adını kontrol et | Orijinal ad + " (re-run)" |
| 3 | Senaryo sayısını kontrol et | Orijinal koşu ile aynı |

---
_Section: Test Koşusu ve Sonuçlar (Executions). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
