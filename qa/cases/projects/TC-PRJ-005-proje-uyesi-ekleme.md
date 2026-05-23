---
id: TC-PRJ-005
title: "Projeye yeni üye ekleme"
suite: projects
priority: P1
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

# TC-PRJ-005 — Proje üyesi ekleme

## Önkoşul

Proje mevcut, eklenecek kullanıcı mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/members` ile `{"user_id": "...", "role": "tester"}` gönder | HTTP 201 döner |
| 2 | `GET /api/v1/tspm/projects/{id}/members` ile üye listesini sorgula | Eklenen üye listede |

---
_Section: Proje Yönetimi (Project Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
