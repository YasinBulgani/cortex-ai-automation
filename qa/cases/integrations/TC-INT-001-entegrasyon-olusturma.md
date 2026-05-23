---
id: TC-INT-001
title: "Yeni entegrasyon oluşturma (Jira, Jenkins vb.)"
suite: integrations
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-INT-001]
pre_conditions: [PRE-002, PRE-003]
tags: [migrated-pr3]
---

# TC-INT-001 — Entegrasyon oluşturma

## Önkoşul

Proje mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../integrations` ile `{"provider": "jira", "config": {...}, "is_active": true}` gönder | HTTP 201 |
| 2 | `provider`, `is_active` kontrol et | Gönderilen değerler |

---
_Section: Entegrasyonlar (Integrations). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
