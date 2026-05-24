---
id: TC-SYN-003
title: "Kişisel veri (PII) tespiti"
suite: synthetic-data
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-SYN-003]
pre_conditions: [PRE-002, PRE-003, PRE-006]
tags: [migrated-pr3]
---

# TC-SYN-003 — PII tespiti

## Önkoşul

PII içeren veri seti yüklenmiş

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/detect-pii` ile veri seti gönder | PII alanları tespit edilmeli |
| 2 | TCKN, telefon, e-posta gibi alanları kontrol et | Doğru sınıflandırılmış |

---
_Section: Sentetik Veri ve Test Verisi (Synthetic Data). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
