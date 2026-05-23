---
id: TC-AUTH-008
title: "Giriş alanlarında SQL injection koruması"
suite: auth
priority: P1
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-AUTH-003]
pre_conditions: [PRE-001, PRE-004]
tags: [migrated-pr3]
---

# TC-AUTH-008 — SQL injection denemesi

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Email alanına `' OR '1'='1` gönder | HTTP 401 döner (SQL injection çalışmamalı) |
| 2 | Parola alanına `'; DROP TABLE users;--` gönder | HTTP 401 döner, tablo sağlam kalmalı |

---
_Section: Kimlik Doğrulama (Authentication). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
