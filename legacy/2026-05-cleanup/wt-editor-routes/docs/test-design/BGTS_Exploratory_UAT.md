# BGTS Test Dönüşüm — Keşifsel Test Oturumları (Exploratory) & UAT Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03

---

## Bölüm 1: Keşifsel Test Oturumları (Exploratory Testing Charters)

> Her charter ~30 dakikalık zaman kutulu bir keşifsel test oturumudur.

### Charter Formatı

```
Charter: [Başlık]
Alan: [Modül/sayfa]
Misyon: [Ne keşfedilecek]
Süre: 30 dakika
Notlar: [Bulunan sorunlar, gözlemler, sorular]
```

---

### EXP-01: Login Sayfası Keşif

| Alan | Değer |
|------|-------|
| **Misyon** | Login sayfasındaki tüm etkileşimleri keşfet; edge case ve UX sorunlarını bul |
| **Odak** | Form davranışları, hata mesajları, keyboard navigasyon, clipboard paste, otomatik doldurma |
| **Deney Fikirleri** | SQL injection dene, çok uzun e-posta gir, özel karakterli parola, copy-paste ile giriş, tarayıcı password manager davranışı, çift tıklama, mobil keyboard |
| **Başarı Kriteri** | En az 3 bug veya UX iyileştirme bulundu |

### EXP-02: Senaryo Oluşturma Akışı Keşif

| Alan | Değer |
|------|-------|
| **Misyon** | Senaryo oluşturma → düzenleme → versiyon → silme akışındaki sorunları keşfet |
| **Odak** | Form state korunumu, tarayıcı geri tuşu, çok uzun adım metinleri, Türkçe karakter, concurrent edit |
| **Deney Fikirleri** | 100+ adım ekle, HTML/script tag yapıştır, formun yarısını doldur ve sayfadan ayrıl, 2 tarayıcıda aynı senaryoyu düzenle |
| **Başarı Kriteri** | Data loss veya UX friction noktaları tespit edildi |

### EXP-03: BDD Üretimi (AI) Keşif

| Alan | Değer |
|------|-------|
| **Misyon** | AI BDD üretiminin farklı analiz dokümanlarıyla nasıl davrandığını keşfet |
| **Odak** | Çok kısa metin, çok uzun metin, İngilizce metin, teknik olmayan metin, tablo formatında metin |
| **Deney Fikirleri** | Boş metin gönder, sadece emoji gönder, 50.000 karakter yapıştır, zaten Gherkin olan metin gönder, farklı dillerde metin |
| **Başarı Kriteri** | AI hata senaryoları ve yanıt kalitesi değerlendirildi |

### EXP-04: Dashboard ve Analitik Keşif

| Alan | Değer |
|------|-------|
| **Misyon** | Dashboard metriklerinin doğruluğunu ve edge case'leri keşfet |
| **Odak** | Boş proje dashboard, çok fazla verili dashboard, sayaç doğruluğu, trend grafik render |
| **Deney Fikirleri** | 1000 senaryo olan projede dashboard, aynı anda 50 koşu oluştur ve dashboard kontrol et, tarayıcı zoom ile grafik bozulma |
| **Başarı Kriteri** | Hesaplama hataları veya performans sorunları tespit edildi |

### EXP-05: Akış Editörü (React Flow) Keşif

| Alan | Değer |
|------|-------|
| **Misyon** | React Flow tabanlı akış editörünün sınırlarını ve UX sorunlarını keşfet |
| **Odak** | Drag & drop, zoom, pan, node ekleme/silme, edge oluşturma, canvas boyutu, mobil kullanım |
| **Deney Fikirleri** | 50+ node ekle, döngüsel bağlantı oluştur, node'u canvas dışına sürükle, save etmeden sayfayı kapat, dokunmatik cihazda kullan |
| **Başarı Kriteri** | Editör stabilitesi ve kullanılabilirlik değerlendirildi |

### EXP-06: Regresyon ve Zamanlama Keşif

| Alan | Değer |
|------|-------|
| **Misyon** | Regresyon seti + zamanlama + tetikleme zincirinin uçtan uca davranışını keşfet |
| **Odak** | AI önerisi kalitesi, önerilen seti kabul → zamanlama oluştur → tetikle → koşu kontrol |
| **Deney Fikirleri** | Boş seti tetikle, silinmiş senaryo ID'si ile set oluştur, geçersiz cron ifadesi gir |
| **Başarı Kriteri** | Zincirdeki kırılma noktaları tespit edildi |

### EXP-07: Engine Test Recorder Keşif

| Alan | Değer |
|------|-------|
| **Misyon** | Engine'in test kaydedici modülünün farklı web sayfalarında davranışını keşfet |
| **Odak** | Kayıt başlatma, farklı element tipleri, SPA navigasyon, popup/modal, iframe, dosya upload |
| **Deney Fikirleri** | Gmail gibi karmaşık SPA'da kayıt yap, iframe içindeki elemente tıkla, dosya dialog'u aç, kaydı durdurmadan tarayıcı kapat |
| **Başarı Kriteri** | Kayıt doğruluğu ve kod üretim kalitesi değerlendirildi |

### EXP-08: Görsel Regresyon Keşif

| Alan | Değer |
|------|-------|
| **Misyon** | Görsel regresyon test sisteminin farklı sayfa türlerinde davranışını keşfet |
| **Odak** | Baseline oluşturma, pixel diff, SSIM threshold, dark/light tema farkı, responsive viewport |
| **Deney Fikirleri** | Font değişikliği ile diff, animasyon içeren sayfa, lazy-load içerik, farklı viewport'larda baseline |
| **Başarı Kriteri** | False positive/negative oranı değerlendirildi |

---

## Bölüm 2: Kullanıcı Kabul Testleri (UAT)

> UAT senaryoları iş kullanıcıları (test liderleri, kalite mühendisleri) tarafından çalıştırılır.

### UAT-01: Yeni Test Lideri Onboarding Akışı

| Adım | İşlem | Beklenen |
|------|-------|----------|
| 1 | Admin'den hesap al, login ol | Dashboard görünür |
| 2 | Yeni proje oluştur | Proje kartı listede |
| 3 | 5 senaryo oluştur (manuel) | Senaryolar listede, draft status |
| 4 | Analiz dokümanından BDD üret | AI senaryoları önizlenir |
| 5 | 3 senaryoyu seç ve kaydet | Senaryolar havuza eklenir |
| 6 | Gereksinim oluştur ve senaryolara bağla | Coverage matrix %100 |
| 7 | Koşu oluştur ve sonuçları güncelle | Dashboard'da pass rate görünür |
| 8 | Regresyon seti oluştur | Seçili senaryolar gruplanır |

### UAT-02: Sprint Sonu Test Koşusu Akışı

| Adım | İşlem | Beklenen |
|------|-------|----------|
| 1 | Login ol, projeye git | Dashboard metrikler güncel |
| 2 | Tüm senaryolarla koşu oluştur | Running statusünde koşu |
| 3 | Her senaryonun sonucunu güncelle | Passed/failed sayaçlar güncellenir |
| 4 | Flaky test listesini kontrol et | Varsa flip eden senaryolar görünür |
| 5 | Trend grafiğini incele | Son sprintlerin başarı oranları |
| 6 | Coverage gaps kontrol et | Kapsanmayan gereksinimler listelenir |
| 7 | Rapor screenshot'larını al | Yöneticiye sunulabilir |

### UAT-03: AI Asistanlı Test Üretimi Akışı

| Adım | İşlem | Beklenen |
|------|-------|----------|
| 1 | Login ol, projeye git | — |
| 2 | "BDD Üret" sayfasına git | Analiz dokümanı alanı görünür |
| 3 | Gerçek bir analiz dokümanı yapıştır | — |
| 4 | Ek talimat ekle: "Negatif senaryolara odaklan" | — |
| 5 | "Senaryoları Üret" tıkla | Loading animasyonu; 10-30sn |
| 6 | Üretilen senaryoları incele | Gherkin formatında, Türkçe |
| 7 | İstediğin senaryoları seç, istemediğini kaldır | Checkbox seçimi |
| 8 | "Seçilenleri kaydet" | Senaryolar draft olarak havuzda |

### UAT-04: Regresyon Zamanlama Akışı

| Adım | İşlem | Beklenen |
|------|-------|----------|
| 1 | Regresyon seti oluştur veya AI önerisini kabul et | Set oluşur |
| 2 | Zamanlama oluştur: "Her gece 02:00" | Cron: `0 2 * * *` |
| 3 | Zamanlama regression set'e bağla | — |
| 4 | Manuel tetikle | Koşu oluşur; senaryo sonuçları pending |
| 5 | Sonuçları güncelle | Dashboard güncellenir |

### UAT-05: Veri Bazlı Test Akışı

| Adım | İşlem | Beklenen |
|------|-------|----------|
| 1 | Test veri seti oluştur (Login verileri) | Kolonlar ve satırlar tanımlı |
| 2 | Parametrik senaryo oluştur: `{{email}}` `{{password}}` | Adımlarda placeholder |
| 3 | Veri setini senaryoya bağla | Mapping oluşturulur |
| 4 | Genişletilmiş (expanded) görünümü incele | Her satır için ayrı adım seti |

### UAT-06: Coverage ve Raporlama Akışı

| Adım | İşlem | Beklenen |
|------|-------|----------|
| 1 | 10 gereksinim oluştur | — |
| 2 | 8 gereksinimi senaryolara bağla | — |
| 3 | Coverage matrix görüntüle | %80 kapsam, 2 gap |
| 4 | Coverage gaps listesini incele | 2 bağlantısız gereksinim |
| 5 | Eksik 2 gereksinim için senaryo oluştur ve bağla | — |
| 6 | Coverage matrix tekrar kontrol et | %100 kapsam |

---

## Bölüm 3: Kabul Testi Kontrol Listesi

| # | Kriter | Kabul Edildi |
|---|--------|-------------|
| 1 | Login/logout akışı sorunsuz çalışıyor | ☐ |
| 2 | Proje CRUD işlemleri çalışıyor | ☐ |
| 3 | Senaryo CRUD + versiyon çalışıyor | ☐ |
| 4 | BDD AI üretimi çalışıyor (veya fallback var) | ☐ |
| 5 | Onay kuyruğu (approve/reject) çalışıyor | ☐ |
| 6 | Koşu oluşturma ve sonuç güncelleme çalışıyor | ☐ |
| 7 | Dashboard metrikleri doğru hesaplanıyor | ☐ |
| 8 | Coverage matrix doğru hesaplanıyor | ☐ |
| 9 | Regresyon seti + AI önerisi çalışıyor | ☐ |
| 10 | Zamanlama oluşturma ve tetikleme çalışıyor | ☐ |
| 11 | Test verisi bağlama ve genişletme çalışıyor | ☐ |
| 12 | Akış editörü (React Flow) çalışıyor | ☐ |
| 13 | Sidebar navigasyonu tam çalışıyor | ☐ |
| 14 | Dark/light tema çalışıyor | ☐ |
| 15 | Responsive layout (mobil/tablet) kabul edilebilir | ☐ |
| 16 | Performans kabul edilebilir seviyede (< 2sn sayfa yükleme) | ☐ |
| 17 | Türkçe karakter/içerik desteği tam | ☐ |
| 18 | Hata mesajları anlaşılır ve Türkçe | ☐ |

---

## Toplam

| Kategori | Sayı |
|----------|------|
| Keşifsel test charter'ı | 8 |
| UAT senaryosu | 6 |
| Kabul kriteri | 18 |
| **Toplam** | **32** |
