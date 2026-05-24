# BGTS Test Dönüşüm Platformu — Kapsamlı Manuel Test Tasarımı

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Hazırlayan:** Analysis to Test Design Agent  
**Kaynak Analiz:** `docs/product.md`, `docs/architecture.md`, `PROGRESS.md`, Backend TSPM models/schemas/router, Auth module  

---

## 1. İş Kuralları Çıkarımı

### BR-001: Kimlik Doğrulama ve Yetkilendirme
- Kullanıcılar JWT tabanlı token ile oturum açar.
- Login işlemi e-posta + parola gerektirir; hatalı bilgide 401 döner.
- Devre dışı bırakılmış hesaplar (`is_active=False`) 403 Forbidden alır.
- Başarılı login audit log kaydı oluşturur.
- 3 rol tanımlıdır: `admin`, `operator`, `viewer`.
- `viewer` rolü yalnızca `project.read` ve `scenario.read` iznine sahiptir.
- `operator` tüm CRUD işlemleri yapabilir ancak `admin.*` yoktur.
- `admin` tüm izinlere sahiptir.

### BR-002: Proje Yönetimi
- Proje oluşturma `name` alanı zorunludur (min 1 karakter).
- Projeler oluşturma tarihine göre ters sırada listelenir.
- Proje silindiğinde cascade ile tüm bağlı varlıklar (senaryolar, koşular, akışlar, vb.) silinir.
- Projeler arşivlenebilir (`archived` boolean flag).

### BR-003: Senaryo Yönetimi
- Senaryo oluşturma `title` alanı zorunludur (min 1 karakter).
- Senaryo varsayılan status değeri `draft`'tır.
- Senaryo güncellendiğinde mevcut durum `TspmScenarioVersion` tablosuna versiyon olarak kaydedilir.
- Her güncelleme `current_version` değerini 1 artırır.
- Senaryolar `q` parametresi ile başlıkta aranabilir (ilike).
- Toplu silme (bulk-delete) desteklenir; yalnızca aynı projeye ait senaryolar silinir.
- Senaryo yalnızca ait olduğu proje üzerinden erişilebilir.

### BR-004: BDD Senaryo Üretimi
- `analysis_text` alanı minimum 10 karakter olmalıdır.
- OpenAI/LLM ile analiz dokümanından Gherkin formatında senaryolar üretilir.
- Üretilen senaryolar toplu olarak veritabanına kaydedilebilir.
- Kaydedilen BDD senaryoları `draft` statusü ile oluşturulur.

### BR-005: Onay Kuyruğu
- Onaylar `pending`, `approved`, `rejected` statuslerinde olabilir.
- Onay kararı verildiğinde `decided_at` zaman damgası eklenir.
- Yalnızca mevcut projeye ait onaylar işlenebilir.

### BR-006: İçe Aktarma (Import)
- Import oluşturma `filename` gerektirir.
- Oluşturulan import varsayılan olarak `completed` statusünde kaydedilir.
- Ham payload `raw_text` olarak JSONB alanında saklanır.

### BR-007: Test Koşuları (Execution)
- Koşu oluşturma `scenario_ids` listesi kabul eder.
- Yeni koşu `running` statusünde başlar.
- Her senaryo için `TspmExecutionResult` kaydı `pending` statusle oluşturulur.
- `TspmExecutionMetrics` kaydı otomatik oluşturulur.
- Koşu sonuçlarının statusü güncellenebilir (passed/failed/skipped).
- Re-run: mevcut koşunun senaryoları yeni bir koşu olarak tekrar oluşturulur; isim sonuna `(re-run)` eklenir.

### BR-008: Koşu Analitikleri
- Son 30 güne göre trend verileri (gün bazında total/passed/failed/pass_rate).
- Flaky test tespiti: son 10 koşuda passed↔failed geçişi yapan senaryolar.
- Genel istatistikler: toplam koşu, toplam çalıştırılan senaryo, ortalama başarı oranı.

### BR-009: Akış Editörü (Flows)
- Akış oluşturma `name` alanı zorunludur (min 1 karakter).
- Akışlar JSON formatında `nodes` ve `edges` içerir.
- Graph update ile nodes/edges güncellenebilir.

### BR-010: Regresyon Setleri
- Set oluşturma `name` alanı zorunludur (min 1 karakter).
- Sete senaryo ekleme: mevcut ID'lere yeni ID'ler merge edilir (tekrar eklenmez).
- AI ile regresyon seti önerisi: projede en az 1 senaryo olmalıdır.
- AI önerilerinden seçilen setler toplu oluşturulabilir.

### BR-011: Gereksinimler ve Kapsam
- Gereksinim `external_id` ve `title` zorunludur.
- Senaryo-Gereksinim bağlantısı N:N ilişkidir.
- Aynı bağlantı tekrar eklenemez (idempotent).
- Coverage matrix: tüm gereksinimlerin senaryo kapsama yüzdesini hesaplar.
- Coverage gaps: hiçbir senaryoya bağlanmamış gereksinimleri listeler.

### BR-012: Zamanlamalar (Schedules)
- Zamanlama `name` ve `cron_expression` zorunludur.
- Zamanlama tetiklendiğinde: önce schedule'ın `scenario_ids`'ine, yoksa `regression_set_id`'den senaryolar alınır.
- Eğer hiç senaryo bulunamazsa 400 Bad Request döner.
- Tetikleme sonrası `last_run_at` güncellenir.

### BR-013: Test Verisi Yönetimi
- Veri seti `name` zorunludur (min 1 karakter).
- Senaryo-veri bağlama: parametrik eşleştirme (`parameter_mapping`) ile adım metinlerinde `{{param}}` yer tutucuları değiştirilir.
- Expanded scenario: veri setindeki her satır için adımlar genişletilir.

### BR-014: Entegrasyonlar
- Entegrasyon `provider` alanı zorunludur (min 1 karakter).
- Sync işlemi `last_sync_at` tarihini günceller (stub döner).

### BR-015: API Testi
- Koleksiyon oluşturma `name` zorunludur.
- Request oluşturma koleksiyona bağlıdır; koleksiyon projeye ait olmalıdır.
- Koleksiyon çalıştırma: tüm request'ler sırayla HTTP çağrısı yapar; timeout 30sn.
- Response body ilk 2000 karakter ile kesilir.
- Hata durumunda `passed: false, error: <mesaj>` döner.

### BR-016: Proje Üyeleri
- Üye ekleme `user_id` ve `role` gerektirir; varsayılan rol `viewer`.
- Üye silme projeye ait olmalıdır.

### BR-017: Senaryo Versiyonlama
- Her güncelleme önceki durumu versiyon olarak saklar.
- İki versiyon karşılaştırılabilir (diff): title, description, steps, status değişim bayrakları.

---

## 2. Aktörler

| Aktör | Açıklama | Yetkiler |
|-------|----------|----------|
| **Admin** | Platform yöneticisi | Tüm izinler (`admin.*` dahil) |
| **Operator** | Test lideri / Kalite mühendisi | Proje CRUD, senaryo CRUD, onay karar, koşu, import, akış, gereksinim, zamanlama, entegrasyon, API test, test verisi |
| **Viewer** | Gözlemci / Dış paydaş | Yalnızca proje ve senaryo okuma |
| **Sistem (AI/LLM)** | Otonom BDD üretici, regresyon önericisi | Senaryo taslağı üretme, regresyon seti önerme |
| **n8n Workflow** | Harici otomasyon | Webhook callback ile import/durum güncelleme |

---

## 3. Ön Koşullar (Genel)

| ID | Ön Koşul |
|----|----------|
| PC-001 | PostgreSQL ve Redis servisleri çalışır durumda |
| PC-002 | Backend (FastAPI :8000) ayakta |
| PC-003 | Frontend (Next.js :3000) ayakta |
| PC-004 | Admin kullanıcı seed edilmiş (`admin@example.com / admin123`) |
| PC-005 | Geçerli JWT token alınmış |
| PC-006 | En az 1 proje oluşturulmuş |
| PC-007 | Projede en az 1 senaryo mevcut |
| PC-008 | Projede en az 1 gereksinim mevcut |

---

## 4. Test Setleri ve Senaryolar

---

### TS-01: Kimlik Doğrulama ve Oturum Yönetimi

#### TC-0101: Geçerli Kullanıcı Başarılı Login
- **ID:** TC-0101
- **Başlık:** Geçerli e-posta ve parola ile başarılı oturum açma
- **Ön Koşul:** PC-001, PC-002, PC-004
- **Test Adımları:**
  1. `POST /api/v1/auth/login` endpoint'ine `{ "email": "admin@example.com", "password": "admin123" }` gönder
  2. Yanıt kodunu kontrol et
  3. Yanıt body'sini kontrol et
- **Beklenen Sonuç:** HTTP 200; `access_token` ve `token_type: "bearer"` döner
- **Öncelik:** Critical
- **Tip:** Pozitif
- **İlgili Requirement:** BR-001

#### TC-0102: Hatalı Parola ile Login Reddi
- **ID:** TC-0102
- **Başlık:** Yanlış parola ile oturum açma denemesi reddedilir
- **Ön Koşul:** PC-001, PC-002, PC-004
- **Test Adımları:**
  1. `POST /api/v1/auth/login` endpoint'ine `{ "email": "admin@example.com", "password": "wrongpass" }` gönder
  2. Yanıt kodunu kontrol et
  3. Hata mesajını kontrol et
- **Beklenen Sonuç:** HTTP 401; `"E-posta veya parola hatalı"` mesajı döner
- **Öncelik:** Critical
- **Tip:** Negatif
- **İlgili Requirement:** BR-001

#### TC-0103: Hatalı E-posta ile Login Reddi
- **ID:** TC-0103
- **Başlık:** Kayıtlı olmayan e-posta ile oturum açma denemesi reddedilir
- **Ön Koşul:** PC-001, PC-002
- **Test Adımları:**
  1. `POST /api/v1/auth/login` endpoint'ine `{ "email": "nonexistent@test.com", "password": "admin123" }` gönder
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 401; `"E-posta veya parola hatalı"` mesajı döner
- **Öncelik:** High
- **Tip:** Negatif
- **İlgili Requirement:** BR-001

#### TC-0104: Devre Dışı Hesap ile Login
- **ID:** TC-0104
- **Başlık:** Devre dışı bırakılmış hesap login yapamaz
- **Ön Koşul:** PC-001, PC-002; `is_active=False` olan kullanıcı mevcut
- **Test Adımları:**
  1. Devre dışı kullanıcı bilgileri ile `POST /api/v1/auth/login` gönder
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 403; `"Hesap devre dışı"` mesajı döner
- **Öncelik:** High
- **Tip:** Negatif
- **İlgili Requirement:** BR-001

#### TC-0105: Boş E-posta Alanı ile Login
- **ID:** TC-0105
- **Başlık:** E-posta alanı boş bırakıldığında doğrulama hatası
- **Ön Koşul:** PC-001, PC-002
- **Test Adımları:**
  1. `POST /api/v1/auth/login` endpoint'ine `{ "email": "", "password": "admin123" }` gönder
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 422; Pydantic validation error döner
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-001

#### TC-0106: Boş Parola Alanı ile Login
- **ID:** TC-0106
- **Başlık:** Parola alanı boş bırakıldığında doğrulama hatası
- **Ön Koşul:** PC-001, PC-002
- **Test Adımları:**
  1. `POST /api/v1/auth/login` endpoint'ine `{ "email": "admin@example.com", "password": "" }` gönder
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 422; Pydantic validation error (min_length=1)
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-001

#### TC-0107: Geçersiz E-posta Formatı ile Login
- **ID:** TC-0107
- **Başlık:** Geçersiz e-posta formatı doğrulama hatası verir
- **Ön Koşul:** PC-001, PC-002
- **Test Adımları:**
  1. `POST /api/v1/auth/login` endpoint'ine `{ "email": "not-an-email", "password": "admin123" }` gönder
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 422; EmailStr validation error
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-001

#### TC-0108: Authenticated /me Endpoint Kontrolü
- **ID:** TC-0108
- **Başlık:** Geçerli token ile kullanıcı bilgileri alınabilir
- **Ön Koşul:** PC-005
- **Test Adımları:**
  1. Geçerli JWT token ile `GET /api/v1/auth/me` çağır
  2. Yanıt body'sinde `id`, `email`, `roles`, `permissions` alanlarını kontrol et
- **Beklenen Sonuç:** HTTP 200; kullanıcı bilgileri ve roller doğru şekilde döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-001

#### TC-0109: Token Olmadan Korumalı Endpoint Erişimi
- **ID:** TC-0109
- **Başlık:** Token olmadan korumalı endpoint'e erişim reddedilir
- **Ön Koşul:** PC-002
- **Test Adımları:**
  1. Authorization header olmadan `GET /api/v1/tspm/projects` çağır
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 401 veya 403; erişim reddedilir
- **Öncelik:** Critical
- **Tip:** Negatif
- **İlgili Requirement:** BR-001

#### TC-0110: Login Sonrası Audit Log Kaydı
- **ID:** TC-0110
- **Başlık:** Başarılı login işlemi audit log tablosuna yazılır
- **Ön Koşul:** PC-001, PC-002, PC-004
- **Test Adımları:**
  1. Başarılı login yap
  2. Veritabanında `audit_logs` tablosunu kontrol et
  3. `action=auth.login`, `resource_type=user` kaydını doğrula
- **Beklenen Sonuç:** Audit log kaydı oluşturulmuş; actor_user_id doğru
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-001

---

### TS-02: Proje Yönetimi

#### TC-0201: Yeni Proje Oluşturma (Pozitif)
- **ID:** TC-0201
- **Başlık:** Geçerli bilgilerle yeni proje oluşturma
- **Ön Koşul:** PC-005
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects` endpoint'ine `{ "name": "Test Projesi", "description": "Açıklama" }` gönder
  2. Yanıt kodunu ve body'yi kontrol et
- **Beklenen Sonuç:** HTTP 201; id, name, description, `archived: false` döner
- **Öncelik:** Critical
- **Tip:** Pozitif
- **İlgili Requirement:** BR-002

#### TC-0202: Boş İsim ile Proje Oluşturma
- **ID:** TC-0202
- **Başlık:** İsim alanı boş bırakıldığında proje oluşturulamaz
- **Ön Koşul:** PC-005
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects` endpoint'ine `{ "name": "" }` gönder
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 422; `min_length` validation error
- **Öncelik:** High
- **Tip:** Boundary
- **İlgili Requirement:** BR-002

#### TC-0203: Tek Karakterli Proje İsmi (Boundary)
- **ID:** TC-0203
- **Başlık:** Minimum uzunlukta (1 karakter) proje ismi kabul edilir
- **Ön Koşul:** PC-005
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects` endpoint'ine `{ "name": "A" }` gönder
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 201; proje başarıyla oluşturulur
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-002

#### TC-0204: Çok Uzun Proje İsmi (Boundary)
- **ID:** TC-0204
- **Başlık:** 200 karakterden uzun proje ismi ile oluşturma
- **Ön Koşul:** PC-005
- **Test Adımları:**
  1. 201 karakter uzunluğunda isimle `POST /api/v1/tspm/projects` gönder
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 422 veya DB hatası (String(200) limiti)
- **Öncelik:** Low
- **Tip:** Boundary
- **İlgili Requirement:** BR-002

#### TC-0205: Proje Listeleme Sıralama Kontrolü
- **ID:** TC-0205
- **Başlık:** Projeler oluşturma tarihine göre ters sırada listelenir
- **Ön Koşul:** PC-005; en az 2 proje oluşturulmuş
- **Test Adımları:**
  1. Sırayla 2 proje oluştur
  2. `GET /api/v1/tspm/projects` çağır
  3. Listenin sırasını kontrol et
- **Beklenen Sonuç:** En son oluşturulan proje listenin başında
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-002

#### TC-0206: Olmayan Proje ID ile İşlem
- **ID:** TC-0206
- **Başlık:** Var olmayan proje ID ile dashboard/senaryo erişimi 404 döner
- **Ön Koşul:** PC-005
- **Test Adımları:**
  1. `GET /api/v1/tspm/projects/nonexistent-uuid/dashboard` çağır
  2. Yanıt kodunu kontrol et
- **Beklenen Sonuç:** HTTP 404; `"Proje bulunamadı"` mesajı
- **Öncelik:** High
- **Tip:** Negatif
- **İlgili Requirement:** BR-002

---

### TS-03: Senaryo Yönetimi

#### TC-0301: Yeni Senaryo Oluşturma
- **ID:** TC-0301
- **Başlık:** Geçerli bilgilerle yeni senaryo oluşturma
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/scenarios` endpoint'ine `{ "title": "Login Testi", "description": "Login fonksiyonelliği", "steps": [{"order": 1, "keyword": "Given", "text": "Kullanıcı login sayfasında"}] }` gönder
  2. Yanıt kodunu ve body'yi kontrol et
- **Beklenen Sonuç:** HTTP 201; id, title, `status: "draft"`, `current_version: 1` döner
- **Öncelik:** Critical
- **Tip:** Pozitif
- **İlgili Requirement:** BR-003

#### TC-0302: Boş Başlıklı Senaryo Oluşturma
- **ID:** TC-0302
- **Başlık:** Boş başlıkla senaryo oluşturulamaz
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/scenarios` endpoint'ine `{ "title": "" }` gönder
- **Beklenen Sonuç:** HTTP 422; `min_length` validation error
- **Öncelik:** High
- **Tip:** Boundary
- **İlgili Requirement:** BR-003

#### TC-0303: Senaryo Güncelleme ve Versiyonlama
- **ID:** TC-0303
- **Başlık:** Senaryo güncellendiğinde versiyon numarası artar ve eski durum saklanır
- **Ön Koşul:** PC-005, PC-006, PC-007
- **Test Adımları:**
  1. Mevcut senaryonun `current_version` değerini not al (örn: 1)
  2. `PUT /api/v1/tspm/projects/{pid}/scenarios/{sid}` ile `{ "title": "Güncellenmiş Başlık" }` gönder
  3. Yanıttaki `current_version` değerini kontrol et
  4. `GET .../scenarios/{sid}/versions` ile versiyon listesini çek
- **Beklenen Sonuç:** `current_version` 2 olur; versiyon listesinde eski başlık, versiyon 1 olarak saklanır
- **Öncelik:** Critical
- **Tip:** Pozitif
- **İlgili Requirement:** BR-003, BR-017

#### TC-0304: Farklı Projeye Ait Senaryoya Erişim
- **ID:** TC-0304
- **Başlık:** Bir projenin senaryosuna farklı bir proje ID ile erişilemez
- **Ön Koşul:** PC-005; 2 farklı proje ve her birinde 1 senaryo
- **Test Adımları:**
  1. Proje-A'nın senaryo ID'sini al
  2. `GET /api/v1/tspm/projects/{ProjeB_id}/scenarios/{senaryoA_id}` çağır
- **Beklenen Sonuç:** HTTP 404; `"Senaryo bulunamadı"`
- **Öncelik:** High
- **Tip:** Negatif
- **İlgili Requirement:** BR-003

#### TC-0305: Senaryo Arama (Query Parametresi)
- **ID:** TC-0305
- **Başlık:** Senaryolar başlık ile aranabilir
- **Ön Koşul:** PC-005, PC-006; farklı başlıklarda senaryolar
- **Test Adımları:**
  1. "Login" başlıklı ve "Ödeme" başlıklı senaryolar oluştur
  2. `GET /api/v1/tspm/projects/{id}/scenarios?q=Login` çağır
  3. Sonuçları kontrol et
- **Beklenen Sonuç:** Yalnızca başlığında "Login" geçen senaryolar döner
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-003

#### TC-0306: Toplu Senaryo Silme
- **ID:** TC-0306
- **Başlık:** Birden fazla senaryo toplu silinebilir
- **Ön Koşul:** PC-005, PC-006; en az 3 senaryo
- **Test Adımları:**
  1. 3 senaryo oluştur
  2. `POST /api/v1/tspm/projects/{id}/scenarios/bulk-delete` ile 2 tanesinin ID'sini gönder
  3. Senaryo listesini kontrol et
- **Beklenen Sonuç:** HTTP 204; silinen senaryolar listede görünmez, silinmeyen kalır
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-003

#### TC-0307: Farklı Projeye Ait Senaryo ID'si ile Toplu Silme
- **ID:** TC-0307
- **Başlık:** Toplu silmede farklı projeye ait ID'ler yok sayılır
- **Ön Koşul:** PC-005; 2 proje, her birinde senaryo
- **Test Adımları:**
  1. Proje-A altında Proje-B'nin senaryo ID'sini toplu silme isteğine ekle
  2. İsteği gönder
  3. Proje-B'nin senaryosunun hâlâ mevcut olduğunu doğrula
- **Beklenen Sonuç:** Proje-B'nin senaryosu silinmez; yalnızca proje-A'ya ait olanlar silinir
- **Öncelik:** High
- **Tip:** Negatif
- **İlgili Requirement:** BR-003

#### TC-0308: Senaryo Versiyon Karşılaştırma (Diff)
- **ID:** TC-0308
- **Başlık:** İki versiyon arasındaki farklar doğru raporlanır
- **Ön Koşul:** PC-005, PC-006, PC-007; senaryo en az 2 kez güncellenmiş
- **Test Adımları:**
  1. Senaryo oluştur (v1)
  2. Başlığı güncelle (v2 oluşur)
  3. Adımları güncelle (v3 oluşur)
  4. `GET .../versions/1/diff/2` çağır
- **Beklenen Sonuç:** `title_changed: true`, `steps_changed: false` (v1→v2); her iki versiyon snapshot'ı döner
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-017

#### TC-0309: Olmayan Versiyon Numarası ile Diff
- **ID:** TC-0309
- **Başlık:** Var olmayan versiyon numarası ile karşılaştırma 404 döner
- **Ön Koşul:** PC-005, PC-006, PC-007
- **Test Adımları:**
  1. `GET .../versions/1/diff/999` çağır
- **Beklenen Sonuç:** HTTP 404; `"Versiyon bulunamadı"`
- **Öncelik:** Medium
- **Tip:** Negatif
- **İlgili Requirement:** BR-017

---

### TS-04: BDD Senaryo Üretimi

#### TC-0401: Geçerli Analiz Metni ile BDD Üretimi
- **ID:** TC-0401
- **Başlık:** Geçerli analiz dokümanından BDD senaryoları üretilir
- **Ön Koşul:** PC-005, PC-006; LLM servisi erişilebilir
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/scenarios/generate-bdd` ile `{ "analysis_text": "Kullanıcı sisteme giriş yapabilmeli, hatalı girişte 3 deneme sonra hesap kilitlenmeli." }` gönder
  2. Yanıtı kontrol et
- **Beklenen Sonuç:** HTTP 200; `scenarios` listesi içinde Gherkin formatında senaryolar döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-004

#### TC-0402: Kısa Analiz Metni ile BDD Üretimi (Boundary)
- **ID:** TC-0402
- **Başlık:** 10 karakterden kısa analiz metni reddedilir
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../generate-bdd` ile `{ "analysis_text": "Kısa" }` gönder (5 karakter)
- **Beklenen Sonuç:** HTTP 422; `min_length` validation error
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-004

#### TC-0403: Tam 10 Karakterli Analiz Metni (Boundary)
- **ID:** TC-0403
- **Başlık:** Tam 10 karakterlik analiz metni kabul edilir
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../generate-bdd` ile `{ "analysis_text": "1234567890" }` gönder
- **Beklenen Sonuç:** HTTP 200; üretim başarılı (içerik LLM yanıtına bağlı)
- **Öncelik:** Low
- **Tip:** Boundary
- **İlgili Requirement:** BR-004

#### TC-0404: Üretilen BDD Senaryolarını Kaydetme
- **ID:** TC-0404
- **Başlık:** AI tarafından üretilen BDD senaryoları veritabanına kaydedilir
- **Ön Koşul:** PC-005, PC-006; TC-0401 başarılı
- **Test Adımları:**
  1. BDD üretim yanıtındaki senaryoları `POST .../save-bdd` ile gönder
  2. Senaryo listesini kontrol et
- **Beklenen Sonuç:** HTTP 201; tüm senaryolar `draft` statusünde kaydedilir
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-004

---

### TS-05: Onay Kuyruğu

#### TC-0501: Onay Listesi Görüntüleme
- **ID:** TC-0501
- **Başlık:** Projeye ait onaylar listelenir
- **Ön Koşul:** PC-005, PC-006; projede onay kayıtları var
- **Test Adımları:**
  1. `GET /api/v1/tspm/projects/{id}/approvals` çağır
  2. Yanıtı kontrol et
- **Beklenen Sonuç:** HTTP 200; onay listesi `id`, `title`, `status`, `created_at` alanlarıyla döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-005

#### TC-0502: Onay Kabul Etme
- **ID:** TC-0502
- **Başlık:** Bekleyen onay "approved" olarak işaretlenir
- **Ön Koşul:** PC-005, PC-006; `pending` statusünde onay mevcut
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/approvals/{aid}/decide` ile `{ "decision": "approved" }` gönder
  2. Onayın statusünü kontrol et
- **Beklenen Sonuç:** Onay statusü `approved` olur; `decided_at` dolu
- **Öncelik:** Critical
- **Tip:** Pozitif
- **İlgili Requirement:** BR-005

#### TC-0503: Onay Reddetme
- **ID:** TC-0503
- **Başlık:** Bekleyen onay "rejected" olarak işaretlenir
- **Ön Koşul:** PC-005, PC-006; `pending` statusünde onay mevcut
- **Test Adımları:**
  1. `POST .../decide` ile `{ "decision": "rejected" }` gönder
- **Beklenen Sonuç:** Onay statusü `rejected` olur; `decided_at` dolu
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-005

#### TC-0504: Olmayan Onay ID ile Karar
- **ID:** TC-0504
- **Başlık:** Var olmayan onay ID'si ile karar 404 döner
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/approvals/nonexistent/decide` çağır
- **Beklenen Sonuç:** HTTP 404; `"Onay bulunamadı"`
- **Öncelik:** Medium
- **Tip:** Negatif
- **İlgili Requirement:** BR-005

---

### TS-06: Test Koşuları (Execution)

#### TC-0601: Yeni Koşu Oluşturma
- **ID:** TC-0601
- **Başlık:** Senaryo ID'leri ile yeni test koşusu oluşturma
- **Ön Koşul:** PC-005, PC-006, PC-007; en az 3 senaryo
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/executions` ile `{ "name": "Sprint-1 Koşusu", "scenario_ids": ["sid1", "sid2", "sid3"] }` gönder
  2. Yanıtı kontrol et
- **Beklenen Sonuç:** HTTP 201; `status: "running"`, `scenario_total: 3`, `passed_count: 0`, `failed_count: 0`
- **Öncelik:** Critical
- **Tip:** Pozitif
- **İlgili Requirement:** BR-007

#### TC-0602: Koşu Detayı ve Sonuçları
- **ID:** TC-0602
- **Başlık:** Koşu detayında tüm senaryo sonuçları listelenir
- **Ön Koşul:** PC-005; TC-0601 başarılı
- **Test Adımları:**
  1. `GET /api/v1/tspm/projects/{id}/executions/{runId}` çağır
  2. `results` listesini kontrol et
- **Beklenen Sonuç:** Her senaryo için `pending` statusünde sonuç kaydı var; `scenario_title` dolu
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-007

#### TC-0603: Koşu Sonucu Status Güncelleme
- **ID:** TC-0603
- **Başlık:** Bireysel senaryo sonucu passed/failed olarak güncellenebilir
- **Ön Koşul:** PC-005; koşu oluşturulmuş
- **Test Adımları:**
  1. `PATCH .../results/{resultId}` ile `{ "status": "passed" }` gönder
  2. Koşu detayını tekrar çek ve ilgili sonucun statusünü doğrula
- **Beklenen Sonuç:** Sonuç statusü `passed` olarak güncellenir
- **Öncelik:** Critical
- **Tip:** Pozitif
- **İlgili Requirement:** BR-007

#### TC-0604: Koşu Re-run
- **ID:** TC-0604
- **Başlık:** Mevcut koşu yeniden çalıştırılabilir
- **Ön Koşul:** PC-005; en az 1 tamamlanmış koşu
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/executions/{runId}` (re-run endpoint)
  2. Yeni koşunun adını ve senaryo sayısını kontrol et
- **Beklenen Sonuç:** HTTP 201; yeni koşu adı `"<eski ad> (re-run)"`, aynı senaryo sayısı, tüm sonuçlar `pending`
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-007

#### TC-0605: Olmayan Koşu ID ile Re-run
- **ID:** TC-0605
- **Başlık:** Var olmayan koşu ID'si ile re-run 404 döner
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/executions/nonexistent-id`
- **Beklenen Sonuç:** HTTP 404; `"Koşu bulunamadı"`
- **Öncelik:** Medium
- **Tip:** Negatif
- **İlgili Requirement:** BR-007

#### TC-0606: Boş Senaryo Listesi ile Koşu Oluşturma
- **ID:** TC-0606
- **Başlık:** Boş senaryo listesi ile koşu oluşturma
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../executions` ile `{ "name": "Boş Koşu", "scenario_ids": [] }` gönder
- **Beklenen Sonuç:** HTTP 201; `scenario_total: 0` (koşu oluşur ama sonuç kaydı yok)
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-007

---

### TS-07: Koşu Analitikleri

#### TC-0701: Execution Trends Kontrolü
- **ID:** TC-0701
- **Başlık:** Son 30 günlük koşu trend verileri döner
- **Ön Koşul:** PC-005, PC-006; en az 1 koşu metriği mevcut
- **Test Adımları:**
  1. `GET /api/v1/tspm/projects/{id}/execution-trends?days=30` çağır
  2. `data_points` listesini kontrol et
- **Beklenen Sonuç:** HTTP 200; tarih bazında total, passed, failed, pass_rate verileri döner
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-008

#### TC-0702: Flaky Test Tespiti
- **ID:** TC-0702
- **Başlık:** Passed-Failed arası geçiş yapan senaryolar flaky olarak raporlanır
- **Ön Koşul:** PC-005, PC-006; aynı senaryo farklı koşularda passed ve failed olmuş
- **Test Adımları:**
  1. Senaryo-A'yı koşu-1'de passed, koşu-2'de failed yap
  2. `GET /api/v1/tspm/projects/{id}/flaky-tests` çağır
- **Beklenen Sonuç:** Senaryo-A `flip_count >= 1` ile flaky listesinde görünür
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-008

#### TC-0703: Koşu İstatistikleri
- **ID:** TC-0703
- **Başlık:** Genel koşu istatistikleri doğru hesaplanır
- **Ön Koşul:** PC-005, PC-006; birden fazla koşu
- **Test Adımları:**
  1. `GET /api/v1/tspm/projects/{id}/execution-stats` çağır
  2. `total_executions`, `avg_pass_rate` kontrol et
- **Beklenen Sonuç:** HTTP 200; doğru istatistikler
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-008

---

### TS-08: Akış Editörü (Flows)

#### TC-0801: Yeni Akış Oluşturma
- **ID:** TC-0801
- **Başlık:** Geçerli isimle yeni akış oluşturulur
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/flows` ile `{ "name": "Login Akışı", "description": "Giriş akış diyagramı" }` gönder
- **Beklenen Sonuç:** HTTP 201; id, name, description döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-009

#### TC-0802: Akış Grafı Güncelleme
- **ID:** TC-0802
- **Başlık:** Akışın nodes ve edges verisi güncellenir
- **Ön Koşul:** PC-005, PC-006; akış oluşturulmuş
- **Test Adımları:**
  1. `PUT .../flows/{fid}/graph` ile nodes/edges JSON'u gönder
  2. `GET .../flows/{fid}` ile akış detayını çek
- **Beklenen Sonuç:** Akış detayında güncel nodes ve edges döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-009

#### TC-0803: Boş İsimle Akış Oluşturma
- **ID:** TC-0803
- **Başlık:** Boş isimle akış oluşturulamaz
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../flows` ile `{ "name": "" }` gönder
- **Beklenen Sonuç:** HTTP 422; validation error
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-009

---

### TS-09: Regresyon Setleri

#### TC-0901: Yeni Regresyon Seti Oluşturma
- **ID:** TC-0901
- **Başlık:** Geçerli isimle regresyon seti oluşturulur
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST /api/v1/tspm/projects/{id}/regression-sets` ile `{ "name": "Smoke Seti" }` gönder
- **Beklenen Sonuç:** HTTP 201; `scenario_count: 0`
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-010

#### TC-0902: Regresyon Setine Senaryo Ekleme
- **ID:** TC-0902
- **Başlık:** Regresyon setine senaryolar eklenir
- **Ön Koşul:** PC-005, PC-006; set ve senaryolar oluşturulmuş
- **Test Adımları:**
  1. `POST .../regression-sets/{setId}/add` ile `{ "scenario_ids": ["s1", "s2"] }` gönder
  2. Set detayını kontrol et
- **Beklenen Sonuç:** Set'te 2 senaryo; tekrar aynı ID'ler eklendiğinde sayı artmaz (idempotent)
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-010

#### TC-0903: Regresyon Setine Tekrar Aynı Senaryo Ekleme (Idempotent)
- **ID:** TC-0903
- **Başlık:** Zaten eklenen senaryo ID'si tekrar eklendiğinde duplicate oluşmaz
- **Ön Koşul:** TC-0902 başarılı
- **Test Adımları:**
  1. Aynı senaryo ID'lerini tekrar ekle
  2. Set detayındaki sayıyı kontrol et
- **Beklenen Sonuç:** Senaryo sayısı değişmez
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-010

#### TC-0904: AI Regresyon Seti Önerisi
- **ID:** TC-0904
- **Başlık:** AI projeden regresyon setleri önerir
- **Ön Koşul:** PC-005, PC-006, PC-007; LLM erişilebilir
- **Test Adımları:**
  1. `POST .../regression-sets/suggest` ile `{ "extra_instructions": "" }` gönder
- **Beklenen Sonuç:** HTTP 200; `sets` listesinde en az 1 öneri
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-010

#### TC-0905: Senaryo Olmayan Projede AI Önerisi
- **ID:** TC-0905
- **Başlık:** Senaryosu olmayan projede AI önerisi 400 döner
- **Ön Koşul:** PC-005; senaryo olmayan proje
- **Test Adımları:**
  1. `POST .../regression-sets/suggest` çağır
- **Beklenen Sonuç:** HTTP 400; `"Öneri yapılabilmesi için projede en az bir senaryo olmalı."`
- **Öncelik:** Medium
- **Tip:** Negatif
- **İlgili Requirement:** BR-010

#### TC-0906: AI Önerilerini Kabul Etme
- **ID:** TC-0906
- **Başlık:** AI önerilerinden seçilen setler toplu oluşturulur
- **Ön Koşul:** TC-0904 başarılı
- **Test Adımları:**
  1. `POST .../regression-sets/accept-suggestions` ile önerilen setleri gönder
  2. Set listesini kontrol et
- **Beklenen Sonuç:** HTTP 201; tüm önerilen setler oluşturulur
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-010

---

### TS-10: Gereksinimler ve Kapsam Matrisi

#### TC-1001: Yeni Gereksinim Oluşturma
- **ID:** TC-1001
- **Başlık:** Geçerli bilgilerle gereksinim oluşturulur
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../requirements` ile `{ "external_id": "REQ-001", "title": "Login Fonksiyonu", "priority": "high" }` gönder
- **Beklenen Sonuç:** HTTP 201; `external_id`, `title`, `priority`, `scenario_count: 0` döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-011

#### TC-1002: Senaryo-Gereksinim Bağlantısı
- **ID:** TC-1002
- **Başlık:** Senaryo ile gereksinim başarılı şekilde ilişkilendirilir
- **Ön Koşul:** PC-005, PC-006, PC-007, PC-008
- **Test Adımları:**
  1. `POST .../scenarios/{sid}/requirements` ile `{ "requirement_ids": ["reqId"] }` gönder
  2. Gereksinim listesinde `scenario_count` kontrol et
- **Beklenen Sonuç:** `scenario_count` 1 olur
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-011

#### TC-1003: Duplicate Bağlantı Ekleme (Idempotent)
- **ID:** TC-1003
- **Başlık:** Aynı senaryo-gereksinim bağlantısı tekrar eklendiğinde duplicate oluşmaz
- **Ön Koşul:** TC-1002 başarılı
- **Test Adımları:**
  1. Aynı bağlantıyı tekrar gönder
  2. `scenario_count` kontrol et
- **Beklenen Sonuç:** `scenario_count` hâlâ 1
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-011

#### TC-1004: Coverage Matrix Hesaplama
- **ID:** TC-1004
- **Başlık:** Kapsam matrisi doğru hesaplanır
- **Ön Koşul:** PC-005, PC-006; 3 gereksinim, 2'si senaryoya bağlı, 1'i bağlı değil
- **Test Adımları:**
  1. `GET .../coverage-matrix` çağır
  2. `total_requirements`, `covered_count`, `coverage_percent` kontrol et
- **Beklenen Sonuç:** `total: 3`, `covered: 2`, `coverage_percent: 66.7`
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-011

#### TC-1005: Coverage Gaps Tespiti
- **ID:** TC-1005
- **Başlık:** Senaryo kapsamında olmayan gereksinimler listelenir
- **Ön Koşul:** TC-1004 başarılı
- **Test Adımları:**
  1. `GET .../coverage-gaps` çağır
- **Beklenen Sonuç:** Bağlanmamış 1 gereksinim döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-011

#### TC-1006: Gereksinim Silme ve Cascade
- **ID:** TC-1006
- **Başlık:** Gereksinim silindiğinde senaryo bağlantıları da temizlenir
- **Ön Koşul:** PC-005, PC-006, PC-008; bağlantılı gereksinim
- **Test Adımları:**
  1. `DELETE .../requirements/{reqId}`
  2. Coverage matrix'i kontrol et
- **Beklenen Sonuç:** HTTP 204; gereksinim ve bağlantıları silinir
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-011

#### TC-1007: Boş external_id ile Gereksinim Oluşturma
- **ID:** TC-1007
- **Başlık:** `external_id` boş bırakılamaz
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../requirements` ile `{ "external_id": "", "title": "Test" }` gönder
- **Beklenen Sonuç:** HTTP 422; validation error
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-011

---

### TS-11: Zamanlamalar (Schedules)

#### TC-1101: Zamanlama Oluşturma
- **ID:** TC-1101
- **Başlık:** Cron ifadesi ile zamanlama oluşturulur
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../schedules` ile `{ "name": "Gece Koşusu", "cron_expression": "0 2 * * *", "scenario_ids": ["s1"], "is_active": true }` gönder
- **Beklenen Sonuç:** HTTP 201; zamanlama bilgileri döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-012

#### TC-1102: Zamanlama Tetikleme (Trigger)
- **ID:** TC-1102
- **Başlık:** Zamanlama manuel olarak tetiklendiğinde koşu oluşturulur
- **Ön Koşul:** PC-005, PC-006; zamanlama ve senaryolar mevcut
- **Test Adımları:**
  1. `POST .../schedules/{schedId}/trigger` çağır
  2. Yeni koşuyu kontrol et
- **Beklenen Sonuç:** HTTP 201; koşu adı `"Scheduled: <sched_name>"`, `last_run_at` güncellenir
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-012

#### TC-1103: Senaryosuz Zamanlama Tetikleme
- **ID:** TC-1103
- **Başlık:** Senaryo ataması olmayan zamanlama tetiklendiğinde 400 döner
- **Ön Koşul:** PC-005, PC-006; `scenario_ids: []` ve `regression_set_id: null` olan zamanlama
- **Test Adımları:**
  1. `POST .../schedules/{schedId}/trigger` çağır
- **Beklenen Sonuç:** HTTP 400; `"Zamanlamada senaryo bulunamadı"`
- **Öncelik:** High
- **Tip:** Negatif
- **İlgili Requirement:** BR-012

#### TC-1104: Zamanlama Regression Set'ten Senaryo Çekme
- **ID:** TC-1104
- **Başlık:** Zamanlama tetiklendiğinde `scenario_ids` boşsa regression set'ten çekilir
- **Ön Koşul:** PC-005, PC-006; `scenario_ids: []`, `regression_set_id` dolu ve sette senaryolar var
- **Test Adımları:**
  1. Zamanlama tetikle
  2. Koşudaki senaryo sayısını doğrula
- **Beklenen Sonuç:** Regression set'teki senaryolar ile koşu oluşturulur
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-012

#### TC-1105: Boş Cron Expression ile Zamanlama
- **ID:** TC-1105
- **Başlık:** Boş cron ifadesi ile zamanlama oluşturulamaz
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../schedules` ile `{ "name": "Test", "cron_expression": "" }` gönder
- **Beklenen Sonuç:** HTTP 422; validation error
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-012

---

### TS-12: Test Verisi Yönetimi

#### TC-1201: Test Veri Seti Oluşturma
- **ID:** TC-1201
- **Başlık:** Kolonlar ve satırlarla test veri seti oluşturulur
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../test-data` ile `{ "name": "Login Verileri", "columns": [{"name": "username"}, {"name": "password"}], "rows": [{"username": "user1", "password": "pass1"}] }` gönder
- **Beklenen Sonuç:** HTTP 201; veri seti bilgileri döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-013

#### TC-1202: Senaryoya Veri Bağlama
- **ID:** TC-1202
- **Başlık:** Senaryo adımlarına test verisi parametreleri bağlanır
- **Ön Koşul:** PC-005, PC-006, PC-007; test veri seti oluşturulmuş
- **Test Adımları:**
  1. `POST .../scenarios/{sid}/bind-data` ile `{ "data_set_id": "dsId", "parameter_mapping": {"kullanici": "username"} }` gönder
- **Beklenen Sonuç:** HTTP 201; binding kaydı oluşturulur
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-013

#### TC-1203: Expanded Scenario (Parametre Genişletme)
- **ID:** TC-1203
- **Başlık:** Veri satırları ile senaryo adımları genişletilir
- **Ön Koşul:** TC-1202 başarılı; adımlarda `{{kullanici}}` yer tutucusu var
- **Test Adımları:**
  1. `GET .../scenarios/{sid}/expanded` çağır
  2. `expanded_rows` listesini kontrol et
- **Beklenen Sonuç:** Her veri satırı için adımlar genişletilmiş; `{{kullanici}}` yerine gerçek değerler yerleştirilmiş
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-013

#### TC-1204: Olmayan Veri Seti ile Binding
- **ID:** TC-1204
- **Başlık:** Var olmayan veri seti ID'si ile bağlama 404 döner
- **Ön Koşul:** PC-005, PC-006, PC-007
- **Test Adımları:**
  1. `POST .../scenarios/{sid}/bind-data` ile `{ "data_set_id": "nonexistent" }` gönder
- **Beklenen Sonuç:** HTTP 404; `"Veri seti bulunamadı"`
- **Öncelik:** Medium
- **Tip:** Negatif
- **İlgili Requirement:** BR-013

---

### TS-13: Entegrasyonlar

#### TC-1301: Entegrasyon Oluşturma
- **ID:** TC-1301
- **Başlık:** Yeni entegrasyon kaydı oluşturulur
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../integrations` ile `{ "provider": "jira", "config": {"url": "https://jira.example.com"} }` gönder
- **Beklenen Sonuç:** HTTP 201; entegrasyon bilgileri döner
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-014

#### TC-1302: Entegrasyon Sync
- **ID:** TC-1302
- **Başlık:** Entegrasyon sync işlemi `last_sync_at` günceller
- **Ön Koşul:** TC-1301 başarılı
- **Test Adımları:**
  1. `POST .../integrations/{intgId}/sync` çağır
  2. `last_sync_at` değerini kontrol et
- **Beklenen Sonuç:** HTTP 200; `last_sync_at` güncellenir; `synced_count: 0` (stub)
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-014

#### TC-1303: Boş Provider ile Entegrasyon
- **ID:** TC-1303
- **Başlık:** Provider alanı boş bırakılamaz
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../integrations` ile `{ "provider": "" }` gönder
- **Beklenen Sonuç:** HTTP 422; validation error
- **Öncelik:** Low
- **Tip:** Boundary
- **İlgili Requirement:** BR-014

---

### TS-14: API Testi

#### TC-1401: API Koleksiyonu Oluşturma
- **ID:** TC-1401
- **Başlık:** API test koleksiyonu oluşturulur
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../api-tests/collections` ile `{ "name": "Auth API", "base_url": "http://localhost:8000" }` gönder
- **Beklenen Sonuç:** HTTP 201; koleksiyon bilgileri döner; `request_count: 0`
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-015

#### TC-1402: Koleksiyona Request Ekleme
- **ID:** TC-1402
- **Başlık:** Koleksiyona HTTP request eklenir
- **Ön Koşul:** TC-1401 başarılı
- **Test Adımları:**
  1. `POST .../collections/{colId}/requests` ile `{ "name": "Health Check", "method": "GET", "path": "/health" }` gönder
- **Beklenen Sonuç:** HTTP 201; request bilgileri döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-015

#### TC-1403: Koleksiyon Çalıştırma
- **ID:** TC-1403
- **Başlık:** Koleksiyondaki tüm request'ler sırayla çalıştırılır
- **Ön Koşul:** TC-1402 başarılı; en az 1 request
- **Test Adımları:**
  1. `POST .../collections/{colId}/run` çağır
  2. Yanıttaki `results` listesini kontrol et
- **Beklenen Sonuç:** HTTP 200; her request için `status_code`, `duration_ms`, `passed` alanları döner
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-015

#### TC-1404: Erişilemeyen URL ile Koleksiyon Çalıştırma
- **ID:** TC-1404
- **Başlık:** Erişilemeyen base_url ile request hatası döner
- **Ön Koşul:** PC-005; `base_url: "http://unreachable:9999"` olan koleksiyon
- **Test Adımları:**
  1. Koleksiyonu çalıştır
  2. Results'daki `passed` ve `error` alanlarını kontrol et
- **Beklenen Sonuç:** `passed: false`, `error` alanı dolu, `status_code: 0`
- **Öncelik:** Medium
- **Tip:** Exception
- **İlgili Requirement:** BR-015

---

### TS-15: Proje Üyeleri

#### TC-1501: Proje Üyesi Ekleme
- **ID:** TC-1501
- **Başlık:** Projeye yeni üye eklenir
- **Ön Koşul:** PC-005, PC-006; başka bir user_id mevcut
- **Test Adımları:**
  1. `POST .../members` ile `{ "user_id": "otherUserId", "role": "operator" }` gönder
- **Beklenen Sonuç:** HTTP 201; üye bilgileri döner; `role: "operator"`
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-016

#### TC-1502: Proje Üyesi Silme
- **ID:** TC-1502
- **Başlık:** Proje üyesi kaldırılır
- **Ön Koşul:** TC-1501 başarılı
- **Test Adımları:**
  1. `DELETE .../members/{memberId}`
  2. Üye listesini kontrol et
- **Beklenen Sonuç:** HTTP 204; üye listede görünmez
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-016

#### TC-1503: Varsayılan Rol Kontrolü
- **ID:** TC-1503
- **Başlık:** Rol belirtilmezse varsayılan `viewer` atanır
- **Ön Koşul:** PC-005, PC-006
- **Test Adımları:**
  1. `POST .../members` ile `{ "user_id": "someId" }` gönder (rol belirtilmez)
- **Beklenen Sonuç:** HTTP 201; `role: "viewer"`
- **Öncelik:** Medium
- **Tip:** Pozitif
- **İlgili Requirement:** BR-016

---

### TS-16: Dashboard

#### TC-1601: Dashboard İstatistikleri
- **ID:** TC-1601
- **Başlık:** Proje dashboard'u doğru istatistikleri döner
- **Ön Koşul:** PC-005, PC-006; projede senaryolar, onaylar, importlar ve koşular var
- **Test Adımları:**
  1. `GET /api/v1/tspm/projects/{id}/dashboard` çağır
  2. `scenario_count`, `pending_approvals`, `import_count`, `execution_count`, `latest_run_pass_rate` kontrol et
- **Beklenen Sonuç:** HTTP 200; tüm sayaçlar doğru hesaplanmış
- **Öncelik:** High
- **Tip:** Pozitif
- **İlgili Requirement:** BR-002, BR-008

#### TC-1602: Boş Proje Dashboard'u
- **ID:** TC-1602
- **Başlık:** Hiç verisi olmayan proje dashboard'u sıfır değerler döner
- **Ön Koşul:** PC-005; yeni oluşturulmuş boş proje
- **Test Adımları:**
  1. `GET .../dashboard` çağır
- **Beklenen Sonuç:** Tüm sayaçlar 0; `latest_run_pass_rate: null`
- **Öncelik:** Medium
- **Tip:** Boundary
- **İlgili Requirement:** BR-002

---

## 5. BDD Feature Özetleri (Gherkin-Ready)

```gherkin
Feature: Kimlik Doğrulama
  Kullanıcılar JWT tabanlı token ile oturum açar ve korumalı kaynaklara erişir.

  Scenario: Başarılı Login
    Given admin kullanıcısı mevcut
    When geçerli e-posta ve parola ile login isteği gönderilir
    Then HTTP 200 ve access_token döner
    And audit log kaydı oluşturulur

  Scenario: Hatalı Parola ile Login
    Given admin kullanıcısı mevcut
    When yanlış parola ile login isteği gönderilir
    Then HTTP 401 ve "E-posta veya parola hatalı" mesajı döner

  Scenario: Devre Dışı Hesap Login
    Given devre dışı bırakılmış kullanıcı mevcut
    When o kullanıcının bilgileriyle login isteği gönderilir
    Then HTTP 403 ve "Hesap devre dışı" mesajı döner

Feature: Proje Yönetimi
  Test ekipleri projelerini oluşturur, listeler ve yönetir.

  Scenario: Yeni Proje Oluşturma
    Given kullanıcı oturum açmış
    When geçerli isim ve açıklama ile proje oluşturma isteği gönderilir
    Then HTTP 201 ve proje bilgileri döner
    And proje archived=false olarak kaydedilir

  Scenario: Boş İsimle Proje Oluşturma
    Given kullanıcı oturum açmış
    When isim alanı boş bırakılarak proje oluşturma isteği gönderilir
    Then HTTP 422 validation hatası döner

Feature: Senaryo Yönetimi
  Senaryolar oluşturulur, güncellenir, versiyonlanır ve toplu işlem yapılır.

  Scenario: Senaryo Oluşturma ve Varsayılan Status
    Given proje mevcut
    When yeni senaryo oluşturulur
    Then senaryo "draft" statusünde ve version=1 olarak kaydedilir

  Scenario: Senaryo Güncelleme ile Otomatik Versiyonlama
    Given proje ve senaryo mevcut
    When senaryo başlığı güncellenir
    Then mevcut durum version tablosuna kaydedilir
    And current_version 1 artırılır

  Scenario: Toplu Senaryo Silme
    Given projede birden fazla senaryo mevcut
    When seçilen senaryo ID'leri ile toplu silme isteği gönderilir
    Then yalnızca bu projeye ait seçili senaryolar silinir

Feature: BDD Senaryo Üretimi
  Analiz dokümanından AI ile BDD senaryoları üretilir ve kaydedilir.

  Scenario: Analiz Metninden BDD Üretimi
    Given proje mevcut ve LLM servisi erişilebilir
    When analiz metni ile BDD üretim isteği gönderilir
    Then Gherkin formatında senaryo listesi döner

  Scenario: Üretilen Senaryoları Kaydetme
    Given BDD senaryoları üretilmiş
    When kaydetme isteği gönderilir
    Then tüm senaryolar draft statusünde kaydedilir

Feature: Onay Kuyruğu
  AI taslakları onay kuyruğundan geçirilerek senaryo havuzuna yazılır.

  Scenario: Onay Kabul
    Given pending statusünde onay mevcut
    When "approved" kararı verilir
    Then onay statusü approved olur ve decided_at kaydedilir

Feature: Test Koşuları
  Senaryolar koşulara eklenir, çalıştırılır ve sonuçları takip edilir.

  Scenario: Yeni Koşu Oluşturma
    Given projede senaryolar mevcut
    When senaryo ID'leri ile koşu oluşturma isteği gönderilir
    Then koşu "running" statusünde başlar
    And her senaryo için "pending" sonuç kaydı oluşturulur

  Scenario: Koşu Re-run
    Given tamamlanmış koşu mevcut
    When re-run isteği gönderilir
    Then aynı senaryolarla yeni koşu oluşturulur
    And koşu adına "(re-run)" eklenir

Feature: Gereksinimler ve Kapsam
  Gereksinimler senaryolara bağlanarak kapsam matrisi hesaplanır.

  Scenario: Kapsam Matrisi Hesaplama
    Given projede gereksinimler ve senaryo bağlantıları mevcut
    When kapsam matrisi istenir
    Then her gereksinim için bağlı senaryolar ve kapsama yüzdesi döner

  Scenario: Kapsam Boşluklarını Tespit
    Given bazı gereksinimler senaryoya bağlı değil
    When coverage-gaps istenir
    Then bağlantısız gereksinimler listelenir

Feature: Regresyon Setleri
  Senaryolar regresyon setlerine gruplanır; AI öneri yapar.

  Scenario: AI Regresyon Seti Önerisi
    Given projede senaryolar mevcut
    When AI öneri isteği gönderilir
    Then kategorize edilmiş set önerileri döner

Feature: Zamanlamalar
  Cron ifadesi ile periyodik koşular zamanlanır.

  Scenario: Zamanlama Tetikleme
    Given zamanlama ve senaryoları mevcut
    When zamanlama tetiklendiğinde
    Then ilgili senaryolarla yeni koşu oluşturulur
    And last_run_at güncellenir

Feature: Test Verisi Yönetimi
  Veri setleri senaryolara parametrik olarak bağlanır.

  Scenario: Parametre Genişletme
    Given senaryo adımlarında yer tutucular var
    And veri seti bağlanmış
    When expanded senaryo istenir
    Then her veri satırı için adımlar genişletilmiş döner
```

---

## 6. Traceability Matrix (İzlenebilirlik Matrisi)

| Requirement | Test Senaryoları | Kapsam Durumu |
|-------------|-----------------|---------------|
| **BR-001** Kimlik Doğrulama | TC-0101, TC-0102, TC-0103, TC-0104, TC-0105, TC-0106, TC-0107, TC-0108, TC-0109, TC-0110 | ✅ Tam |
| **BR-002** Proje Yönetimi | TC-0201, TC-0202, TC-0203, TC-0204, TC-0205, TC-0206, TC-1601, TC-1602 | ✅ Tam |
| **BR-003** Senaryo Yönetimi | TC-0301, TC-0302, TC-0303, TC-0304, TC-0305, TC-0306, TC-0307 | ✅ Tam |
| **BR-004** BDD Üretimi | TC-0401, TC-0402, TC-0403, TC-0404 | ✅ Tam |
| **BR-005** Onay Kuyruğu | TC-0501, TC-0502, TC-0503, TC-0504 | ✅ Tam |
| **BR-006** İçe Aktarma | TC-0601 (dolaylı - import endpoint stub) | ⚠️ Kısmi |
| **BR-007** Test Koşuları | TC-0601, TC-0602, TC-0603, TC-0604, TC-0605, TC-0606 | ✅ Tam |
| **BR-008** Koşu Analitikleri | TC-0701, TC-0702, TC-0703, TC-1601, TC-1602 | ✅ Tam |
| **BR-009** Akış Editörü | TC-0801, TC-0802, TC-0803 | ✅ Tam |
| **BR-010** Regresyon Setleri | TC-0901, TC-0902, TC-0903, TC-0904, TC-0905, TC-0906 | ✅ Tam |
| **BR-011** Gereksinimler/Kapsam | TC-1001, TC-1002, TC-1003, TC-1004, TC-1005, TC-1006, TC-1007 | ✅ Tam |
| **BR-012** Zamanlamalar | TC-1101, TC-1102, TC-1103, TC-1104, TC-1105 | ✅ Tam |
| **BR-013** Test Verisi | TC-1201, TC-1202, TC-1203, TC-1204 | ✅ Tam |
| **BR-014** Entegrasyonlar | TC-1301, TC-1302, TC-1303 | ✅ Tam |
| **BR-015** API Testi | TC-1401, TC-1402, TC-1403, TC-1404 | ✅ Tam |
| **BR-016** Proje Üyeleri | TC-1501, TC-1502, TC-1503 | ✅ Tam |
| **BR-017** Versiyonlama | TC-0303, TC-0308, TC-0309 | ✅ Tam |

---

## 7. Test Senaryo Dağılım Özeti

| Tip | Sayı |
|-----|------|
| Pozitif | 42 |
| Negatif | 16 |
| Boundary | 16 |
| Exception | 1 |
| **Toplam** | **75** |

| Öncelik | Sayı |
|---------|------|
| Critical | 10 |
| High | 35 |
| Medium | 25 |
| Low | 5 |

---

## 8. Ek Notlar

- **Import modülü** şu an stub aşamasında; n8n pipeline entegrasyonu tamamlandığında kapsamlı test senaryoları eklenmelidir.
- **RBAC tabanlı izin testleri** mevcut implementasyonda router seviyesinde kontrol edilmemektedir; `viewer` rolünün yazma işlemlerini yapamadığının testi ilerleyen fazlarda eklenmelidir.
- **Rate Limiting** testleri (429 Too Many Requests) platform enhancement testlerinde ayrıca ele alınmalıdır.
- **Audit Log** testleri tüm CRUD operasyonları için genişletilebilir.
- **WebSocket** tabanlı bildirim senaryoları frontend bağlamında test edilmelidir.
