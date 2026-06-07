# Frontend İşlevsel Eksiklik Raporu

**Tarih:** 5 Haziran 2026
**Kapsam:** Cortex AI Automation — Management Modülü ve Bağlantılı Frontend Sayfaları
**Analist:** 71 Ajan Otomatik Analiz (feature/qa-system-bootstrap branch)

---

## Yönetici Özeti

Bu rapor, `feature/qa-system-bootstrap` branch'ında bulunan frontend kodunun statik analizi sonucunda üretilmiştir. Analiz üç veri kaynağını kapsamaktadır: management workspace sayfaları (30 dosya), localStorage/mock bağımlılığı ölçümü (14 dosya) ve API bağlantı doğrulaması.

**Genel sonuç:** Management modülünün çekirdeği (%85 API bağlantılı) üretim kalitesine yakındır. Ancak entegrasyon panelleri, ayarlar ve sentetik veri modülü ciddi işlevsel boşluklar içermektedir. Toplamda 7 tamamen kopuk API çağrısı, 3 UI-only stub özellik, 8 sıfır-API sayfası ve 4 hatalı akış tespit edilmiştir.

**Frontend Olgunluk Skoru: 67 / 100**

---

## Kritik Eksiklikler (Hemen Düzeltilmeli)

### 1. SSO/SAML Konfigürasyonu — Tamamen localStorage

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/integrations/page.tsx` (satır 318)

SSO/SAML yapılandırması yalnızca `SSO_STORAGE_KEY` localStorage anahtarına yazılmaktadır. Kaydet butonuna basıldığında hiçbir backend API çağrısı yapılmamaktadır. "Bağlantıyı Test Et" butonu (satır 359) yalnızca `config.entityId && config.ssoUrl` boş olmayan string kontrolü yapmakta; gerçek bir SAML endpoint isteği gönderilmemektedir. Okta, Azure AD ve Auth0 seçenekleri görsel olarak sunulmakta, ancak hiçbiri işlevsel değildir. Konfigürasyon tarayıcı temizlendiğinde veya farklı kullanıcı oturumu açıldığında tamamen kaybolmaktadır.

**Etki:** Ekip genelinde SSO hiçbir zaman gerçek anlamda etkinleştirilemez. Test bağlantısı her zaman başarılı döner — bu durum yanlış güven yaratır.

**Gerekli aksiyon:** Backend'de SAML konfigürasyon endpoint'i oluşturulmalı; `SsoPanel` bileşeni `useMutation`/`apiFetch` ile bu endpoint'e bağlanmalıdır.

---

### 2. Webhook Bildirimleri — Tamamen localStorage

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/integrations/page.tsx` (satır 502)

`WebhookNotificationsPanel` bileşeni, webhook aboneliklerini `WEBHOOKS_STORAGE_KEY` localStorage anahtarına yazar. Ekleme, silme ve listeleme işlemleri yalnızca istemci state'i ve localStorage'ı mutasyona uğratmaktadır. Backend'de webhook CRUD endpoint'i bulunmamaktadır. Webhook listesi ekip üyeleri arasında paylaşılmamakta; tarayıcı temizlendiğinde silinmektedir.

**Etki:** Kullanıcılar webhook kayıtlarının kalıcı olduğunu zannetmekte, ancak veri tamamen kaybolabilir niteliktedir.

**Gerekli aksiyon:** Backend webhook abonelik CRUD API'si oluşturulmalı; panel bu API'ye bağlanmalıdır.

---

## Yüksek Öncelikli Eksiklikler

### 3. CI/CD Webhook Testi — CORS Engeli

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/integrations/page.tsx` (satır 923–946)

`CiCdWebhookPanel` bileşenindeki "Test Webhook" işlevi, kullanıcının girdiği harici URL'ye doğrudan tarayıcı tarafında `fetch()` çağrısı yapmaktadır. Çoğu CI/CD servisinde (GitHub Actions, GitLab CI, Jenkins vb.) CORS politikası bu isteği engelleyecektir; kullanıcıya sessiz bir hata verilmekte ya da hata hiç gösterilmemektedir. Webhook konfigürasyonu backend'e kalıcı olarak kaydedilmemektedir.

**Gerekli aksiyon:** Webhook test isteği bir backend proxy üzerinden yönlendirilmeli; konfigürasyon backend'e kalıcı olarak kaydedilmelidir.

---

### 4. API Anahtarları Yönetimi — localStorage'dan Öteye Geçilemiyor

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/settings/page.tsx` (satır 183–234)

Ayarlar sayfasının API Anahtarları sekmesi, anahtar girişlerini `apiKeysStorageKey` localStorage anahtarına kaydederken hiçbir `apiFetch` veya `useMutation` çağrısı yapmamaktadır. Üretilen anahtarlar yalnızca tarayıcıda saklanmaktadır; sunucu tarafında kayıt altına alınmadığından gerçek kimlik doğrulaması için kullanılamazlar.

**Gerekli aksiyon:** Backend'de API key CRUD endpoint'i oluşturulmalı; localStorage fallback kaldırılmalıdır.

---

### 5. Sentetik Veri Modülü — 7 Kopuk API Çağrısı

**Dosya:** `apps/web/lib/hooks/use-synthetic-advanced.ts`

| Frontend Çağrısı | Backend Durumu |
|---|---|
| `GET/POST /api/v1/synthetic/kde/fit` | Route yok — `/generate` endpoint'i `generator_type` discriminator kullanıyor |
| `GET/POST /api/v1/synthetic/kde/generate` | Route yok — aynı sebep |
| `POST /api/v1/synthetic/ctgan/train` | Route yok — CTGAN `/generate` içinde işleniyor |
| `POST /api/v1/synthetic/ctgan/generate` | Route yok — aynı sebep |
| `GET /api/v1/synthetic/quality` | Yol yanlış — backend `/quality-check` olarak kayıtlı |
| `POST /api/v1/synthetic/banking/generate` | Yol yanlış — backend `/banking-dataset` olarak kayıtlı |
| `POST /api/v1/ai/nl-test/suggestions` | Yol yanlış — backend `/nl-test/suggest/{endpoint_id}` (parametreli) |

**Gerekli aksiyon:** Frontend hook'larını mevcut `/generate` endpoint'ine `generator_type` ile yönlendir; URL uyuşmazlıklarını düzelt.

---

### 6. Tester Sayfası — Ham `fetch()` ve Sessiz Hata Yutma

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/tester/page.tsx` (satır 139–143)

Bu sayfa, paylaşılan `apiFetch` yardımcısı yerine doğrudan `fetch()` kullanmaktadır. Hata işleme yalnızca `if (res.ok) setCases(...)` şeklindedir; başarısız yanıtlar sessizce yutulmaktadır.

**Gerekli aksiyon:** `fetch()` → `apiFetch`, hata state'i ekle.

---

## Orta Öncelikli Eksiklikler

### 7. Tasarım Tekniği Şablonları — localStorage ile Sınırlı

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/design/_components/DesignTechniqueShell.tsx` (satır 79)

BVA, EQ ve DT şablonları `templateKey` localStorage anahtarına kaydedilmektedir. Ekip üyeleri arasında paylaşılamaz.

---

### 8. Raporlar Sayfası — Sahte Trend Verisi

**Dosya:** `apps/web/app/(dashboard)/p/[projectId]/management/reports/page.tsx` (satır 1162)

`trendData` dizisi `[62, 68, 71, 65, 74, 78, Math.round(passRate)]` şeklinde hardcode edilmiştir. İlk 6 değer statik sabitlerdir.

---

### 9. Sıfır-API Sayfaları

| Sayfa | localStorage Çağrısı | API Çağrısı |
|---|---|---|
| `management/settings/page.tsx` | 10 | 0 |
| `scenarios/page.tsx` | 4 | 0 |
| `scenarios/new/page.tsx` | 2 | 0 |
| `nexus-code/page.tsx` | 2 | 0 |
| `monkey/page.tsx` | 2 | 0 |
| `dashboards/page.tsx` | 1 | 0 |
| `design/DesignTechniqueShell.tsx` | 3 | 0 |

---

## Bölüm Bazlı Durum Tablosu

| Bölüm | Tamamlanma % | Kritik Sorun | Mock/localStorage | API Bağlantısı |
|---|---|---|---|---|
| Test Case CRUD (workspace) | %100 | Yok | Yok | Tam |
| Run Execution | %100 | Yok | Yok | Tam |
| Defect Management | %100 | Yok | Yok | Tam |
| Plans / Cycles | %100 | Yok | Yok | Tam |
| Regression Sets | %100 | Yok | Yok | Tam |
| Reports (raporlama) | %90 | Trend sabit veri | Kısmi | Büyük ölçüde bağlı |
| Import / Export | %95 | Yok | Yok | Tam |
| AI Design (BVA/EQ/DT/Gherkin) | %80 | Şablon localStorage | localStorage şablonlar | AI çağrıları bağlı |
| SSO / SAML Entegrasyonu | %5 | Test her zaman başarılı | Tam localStorage | Yok |
| Webhook Bildirimleri | %5 | Veri kaybolabilir | Tam localStorage | Yok |
| CI/CD Webhook Testi | %40 | CORS engeli | Kısmi | Proxy eksik |
| API Keys Yönetimi | %10 | Sunucu kaydı yok | Tam localStorage | Yok |
| Tester Sayfası | %60 | Sessiz hata yutma | Yok | Kırık fetch |
| Sentetik Veri (KDE/CTGAN) | %30 | 7 kopuk route | Yok | Route uyuşmazlığı |
| Scenarios / Nexus-Code | %10 | Tam stub | Tam localStorage | Yok |
| Dashboard (proje bazlı) | %15 | Tam stub | localStorage | Yok |

---

## Mock / LocalStorage Bağımlılık Haritası

Toplamda **14 dosyada 43 localStorage kullanımı** tespit edilmiştir. **8 adedi sıfır API çağrısına sahiptir.**

```
management/settings/page.tsx     ████████████████████  10 ls / 0 API  ← En kritik
integrations/page.tsx            ████████              4 ls / 4 API   ← Karma
design/DesignTechniqueShell.tsx  ██████                3 ls / 0 API
onboarding/page.tsx              ██████                5 ls / 4 API   ← Karma
scenarios/page.tsx               ████                  4 ls / 0 API
notifications/page.tsx           ██████                3 ls / 3 API   ← Karma
scenarios/new/page.tsx           ████                  2 ls / 0 API
nexus-code/page.tsx              ████                  2 ls / 0 API
monkey/page.tsx                  ████                  2 ls / 0 API
dashboards/page.tsx              ██                    1 ls / 0 API
```

> **Not:** `use-management-project-id.ts` hook'u projectId önbellekleme için localStorage kullanmaktadır (5 kullanım). Bu tasarım gereğidir; sorun değildir.

---

## Frontend Olgunluk Skoru: 67 / 100

| Boyut | Puan | Açıklama |
|---|---|---|
| **Sayfa Tamamlanma** | 18 / 25 | Çekirdek CRUD sayfaları tamamdır; SSO, API keys, senaryolar stub'dır |
| **API Bağlantısı** | 17 / 25 | 7 kopuk route, 3 UI-only stub, 8 sıfır-API sayfası |
| **Hata İşleme** | 15 / 25 | Sessiz hata yutma, daima-başarılı SSO testi, uyarısız eski veri fallback |
| **UX Kalitesi** | 17 / 25 | Çekirdek sayfalar kullanışlı; entegrasyon panelleri yanıltıcı geri bildirim veriyor |

---

## Düzeltme Öncelik Sırası

1. SSO konfigürasyonunu backend'e taşı (güvenlik + kullanıcı güveni)
2. Webhook bildirim CRUD endpoint'i oluştur (ekip verisi tarayıcıda kaybolmamalı)
3. Sentetik veri route uyuşmazlıklarını düzelt (7 kopuk çağrı, tek PR)
4. API Keys için backend endpoint oluştur
5. Tester sayfasını `apiFetch` ile yeniden yaz
6. CI/CD webhook testini backend proxy üzerinden yönlendir
7. Raporlar trend verisini gerçek API'ye bağla
8. Tasarım şablonlarını backend'e taşı
