---
id: TC-DESIGN-001
title: "Karar tablosu (DT) ile test case üretimi"
suite: design-techniques
priority: P1
type: [functional, integration]
status: active
owner: "@unassigned"
created: 2026-06-08
updated: 2026-06-08
automation:
  status: not-automated
requirements: [REQ-DESIGN-001]
pre_conditions: [PRE-002, PRE-003]
tags: [design, dt, decision-table]
---

# TC-DESIGN-001 — Karar tablosu (DT) ile test case üretimi

## Önkoşul

Backend çalışır, test management projesi mevcut, kullanıcı `test_lead` veya üstü yetkiye sahip

## Adımlar

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Management > Design > Decision Table sayfasına git | Sayfa yüklenir, koşul ve aksiyon giriş alanları görünür |
| 2 | "Koşul Ekle" ile 2 koşul ekle: "Kullanıcı Giriş Yapmış", "Admin Yetkisi Var" | Koşullar listeye eklenir |
| 3 | "Aksiyon Ekle" ile 1 aksiyon ekle: "Yönetim Paneli Göster" | Aksiyon eklenir |
| 4 | "Karar Tablosu Çalıştır" butonuna tıkla | Yükleme göstergesi görünür |
| 5 | Sonuçları bekle | HTTP 200, en az 1 üretilmiş senaryo |
| 6 | "Tablo" görünümüne geç | Matris tablosu görünür: koşullar Y/N, aksiyonlar ✓/— olarak |
| 7 | Tümü-doğru satırının aksiyon sütununu kontrol et | "✓" işareti görünür |
| 8 | "Tümünü Kaydet" butonuna tıkla | Senaryolar proje test case havuzuna kaydedilir |

## Ek Notlar

- 2 boolean koşul → maksimum 4 kural (2²), backend cap 16 row'u aşmaz
- `POST /api/v1/test-management/design/dt` → `{"conditions": [...], "actions": [...]}` formatını kabul etmeli
- LLM mevcut değilse deterministik fallback devreye girmeli (`source: "fallback"`)

---
_Section: Design Techniques — Decision Table._
