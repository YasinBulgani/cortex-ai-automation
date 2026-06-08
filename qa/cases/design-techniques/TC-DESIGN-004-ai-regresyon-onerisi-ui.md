---
id: TC-DESIGN-004
title: "AI destekli regresyon önerisi paneli (Regression sayfası)"
suite: design-techniques
priority: P1
type: [functional, integration]
status: active
owner: "@unassigned"
created: 2026-06-08
updated: 2026-06-08
automation:
  status: not-automated
requirements: [REQ-REG-002]
pre_conditions: [PRE-002, PRE-003, PRE-005]
tags: [regression, ai, suggestion, ui]
---

# TC-DESIGN-004 — AI destekli regresyon önerisi paneli

## Önkoşul

- Projede en az 5 aktif test case mevcut (farklı öncelik ve son koşu durumlarına sahip)
- Backend `/regression/suggest` endpoint'i çalışır
- Kullanıcı `test_lead` veya üstü yetkiye sahip

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Management > Regression sayfasına git | Regresyon setleri listesi görünür |
| 2 | Herhangi bir regresyon seti için "Case Ekle" butonuna tıkla | Modal açılır; "Manuel" ve "✦ AI Öner" sekmeleri görünür |
| 3 | "✦ AI Öner" sekmesine geç | AI öneri paneli görünür; filtre seçenekleri ve "✦ AI ile Öner" butonu aktif |
| 4 | "Son çalışmada başarısız" ve "Hiç çalıştırılmamış" filtrelerini işaretle | Checkbox'lar seçili durumda |
| 5 | "✦ AI ile Öner" butonuna tıkla | Yükleme göstergesi görünür |
| 6 | Öneri listesini kontrol et | En az 1 aday; case ID, başlık, risk skoru (renkli) ve nedenler görünür |
| 7 | Birkaç adayı checkbox ile seç | Seçim sayacı güncellenir |
| 8 | "Case Ekle (N)" butonuna tıkla | Seçilen case'ler regresyon setine eklenir, modal kapanır |
| 9 | Regresyon setinin case listesini kontrol et | Eklenen case'ler listede görünür |

## Ek Notlar

- Risk skoru: P0/P1 → +30/20, başarısız koşu → +25, blocker/critical → +30/24
- `POST /api/v1/test-management/projects/{pid}/regression/suggest` → `{"include_last_failed": true, "include_not_run": true}`
- "Tümünü Seç" checkbox'ı tüm adayları tek seferde seçer

---
_Section: Design Techniques — AI Regression Suggestion UI._
