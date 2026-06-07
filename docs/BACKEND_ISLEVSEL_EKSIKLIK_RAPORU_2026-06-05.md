# Backend İşlevsel Eksiklik Raporu

**Tarih:** 5 Haziran 2026
**Kapsam:** Cortex AI Automation — Tüm Backend Domain'leri, AI/Engine, Güvenlik, Test Coverage, Bağlantı Analizi
**Hazırlayan:** 71 Ajan Otomatik Analiz (feature/qa-system-bootstrap branch)

---

## Yönetici Özeti

Analiz 54 backend domain'ini, AI Gateway ve Engine servislerini, güvenlik açıklarını, test coverage durumunu ve frontend-backend bağlantı tutarlılığını kapsamaktadır.

Sistem genel olarak olgun bir mimari sergiliyor; 469 test dosyası, gerçek iş mantığıyla dolu handler'lar ve kapsamlı domain yapısıyla üretim ortamına yakın bir seviyede. Ancak **11 domain'de kimlik doğrulama eksikliği**, **1 kritik SQL enjeksiyon açığı**, **1 yüksek öncelikli XSS açığı** ve **7 frontend-backend bağlantı kopukluğu** tespit edilmiştir.

**Backend Olgunluk Skoru: 71 / 100**

---

## Kritik Güvenlik Açıkları

### KRİTİK-1 — Kimlik Doğrulamasız SQL Enjeksiyonu

**Dosya:** `backend/app/engine/routes/banking.py:789–809`
**Ciddiyet:** Kritik

`POST /api/banking/db/query` endpoint'i hiçbir kimlik doğrulama bağımlılığı içermiyor. `Depends(get_current_user)` veya `_require_internal_auth` kullanılmıyor. Saldırgan, `conn_str` parametresi aracılığıyla sunucudaki herhangi bir SQLite dosyasını okuyabilir; `sql` parametresiyle de doğrudan SQL çalıştırabilir.

```python
# backend/app/engine/routes/banking.py:809
c.execute(f"{body.sql} LIMIT {body.limit}")
```

SELECT-prefix kontrolü, `SELECT ... UNION SELECT ...` gibi yapılarla kolayca atlatılabilir.

**Öneri:** Endpoint'e `_require_internal_auth` bağımlılığı ekle, `conn_str` değerini izin verilenler listesiyle kısıtla, parametreli sorgular kullan.

---

### YÜKSEK-1 — Depolanan XSS (Knowledge Base)

**Dosya:** `apps/web/app/(dashboard)/kb/[articleId]/page.tsx:100`
**Ciddiyet:** Yüksek

`renderMarkdown()` fonksiyonu DOMPurify veya sanitize-html olmadan çalışmaktadır.

```tsx
dangerouslySetInnerHTML={{ __html: renderMarkdown(article.body) }}
```

KB makale yazma yetkisine sahip herhangi bir kullanıcı, keyfi `<script>` tag'leri enjekte edebilir.

**Öneri:** `renderMarkdown()` çıktısını `DOMPurify.sanitize()` ile filtrele.

---

### YÜKSEK-2 — Proje Kapsamı Olmayan Cross-Project Veri Sızıntısı

**Dosya:** `backend/app/domains/agents/router.py`
**Ciddiyet:** Yüksek

`agents` domain'indeki 11 endpoint kimlik doğrulama içeriyor ancak proje düzeyinde yetkilendirme (`_require_scoped_project_id`) uygulamıyor.

| Endpoint | Risk |
|---|---|
| `GET /agents/llm-traces` | Cross-project LLM trace erişimi |
| `GET /agents/heal/stats` | Proje filtresi olmadan KnowledgeStore |
| `GET /agents/locator/stability` | Proje erişim kontrolü yok |
| `POST /agents/locator/improve` | Proje kapsamı dışında öneriler |
| `POST /agents/locator/pom/generate` | Proje kapsamı dışında POM oluşturma |
| `POST /agents/locator/predict` | Proje kapsamı dışında tahmin |
| `POST /agents/banking/run` | Paylaşımlı bellek içi durum |
| `GET /agents/pipeline/status` | Global pipeline durumu herkese açık |
| `GET /agents/pipeline/logs` | Global pipeline logları herkese açık |
| `GET /agents/pipeline/report` | Global pipeline raporu herkese açık |
| `POST /agents/pipeline/cancel` | Herhangi bir kullanıcı başkasının pipeline'ını iptal edebilir |

**Öneri:** Proje parametresi alan endpoint'lere `_require_scoped_project_id` ekle; pipeline/banking durumunu kullanıcı veya proje bazlı izole et.

---

### ORTA-1 — Kiracı Middleware SQL Enjeksiyonu Riski

**Dosya:** `backend/app/core/tenant_middleware.py:86`

```python
dbapi_connection.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
```

Ana middleware UUID doğrulaması yapıyor ancak `set_tenant_on_connect()` doğrudan çağrılabiliyor.

**Öneri:** UUID doğrulamasını `set_tenant_on_connect()` içine taşı.

---

### ORTA-2 — Knowledge Store WHERE Clause Enjeksiyonu

**Dosya:** `backend/app/domains/ai/knowledge_store.py:554`

```python
cur.execute(f"SELECT ... {where} LIMIT 200", params)
```

**Öneri:** WHERE clause oluşturmayı parametre bağlama ile refaktör et.

---

### ORTA-3 — Hardcoded Geliştirici Dosya Yolu (Üretim Kırılması)

**Dosya:** `backend/app/domains/ai/router.py:1192`

```python
base_path: str = "/Users/yasin_bulgan/Desktop/BGTS_Test_Donusum"
```

Bu yol hiçbir staging, CI veya üretim makinesinde mevcut olmayacak.

**Öneri:** `settings.BDD_BASE_PATH` çevre değişkeni ile değiştir.

---

### ORTA-4 — Çok İşlemli Ortamda Rate Limiter Bypass

**Dosya:** `ai-gateway/app/routes/ai_routes.py`, `backend/app/domains/ai/router.py`

In-process `deque` tabanlı rate limiter birden fazla uvicorn worker ile etkin limiti `N × yapılandırılmış değer` yapıyor.

**Öneri:** Redis destekli sliding window rate limiter.

---

## Stub ve Tamamlanmamış Endpoint'ler

Kapsamlı analiz boyunca gerçek `NotImplementedError` veya boş handler stub'ı **bulunamadı**. Tüm `pass` kullanımları:
1. `except Exception: pass` — cache hatası baskılama (tasarım gereği)
2. `except ImportError: pass` — opsiyonel bağımlılık fallback
3. WebSocket `WebSocketDisconnect` handler — kasıtlı no-op

**Mimari stub'lar (handler değil):**
- `backend/app/engine/core/ai_engine_extensions.py` — 12 satır, doldurulmamış uzantı noktası
- `backend/app/domains/automation_suite/service.py:85` — `_RunRegistry` in-memory depolama; SQL tablosuna geçiş gerekiyor

---

## Kimlik Doğrulama Eksikliği — Konsolide Liste

| Domain | Korumasız Endpoint Sayısı | En Kritik Risk |
|---|---|---|
| **events** | 3 | `publish_test_event` herkese açık |
| **ingestion** | 5 | `jira_webhook`, `confluence_webhook` yazma açık |
| **navigation** | 4 | Tüm kullanıcıların bookmark'larına erişim |
| **onboarding** | 4 | `DELETE /progress/{project_id}` herkese açık |
| **accessibility** | 2 | Analiz endpoint'leri public |
| **health** | 2 | `db_health` dahili bağlantı detayları sızdırıyor |
| **automation** | 1 | `/health` engine URL sızdırıyor |
| **pr_bot** | 2 | `/analyze` herkese açık |
| **quality** | 1 | `/quality/metrics` korumasız |

---

## Domain Bazlı Durum Tablosu

| Domain | Ciddiyet | Stub Sayısı | Auth Eksik | TODO | Genel Durum |
|---|---|---|---|---|---|
| **agents** | Yüksek | 0 | 11 endpoint | 0 | Proje izolasyonu yok |
| **ai** | Orta | 0 | 0 | 0 | Hardcoded geliştirici yolu |
| **ai_synthetic_data** | Düşük | 0 | 0 | 0 | Üretime hazır |
| **api_testing** | Düşük | 0 | 0 | 1 | SQLAlchemy2 sorgu incelemesi |
| **audit** | Düşük | 0 | 0 | 0 | Üretime hazır |
| **auth** | Düşük | 0 | 0 | 0 | Üretime hazır |
| **automation** | Orta | 0 | 1 (`/health`) | 0 | Engine URL sızıntısı |
| **automation_suite** | Düşük | 0 | 0 | 1 | In-memory run kaydı |
| **accessibility** | Orta | 0 | 2 endpoint | 0 | Gözden geçirilmeli |
| **collaboration** | Düşük | 1 (kasıtlı) | 0 | 0 | WS disconnect no-op normal |
| **events** | Yüksek | 0 | 3 endpoint | 0 | Tüm endpoint'ler korumasız |
| **health** | Orta | 0 | 2 endpoint | 0 | Dahili bilgi sızdırıyor |
| **ingestion** | Yüksek | 0 | 5 endpoint | 0 | Veri yazma/okuma açık |
| **marketplace** | Düşük | 0 | 0 | 0 | type: ignore tutarsızlığı |
| **migration** | Orta | 0 | — | 0 | HTTP endpoint kayıt dışı |
| **navigation** | Yüksek | 0 | 4 endpoint | 0 | Tüm bookmark'lara erişim |
| **onboarding** | Yüksek | 0 | 4 endpoint | 0 | Reset endpoint korumasız |
| **pr_bot** | Orta | 0 | 2 endpoint | 0 | Auth yok |
| **quality** | Orta | 0 | 1 endpoint | 0 | Metrics endpoint korumasız |
| **visual** | Düşük | 0 | 0 | 0 | Üretime hazır |

---

## Test Coverage Boşlukları

| Metrik | Değer |
|---|---|
| Toplam backend domain sayısı | 54 |
| Toplam backend test dosyası | 469 |
| Frontend test dosyası | 100 |
| E2E test spec'i | 34 |
| Integration test dosyası | 28 |

### Kritik Domain Coverage

| Domain | Test Dosyası | Durum |
|---|---|---|
| **ai** | 68 | Kapsamlı |
| **tspm** | 21 | Kapsamlı |
| **auth** | 10 | Kapsamlı |
| **cicd** | 10 | Kapsamlı |
| **billing** | 8 | Kapsamlı |
| **rbac** | 7 | Kapsamlı |
| **compliance** | 5 | Kapsamlı |
| **test_management** | 9 | Kapsamlı |
| **sso** | 1 | Kısmi — yetersiz |
| **organizations** | 0 | **Eksik — kritik** |

---

## AI/Engine Değerlendirmesi

### AI Gateway
- **Durum:** İşlevsel
- Provider fallback zinciri: Groq → Gemini → Ollama → g4f
- **Sorun 1:** In-process rate limiter — multi-worker bypass riski
- **Sorun 2:** `prometheus_client` opsiyonel; yüklü değilse metrics 503
- **Sorun 3:** `_INSECURE_INTERNAL_KEY_DEFAULT = 'bgts-internal-key-change-me'` hardcoded

### Engine
- **Durum:** İşlevsel
- Playwright AI test oluşturma tamamlanmış
- **Sorun:** Opsiyonel bağımlılık başarısızlıkları log'a yazılmıyor

### Backend AI Domain
- **Durum:** İşlevsel — 60+ dosya, ~23k satır
- Tüm `pass` ifadeleri exception handler fallback — stub değil

---

## Frontend-Backend Bağlantı Kopuklukları

Tamamı `use-synthetic-advanced.ts` hook'unda:

| Frontend Çağrısı | Backend Durumu | Kök Neden |
|---|---|---|
| `GET/POST /api/v1/synthetic/kde/fit` | Endpoint yok | KDE alt-rotaları oluşturulmamış |
| `GET/POST /api/v1/synthetic/kde/generate` | Endpoint yok | `/generate` + `generator_type` kullanılmalı |
| `POST /api/v1/synthetic/ctgan/train` | Endpoint yok | CTGAN `/generate` içine gömülü |
| `POST /api/v1/synthetic/ctgan/generate` | Endpoint yok | Aynı |
| `GET /api/v1/synthetic/quality` | `/quality-check` mevcut | URL isim uyumsuzluğu |
| `POST /api/v1/synthetic/banking/generate` | `/banking-dataset` mevcut | URL isim uyumsuzluğu |
| `POST /api/v1/ai/nl-test/suggestions` | `/nl-test/suggest/{endpoint_id}` mevcut | Path parametresi uyumsuzluğu |

---

## Backend Olgunluk Skoru: 71 / 100

| Boyut | Puan | Açıklama |
|---|---|---|
| **API Tamamlanma** | 20 / 25 | Handler stub yok; 7 bağlantı kopukluğu, in-memory RunRegistry, kayıt dışı migration router |
| **Güvenlik** | 15 / 25 | 1 kritik SQL injection, 1 XSS, 9 domain'de auth eksikliği, rate limiter bypass, tenant middleware riski |
| **Test Coverage** | 21 / 25 | 469 dosya güçlü; organizations sıfır test, sso yetersiz |
| **Kod Kalitesi** | 15 / 25 | Hardcoded geliştirici yolu, hardcoded iç auth anahtarı, sessiz bağımlılık başarısızlıkları, type: ignore kullanımı |

---

## Öncelikli Aksiyon Planı

### Acil (Üretim Öncesi Zorunlu)

1. `backend/app/engine/routes/banking.py` — `_require_internal_auth` ekle, parametreli sorgular kullan
2. `backend/app/domains/agents/router.py` — 11 endpoint'e `_require_scoped_project_id` ekle
3. `backend/app/domains/events/router.py` — Tüm endpoint'lere `get_current_user` ekle
4. `backend/app/domains/ingestion/router.py` — Tüm endpoint'lere `get_current_user` ekle
5. `backend/app/domains/navigation/router.py` — Token doğrulaması ekle
6. `backend/app/domains/onboarding/router.py` — Auth ekle, reset endpoint admin-gate ile koru
7. `apps/web/app/(dashboard)/kb/[articleId]/page.tsx` — DOMPurify sanitizasyonu ekle

### Kısa Vadeli (Sprint İçi)

8. `backend/app/domains/ai/router.py:1192` — Hardcoded yolu `settings.BDD_BASE_PATH` ile değiştir
9. AI Gateway + backend AI domain — Redis destekli rate limiter geçişi
10. `backend/app/core/tenant_middleware.py:86` — UUID doğrulamasını fonksiyon içine taşı
11. `apps/web/lib/hooks/use-synthetic-advanced.ts` — 7 kopuk API çağrısını düzelt

### Orta Vadeli

12. `backend/app/domains/organizations/` için test suite oluştur
13. `backend/app/domains/sso/` test kapsamasını genişlet
14. `backend/app/domains/automation_suite/service.py` — `_RunRegistry`'yi SQL tablosuna taşı
15. `backend/app/engine/core/ai_engine_extensions.py` — Uzantı noktasını tanımla veya kaldır
