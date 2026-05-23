---
id: TC-IMP-003
title: "Desteklenmeyen dosya formatı kontrolü"
suite: imports
priority: P2
type: [functional]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/import/import_tests.feature:22
requirements: [REQ-IMP-002]
pre_conditions: [PRE-002, PRE-003]
tags: [migrated-pr3]
---

# TC-IMP-003 — Geçersiz dosya formatı ile içe aktarma

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `.exe` uzantılı dosya ile import denemesi | Hata mesajı veya validasyon uyarısı |

---
_Section: İçe Aktarma Akışı (Import Flow). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
