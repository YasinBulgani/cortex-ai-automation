---
id: TC-REC-001
title: "Kullanıcı aksiyonlarını kaydedip test kodu üretme"
suite: recorder
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-REC-001]
pre_conditions: [PRE-002, PRE-003]
tags: [migrated-pr3]
---

# TC-REC-001 — Test kaydı başlatma ve durdurma

## Önkoşul

Engine çalışır, tarayıcı kullanılabilir

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/recorder/start` ile kayıt başlat | HTTP 200, session ID |
| 2 | Kullanıcı aksiyonları gerçekleştir | Aksiyonlar kaydedilir |
| 3 | `POST /api/recorder/stop` ile kaydı durdur | HTTP 200 |
| 4 | Üretilen test kodunu kontrol et | Playwright/Cucumber/POM formatında |

---
_Section: Engine: Test Kaydedici (Recorder). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
