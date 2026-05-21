# BGTS Test Dönüşüm — Smoke Test & Release Kontrol Listesi

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kullanım:** Her release/deployment öncesi ve sonrası bu listeler çalıştırılmalıdır.

---

## 1. Pre-Release Smoke Test Checklist (10 dakika)

> Her deployment öncesi bu 25 maddelik listeyi hızla geçin. Herhangi biri FAIL olursa release durdurulur.

### Altyapı Sağlık Kontrolleri

| # | Test | Komut/Adım | Pass/Fail |
|---|------|-----------|-----------|
| S-01 | Backend health check | `curl http://localhost:8000/health` → `{"status":"healthy"}` | ☐ |
| S-02 | PostgreSQL bağlantısı | `docker exec bgts_postgres pg_isready` | ☐ |
| S-03 | Redis bağlantısı | `docker exec bgts_redis redis-cli ping` → `PONG` | ☐ |
| S-04 | Frontend erişim | `curl -s http://localhost:3000 | head -1` → HTML | ☐ |
| S-05 | Swagger UI erişim | `curl -s http://localhost:8000/docs` → HTML | ☐ |

### Authentication

| # | Test | Adım | Pass/Fail |
|---|------|------|-----------|
| S-06 | Admin login API | POST `/auth/login` → 200 + token | ☐ |
| S-07 | Admin login UI | `/login` → e-posta/parola → `/projects` yönlendirme | ☐ |
| S-08 | Token ile /me erişimi | GET `/auth/me` → kullanıcı bilgileri | ☐ |
| S-09 | Hatalı parola reddi | POST `/auth/login` yanlış → 401 | ☐ |

### CRUD Operasyonları

| # | Test | Adım | Pass/Fail |
|---|------|------|-----------|
| S-10 | Proje oluşturma | POST `/tspm/projects` → 201 | ☐ |
| S-11 | Proje listeleme | GET `/tspm/projects` → array | ☐ |
| S-12 | Senaryo oluşturma | POST `.../scenarios` → 201 | ☐ |
| S-13 | Senaryo listeleme | GET `.../scenarios` → array | ☐ |
| S-14 | Senaryo güncelleme | PUT `.../scenarios/{id}` → 200, version++ | ☐ |
| S-15 | Koşu oluşturma | POST `.../executions` → 201, status:running | ☐ |

### İleri Özellikler

| # | Test | Adım | Pass/Fail |
|---|------|------|-----------|
| S-16 | Dashboard metrikleri | GET `.../dashboard` → tüm alanlar dolu | ☐ |
| S-17 | Gereksinim oluşturma | POST `.../requirements` → 201 | ☐ |
| S-18 | Coverage matrix | GET `.../coverage-matrix` → hesaplama doğru | ☐ |
| S-19 | Regresyon seti oluşturma | POST `.../regression-sets` → 201 | ☐ |
| S-20 | Akış oluşturma | POST `.../flows` → 201 | ☐ |

### UI Temel Kontroller

| # | Test | Adım | Pass/Fail |
|---|------|------|-----------|
| S-21 | Sidebar navigasyon | Tüm 14 menü linki görünür ve tıklanabilir | ☐ |
| S-22 | Proje sayfası | `/projects` → proje kartları yüklenir | ☐ |
| S-23 | Senaryo sayfası | `.../scenarios` → liste yüklenir | ☐ |
| S-24 | Tema değiştirme | Dark/light toggle çalışır | ☐ |
| S-25 | Logout | Çıkış → login sayfasına yönlendirme | ☐ |

---

## 2. Post-Release Doğrulama (5 dakika)

| # | Test | Adım | Pass/Fail |
|---|------|------|-----------|
| P-01 | Health endpoint | 200 döner | ☐ |
| P-02 | Yeni kullanıcı login | Admin login başarılı | ☐ |
| P-03 | Mevcut veriler korunmuş | Eski projeler/senaryolar erişilebilir | ☐ |
| P-04 | Migration başarılı | `alembic current` → head revision | ☐ |
| P-05 | Error log kontrolü | Son 5 dakika container log'larında critical hata yok | ☐ |

---

## 3. Tam Regresyon Test Matrisi (Sprint Sonu)

### Öncelik P0 — Her Sprint (30 dakika)

| Alan | Test Sayısı | Testler |
|------|------------|---------|
| Auth | 5 | TC-0101, TC-0102, TC-0104, TC-0108, TC-0109 |
| Proje CRUD | 3 | TC-0201, TC-0202, TC-0206 |
| Senaryo CRUD | 4 | TC-0301, TC-0302, TC-0303, TC-0306 |
| Koşu | 3 | TC-0601, TC-0603, TC-0604 |
| Onay | 2 | TC-0502, TC-0503 |
| **Toplam P0** | **17** | |

### Öncelik P1 — Her 2 Sprint (45 dakika)

| Alan | Test Sayısı | Testler |
|------|------------|---------|
| BDD Üretimi | 3 | TC-0401, TC-0402, TC-0404 |
| Gereksinim/Kapsam | 4 | TC-1001, TC-1002, TC-1004, TC-1005 |
| Regresyon | 3 | TC-0901, TC-0902, TC-0904 |
| Zamanlama | 3 | TC-1101, TC-1102, TC-1103 |
| Test Verisi | 3 | TC-1201, TC-1202, TC-1203 |
| **Toplam P1** | **16** | |

### Öncelik P2 — Her Major Release (60 dakika)

| Alan | Test Sayısı |
|------|------------|
| Tüm boundary testleri | 16 |
| Akış editörü | 3 |
| Entegrasyonlar | 3 |
| API test | 4 |
| Proje üyeleri | 3 |
| Versiyonlama | 3 |
| Analitik | 3 |
| **Toplam P2** | **35** |

---

## 4. Release Go/No-Go Kriterleri

| Kriter | Eşik | Karar |
|--------|-------|-------|
| Smoke test pass rate | 100% | < 100% → NO-GO |
| P0 test pass rate | 100% | < 100% → NO-GO |
| P1 test pass rate | > 95% | < 90% → NO-GO |
| P2 test pass rate | > 90% | < 80% → Discuss |
| Güvenlik critical bulgu | 0 | > 0 → NO-GO |
| Performans degradasyonu | < 20% | > 50% → NO-GO |
| Open P0 bug | 0 | > 0 → NO-GO |
| Open P1 bug | < 3 | > 5 → Discuss |
