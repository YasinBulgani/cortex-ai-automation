---
id: TC-SCH-002
title: "Zamanlamayı manuel tetikleme"
suite: schedules
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SCH-002]
pre_conditions: [PRE-002, PRE-003, PRE-005]
tags: [migrated-pr3]
---

# TC-SCH-002 — Zamanlama tetikleme

## Önkoşul

Zamanlama mevcut, senaryo ID'leri bağlı

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../schedules/{id}/trigger` | HTTP 201, yeni koşu |
| 2 | Koşu adını kontrol et | "Scheduled: {zamanlama adı}" |
| 3 | Senaryo sayısını kontrol et | Zamanlamadaki senaryo sayısı |

---
_Section: Zamanlamalar (Schedules). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
