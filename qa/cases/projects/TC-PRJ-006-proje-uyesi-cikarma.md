---
id: TC-PRJ-006
title: "Projeden üye çıkarma"
suite: projects
priority: P3
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-PRJ-003]
pre_conditions: [PRE-002, PRE-004]
tags: [migrated-pr3]
---

# TC-PRJ-006 — Proje üyesi çıkarma

## Önkoşul

Proje üyesi mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `DELETE /api/v1/tspm/projects/{id}/members/{memberId}` gönder | HTTP 204 döner |
| 2 | Üye listesini tekrar sorgula | Çıkarılan üye listede olmamalı |

---
_Section: Proje Yönetimi (Project Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
