---
id: PRE-009
title: "Bekleyen onay (approval) mevcut"
description: "Approval TC'leri (TC-APR-002 onay kabul, TC-APR-003 reddet) bekleyen bir onay kaydı gerektirir."
setup_steps:
  - "PRE-005 (senaryo) uygulanmış"
  - "AI üretti senaryo onay kuyruğuna düşmüş (status: pending_approval)"
  - "VEYA: Manuel olarak POST /api/v1/tspm/approvals ile pending kayıt oluşturulmuş"
teardown_steps: []
---

# PRE-009 — Bekleyen onay mevcut

## Amaç

Onay iş akışı TC'leri var olan bir pending approval kaydı üzerinden işlem yapar.

## Bağımlılık

- PRE-005 (senaryo)
