---
id: TC-PRJ-002
title: "Tüm projelerin listelenmesi"
suite: projects
priority: P1
type: [functional, smoke]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/projects/project_management.feature:17
    - backend/tests/bdd/features/project_management.feature:35
requirements: [REQ-PRJ-001]
pre_conditions: [PRE-002, PRE-004]
tags: [migrated-pr3]
---

# TC-PRJ-002 — Proje listesi sorgulama

## Önkoşul

En az 1 proje mevcut, geçerli JWT

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects` isteği gönder | HTTP 200 döner |
| 2 | Yanıt gövdesini kontrol et | JSON dizisi döner |
| 3 | Sıralamayı kontrol et | `created_at` azalan sırada |

---
_Section: Proje Yönetimi (Project Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
