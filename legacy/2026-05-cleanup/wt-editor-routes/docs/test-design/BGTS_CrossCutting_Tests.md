# BGTS Test Dönüşüm — Cross-Cutting Concerns Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kapsam:** Audit Logging, Webhooks, Rate Limiting, Error Handling, Data Versioning, Quality Dashboard

---

## TS-CC-01: Audit Logging Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| CC-0101 | Login işlemi audit log kaydı | Pozitif | High | 1. Login yap 2. Audit log tablosunu kontrol et | `auth.login` kaydı mevcut |
| CC-0102 | Proje oluşturma audit log | Pozitif | Medium | 1. Proje oluştur 2. Audit log kontrol et | İlgili kayıt mevcut |
| CC-0103 | Senaryo silme audit log | Pozitif | Medium | 1. Senaryo sil 2. Audit log kontrol et | Delete aksiyonu loglanmış |
| CC-0104 | Audit log filtreleme | Pozitif | Medium | 1. `GET /api/v1/audit/logs?action=auth.login` çağır | Yalnızca login logları döner |
| CC-0105 | Audit log CSV export | Pozitif | Low | 1. Audit log export endpoint'i çağır | CSV formatında dosya indirilir |
| CC-0106 | Audit log'da hassas veri yok | Güvenlik | High | 1. Tüm audit log kayıtlarını incele | Parola, token gibi hassas bilgi yok |
| CC-0107 | Audit log X-Request-ID izleme | Pozitif | Medium | 1. İstek gönder, X-Request-ID header al 2. Audit log'da aynı ID ile eşleştir | İstek izlenebilir |

---

## TS-CC-02: Webhook Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| CC-0201 | Webhook kaydı oluşturma | Pozitif | High | 1. `POST /api/webhooks` ile URL ve event belirle | Webhook kaydedilir |
| CC-0202 | Webhook test gönderimi | Pozitif | High | 1. `POST /api/webhooks/{id}/test` çağır | Test payload gönderilir |
| CC-0203 | Webhook HMAC-SHA256 imza doğrulama | Güvenlik | Critical | 1. Webhook payload ve signature al 2. Secret ile doğrula | İmza geçerli |
| CC-0204 | Webhook retry mekanizması | Pozitif | High | 1. Erişilemeyen URL ile webhook kaydet 2. Event tetikle 3. Delivery log kontrol et | 3 retry denemesi görünür |
| CC-0205 | Webhook otomatik devre dışı bırakma | Pozitif | Medium | 1. 10 ardışık başarısız teslimat simüle et | Webhook otomatik devre dışı olur |
| CC-0206 | Webhook soft delete | Pozitif | Medium | 1. `DELETE /api/webhooks/{id}` çağır | Webhook silinir (soft delete) |
| CC-0207 | Webhook event filtreleme | Pozitif | Medium | 1. Sadece `generation.completed` event'ini dinleyen webhook oluştur 2. `analysis.completed` tetikle | Webhook tetiklenmemeli |

---

## TS-CC-03: Rate Limiting Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| CC-0301 | Normal istek rate limit header'ları | Pozitif | Medium | 1. Herhangi bir endpoint'e istek gönder 2. Response header'ları kontrol et | X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset mevcut |
| CC-0302 | Rate limit aşıldığında 429 | Negatif | High | 1. Limiti aşacak sayıda istek gönder | HTTP 429 Too Many Requests |
| CC-0303 | Sliding window penceresi | Pozitif | Medium | 1. Limite yakın istek gönder 2. Pencere yenilenene kadar bekle 3. Tekrar istek gönder | Pencere yenilendikten sonra kabul edilir |
| CC-0304 | IP bazlı izolasyon | Pozitif | Medium | 1. IP-A'dan limit aş 2. IP-B'den istek gönder | IP-B etkilenmez |
| CC-0305 | Whitelist IP muafiyeti | Pozitif | Low | 1. Whitelist'teki IP'den yoğun istek gönder | Rate limit uygulanmaz |

---

## TS-CC-04: Error Handling Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| CC-0401 | 404 hatası standart format | Pozitif | Medium | 1. Var olmayan endpoint'e istek gönder | `{ "detail": "..." }` formatında JSON |
| CC-0402 | 422 validation error detaylı format | Pozitif | Medium | 1. Geçersiz veri ile POST gönder | `{ "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }` |
| CC-0403 | 500 hatası bilgi sızdırmaz | Güvenlik | High | 1. Sunucu hatası tetikle | Stack trace client'a döndürülmemeli (DEBUG=False'da) |
| CC-0404 | X-Request-ID her yanıtta mevcut | Pozitif | Medium | 1. Çeşitli endpoint'lere istek gönder | Her yanıtta X-Request-ID header'ı var |
| CC-0405 | X-Process-Time header | Pozitif | Low | 1. API isteği gönder | X-Process-Time header'ı saniye cinsinden |
| CC-0406 | JSON parse hatası | Negatif | Medium | 1. Geçersiz JSON body gönder | HTTP 422; açıklayıcı hata mesajı |
| CC-0407 | Büyük payload reddi | Negatif | Medium | 1. 50MB+ body gönder | HTTP 413 veya timeout; sistem çökmemeli |

---

## TS-CC-05: Data Versioning Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| CC-0501 | Otomatik versiyon oluşturma | Pozitif | High | 1. Veri setini güncelle 2. Versiyon listesini çek | Yeni versiyon kaydı oluşturulmuş |
| CC-0502 | Versiyon karşılaştırma (diff) | Pozitif | Medium | 1. 2 versiyon oluştur 2. Diff endpoint'i çağır | Değişen alanlar belirtilmiş |
| CC-0503 | Versiyon geri yükleme | Pozitif | High | 1. Eski versiyon ID'si ile geri yükleme çağır | Veri eski durumuna döner |
| CC-0504 | Versiyon checksum doğruluğu | Pozitif | Medium | 1. Versiyon kaydının checksum'ını doğrula | Veri bütünlüğü korunmuş |

---

## TS-CC-06: Quality Dashboard Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| CC-0601 | Kalite raporu hesaplama | Pozitif | Medium | 1. Veri seti için kalite analizi çağır | 5 boyutlu kalite skoru döner |
| CC-0602 | Kalite seviyesi sınıflandırma | Pozitif | Medium | 1. Farklı kalite skorları ile test | excellent (>90), good (>70), fair (>50), poor (>30), critical (<=30) |
| CC-0603 | Kalite geçmişi (trend) | Pozitif | Low | 1. Kalite geçmişi endpoint'i çağır | Zaman serisi verisi döner |

---

## TS-CC-07: Export Template Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| CC-0701 | Export şablonu oluşturma | Pozitif | Medium | 1. Kolon seçimi ve filtre ile şablon oluştur | Şablon kaydedilir |
| CC-0702 | CSV formatında export | Pozitif | High | 1. CSV şablonu ile export çağır | UTF-8 CSV dosyası indirilir |
| CC-0703 | JSON formatında export | Pozitif | High | 1. JSON şablonu ile export çağır | Geçerli JSON dosyası |
| CC-0704 | SQL INSERT formatında export | Pozitif | Medium | 1. SQL şablonu ile export çağır | Geçerli INSERT ifadeleri |
| CC-0705 | Filtre uygulamalı export | Pozitif | Medium | 1. `status=active` filtresi ile export | Yalnızca aktif kayıtlar |

---

## Toplam Cross-Cutting Test Sayısı: 42

| Kategori | Sayı |
|----------|------|
| Audit Logging | 7 |
| Webhooks | 7 |
| Rate Limiting | 5 |
| Error Handling | 7 |
| Data Versioning | 4 |
| Quality Dashboard | 3 |
| Export Templates | 5 |
| **İmport (Stub)** | **4** |

---

## TS-CC-08: Import İşlemleri (Stub — Genişletilecek)

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| CC-0801 | Import kaydı oluşturma | Pozitif | High | 1. Filename ve raw_text ile import oluştur | HTTP 201; status: completed |
| CC-0802 | Import listesi görüntüleme | Pozitif | Medium | 1. Import listesini çek | Oluşturulan importlar listelenir |
| CC-0803 | Büyük dosya importu | Boundary | Medium | 1. 10MB+ metin ile import oluştur | Başarılı veya uygun hata mesajı |
| CC-0804 | n8n webhook callback (gelecekte) | Pozitif | High | 1. n8n pipeline sonucu callback gönder | Import statusü güncellenir; onay kuyruğuna taslak düşer |
