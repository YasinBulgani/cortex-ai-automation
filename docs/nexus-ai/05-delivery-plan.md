# Nexus AI — 12 Haftalık Teslim Planı

Durum: Faz 1 uygulama planı
Süre: 12 hafta
Ana çıktı: Enterprise kullanıma hazır `Nexus AI / Visium Intelligence v1`

## 1. Faz Hedefleri

| Faz | Haftalar | Amaç |
|-----|----------|------|
| Faz A | 1-2 | Ürün iskeleti ve bağlam yapısı |
| Faz B | 3-4 | LLM Metrikleri dashboard v1 |
| Faz C | 5-6 | AI Asistan v1 |
| Faz D | 7-8 | NL Test Üretici v1 |
| Faz E | 9-10 | QA Orkestratör v1 |
| Faz F | 11-12 | Güvenlik, sertleştirme, pilot hazırlık |

## 2. Epic Yapısı

### Epic 1 — Product Shell

Amaç:
- `Nexus AI` içinde ürün seçimi ve ürün özel landing yapısını kurmak

İşler:
- ürün seçimi sayfası
- ayrı ürün route'ları
- ürün bağlamı state yönetimi
- sağ panel başlangıç yolu
- önerilen proje listesi alanı

Çıkış kriteri:
- kullanıcı ürün seçtikten sonra ayrı ürün sayfasına gidebilmeli

### Epic 2 — LLM Metrikleri

Amaç:
- QA Lead için ilk değer dashboard'unu üretmek

İşler:
- metrik veri modeli
- dashboard API
- kartlar, grafikler, filtreler
- test üretim hızı metriği
- aksiyona geçiş CTA'ları

Çıkış kriteri:
- QA Lead ilk 5 dakikada anlamlı operasyonel görünürlük almalı

### Epic 3 — AI Asistan

Amaç:
- bağlama duyarlı sohbet ve aksiyon yüzeyi oluşturmak

İşler:
- sohbet arayüzü
- ürün ve proje bağlam etiketi
- önerilen aksiyon düğmeleri
- artefakt oluşturma
- metrikten bağlam taşıma

Çıkış kriteri:
- kullanıcı asistan üzerinden gerçek aksiyon başlatabilmeli

### Epic 4 — NL Test Üretici

Amaç:
- doğal dilden test artefaktı üretmek

İşler:
- girdi formu
- çıktı türü seçimi
- test case, Gherkin, kod üretimi
- refine akışı
- kaydet ve export

Çıkış kriteri:
- kullanıcı en az bir kullanılabilir artefakt üretebilmeli

### Epic 5 — QA Orkestratör

Amaç:
- çok adımlı AI pipeline'ını görünür hale getirmek

İşler:
- pipeline builder v1
- adım durumu
- retry
- fallback
- otomatik uygulama sınırları
- sonuç özeti

Çıkış kriteri:
- uçtan uca en az bir pipeline başarıyla çalışmalı

### Epic 6 — Security and Governance

Amaç:
- enterprise dağıtıma uygun güvenlik sınırlarını kurmak

İşler:
- veri maskeleme
- audit log
- otomatik aksiyon whitelist
- teknik ekip yönetimi
- self-hosted inference doğrulaması

Çıkış kriteri:
- müşteri verisinin dış modele gitmediği doğrulanmalı

## 3. Haftalık Plan

### Hafta 1

- ürün bilgi mimarisi
- `docs/nexus-ai` karar seti tamamlanması
- frontend route tasarımı
- ürün bağlam modeli

### Hafta 2

- ürün seçimi ekranı
- ayrı ürün landing sayfaları
- başlangıç yolu bileşeni
- önerilen proje veri modeli

### Hafta 3

- LLM metrik veri pipeline'ı
- dashboard API şeması
- ilk kart seti
- hız metriği tanımı

### Hafta 4

- grafikler ve filtreler
- ürün ve proje bazlı breakdown
- dashboard'tan aksiyon CTA'ları
- QA Lead review

### Hafta 5

- AI Asistan arayüzü
- bağlam taşıma
- sohbet oturumu modeli
- aksiyon chip'leri

### Hafta 6

- artefakt üretim bağlantıları
- metrikten asistana geçiş
- ilk kullanılabilir sohbet senaryoları
- kalite kontrol testleri

### Hafta 7

- NL Test Üretici giriş ve çıktı akışı
- requirement → test case
- requirement → Gherkin

### Hafta 8

- requirement → test kodu
- refine döngüsü
- çoklu hedefe kayıt
- üretici ekranı polish

### Hafta 9

- orkestratör step modeli
- pipeline başlatma
- durum paneli
- retry akışı

### Hafta 10

- fallback ve log görünümü
- otomatik uygulama whitelist
- pipeline summary ekranı
- metrik entegrasyonu

### Hafta 11

- veri maskeleme
- audit log
- güvenlik testleri
- kurum içi inference sertleştirme

### Hafta 12

- pilot senaryolar
- performans iyileştirme
- kabul testleri
- rollout checklist

## 4. Backlog Önceliklendirme

### P0

- ürün seçimi sonrası ayrı route
- LLM dashboard ana ekranı
- test üretim hızı metriği
- self-hosted inference akışı
- müşteri verisi maskeleme
- artefakt çoklu hedef kaydı

### P1

- AI Asistan aksiyon akışı
- NL Test Üretici
- QA Orkestratör v1
- önerilen proje listeleri
- audit log

### P2

- prompt profile görünürlüğü
- ileri düzey karşılaştırmalı metrikler
- otomatik optimizasyon önerileri

## 5. Teslim Ekibi Önerisi

- 1 Product Manager
- 1 Tech Lead
- 2 Full-stack geliştirici
- 1 AI/Backend geliştirici
- 1 QA/Prompt evaluator
- 1 UI/UX designer

## 6. Riskler

### Risk 1

Tüm modülleri aynı fazda açmak kapsamı büyütür.

Önlem:
- LLM Metrikleri ilk ekran olarak sabitlenir
- diğer modüller v1 kapsamlı ama kontrollü açılır

### Risk 2

Self-hosted açık kaynak modeller beklenen kaliteyi her görevde vermeyebilir.

Önlem:
- görev bazlı model eşlemesi
- prompt registry ve kalite testleri
- üretim öncesi benchmark

### Risk 3

Otomatik uygulama enterprise güvenlik sınırlarını zorlayabilir.

Önlem:
- whitelist tabanlı otomasyon
- kritik akışları teknik ekip sınırlar

## 7. Çıkış Kriteri

Bu 12 haftalık plan başarılı sayılır, eğer:
- QA Lead ürün açılışında LLM metrik görünürlüğü alıyorsa
- test üretim hızında ölçülebilir iyileşme gözleniyorsa
- en az bir ürün bağlamında uçtan uca AI akışı çalışıyorsa
- sistem müşteri verisini dış modele göndermeden çalışıyorsa
- ürün modülleri aynı tasarım ve kalite diliyle çalışıyorsa
