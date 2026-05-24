---
id: TC-PRJ-003
title: "Proje dashboard verilerinin doğruluğu"
suite: projects
priority: P1
type: [functional, integration]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - backend/tests/bdd/features/project_management.feature:48
requirements: [REQ-PRJ-002]
pre_conditions: [PRE-002, PRE-004]
tags: [migrated-pr3]
---

# TC-PRJ-003 — Proje dashboard istatistikleri

## Önkoşul

Proje mevcut, senaryolar, koşular, onaylar oluşturulmuş

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/{projectId}/dashboard` isteği gönder | HTTP 200 döner |
| 2 | `scenario_count` kontrol et | Gerçek senaryo sayısı ile eşleşmeli |
| 3 | `pending_approvals` kontrol et | Bekleyen onay sayısı ile eşleşmeli |
| 4 | `execution_count` kontrol et | Koşu sayısı ile eşleşmeli |
| 5 | `latest_run_pass_rate` kontrol et | Null veya 0-100 arasında yüzde |

---
_Section: Proje Yönetimi (Project Management). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
