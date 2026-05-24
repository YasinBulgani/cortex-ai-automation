---
id: TC-PRJ-004
title: "Geçersiz proje ID ile 404 hatası"
suite: projects
priority: P1
type: [functional, api]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - backend/tests/bdd/features/project_management.feature:42
requirements: [REQ-PRJ-001]
pre_conditions: [PRE-002, PRE-004]
tags: [migrated-pr3]
---

# TC-PRJ-004 — Olmayan proje ID ile erişim

## Önkoşul

Geçerli JWT

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/nonexistent-id/dashboard` gönder | HTTP 404 döner |
| 2 | Yanıt mesajını kontrol et | "Proje bulunamadı" |

---
_Section: Proje Yönetimi (Project Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
