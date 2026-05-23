---
id: TC-PRJ-001
title: "Başarılı proje oluşturma"
suite: projects
priority: P0
type: [functional, smoke]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/projects/project_management.feature:9
    - backend/tests/bdd/features/project_management.feature:10
requirements: [REQ-PRJ-001]
pre_conditions: [PRE-002, PRE-004]
tags: [migrated-pr3]
---

# TC-PRJ-001 — Yeni proje oluşturma

## Önkoşul

Geçerli JWT token

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects` ile `{"name": "Test Projesi", "description": "Açıklama"}` gönder | HTTP 201 döner |
| 2 | Yanıt gövdesini kontrol et | `id`, `name`, `description`, `created_at` alanları mevcut |
| 3 | `name` değerini doğrula | "Test Projesi" |

---
_Section: Proje Yönetimi (Project Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
