---
id: PRE-006
title: "Veri seti yüklenmiş ve analiz edilmiş"
description: "Sentetik veri (TC-SYN-*) ve veri simülasyon (TC-DSM-*) TC'leri için kaynak veri seti gereklidir."
setup_steps:
  - "PRE-003 (aktif proje)"
  - "POST /api/v1/syndata/datasets ile dataset upload (CSV veya JSON)"
  - "Dataset analyze edilmiş (column profiling, PII tespit tamamlanmış)"
  - "Dataset status = ready (queued/processing değil)"
teardown_steps: []
---

# PRE-006 — Veri seti yüklenmiş

## Amaç

Synthetic data ve DataSim TC'leri var olan bir kaynak veri setine ihtiyaç duyar. Boş projede bu TC'ler skip edilir.

## Bağımlılık

- PRE-003 (aktif proje)
- PRE-004 (backend API)
