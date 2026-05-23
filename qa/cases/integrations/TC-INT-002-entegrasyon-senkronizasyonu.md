---
id: TC-INT-002
title: "Entegrasyon senkronizasyonu tetikleme"
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

# TC-INT-002 — Entegrasyon senkronizasyonu

## Önkoşul

Entegrasyon mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../integrations/{id}/sync` | HTTP 200, `synced_count` ve `message` |

---
_Section: Entegrasyonlar (Integrations). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
