---
id: TC-IMP-002
title: "İçe aktarma sayfasında dosya yükleme akışı"
suite: imports
priority: P1
type: [ui]
status: active
owner: "@unassigned"
created: 2026-05-22
updated: 2026-05-22
automation:
  status: automated
  refs:
    - e2e/bdd/features/import/import_tests.feature:10
requirements: [REQ-IMP-001]
pre_conditions: [PRE-002, PRE-003]
tags: [migrated-pr3]
---

# TC-IMP-002 — İçe aktarma sayfası UI akışı

## Önkoşul

Proje mevcut

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `/p/{projectId}/import` sayfasını aç | İçe aktarma formu görünür |
| 2 | Dosya seçim alanına test dosyası yükle | Dosya adı görüntülenir |
| 3 | Yükleme butonuna tıkla | İlerleme çubuğu gösterilir |
| 4 | İşlem tamamlanınca | Durum ve log bilgileri gösterilir |

---
_Section: İçe Aktarma Akışı (Import Flow). Migrated from `docs/test-analysis/manual-test-scenarios.md` (PR 3)._
