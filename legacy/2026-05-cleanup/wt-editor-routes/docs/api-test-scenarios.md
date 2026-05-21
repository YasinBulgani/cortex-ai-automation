# BGTS Test Donusum - API Test Senaryo Raporu

**Tarih:** 2026-04-03
**Oluşturan:** API & Service Scenario Generation Agent
**Kapsam:** FastAPI Backend (89 endpoint) + Flask Engine (95 endpoint) = **184 endpoint**

---

## 1. ENDPOINT ENVANTERİ

### 1.1 FastAPI Backend (`localhost:8000`)

#### Root Endpoints (Auth: YOK)

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 1 | GET | `/health` | Sağlık kontrolü |
| 2 | GET | `/ready` | Hazırlık kontrolü (DB bağlantısı dahil) |

#### Auth Endpoints (`/api/v1/auth`) — Auth: Belirtildi

| # | Method | Path | Auth | Açıklama |
|---|--------|------|------|----------|
| 3 | POST | `/api/v1/auth/login` | Yok | Kullanıcı girişi (JWT) |
| 4 | GET | `/api/v1/auth/me` | JWT | Mevcut kullanıcı bilgisi |

#### Catalog / Datasets (`/api/v1/datasets`) — Auth: JWT

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 5 | GET | `/api/v1/datasets` | Dataset listesi |
| 6 | POST | `/api/v1/datasets` | Dataset oluştur |
| 7 | GET | `/api/v1/datasets/{dataset_id}` | Dataset detay |
| 8 | POST | `/api/v1/datasets/{dataset_id}/versions` | Version oluştur |
| 9 | GET | `/api/v1/datasets/{dataset_id}/versions` | Version listesi |
| 10 | GET | `/api/v1/datasets/{dataset_id}/versions/{version_id}/schema` | Schema snapshot |

#### Rules (`/api/v1/datasets`) — Auth: JWT

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 11 | GET | `/api/v1/datasets/{dataset_id}/rule-sets` | Kural seti listesi |
| 12 | POST | `/api/v1/datasets/{dataset_id}/rule-sets` | Kural seti oluştur |
| 13 | GET | `/api/v1/datasets/{dataset_id}/rule-sets/{rule_set_id}` | Kural seti detay |

#### Jobs (`/api/v1/jobs`) — Auth: JWT

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 14 | GET | `/api/v1/jobs` | İş listesi (limit query param) |
| 15 | POST | `/api/v1/jobs` | İş kuyruğuna ekle |
| 16 | GET | `/api/v1/jobs/{job_id}` | İş detay |
| 17 | GET | `/api/v1/jobs/{job_id}/events` | İş olayları |
| 18 | GET | `/api/v1/jobs/{job_id}/artifacts` | İş artifaktları |

#### Artifacts (`/api/v1/artifacts`) — Auth: JWT

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 19 | GET | `/api/v1/artifacts/{artifact_id}/download` | Artifakt indir |

#### TSPM — Projects (`/api/v1/tspm`) — Auth: JWT

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 20 | GET | `/api/v1/tspm/projects` | Proje listesi |
| 21 | POST | `/api/v1/tspm/projects` | Proje oluştur |
| 22 | GET | `/api/v1/tspm/projects/{pid}/dashboard` | Dashboard istatistikleri |

#### TSPM — Scenarios

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 23 | GET | `/api/v1/tspm/projects/{pid}/scenarios` | Senaryo listesi (q arama) |
| 24 | POST | `/api/v1/tspm/projects/{pid}/scenarios` | Senaryo oluştur |
| 25 | GET | `/api/v1/tspm/projects/{pid}/scenarios/{sid}` | Senaryo detay |
| 26 | PUT | `/api/v1/tspm/projects/{pid}/scenarios/{sid}` | Senaryo güncelle |
| 27 | POST | `/api/v1/tspm/projects/{pid}/scenarios/generate-bdd` | BDD senaryo üret (AI) |
| 28 | POST | `/api/v1/tspm/projects/{pid}/scenarios/save-bdd` | BDD senaryoları kaydet |
| 29 | POST | `/api/v1/tspm/projects/{pid}/scenarios/bulk-delete` | Toplu senaryo sil |

#### TSPM — Requirements & Coverage

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 30 | POST | `/api/v1/tspm/projects/{pid}/requirements` | Gereksinim oluştur |
| 31 | GET | `/api/v1/tspm/projects/{pid}/requirements` | Gereksinim listesi |
| 32 | PUT | `/api/v1/tspm/projects/{pid}/requirements/{rid}` | Gereksinim güncelle |
| 33 | DELETE | `/api/v1/tspm/projects/{pid}/requirements/{rid}` | Gereksinim sil |
| 34 | POST | `/api/v1/tspm/projects/{pid}/scenarios/{sid}/requirements` | Senaryo-gereksinim bağla |
| 35 | DELETE | `/api/v1/tspm/projects/{pid}/scenarios/{sid}/requirements/{rid}` | Bağlantı kaldır |
| 36 | GET | `/api/v1/tspm/projects/{pid}/coverage-matrix` | Kapsam matrisi |
| 37 | GET | `/api/v1/tspm/projects/{pid}/coverage-gaps` | Kapsam boşlukları |

#### TSPM — Scenario Versions

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 38 | GET | `/api/v1/tspm/projects/{pid}/scenarios/{sid}/versions` | Versiyon listesi |
| 39 | GET | `/api/v1/tspm/projects/{pid}/scenarios/{sid}/versions/{v1}/diff/{v2}` | Versiyon diff |

#### TSPM — Executions

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 40 | GET | `/api/v1/tspm/projects/{pid}/executions` | Execution listesi |
| 41 | POST | `/api/v1/tspm/projects/{pid}/executions` | Execution başlat |
| 42 | GET | `/api/v1/tspm/projects/{pid}/executions/{run_id}` | Execution detay |
| 43 | PATCH | `/api/v1/tspm/projects/{pid}/executions/{run_id}/results/{result_id}` | Sonuç durumu güncelle |
| 44 | POST | `/api/v1/tspm/projects/{pid}/executions/{run_id}` | Yeniden çalıştır |

#### TSPM — Trends & Stats

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 45 | GET | `/api/v1/tspm/projects/{pid}/execution-trends` | Execution trendleri (days param) |
| 46 | GET | `/api/v1/tspm/projects/{pid}/execution-stats` | Execution istatistikleri |
| 47 | GET | `/api/v1/tspm/projects/{pid}/flaky-tests` | Flaky test listesi |

#### TSPM — Flows

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 48 | GET | `/api/v1/tspm/projects/{pid}/flows` | Flow listesi |
| 49 | POST | `/api/v1/tspm/projects/{pid}/flows` | Flow oluştur |
| 50 | GET | `/api/v1/tspm/projects/{pid}/flows/{fid}` | Flow detay |
| 51 | PUT | `/api/v1/tspm/projects/{pid}/flows/{fid}/graph` | Flow graph güncelle |

#### TSPM — Regression Sets

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 52 | GET | `/api/v1/tspm/projects/{pid}/regression-sets` | Regresyon seti listesi |
| 53 | POST | `/api/v1/tspm/projects/{pid}/regression-sets` | Regresyon seti oluştur |
| 54 | GET | `/api/v1/tspm/projects/{pid}/regression-sets/{set_id}` | Regresyon seti detay |
| 55 | POST | `/api/v1/tspm/projects/{pid}/regression-sets/{set_id}/add` | Senaryoları ekle |
| 56 | POST | `/api/v1/tspm/projects/{pid}/regression-sets/suggest` | AI tabanlı öneri |
| 57 | POST | `/api/v1/tspm/projects/{pid}/regression-sets/accept-suggestions` | Önerileri kabul et |

#### TSPM — Approvals

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 58 | GET | `/api/v1/tspm/projects/{pid}/approvals` | Onay listesi |
| 59 | POST | `/api/v1/tspm/projects/{pid}/approvals/{aid}/decide` | Onay kararı ver |

#### TSPM — Imports

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 60 | POST | `/api/v1/tspm/projects/{pid}/imports` | Import oluştur |

#### TSPM — Schedules

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 61 | POST | `/api/v1/tspm/projects/{pid}/schedules` | Zamanlama oluştur |
| 62 | GET | `/api/v1/tspm/projects/{pid}/schedules` | Zamanlama listesi |
| 63 | PUT | `/api/v1/tspm/projects/{pid}/schedules/{sch_id}` | Zamanlama güncelle |
| 64 | DELETE | `/api/v1/tspm/projects/{pid}/schedules/{sch_id}` | Zamanlama sil |
| 65 | POST | `/api/v1/tspm/projects/{pid}/schedules/{sch_id}/trigger` | Zamanlamayı tetikle |

#### TSPM — Test Data

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 66 | POST | `/api/v1/tspm/projects/{pid}/test-data` | Test verisi oluştur |
| 67 | GET | `/api/v1/tspm/projects/{pid}/test-data` | Test verisi listesi |
| 68 | PUT | `/api/v1/tspm/projects/{pid}/test-data/{did}` | Test verisi güncelle |
| 69 | DELETE | `/api/v1/tspm/projects/{pid}/test-data/{did}` | Test verisi sil |
| 70 | POST | `/api/v1/tspm/projects/{pid}/scenarios/{sid}/bind-data` | Veri bağla |
| 71 | GET | `/api/v1/tspm/projects/{pid}/scenarios/{sid}/expanded` | Genişletilmiş senaryo |

#### TSPM — Integrations

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 72 | POST | `/api/v1/tspm/projects/{pid}/integrations` | Entegrasyon oluştur |
| 73 | GET | `/api/v1/tspm/projects/{pid}/integrations` | Entegrasyon listesi |
| 74 | PUT | `/api/v1/tspm/projects/{pid}/integrations/{int_id}` | Entegrasyon güncelle |
| 75 | DELETE | `/api/v1/tspm/projects/{pid}/integrations/{int_id}` | Entegrasyon sil |
| 76 | POST | `/api/v1/tspm/projects/{pid}/integrations/{int_id}/sync` | Senkronize et |

#### TSPM — API Testing

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 77 | POST | `/api/v1/tspm/projects/{pid}/api-tests/collections` | Koleksiyon oluştur |
| 78 | GET | `/api/v1/tspm/projects/{pid}/api-tests/collections` | Koleksiyon listesi |
| 79 | GET | `/api/v1/tspm/projects/{pid}/api-tests/collections/{cid}` | Koleksiyon detay |
| 80 | DELETE | `/api/v1/tspm/projects/{pid}/api-tests/collections/{cid}` | Koleksiyon sil |
| 81 | POST | `/api/v1/tspm/projects/{pid}/api-tests/collections/{cid}/requests` | Request oluştur |
| 82 | GET | `/api/v1/tspm/projects/{pid}/api-tests/collections/{cid}/requests` | Request listesi |
| 83 | PUT | `/api/v1/tspm/projects/{pid}/api-tests/collections/{cid}/requests/{req_id}` | Request güncelle |
| 84 | DELETE | `/api/v1/tspm/projects/{pid}/api-tests/collections/{cid}/requests/{req_id}` | Request sil |
| 85 | POST | `/api/v1/tspm/projects/{pid}/api-tests/collections/{cid}/run` | Koleksiyon çalıştır |
| 86 | GET | `/api/v1/tspm/projects/{pid}/api-tests/runs` | Test run listesi |
| 87 | GET | `/api/v1/tspm/projects/{pid}/api-tests/runs/{run_id}` | Test run detay |

#### TSPM — Members

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 88 | POST | `/api/v1/tspm/projects/{pid}/members` | Üye ekle |
| 89 | GET | `/api/v1/tspm/projects/{pid}/members` | Üye listesi |
| 90 | DELETE | `/api/v1/tspm/projects/{pid}/members/{mid}` | Üye kaldır |

#### Notifications (WebSocket)

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 91 | WS | `/api/v1/ws/notifications` | WebSocket (token query param) |

---

### 1.2 Flask Engine (`localhost:5001`)

#### Core & Health

| # | Method | Path | Auth | Açıklama |
|---|--------|------|------|----------|
| 1 | GET | `/health` | Yok | Sağlık kontrolü |
| 2 | GET | `/` | Session | Ana sayfa |
| 3 | GET | `/ui/<filename>` | Yok | UI statik dosyaları |
| 4 | GET | `/reports/allure-report/<filename>` | Yok | Allure rapor dosyaları |
| 5 | GET | `/reports/allure-report/` | Yok | Allure ana sayfa |

#### Auth

| # | Method | Path | Auth | Açıklama |
|---|--------|------|------|----------|
| 6 | GET | `/login` | Yok | Login sayfası |
| 7 | POST | `/api/auth/register` | Yok | Kayıt |
| 8 | POST | `/api/auth/login` | Yok | Giriş (session-based) |
| 9 | GET | `/api/auth/verify/<token>` | Yok | E-posta doğrulama |
| 10 | POST | `/api/auth/logout` | Session | Çıkış |

#### Features

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 11 | GET | `/api/features` | Feature listesi (ağaç yapısı) |
| 12 | POST | `/api/features/folder` | Klasör oluştur |
| 13 | DELETE | `/api/features/folder` | Klasör sil |
| 14 | GET | `/api/features/<name>` | Feature detay |
| 15 | PUT | `/api/features/<name>` | Feature kaydet |
| 16 | DELETE | `/api/features/<name>` | Feature sil |

#### Regression

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 17 | GET | `/api/regression-sets` | Regresyon seti listesi |
| 18 | POST | `/api/regression-sets` | Regresyon seti oluştur |
| 19 | DELETE | `/api/regression-sets/<set_id>` | Regresyon seti sil |
| 20 | POST | `/api/regression-sets/<set_id>/features` | Feature ekle |
| 21 | DELETE | `/api/regression-sets/<set_id>/features/<name>` | Feature kaldır |

#### Manual Tests

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 22 | GET | `/api/manual-tests` | Manuel test listesi |
| 23 | POST | `/api/manual-tests` | Manuel test oluştur |
| 24 | DELETE | `/api/manual-tests/<test_id>` | Manuel test sil |
| 25 | PUT | `/api/manual-tests/<test_id>` | Durum güncelle |
| 26 | POST | `/api/manual-tests/<test_id>/steps` | Adım ekle |
| 27 | DELETE | `/api/manual-test-steps/<step_id>` | Adım sil |
| 28 | PUT | `/api/manual-test-steps/<step_id>` | Adım durumu güncelle |
| 29 | POST | `/api/generate-manual-from-doc` | Döküman'dan test üret |

#### Locators

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 30 | GET | `/api/locators` | Locator listesi |
| 31 | POST | `/api/locators` | Locator kaydet |
| 32 | DELETE | `/api/locators/<loc_id>` | Locator sil |
| 33 | POST | `/api/discover` | Sayfa keşfet (AI + Playwright) |

#### Runner

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 34 | POST | `/api/run` | Test çalıştır |
| 35 | GET | `/api/run/<run_id>/stream` | SSE stream |
| 36 | POST | `/api/run-maven` | Maven test çalıştır |
| 37 | POST | `/api/projects/create` | Proje oluştur |
| 38 | GET | `/api/projects/list` | Proje listesi |
| 39 | GET | `/api/projects/files/<name>` | Proje dosya ağacı |
| 40 | GET | `/api/projects/read-file` | Dosya oku |
| 41 | POST | `/api/projects/setup` | Sistem kurulum |
| 42 | POST | `/api/projects/start-services` | Servisleri başlat |
| 43 | GET | `/api/projects/status` | Sistem durumu |

#### AI

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 44 | POST | `/api/generate-feature` | Gherkin üret (AI) |
| 45 | POST | `/api/analyze-api-request` | API analiz (AI) |
| 46 | POST | `/api/security-scan` | Güvenlik taraması |
| 47 | POST | `/api/inspect` | Playwright inspector |

#### Utility

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 48 | GET | `/api/settings` | Ayarları getir |
| 49 | POST | `/api/settings` | Ayarları kaydet |
| 50 | GET | `/api/stats` | İstatistikler |
| 51 | GET | `/api/reports/comprehensive` | Kapsamlı rapor |
| 52 | GET | `/api/health` | Sağlık kontrolü |
| 53 | POST | `/api/request` | Proxy request |
| 54 | GET | `/api/export` | Dışa aktar (ZIP) |

#### DataSim

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 55 | GET | `/api/datasim/datasets` | Dataset kataloğu |
| 56 | POST | `/api/datasim/datasets/load` | Dataset yükle |
| 57 | GET | `/api/datasim/check-install` | Kurulum kontrolü |
| 58 | POST | `/api/datasim/install` | Paket kur (SSE) |
| 59 | POST | `/api/datasim/generate` | Sentetik veri üret (SSE) |
| 60 | GET | `/api/datasim/sqlite/catalog` | DB kataloğu |
| 61 | POST | `/api/datasim/sqlite/tables` | Tablo listesi |
| 62 | POST | `/api/datasim/sqlite/preview` | Tablo önizleme |
| 63 | POST | `/api/datasim/sqlite/learn` | DB'den öğren (SSE) |

#### Project Management

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 64 | GET | `/api/projects` | Proje listesi (gelişmiş) |
| 65 | POST | `/api/projects/create` | Proje oluştur |
| 66 | POST | `/api/projects/open` | Proje aç |
| 67 | GET | `/api/projects/<name>` | Proje detay |
| 68 | DELETE | `/api/projects/<name>/delete` | Proje sil |

#### Lifecycle

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 69 | POST | `/api/lifecycle/process-analyst` | Süreç analizi (AI) |
| 70 | POST | `/api/lifecycle/save` | Akış kaydet |

#### Visual Testing

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 71 | GET | `/api/visual/baselines` | Baseline listesi |
| 72 | GET | `/api/visual/baselines/<domain>/<test_name>` | Baseline detay |
| 73 | DELETE | `/api/visual/baselines/<domain>/<test_name>` | Baseline sil |
| 74 | POST | `/api/visual/baselines/upload` | Baseline yükle |
| 75 | POST | `/api/visual/compare` | Görsel karşılaştırma |
| 76 | POST | `/api/visual/compare/upload` | Yüklemeyle karşılaştır |
| 77 | POST | `/api/visual/batch` | Toplu karşılaştırma |
| 78 | POST | `/api/visual/diff-image` | Diff görüntü oluştur |

#### Accessibility

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 79 | POST | `/api/a11y/test` | Erişilebilirlik testi |
| 80 | POST | `/api/a11y/test/batch` | Toplu test |
| 81 | POST | `/api/a11y/report` | Rapor oluştur |
| 82 | GET | `/api/a11y/report/download` | Rapor indir |
| 83 | GET | `/api/a11y/rules` | Kural listesi |
| 84 | GET | `/api/a11y/config` | Yapılandırma getir |
| 85 | PUT | `/api/a11y/config` | Yapılandırma güncelle |

#### Recorder

| # | Method | Path | Açıklama |
|---|--------|------|----------|
| 86 | POST | `/api/recorder/start` | Kayıt başlat |
| 87 | POST | `/api/recorder/<session_id>/stop` | Kayıt durdur |
| 88 | GET | `/api/recorder/sessions` | Oturum listesi |
| 89 | DELETE | `/api/recorder/sessions/<file>` | Oturum sil |
| 90 | POST | `/api/recorder/<session_id>/action` | Aksiyon ekle |
| 91 | GET | `/api/recorder/<session_id>/actions` | Aksiyonları getir |
| 92 | POST | `/api/recorder/generate` | Kod üret |
| 93 | POST | `/api/recorder/generate/download` | Kod indir |
| 94 | GET | `/api/recorder/locators/<domain>` | Locator listesi |
| 95 | GET | `/api/recorder/locators/<domain>/<filename>` | Locator detay |

---

## 2. SERVICE SCENARIO MATRIX

### 2.1 Auth Senaryoları (FastAPI — JWT Based)

#### POST `/api/v1/auth/login`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| AUTH-001 | Pozitif | Geçerli email+password ile login | `{"email":"user@test.com","password":"test123"}` | 200, `access_token` döner |
| AUTH-002 | Negatif | Yanlış password | `{"email":"user@test.com","password":"wrong"}` | 401 Unauthorized |
| AUTH-003 | Negatif | Varolmayan email | `{"email":"nonexist@test.com","password":"x"}` | 401 Unauthorized |
| AUTH-004 | Negatif | Boş password | `{"email":"user@test.com","password":""}` | 422 Validation Error (min_length=1) |
| AUTH-005 | Negatif | Geçersiz email formatı | `{"email":"not-an-email","password":"x"}` | 422 Validation Error (EmailStr) |
| AUTH-006 | Negatif | Body boş gönderilir | `{}` | 422 Validation Error |
| AUTH-007 | Negatif | Body yok (Content-Type yanlış) | Raw text | 422 Validation Error |
| AUTH-008 | Boundary | Çok uzun email (256+ karakter) | `{"email":"a"*256+"@x.com","password":"x"}` | 422 veya 401 |
| AUTH-009 | Boundary | Çok uzun password (10000+ karakter) | Uzun string | Davranış testi |
| AUTH-010 | Exception | SQL injection denemesi | `{"email":"' OR 1=1--","password":"x"}` | 401, injection çalışmaz |
| AUTH-011 | Negatif | Inactive user girişi | Aktif olmayan kullanıcı | 403 Forbidden |

#### GET `/api/v1/auth/me`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| AUTH-012 | Pozitif | Geçerli JWT ile profil | Bearer token | 200, user bilgileri |
| AUTH-013 | Negatif | Token olmadan istek | Header yok | 401 |
| AUTH-014 | Negatif | Süresi dolmuş token | Expired JWT | 401 |
| AUTH-015 | Negatif | Geçersiz token formatı | `Bearer abc123` | 401 |
| AUTH-016 | Negatif | Farklı secret ile imzalı token | Manipüle edilmiş JWT | 401 |

---

### 2.2 Auth Senaryoları (Flask Engine — Session Based)

#### POST `/api/auth/register`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| EAUTH-001 | Pozitif | Geçerli kayıt | `{"email":"new@test.com","password":"pass123"}` | 200, success |
| EAUTH-002 | Negatif | Aynı email ile tekrar kayıt | Mevcut email | 400 duplicate |
| EAUTH-003 | Negatif | Email boş | `{"email":"","password":"x"}` | 400 missing fields |
| EAUTH-004 | Negatif | Password boş | `{"email":"x@x.com","password":""}` | 400 missing fields |
| EAUTH-005 | Negatif | Body boş | `{}` | 400 missing fields |

#### POST `/api/auth/login` (Engine)

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| EAUTH-006 | Pozitif | Geçerli giriş | `{"email":"user@test.com","password":"pass"}` | 200, session set |
| EAUTH-007 | Pozitif | Hardcoded bypass (test/test) | `{"email":"test","password":"test"}` | 200, session set |
| EAUTH-008 | Negatif | Yanlış password | Geçersiz şifre | 401 |
| EAUTH-009 | Negatif | Doğrulanmamış email | Unverified user | 403 |

---

### 2.3 Dataset / Catalog Senaryoları

#### POST `/api/v1/datasets`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| DS-001 | Pozitif | Geçerli dataset oluştur | `{"name":"TestDS","description":"açıklama"}` | 201, dataset döner |
| DS-002 | Pozitif | Description olmadan | `{"name":"TestDS"}` | 201, description=null |
| DS-003 | Negatif | Name boş | `{"name":""}` | 422 (min_length=1) |
| DS-004 | Negatif | Name eksik | `{"description":"x"}` | 422 required field |
| DS-005 | Boundary | Name 200 karakter (max sınır) | 200 char string | 201 başarılı |
| DS-006 | Boundary | Name 201 karakter (max aşımı) | 201 char string | 422 (max_length=200) |
| DS-007 | Boundary | Name 1 karakter (min sınır) | `{"name":"X"}` | 201 başarılı |
| DS-008 | Negatif | Auth olmadan istek | Token yok | 401 |
| DS-009 | Exception | Özel karakterler name'de | `{"name":"<script>alert(1)</script>"}` | 201 veya 422 |

#### POST `/api/v1/datasets/{dataset_id}/versions`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| DS-010 | Pozitif | Geçerli version oluştur | Geçerli snapshot v1 | 201 |
| DS-011 | Negatif | Boş snapshot | `{"snapshot":{}}` | 422 (validation) |
| DS-012 | Negatif | Geçersiz snapshot format | `{"snapshot":{"version":2}}` | 422 (version=1 zorunlu) |
| DS-013 | Negatif | Varolmayan dataset_id | UUID yok | 404 |
| DS-014 | Negatif | Duplicate field names in snapshot | Aynı isimli alanlar | 422 (unique_names validator) |
| DS-015 | Boundary | Geçersiz field name format | `name: "123abc"` | 422 (regex: `^[a-zA-Z_]`) |
| DS-016 | Boundary | Field name max 128 karakter | 128 char | Başarılı |
| DS-017 | Boundary | Field name 129 karakter | 129 char | 422 |

---

### 2.4 Rules Senaryoları

#### POST `/api/v1/datasets/{dataset_id}/rule-sets`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| RL-001 | Pozitif | Geçerli kural seti | `{"name":"Rules1","rules_body":"..."}` | 201 |
| RL-002 | Negatif | Name boş | `{"name":"","rules_body":"x"}` | 422 (min_length=1) |
| RL-003 | Negatif | rules_body boş | `{"name":"X","rules_body":""}` | 422 (min_length=1) |
| RL-004 | Boundary | Name 200 karakter | 200 chars | 201 |
| RL-005 | Boundary | Name 201 karakter | 201 chars | 422 |
| RL-006 | Negatif | Varolmayan dataset_id | UUID yok | 404 |

---

### 2.5 Jobs Senaryoları

#### POST `/api/v1/jobs`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| JB-001 | Pozitif | Geçerli job oluştur | `{"dataset_version_id":"uuid"}` | 202 Accepted |
| JB-002 | Pozitif | Rule set ile job | `{"dataset_version_id":"uuid","rule_set_id":"uuid"}` | 202 |
| JB-003 | Negatif | Varolmayan version_id | Geçersiz UUID | 404 |
| JB-004 | Negatif | Varolmayan rule_set_id | Geçersiz UUID | 400 |
| JB-005 | Negatif | dataset_version_id eksik | `{}` | 422 |

#### GET `/api/v1/jobs`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| JB-006 | Pozitif | Varsayılan limit (50) | Param yok | 200, max 50 kayıt |
| JB-007 | Boundary | limit=0 | `?limit=0` | 200, boş liste veya 422 |
| JB-008 | Boundary | limit=200 (max) | `?limit=200` | 200 |
| JB-009 | Boundary | limit=201 (max aşımı) | `?limit=201` | 422 veya 200 (clamp) |
| JB-010 | Negatif | limit negatif | `?limit=-1` | 422 |

---

### 2.6 TSPM Project Senaryoları

#### POST `/api/v1/tspm/projects`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| PRJ-001 | Pozitif | Geçerli proje oluştur | `{"name":"Proje A"}` | 201 |
| PRJ-002 | Pozitif | Description ile | `{"name":"A","description":"desc"}` | 201 |
| PRJ-003 | Negatif | Name boş | `{"name":""}` | 422 (min_length=1) |
| PRJ-004 | Negatif | Body boş | `{}` | 422 |

---

### 2.7 Scenario CRUD Senaryoları

#### POST `/api/v1/tspm/projects/{pid}/scenarios`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| SC-001 | Pozitif | Geçerli senaryo | `{"title":"Login testi"}` | 201 |
| SC-002 | Pozitif | Tüm alanlarla | `{"title":"X","description":"..","status":"draft","steps":[]}` | 201 |
| SC-003 | Negatif | Title boş | `{"title":""}` | 422 (min_length=1) |
| SC-004 | Negatif | Title eksik | `{}` | 422 |
| SC-005 | Negatif | Varolmayan project_id | Geçersiz UUID | 404 |
| SC-006 | Pozitif | Steps ile senaryo | `{"title":"X","steps":[{"action":"click"}]}` | 201 |

#### PUT `/api/v1/tspm/projects/{pid}/scenarios/{sid}`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| SC-007 | Pozitif | Title güncelle | `{"title":"Yeni Başlık"}` | 200 |
| SC-008 | Pozitif | Kısmi güncelleme | `{"status":"approved"}` | 200 |
| SC-009 | Negatif | Varolmayan scenario_id | Geçersiz UUID | 404 |

#### POST `/api/v1/tspm/projects/{pid}/scenarios/bulk-delete`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| SC-010 | Pozitif | Geçerli toplu silme | `{"ids":["uuid1","uuid2"]}` | 204 |
| SC-011 | Negatif | Boş IDs listesi | `{"ids":[]}` | 204 veya 422 |
| SC-012 | Negatif | Varolmayan ID'ler | `{"ids":["nonexistent"]}` | 204 veya 404 |

---

### 2.8 BDD Generation (AI) Senaryoları

#### POST `/api/v1/tspm/projects/{pid}/scenarios/generate-bdd`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| BDD-001 | Pozitif | Geçerli analiz text | `{"analysis_text":"Kullanıcı giriş yapabilmeli..."}` | 200, senaryolar |
| BDD-002 | Negatif | Kısa text (9 char) | `{"analysis_text":"kısa txt"}` | 422 (min_length=10) |
| BDD-003 | Boundary | Tam 10 karakter | `{"analysis_text":"1234567890"}` | 200 |
| BDD-004 | Negatif | Text boş | `{"analysis_text":""}` | 422 |
| BDD-005 | Exception | AI servisi kapalı | API key geçersiz | 500 veya hata mesajı |

---

### 2.9 Requirements & Coverage Senaryoları

#### POST `/api/v1/tspm/projects/{pid}/requirements`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| REQ-001 | Pozitif | Geçerli gereksinim | `{"external_id":"REQ-1","title":"Login"}` | 201 |
| REQ-002 | Negatif | external_id boş | `{"external_id":"","title":"X"}` | 422 (min_length=1) |
| REQ-003 | Negatif | title boş | `{"external_id":"R1","title":""}` | 422 (min_length=1) |
| REQ-004 | Pozitif | Priority ile | `{"external_id":"R1","title":"X","priority":"high"}` | 201 |

#### POST `/api/v1/tspm/projects/{pid}/scenarios/{sid}/requirements`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| REQ-005 | Pozitif | Geçerli bağlantı | `{"requirement_ids":["uuid"]}` | 201 |
| REQ-006 | Negatif | Boş liste | `{"requirement_ids":[]}` | 201 veya 422 |
| REQ-007 | Negatif | Varolmayan requirement | `{"requirement_ids":["fake"]}` | 404 |

---

### 2.10 Execution Senaryoları

#### POST `/api/v1/tspm/projects/{pid}/executions`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| EXE-001 | Pozitif | Boş execution başlat | `{}` | 201 |
| EXE-002 | Pozitif | Senaryo listesiyle | `{"scenario_ids":["uuid1","uuid2"]}` | 201 |
| EXE-003 | Negatif | Varolmayan project_id | Geçersiz UUID | 404 |

#### PATCH `.../executions/{run_id}/results/{result_id}`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| EXE-004 | Pozitif | Status güncelle | `{"status":"passed"}` | 200 |
| EXE-005 | Pozitif | Failed olarak işaretle | `{"status":"failed"}` | 200 |
| EXE-006 | Negatif | Geçersiz status değeri | `{"status":"bilinmeyen"}` | 200 veya 422 |
| EXE-007 | Negatif | Varolmayan result_id | Geçersiz UUID | 404 |

---

### 2.11 Schedule Senaryoları

#### POST `/api/v1/tspm/projects/{pid}/schedules`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| SCH-001 | Pozitif | Geçerli zamanlama | `{"name":"Daily","cron_expression":"0 9 * * *"}` | 201 |
| SCH-002 | Negatif | Name boş | `{"name":"","cron_expression":"x"}` | 422 |
| SCH-003 | Negatif | Cron boş | `{"name":"X","cron_expression":""}` | 422 |
| SCH-004 | Boundary | Geçersiz cron formatı | `{"name":"X","cron_expression":"invalid"}` | 201 (doğrulama yok) veya 400 |
| SCH-005 | Pozitif | Regression set ile | `{"name":"X","cron_expression":"0 * * * *","regression_set_id":"uuid"}` | 201 |

#### POST `.../schedules/{sch_id}/trigger`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| SCH-006 | Pozitif | Zamanlamayı tetikle | Body yok | 201, execution başlar |
| SCH-007 | Negatif | İnaktif zamanlama tetikle | is_active=false | 400 |
| SCH-008 | Negatif | Varolmayan schedule_id | Geçersiz UUID | 404 |

---

### 2.12 Integration Senaryoları

#### POST `/api/v1/tspm/projects/{pid}/integrations`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| INT-001 | Pozitif | Geçerli entegrasyon | `{"provider":"jira","config":{"url":"..."}}` | 201 |
| INT-002 | Negatif | Provider boş | `{"provider":""}` | 422 (min_length=1) |
| INT-003 | Negatif | Config hatası ile sync | Bozuk config | sync'te hata |

#### POST `.../integrations/{int_id}/sync`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| INT-004 | Pozitif | Geçerli senkronizasyon | Body yok | 200, synced_count |
| INT-005 | Negatif | Varolmayan entegrasyon | Geçersiz UUID | 404 |
| INT-006 | Exception | Harici servis kapalı | Provider unreachable | 500 veya hata mesajı |

---

### 2.13 API Testing Senaryoları

#### POST `.../api-tests/collections`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| APIT-001 | Pozitif | Koleksiyon oluştur | `{"name":"Smoke Tests"}` | 201 |
| APIT-002 | Negatif | Name boş | `{"name":""}` | 422 |
| APIT-003 | Pozitif | Base URL ile | `{"name":"X","base_url":"http://api.test"}` | 201 |

#### POST `.../api-tests/collections/{cid}/requests`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| APIT-004 | Pozitif | GET request ekle | `{"name":"HealthCheck","method":"GET","path":"/health"}` | 201 |
| APIT-005 | Pozitif | POST request + body | `{"name":"Login","method":"POST","path":"/auth","body":{...}}` | 201 |
| APIT-006 | Pozitif | Assertions ile | `{"name":"X","assertions":[{"type":"status","value":200}]}` | 201 |
| APIT-007 | Negatif | Name boş | `{"name":""}` | 422 |

#### POST `.../api-tests/collections/{cid}/run`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| APIT-008 | Pozitif | Koleksiyonu çalıştır | Body yok | 200, run results |
| APIT-009 | Negatif | Boş koleksiyonu çalıştır | 0 request | 200, boş sonuç |
| APIT-010 | Negatif | Varolmayan collection | Geçersiz UUID | 404 |

---

### 2.14 Visual Testing Senaryoları (Engine)

#### POST `/api/visual/compare`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| VIS-001 | Pozitif | Geçerli karşılaştırma | `{"test_name":"login","url":"http://.."}` | 200 |
| VIS-002 | Negatif | test_name eksik | `{"url":"http://.."}` | 400 |
| VIS-003 | Negatif | URL eksik | `{"test_name":"x"}` | 400 |
| VIS-004 | Boundary | threshold=0 | `{..,"threshold":0}` | 200 (her şey match) |
| VIS-005 | Boundary | threshold=1 | `{..,"threshold":1}` | 200 (pixel-perfect) |
| VIS-006 | Pozitif | Baseline güncelle | `{..,"update_baseline":true}` | 200 |

---

### 2.15 Accessibility Testing Senaryoları (Engine)

#### POST `/api/a11y/test`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| A11Y-001 | Pozitif | WCAG AA testi | `{"url":"http://..","wcag_level":"AA"}` | 200, score+violations |
| A11Y-002 | Pozitif | WCAG AAA testi | `{"url":"http://..","wcag_level":"AAA"}` | 200 |
| A11Y-003 | Negatif | URL boş | `{"url":""}` | 400 |
| A11Y-004 | Pozitif | Axe ile test | `{"url":"http://..","use_axe":true}` | 200 |
| A11Y-005 | Boundary | wait_ms=0 | `{"url":"http://..","wait_ms":0}` | 200 |
| A11Y-006 | Exception | Erişilemeyen URL | `{"url":"http://nonexistent.local"}` | 500 |

---

### 2.16 Recorder Senaryoları (Engine)

#### POST `/api/recorder/start`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| REC-001 | Pozitif | Kayıt başlat | `{"name":"login_flow"}` | 200, session_id |
| REC-002 | Negatif | Name boş | `{"name":""}` | 400 |
| REC-003 | Pozitif | Domain ile | `{"name":"x","domain":"prod"}` | 200 |

#### POST `/api/recorder/generate`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| REC-004 | Pozitif | Playwright kodu üret | `{"session_path":"x.json","format":"playwright"}` | 200, code |
| REC-005 | Pozitif | Cucumber kodu üret | `{"session_path":"x.json","format":"cucumber"}` | 200, code |
| REC-006 | Pozitif | POM Python | `{"session_path":"x.json","format":"pom_python"}` | 200, code |
| REC-007 | Pozitif | POM Java | `{"session_path":"x.json","format":"pom_java"}` | 200, code |
| REC-008 | Pozitif | Tüm formatlar | `{"session_path":"x.json","format":"all"}` | 200, files array |
| REC-009 | Negatif | Varolmayan session | `{"session_path":"fake.json"}` | 404 |
| REC-010 | Negatif | Bilinmeyen format | `{"session_path":"x.json","format":"unknown"}` | 400 |

---

### 2.17 DataSim Senaryoları (Engine)

#### POST `/api/datasim/generate`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| DSIM-001 | Pozitif | JSON formatında üret | `{"csv":"col1,col2\n1,2","count":100}` | SSE stream, done |
| DSIM-002 | Pozitif | CSV formatında üret | `{"csv":"...","format":"csv"}` | SSE stream, done |
| DSIM-003 | Negatif | Boş CSV | `{"csv":""}` | 400 |
| DSIM-004 | Boundary | count=1 (min) | `{"csv":"...","count":1}` | SSE, 1 satır |
| DSIM-005 | Boundary | count=5000 (max) | `{"csv":"...","count":5000}` | SSE, 5000 satır |
| DSIM-006 | Boundary | count=5001 (max aşımı) | `{"csv":"...","count":5001}` | Hata veya 5000'e clamp |

---

### 2.18 Engine AI Senaryoları

#### POST `/api/generate-feature`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| EAI-001 | Pozitif | Gherkin üret | `{"requirements":"Login senaryosu..."}` | 200, gherkin content |
| EAI-002 | Negatif | Requirements boş | `{}` | 400 |
| EAI-003 | Pozitif | URL ile üret | `{"requirements":"x","url":"http://..."}` | 200 |
| EAI-004 | Exception | AI API key yok/hatalı | Geçersiz config | 500 |

#### POST `/api/security-scan`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| EAI-005 | Pozitif | Güvenlik taraması | `{"url":"http://target.com"}` | 200, rapor |
| EAI-006 | Negatif | URL boş | `{"url":""}` | 400 |
| EAI-007 | Exception | Erişilemeyen hedef | `{"url":"http://unreachable"}` | 500 |

---

### 2.19 Proxy Request Senaryoları (Engine)

#### POST `/api/request`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| PRX-001 | Pozitif | GET proxy | `{"url":"http://httpbin.org/get"}` | 200, response |
| PRX-002 | Pozitif | POST proxy + body | `{"url":"...","method":"POST","body":"{}"}` | 200 |
| PRX-003 | Negatif | URL boş | `{"url":""}` | 400 |
| PRX-004 | Exception | Timeout hedef | `{"url":"http://10.255.255.1"}` | 500 |
| PRX-005 | Negatif | SSRF denemesi | `{"url":"http://localhost/admin"}` | Güvenlik kontrolü |
| PRX-006 | Negatif | File protocol | `{"url":"file:///etc/passwd"}` | 500 veya 400 |

---

### 2.20 Settings Senaryoları (Engine)

#### POST `/api/settings`

| ID | Tip | Senaryo | Input | Beklenen Sonuç |
|----|-----|---------|-------|----------------|
| SET-001 | Pozitif | Ayar güncelle | `{"BASE_URL":"http://new.url"}` | 200 |
| SET-002 | Pozitif | API key güncelle | `{"OPENAI_API_KEY":"sk-..."}` | 200 |
| SET-003 | Negatif | Session olmadan | Auth yok | 401 |
| SET-004 | Exception | .env yazma hatası | Dosya izni yok | 500 |

---

## 3. COLLECTION YAPISI ÖNERİSİ

### Önerilen Postman/API Test Collection Hiyerarşisi

```
BGTS Test Platform API Collection
├── 01-Health & Readiness
│   ├── [FastAPI] GET /health
│   ├── [FastAPI] GET /ready
│   ├── [Engine] GET /health
│   └── [Engine] GET /api/health
│
├── 02-Authentication
│   ├── FastAPI Auth
│   │   ├── POST /api/v1/auth/login (Happy Path)
│   │   ├── POST /api/v1/auth/login (Invalid Creds)
│   │   ├── POST /api/v1/auth/login (Validation Error)
│   │   ├── GET /api/v1/auth/me (Valid Token)
│   │   └── GET /api/v1/auth/me (No Token)
│   └── Engine Auth
│       ├── POST /api/auth/register
│       ├── POST /api/auth/login
│       ├── GET /api/auth/verify/<token>
│       └── POST /api/auth/logout
│
├── 03-Datasets & Catalog
│   ├── CRUD Operations
│   │   ├── POST /api/v1/datasets (Create)
│   │   ├── GET /api/v1/datasets (List)
│   │   ├── GET /api/v1/datasets/{id} (Get)
│   │   └── Negative Tests
│   └── Versions & Schema
│       ├── POST .../versions (Create Version)
│       ├── GET .../versions (List Versions)
│       └── GET .../versions/{id}/schema (Get Schema)
│
├── 04-Rules
│   ├── POST .../rule-sets (Create)
│   ├── GET .../rule-sets (List)
│   └── GET .../rule-sets/{id} (Get)
│
├── 05-Jobs & Artifacts
│   ├── POST /api/v1/jobs (Enqueue)
│   ├── GET /api/v1/jobs (List)
│   ├── GET /api/v1/jobs/{id} (Get)
│   ├── GET /api/v1/jobs/{id}/events (Events)
│   ├── GET /api/v1/jobs/{id}/artifacts (Artifacts)
│   └── GET /api/v1/artifacts/{id}/download (Download)
│
├── 06-TSPM Projects
│   ├── Project CRUD
│   ├── Dashboard
│   └── Members
│
├── 07-TSPM Scenarios
│   ├── Scenario CRUD
│   ├── BDD Generation (AI)
│   ├── Bulk Delete
│   ├── Versions & Diff
│   └── Negative Tests
│
├── 08-TSPM Requirements & Coverage
│   ├── Requirement CRUD
│   ├── Scenario-Requirement Linking
│   ├── Coverage Matrix
│   └── Coverage Gaps
│
├── 09-TSPM Executions
│   ├── Create & Run
│   ├── Results Update
│   ├── Re-run
│   ├── Trends & Stats
│   └── Flaky Tests
│
├── 10-TSPM Flows
│   ├── Flow CRUD
│   └── Graph Update
│
├── 11-TSPM Regression Sets
│   ├── CRUD
│   ├── Add Scenarios
│   ├── AI Suggestions
│   └── Accept Suggestions
│
├── 12-TSPM Schedules
│   ├── CRUD
│   └── Trigger
│
├── 13-TSPM Test Data
│   ├── CRUD
│   ├── Data Binding
│   └── Expanded Scenario
│
├── 14-TSPM Integrations
│   ├── CRUD
│   └── Sync
│
├── 15-TSPM API Testing
│   ├── Collections CRUD
│   ├── Requests CRUD
│   ├── Run Collection
│   └── Runs History
│
├── 16-TSPM Approvals & Imports
│   ├── List & Decide Approvals
│   └── Create Import
│
├── 17-Engine Features
│   ├── Feature CRUD
│   └── Folder Operations
│
├── 18-Engine Regression
│   ├── Set CRUD
│   └── Feature Management
│
├── 19-Engine Manual Tests
│   ├── Test CRUD
│   ├── Step Operations
│   └── Generate from Doc
│
├── 20-Engine Runner
│   ├── Run Tests
│   ├── SSE Stream
│   ├── Maven Tests
│   └── System Operations
│
├── 21-Engine AI
│   ├── Generate Feature
│   ├── Analyze API
│   ├── Security Scan
│   └── Inspector
│
├── 22-Engine DataSim
│   ├── Dataset Operations
│   ├── Synthetic Generation
│   └── SQLite/DB Operations
│
├── 23-Engine Visual Testing
│   ├── Baseline Management
│   ├── Compare Operations
│   └── Batch & Diff
│
├── 24-Engine Accessibility
│   ├── Single URL Test
│   ├── Batch Test
│   ├── Report Generation
│   └── Config Management
│
├── 25-Engine Recorder
│   ├── Session Management
│   ├── Actions
│   ├── Code Generation
│   └── Locators
│
├── 26-Engine Settings & Utils
│   ├── Settings CRUD
│   ├── Stats & Reports
│   ├── Proxy Request
│   └── Export
│
├── 27-Engine Projects
│   ├── Project CRUD
│   └── File Operations
│
└── 28-Cross-Cutting Concerns
    ├── Auth Token Expiry Flow
    ├── CORS Validation
    ├── Rate Limiting (varsa)
    ├── Error Format Consistency
    └── Concurrent Access Tests
```

---

## 4. API AUTOMATION YAPISI

### Önerilen Dizin Yapısı

```
api-tests/
├── conftest.py                    # Shared fixtures, base URL, auth tokens
├── pytest.ini                     # Pytest configuration
├── requirements.txt               # Dependencies
├── .env.test                      # Test environment variables
│
├── config/
│   ├── __init__.py
│   ├── settings.py                # Test settings from env
│   └── constants.py               # API paths, status codes
│
├── clients/
│   ├── __init__.py
│   ├── base_client.py             # Base HTTP client (requests/httpx)
│   ├── fastapi_client.py          # FastAPI backend client
│   └── engine_client.py           # Flask engine client
│
├── models/
│   ├── __init__.py
│   ├── auth.py                    # Auth request/response models
│   ├── datasets.py                # Dataset models
│   ├── scenarios.py               # Scenario models
│   ├── executions.py              # Execution models
│   └── ...                        # Other domain models
│
├── helpers/
│   ├── __init__.py
│   ├── auth_helper.py             # Login & token management
│   ├── data_factory.py            # Test data generators
│   ├── assertions.py              # Custom assertion helpers
│   └── cleanup.py                 # Test data cleanup
│
├── tests/
│   ├── __init__.py
│   ├── test_health.py             # Health checks
│   ├── test_auth.py               # Authentication tests
│   ├── test_datasets.py           # Dataset CRUD tests
│   ├── test_rules.py              # Rules tests
│   ├── test_jobs.py               # Jobs tests
│   ├── test_artifacts.py          # Artifact tests
│   ├── test_projects.py           # TSPM project tests
│   ├── test_scenarios.py          # Scenario CRUD + BDD tests
│   ├── test_requirements.py       # Requirements & coverage
│   ├── test_executions.py         # Execution tests
│   ├── test_flows.py              # Flow tests
│   ├── test_regression.py         # Regression set tests
│   ├── test_schedules.py          # Schedule tests
│   ├── test_test_data.py          # Test data management
│   ├── test_integrations.py       # Integration tests
│   ├── test_api_testing.py        # API testing feature tests
│   ├── test_approvals.py          # Approval workflow
│   ├── test_imports.py            # Import tests
│   ├── test_members.py            # Project member tests
│   │
│   ├── engine/                    # Engine-specific tests
│   │   ├── test_engine_auth.py
│   │   ├── test_features.py
│   │   ├── test_manual_tests.py
│   │   ├── test_runner.py
│   │   ├── test_ai.py
│   │   ├── test_datasim.py
│   │   ├── test_visual.py
│   │   ├── test_accessibility.py
│   │   ├── test_recorder.py
│   │   └── test_settings.py
│   │
│   └── security/                  # Security tests
│       ├── test_auth_bypass.py
│       ├── test_injection.py
│       └── test_ssrf.py
│
├── reports/                       # Test reports output
│   └── .gitkeep
│
└── allure-results/                # Allure report data
    └── .gitkeep
```

---

## 5. RİSKLİ ENDPOINT LİSTESİ

### Risk Seviyesi: KRİTİK

| # | Endpoint | Risk | Açıklama |
|---|----------|------|----------|
| 1 | `POST /api/v1/auth/login` | **Brute Force / Credential Stuffing** | Rate limiting kontrolü gerekli. Başarısız deneme sayısı sınırlandırılmalı. |
| 2 | `POST /api/request` (Engine Proxy) | **SSRF (Server-Side Request Forgery)** | Herhangi bir URL'ye istek gönderebilir. `localhost`, `127.0.0.1`, iç ağ adresleri, `file://` protokolü filtrelenmeli. |
| 3 | `POST /api/settings` (Engine) | **Hassas Veri Manipülasyonu** | API key, DB URL gibi değerler .env dosyasına yazılıyor. Yetki kontrolü güçlendirilmeli. |
| 4 | `POST /api/auth/login` (Engine - Hardcoded bypass) | **Backdoor** | `test/test` kullanıcı adı/şifre kombinasyonu her zaman çalışıyor. Üretim ortamında kaldırılmalı. |
| 5 | `GET /api/a11y/report/download` | **Path Traversal** | `path` query parametresi doğrudan dosya yoluna dönüştürülüyor. BASE_DIR kontrolü var ama bypass denenebilir. |
| 6 | `GET /api/v1/artifacts/{id}/download` | **Dosya Erişim Kontrolü** | Yetkilendirme yalnızca user varlığını kontrol ediyor, dosya sahipliği kontrol edilmeli (IDOR). |
| 7 | `POST /api/datasim/install` | **Uzaktan Paket Kurulumu** | `pip install` çalıştırıyor. Supply chain attack riski. |

### Risk Seviyesi: YÜKSEK

| # | Endpoint | Risk | Açıklama |
|---|----------|------|----------|
| 8 | `POST /api/run` (Engine) | **Komut Enjeksiyonu** | Pytest komutunu background thread'de çalıştırıyor. `markers` parametresi sanitize edilmeli. |
| 9 | `POST /api/run-maven` (Engine) | **Komut Enjeksiyonu** | `maven_path` parametresiyle `mvn` çalıştırılıyor. Path manipülasyonu riski. |
| 10 | `WS /api/v1/ws/notifications` | **WebSocket Token Doğrulama** | Token query param ile gönderiliyor, URL loglarında görünebilir. |
| 11 | `POST /api/v1/tspm/projects/{pid}/scenarios/generate-bdd` | **AI Prompt Injection** | `analysis_text` doğrudan AI'a gönderiliyor. Prompt injection riski. |
| 12 | `POST /api/generate-feature` (Engine) | **AI Prompt Injection** | `requirements` alanı AI'a gönderiliyor. Hassas veri sızıntısı riski. |
| 13 | `POST /api/security-scan` (Engine) | **Dış Sistemlere Saldırı** | Hedef URL'ye güvenlik taraması yapıyor. Kötüye kullanım riski. |
| 14 | `POST /api/inspect` (Engine) | **Playwright ile Keyfi URL Erişimi** | Herhangi bir URL'de Playwright başlatıyor. İç ağ erişimi riski. |
| 15 | `DELETE /api/projects/<name>/delete` (Engine) | **Veri Kaybı** | Proje silme geri alınamaz. Soft-delete önerilir. |

### Risk Seviyesi: ORTA

| # | Endpoint | Risk | Açıklama |
|---|----------|------|----------|
| 16 | `POST /api/v1/tspm/projects/{pid}/scenarios/bulk-delete` | **Toplu Veri Kaybı** | Çok sayıda senaryoyu tek seferde silebilir. Onay mekanizması önerilir. |
| 17 | `POST /api/visual/compare` (Engine) | **Kaynak Tüketimi** | Playwright açıp screenshot alıyor. DoS riski (çok sayıda eşzamanlı istek). |
| 18 | `POST /api/datasim/generate` (Engine) | **Kaynak Tüketimi** | count=5000 ile büyük veri setleri oluşturulabilir. Bellek/CPU tüketimi. |
| 19 | `POST /api/recorder/start` (Engine) | **Kaynak Tüketimi** | Browser oturumu başlatıyor. Çok sayıda eşzamanlı oturum açılabilir. |
| 20 | `POST /api/v1/tspm/projects/{pid}/imports` | **Büyük Dosya İşleme** | `raw_text` büyük olabilir. Size limit kontrolü önerilir. |
| 21 | Automation Router (Unregistered Proxy) | **Şu An Aktif Değil Ama Potansiyel Risk** | Catch-all proxy pattern var, aktifleştirilirse tüm engine istekleri proxy edilir. |

### Risk Seviyesi: BİLGİ

| # | Endpoint | Risk | Açıklama |
|---|----------|------|----------|
| 22 | `GET /ready` | **İç Bilgi Sızıntısı** | DB bağlantı durumu dışarıya açık. Üretimde erişim kısıtlanmalı. |
| 23 | Route conflicts (Engine) | **Tutarsız Davranış** | `/api/projects/create` ve `/api/projects/list` iki farklı blueprint'te tanımlı. Son kayıtlı kazanır. |
| 24 | `POST /api/lifecycle/save` | **Placeholder Endpoint** | Gerçek iş mantığı yok, simüle ediliyor. |
| 25 | `GET /api/datasim/sqlite/catalog` | **İç Bilgi Sızıntısı** | PostgreSQL bağlantı bilgileri katalogda dönüyor. |

---

## 6. ÖZET İSTATİSTİKLER

| Metrik | Değer |
|--------|-------|
| **Toplam Endpoint** | 184 (91 FastAPI + 95 Engine - 2 conflict) |
| **Auth Mekanizmaları** | JWT (FastAPI) + Session (Engine) |
| **Toplam Pydantic Schema** | ~75 sınıf |
| **Toplam SQLAlchemy Model** | 24 sınıf |
| **Toplam Test Senaryosu** | ~150+ (bu dokümandaki) |
| **Kritik Risk Endpoint** | 7 |
| **Yüksek Risk Endpoint** | 8 |
| **Orta Risk Endpoint** | 6 |
| **AI-Powered Endpoint** | 8 (BDD gen, feature gen, security scan, regression suggest, lifecycle, analyze-api, discover, inspector) |
| **SSE/WebSocket Endpoint** | 5 (WS notifications, run stream, datasim generate, datasim install, datasim learn) |
| **File Upload/Download** | 6 (artifact download, export, visual upload, diff-image, manual-from-doc, a11y report) |

---

## 7. SONRAKİ ADIMLAR

1. **Otomasyon İskeleti Implementasyonu**: Yukarıdaki yapı temel alınarak `api-tests/` dizini oluşturulabilir
2. **Environment Konfigürasyonu**: Test/Staging/Prod ortamları için ayrı `.env` dosyaları
3. **CI/CD Entegrasyonu**: GitHub Actions workflow'una API test adımı eklenmesi
4. **Data-Driven Tests**: `test-data` endpoint'leri kullanılarak parametrik testler
5. **Contract Testing**: OpenAPI spec (`/openapi.json`) üzerinden otomatik contract testleri
6. **Performance Tests**: Locust/k6 ile yük testleri (özellikle AI ve DataSim endpoint'leri)
7. **Security Test Otomasyonu**: OWASP ZAP entegrasyonu ile otomatik güvenlik taraması
