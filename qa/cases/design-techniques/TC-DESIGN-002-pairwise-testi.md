---
id: TC-DESIGN-002
title: "Pairwise (All-Pairs) algoritması ile test case üretimi"
suite: design-techniques
priority: P1
type: [functional, integration]
status: active
owner: "@unassigned"
created: 2026-06-08
updated: 2026-06-08
automation:
  status: not-automated
requirements: [REQ-DESIGN-002]
pre_conditions: [PRE-002, PRE-003]
tags: [design, pairwise, all-pairs]
---

# TC-DESIGN-002 — Pairwise (All-Pairs) algoritması ile test case üretimi

## Önkoşul

Backend çalışır, test management projesi mevcut, kullanıcı `test_lead` veya üstü yetkiye sahip

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Management > Design > Pairwise sayfasına git | Sayfa yüklenir, parametre giriş alanları görünür |
| 2 | Parametre 1: "Tarayıcı", değerler: "Chrome, Firefox, Safari" | Parametre eklenir, 3 değer tag'i görünür |
| 3 | Parametre 2: "OS", değerler: "Windows, macOS, Linux" | Parametre eklenir |
| 4 | "+ Parametre Ekle" ile Parametre 3: "Dil", değerler: "TR, EN" | Parametre eklenir |
| 5 | Tam kombinasyon hesabını kontrol et | 3×3×2 = 18 tam kombinasyon gösterir |
| 6 | "Pairwise Çalıştır" butonuna tıkla | Üretilen senaryolar listelenir |
| 7 | Üretilen case sayısını kontrol et | 18'den az, her parametre-değer çifti en az bir case'de yer alır |
| 8 | "Tablo" görünümüne geç | Her satırda Tarayıcı, OS, Dil sütunları ve değerleri görünür |
| 9 | İki case için "Kaydet" butonuna tıkla | Seçilen case'ler proje havuzuna kaydedilir |
| 10 | "Tümünü Kaydet" butonuna tıkla | Kalan tüm case'ler kaydedilir, "Tümü Kaydedildi ✓" gösterir |

## Ek Notlar

- `POST /api/v1/test-management/design/pairwise` → `{"fields": [{"name": str, "data_type": "enum", "allowed_set": [...]}]}` formatı
- En az 2 parametre zorunludur; tek parametre ile istek → HTTP 422 beklenir
- 8+ parametre × 6+ değer kombinasyonu → max 200 satır güvenlik limiti uygulanır
- LLM yanıt vermezse greedy deterministic fallback tüm ikili kombinasyonları kapsar

---
_Section: Design Techniques — Pairwise (All-Pairs)._
