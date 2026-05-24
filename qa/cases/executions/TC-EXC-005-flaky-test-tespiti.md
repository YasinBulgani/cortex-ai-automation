---
id: TC-EXC-005
title: "Kararsız (flaky) testlerin tespiti"
suite: executions
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-EXC-003]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-007]
tags: [migrated-pr3]
---

# TC-EXC-005 — Flaky test tespiti

## Önkoşul

Aynı senaryo farklı koşularda farklı sonuç vermiş

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../flaky-tests` isteği gönder | HTTP 200 |
| 2 | Flaky testleri kontrol et | `flip_count > 0` olan senaryolar listeli |
| 3 | Sıralamayı kontrol et | `flip_count` azalan sırada |

---
_Section: Test Koşusu ve Sonuçlar (Executions). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
