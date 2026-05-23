---
id: TC-RUN-002
title: "Regresyon seti içindeki testleri koşma"
suite: runs
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-RUN-001]
pre_conditions: [PRE-002, PRE-003, PRE-005, PRE-007]
tags: [migrated-pr3]
---

# TC-RUN-002 — Regresyon seti koşusu

## Önkoşul

Regresyon seti ve feature dosyaları mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/regression-sets/` ile setleri listele | HTTP 200 |
| 2 | Seçilen seti koştur | Tüm senaryolar çalıştırılır |
| 3 | Sonuç raporunu kontrol et | Geçen/kalan/hatalı sayıları doğru |

---
_Section: Engine: Test Çalıştırma. Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
