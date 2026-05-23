---
id: TC-APR-005
title: "Onay sayfasında kaynak ve AI taslağı yan yana görüntüleme"
suite: approvals
priority: P1
type: [ui]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: not-automated
requirements: [REQ-APR-001]
pre_conditions: [PRE-002, PRE-003, PRE-009]
tags: [migrated-pr3]
---

# TC-APR-005 — Onay sayfası UI — Split View

## Önkoşul

Bekleyen onay mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `/p/{projectId}/approvals` sayfasını aç | Onay listesi görüntülenir |
| 2 | Bir onay kaydına tıkla | Split view açılır |
| 3 | Sol panelde kaynak metni kontrol et | Kaynak doküman/metin gösterilir |
| 4 | Sağ panelde AI taslağını kontrol et | AI tarafından üretilen senaryo taslağı |
| 5 | Onayla/Reddet butonlarını kontrol et | Her iki buton aktif ve tıklanabilir |

---
_Section: Onay İş Akışı (Approval Workflow). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
