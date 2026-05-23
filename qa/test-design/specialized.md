# BGTS Test Dönüşüm — Uzmanlaşmış Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kapsam:** WebSocket, Localization (i18n), API Idempotency, Error Recovery, Edge Cases

---

## TS-SPEC-01: WebSocket Bildirim Testleri

### Kaynak Analiz
- `apps/web/lib/useWebSocket.ts` — WebSocket client hook
- Endpoint: `ws://<API_BASE>/api/v1/ws/notifications?token=<JWT>`
- Exponential backoff reconnect: 1s, 2s, 4s, 8s, ... max 30s
- Mesaj formatı: `{ type: string, payload: object, timestamp?: string }`
- Son 50 mesaj saklanır (FIFO)

### Test Senaryoları

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| WS-01 | Token ile başarılı WebSocket bağlantısı | Pozitif | High | `connected=true`; `onopen` tetiklenir |
| WS-02 | Token olmadan WebSocket bağlantısı reddi | Negatif | Critical | Bağlantı reddedilir veya 401 frame gönderilir |
| WS-03 | Expired token ile WebSocket bağlantısı | Negatif | High | Bağlantı reddedilir |
| WS-04 | Mesaj alımı ve state güncelleme | Pozitif | High | JSON mesaj parse edilir; `messages` state güncellenir |
| WS-05 | Malformed JSON mesaj toleransı | Exception | Medium | Parse hatası yakalanır; uygulama çökmez |
| WS-06 | Bağlantı kopması sonrası otomatik reconnect | Pozitif | High | Exponential backoff ile yeniden bağlanma (1s, 2s, 4s...) |
| WS-07 | Maximum reconnect delay (30s cap) | Boundary | Medium | 30 saniyeyi aşmaz |
| WS-08 | 50 mesaj limiti (FIFO buffer) | Boundary | Medium | 51. mesaj geldiğinde en eski mesaj düşer |
| WS-09 | clearMessages fonksiyonu | Pozitif | Low | Tüm mesajlar temizlenir |
| WS-10 | Component unmount'ta bağlantı kapatılır | Pozitif | Medium | `ws.close()` çağrılır; memory leak yok |
| WS-11 | Backend'den bildirim yayını (gerçek event) | Pozitif | High | Senaryo oluşturulduğunda WS mesajı gelir |
| WS-12 | Çoklu tab'da WebSocket | Pozitif | Medium | Her tab kendi bağlantısı; mesajlar senkron |

---

## TS-SPEC-02: Localization / Türkçe Uyumluluk Testleri

### Türkçe Karakter ve İçerik Testleri

| ID | Başlık | Senaryo | Beklenen |
|----|--------|---------|----------|
| L10N-01 | Türkçe karakterli proje adı | `"İŞ AKIŞI Öğrenci Çalışma"` ile proje oluştur | Doğru kaydedilir ve gösterilir |
| L10N-02 | Türkçe karakter arama (case-insensitive) | `"iş"` aramasında `"İŞ"` sonuçları da gelmeli | ilike Türkçe duyarlı çalışmalı |
| L10N-03 | Uzun Türkçe açıklama | 500+ karakter Türkçe metin ile senaryo oluştur | Kesme/bozulma olmadan kaydedilir |
| L10N-04 | Emoji içeren metin | `"Test 🧪 Senaryo ✅"` başlıklı senaryo | Doğru kaydedilir ve gösterilir |
| L10N-05 | UI metinleri Türkçe | Login, sidebar, butonlar, hata mesajları | Tüm statik metinler Türkçe |
| L10N-06 | API hata mesajları Türkçe | 404 → "Proje bulunamadı", 401 → "E-posta veya parola hatalı" | Türkçe hata mesajları |
| L10N-07 | Tarih formatı Türk standardı | Dashboard ve listeler | GG.AA.YYYY veya ISO format |
| L10N-08 | Büyük/küçük İ harfi sorunu | `"İstanbul"` vs `"istanbul"` karşılaştırma | Türkçe locale'a uygun çalışır |

### PostgreSQL Collation Kontrolü

```sql
-- Veritabanı collation kontrolü
SELECT datname, datcollate, datctype FROM pg_database WHERE datname = 'bgts_db';
-- Beklenen: tr_TR.UTF-8 veya en_US.UTF-8 (minimum)
```

---

## TS-SPEC-03: API Idempotency Testleri

| ID | Başlık | Senaryo | Beklenen |
|----|--------|---------|----------|
| IDP-01 | GET isteği idempotent | Aynı GET isteğini 10 kez gönder | Her seferinde aynı yanıt; side effect yok |
| IDP-02 | POST proje oluşturma non-idempotent | Aynı body ile 2 kez POST | 2 farklı proje oluşur (farklı UUID) |
| IDP-03 | PUT senaryo güncelleme idempotent | Aynı PUT isteğini 2 kez gönder | İkinci PUT'ta versiyon tekrar artmasın mı? (mevcut impl: her PUT versiyon artırır — non-idempotent) |
| IDP-04 | DELETE idempotent davranış | Aynı kaynağı 2 kez DELETE | İlk: 204, İkinci: 404 (güvenli) |
| IDP-05 | Senaryo-gereksinim link idempotent | Aynı bağlantıyı 2 kez ekle | Duplicate oluşmaz; mevcut impl idempotent ✅ |
| IDP-06 | Regresyon seti senaryo ekleme idempotent | Aynı ID'leri tekrar ekle | Set merge; duplicate yok ✅ |
| IDP-07 | Onay kararı tekrar gönderme | Zaten approved onaya tekrar approved gönder | İkinci istek de başarılı (idempotent); decided_at güncellenir |
| IDP-08 | Bulk-delete ile boş ID listesi | `{ "ids": [] }` gönder | 204; hiçbir şey silinmez |

---

## TS-SPEC-04: Error Recovery / Dayanıklılık Testleri

| ID | Başlık | Senaryo | Beklenen |
|----|--------|---------|----------|
| REC-01 | PostgreSQL restart sonrası recovery | 1. Docker ile postgres restart 2. Hemen API çağır | İlk 1-2 istek fail olabilir; connection pool auto-reconnect yapmalı |
| REC-02 | Redis restart sonrası recovery | Redis durdur → başlat → istek gönder | RQ queue devam etmeli; API çalışmalı |
| REC-03 | Frontend build hatası sonrası graceful fallback | Geçersiz API base URL ayarla → sayfa yükle | Anlaşılır hata mesajı; beyaz ekran olmamalı |
| REC-04 | LLM servisi timeout | BDD üretim isteği gönder, LLM 60s timeout | Timeout mesajı; kullanıcı tekrar deneyebilmeli |
| REC-05 | Disk dolu durumu | Upload sırasında disk dol | 507 veya 500; anlaşılır mesaj; corrupt dosya bırakılmamalı |
| REC-06 | Out of memory (OOM) koruması | 1 milyon satırlık veri yükle | Memory limit aşımı graceful handle; worker kill olursa restart |

---

## TS-SPEC-05: Edge Case / Köşe Durumu Testleri

| ID | Başlık | Senaryo | Beklenen |
|----|--------|---------|----------|
| EDGE-01 | UUID olmayan proje ID | GET `/tspm/projects/abc/dashboard` | 404 veya 422 (UUID parse error) |
| EDGE-02 | Çok uzun URL | 8000+ karakter URL ile istek | HTTP 414 URI Too Long |
| EDGE-03 | Boş JSON body | `{}` body ile POST `.../scenarios` | 422 (title required) |
| EDGE-04 | Null değerler | `{ "title": null }` ile POST | 422 |
| EDGE-05 | Integer overflow senaryo versiyon | Version değerini MAX_INT'e yaklaştır | Overflow hatası yok; güvenli artış |
| EDGE-06 | Tarih edge case | `"2000-01-01T00:00:00Z"` tarihli veri | Kaydedilir ve doğru gösterilir |
| EDGE-07 | Content-Type header eksik | JSON body gönder ama Content-Type header koyma | 422 veya otomatik parse |
| EDGE-08 | Accept header kontrolü | `Accept: text/xml` ile istek gönder | JSON döner (tek format); 406 değil |
| EDGE-09 | HTTP method mismatch | GET yerine DELETE ile proje listesi | 405 Method Not Allowed |
| EDGE-10 | Trailing slash | `/api/v1/tspm/projects/` vs `/api/v1/tspm/projects` | Her ikisi de çalışmalı |
| EDGE-11 | Query parametresinde özel karakterler | `?q=test%20senaryo&q=%27OR%201=1` | URL decode edilir; injection yok |
| EDGE-12 | Aynı anda 1000 senaryo oluşturma | Bulk script ile 1000 POST | Tamamı başarılı veya rate limit; DB tutarlı |
| EDGE-13 | Boş proje ismiyle senaryo arama | `?q=` (boş arama) | Tüm senaryolar döner (filtre uygulanmaz) |
| EDGE-14 | Senaryo adımları sırası | `[{order:2}, {order:0}, {order:1}]` ile senaryo oluştur | Sıra verilen şekilde kaydedilir |
| EDGE-15 | 0 byte body | POST isteği body olmadan | 422 validation error |

---

## Toplam Uzmanlaşmış Test Sayısı

| Kategori | Sayı |
|----------|------|
| WebSocket | 12 |
| Localization / Türkçe | 8 |
| API Idempotency | 8 |
| Error Recovery | 6 |
| Edge Cases | 15 |
| **Toplam** | **49** |

---

## Güncellenmiş Genel Toplam (Tüm Dokümanlar)

| Doküman | Test Sayısı |
|---------|------------|
| Ana Test Tasarımı | 75 |
| E2E UI Senaryoları | 59 |
| Güvenlik | 33 |
| Performans | 28 |
| RBAC Matrisi | 180+ |
| API Contract | 45+ |
| Cross-Cutting | 42 |
| İleri Seviye (Concurrency, a11y, DI) | 84 |
| Smoke / Release | 30 |
| Uzmanlaşmış (WebSocket, i18n, Edge) | 49 |
| **GENEL TOPLAM** | **625+** |
