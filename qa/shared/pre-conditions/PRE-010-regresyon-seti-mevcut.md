---
id: PRE-010
title: "Regresyon seti mevcut (en az 1)"
description: "Regression koşumu, regresyon TC'leri (TC-REG-002..004) için var olan bir regresyon seti gerektirir."
setup_steps:
  - "PRE-005 (en az 1 senaryo)"
  - "POST /api/v1/tspm/regression-sets ile set oluşturulmuş"
  - "Set'e en az 1 senaryo eklenmiş"
teardown_steps: []
---

# PRE-010 — Regresyon seti mevcut

## Amaç

Regresyon TC'leri var olan bir set üzerinde işlem yapar. Boş projede skip.

## Bağımlılık

- PRE-005
