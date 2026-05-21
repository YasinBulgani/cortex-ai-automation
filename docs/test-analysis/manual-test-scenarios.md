# BGTS Test Dönüşüm — Manuel Test Senaryoları

**Hazırlayan:** QA Analiz Ekibi  
**Tarih:** 2026-04-03  
**Versiyon:** 1.0

---

## Kısaltmalar

| Kısaltma | Açıklama |
|----------|----------|
| P0 | Kritik öncelik (blokçu) |
| P1 | Yüksek öncelik |
| P2 | Orta öncelik |
| P3 | Düşük öncelik |
| FT | Fonksiyonel Test |
| ST | Smoke Test |
| RT | Regresyon Testi |
| IT | Entegrasyon Testi |
| AT | API Testi |
| UT | UI Testi |
| PT | Performans Testi |

---

## 1. Kimlik Doğrulama (Authentication)

### TC-AUTH-001: Başarılı kullanıcı girişi

| Alan | Değer |
|------|-------|
| **ID** | TC-AUTH-001 |
| **Başlık** | Geçerli kimlik bilgileri ile başarılı giriş |
| **Önkoşullar** | Aktif kullanıcı hesabı mevcut (email: test@bgts.com, parola: Test1234!) |
| **Öncelik** | P0 |
| **Tür** | FT, ST |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/auth/login` endpoint'ine `{"email": "test@bgts.com", "password": "Test1234!"}` gönder | HTTP 200 döner |
| 2 | Yanıt gövdesini kontrol et | `access_token` alanı mevcut ve boş değil |
| 3 | Token formatını doğrula | JWT formatında (header.payload.signature) |
| 4 | `/login` sayfasında form alanlarını doldur ve giriş butonuna tıkla | `/projects` sayfasına yönlendirme |

---

### TC-AUTH-002: Geçersiz parola ile giriş reddi

| Alan | Değer |
|------|-------|
| **ID** | TC-AUTH-002 |
| **Başlık** | Hatalı parola ile giriş denemesi reddedilmeli |
| **Önkoşullar** | Aktif kullanıcı hesabı mevcut |
| **Öncelik** | P0 |
| **Tür** | FT, ST |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/auth/login` ile yanlış parola gönder | HTTP 401 döner |
| 2 | Yanıt gövdesini kontrol et | `detail`: "E-posta veya parola hatalı" |
| 3 | Token alanını kontrol et | `access_token` alanı mevcut olmamalı |

---

### TC-AUTH-003: Geçersiz e-posta ile giriş reddi

| Alan | Değer |
|------|-------|
| **ID** | TC-AUTH-003 |
| **Başlık** | Sistemde olmayan e-posta ile giriş denemesi |
| **Önkoşullar** | — |
| **Öncelik** | P0 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/auth/login` ile olmayan e-posta gönder | HTTP 401 döner |
| 2 | Yanıt mesajını kontrol et | "E-posta veya parola hatalı" (bilgi sızdırmaz) |

---

### TC-AUTH-004: Devre dışı hesap ile giriş engeli

| Alan | Değer |
|------|-------|
| **ID** | TC-AUTH-004 |
| **Başlık** | Devre dışı bırakılmış hesap ile giriş engellenmeli |
| **Önkoşullar** | `is_active=false` olan kullanıcı hesabı |
| **Öncelik** | P0 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Devre dışı hesap ile login isteği gönder | HTTP 403 döner |
| 2 | Yanıt mesajını kontrol et | "Hesap devre dışı" |

---

### TC-AUTH-005: JWT token ile kullanıcı bilgisi sorgulama

| Alan | Değer |
|------|-------|
| **ID** | TC-AUTH-005 |
| **Başlık** | /me endpoint'i ile oturum sahibi bilgileri |
| **Önkoşullar** | Geçerli JWT token |
| **Öncelik** | P0 |
| **Tür** | FT, AT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/auth/me` ile geçerli token gönder | HTTP 200 döner |
| 2 | Yanıt gövdesini kontrol et | `id`, `email`, `roles`, `permissions` alanları mevcut |
| 3 | `roles` alanını kontrol et | Kullanıcının atanmış rolleri listelenmeli |

---

### TC-AUTH-006: Geçersiz/süresi dolmuş token ile erişim reddi

| Alan | Değer |
|------|-------|
| **ID** | TC-AUTH-006 |
| **Başlık** | Geçersiz token ile korumalı endpoint erişimi engellenmeli |
| **Önkoşullar** | Geçersiz veya süresi dolmuş token |
| **Öncelik** | P0 |
| **Tür** | FT, AT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/auth/me` ile geçersiz token gönder | HTTP 401 döner |
| 2 | `GET /api/v1/tspm/projects` ile token olmadan gönder | HTTP 401 döner |

---

### TC-AUTH-007: Boş form alanları ile giriş denemesi

| Alan | Değer |
|------|-------|
| **ID** | TC-AUTH-007 |
| **Başlık** | Eksik alanlar ile giriş formu validasyonu |
| **Önkoşullar** | — |
| **Öncelik** | P1 |
| **Tür** | FT, UT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `/login` sayfasında e-posta boş bırakıp giriş butonuna tıkla | Validasyon hatası gösterilmeli |
| 2 | E-posta doldur, parola boş bırakıp giriş butonuna tıkla | Validasyon hatası gösterilmeli |
| 3 | `POST /api/v1/auth/login` ile boş body gönder | HTTP 422 (Validation Error) döner |

---

### TC-AUTH-008: SQL injection denemesi

| Alan | Değer |
|------|-------|
| **ID** | TC-AUTH-008 |
| **Başlık** | Giriş alanlarında SQL injection koruması |
| **Önkoşullar** | — |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Email alanına `' OR '1'='1` gönder | HTTP 401 döner (SQL injection çalışmamalı) |
| 2 | Parola alanına `'; DROP TABLE users;--` gönder | HTTP 401 döner, tablo sağlam kalmalı |

---

## 2. Proje Yönetimi (Project Management)

### TC-PRJ-001: Yeni proje oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-PRJ-001 |
| **Başlık** | Başarılı proje oluşturma |
| **Önkoşullar** | Geçerli JWT token |
| **Öncelik** | P0 |
| **Tür** | FT, ST |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects` ile `{"name": "Test Projesi", "description": "Açıklama"}` gönder | HTTP 201 döner |
| 2 | Yanıt gövdesini kontrol et | `id`, `name`, `description`, `created_at` alanları mevcut |
| 3 | `name` değerini doğrula | "Test Projesi" |

---

### TC-PRJ-002: Proje listesi sorgulama

| Alan | Değer |
|------|-------|
| **ID** | TC-PRJ-002 |
| **Başlık** | Tüm projelerin listelenmesi |
| **Önkoşullar** | En az 1 proje mevcut, geçerli JWT |
| **Öncelik** | P1 |
| **Tür** | FT, ST |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects` isteği gönder | HTTP 200 döner |
| 2 | Yanıt gövdesini kontrol et | JSON dizisi döner |
| 3 | Sıralamayı kontrol et | `created_at` azalan sırada |

---

### TC-PRJ-003: Proje dashboard istatistikleri

| Alan | Değer |
|------|-------|
| **ID** | TC-PRJ-003 |
| **Başlık** | Proje dashboard verilerinin doğruluğu |
| **Önkoşullar** | Proje mevcut, senaryolar, koşular, onaylar oluşturulmuş |
| **Öncelik** | P1 |
| **Tür** | FT, IT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/{projectId}/dashboard` isteği gönder | HTTP 200 döner |
| 2 | `scenario_count` kontrol et | Gerçek senaryo sayısı ile eşleşmeli |
| 3 | `pending_approvals` kontrol et | Bekleyen onay sayısı ile eşleşmeli |
| 4 | `execution_count` kontrol et | Koşu sayısı ile eşleşmeli |
| 5 | `latest_run_pass_rate` kontrol et | Null veya 0-100 arasında yüzde |

---

### TC-PRJ-004: Olmayan proje ID ile erişim

| Alan | Değer |
|------|-------|
| **ID** | TC-PRJ-004 |
| **Başlık** | Geçersiz proje ID ile 404 hatası |
| **Önkoşullar** | Geçerli JWT |
| **Öncelik** | P1 |
| **Tür** | FT, AT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/nonexistent-id/dashboard` gönder | HTTP 404 döner |
| 2 | Yanıt mesajını kontrol et | "Proje bulunamadı" |

---

### TC-PRJ-005: Proje üyesi ekleme

| Alan | Değer |
|------|-------|
| **ID** | TC-PRJ-005 |
| **Başlık** | Projeye yeni üye ekleme |
| **Önkoşullar** | Proje mevcut, eklenecek kullanıcı mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/members` ile `{"user_id": "...", "role": "tester"}` gönder | HTTP 201 döner |
| 2 | `GET /api/v1/tspm/projects/{id}/members` ile üye listesini sorgula | Eklenen üye listede |

---

### TC-PRJ-006: Proje üyesi çıkarma

| Alan | Değer |
|------|-------|
| **ID** | TC-PRJ-006 |
| **Başlık** | Projeden üye çıkarma |
| **Önkoşullar** | Proje üyesi mevcut |
| **Öncelik** | P3 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `DELETE /api/v1/tspm/projects/{id}/members/{memberId}` gönder | HTTP 204 döner |
| 2 | Üye listesini tekrar sorgula | Çıkarılan üye listede olmamalı |

---

## 3. Senaryo Yönetimi (Scenario Management)

### TC-SCN-001: Yeni senaryo oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-SCN-001 |
| **Başlık** | Projeye yeni test senaryosu ekleme |
| **Önkoşullar** | Proje mevcut, geçerli JWT |
| **Öncelik** | P0 |
| **Tür** | FT, ST |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/scenarios` ile senaryo verisi gönder | HTTP 201 döner |
| 2 | Yanıtta `id`, `title`, `status`, `current_version` kontrol et | Tüm alanlar dolu, `current_version=1` |
| 3 | Oluşturulan senaryoyu `GET` ile sorgula | Aynı veri döner |

---

### TC-SCN-002: Senaryo güncelleme ve versiyon artışı

| Alan | Değer |
|------|-------|
| **ID** | TC-SCN-002 |
| **Başlık** | Senaryo güncellenince versiyon numarası artmalı |
| **Önkoşullar** | Mevcut senaryo |
| **Öncelik** | P0 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Mevcut senaryo `current_version` değerini not al | Örneğin `1` |
| 2 | `PUT /api/v1/tspm/projects/{id}/scenarios/{scenarioId}` ile güncelleme gönder | HTTP 200 döner |
| 3 | `current_version` kontrol et | `2` (bir artmış) |
| 4 | Versiyon geçmişini sorgula | Önceki versiyon kaydedilmiş olmalı |

---

### TC-SCN-003: Senaryo listeleme ve arama

| Alan | Değer |
|------|-------|
| **ID** | TC-SCN-003 |
| **Başlık** | Senaryo listesinde arama filtrelemesi |
| **Önkoşullar** | Birden fazla senaryo mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/{id}/scenarios` ile tam liste al | Tüm senaryolar döner |
| 2 | `GET /api/v1/tspm/projects/{id}/scenarios?q=login` ile arama yap | Sadece başlığında "login" geçen senaryolar |
| 3 | Olmayan bir terimle arama yap | Boş dizi döner |

---

### TC-SCN-004: Senaryo toplu silme

| Alan | Değer |
|------|-------|
| **ID** | TC-SCN-004 |
| **Başlık** | Birden fazla senaryonun toplu silinmesi |
| **Önkoşullar** | Birden fazla senaryo mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | 3 senaryo oluştur, ID'leri kaydet | 3 senaryo mevcut |
| 2 | `POST /api/v1/tspm/projects/{id}/scenarios/bulk-delete` ile 3 ID gönder | HTTP 204 döner |
| 3 | Silinen senaryoları GET ile sorgula | HTTP 404 döner |

---

### TC-SCN-005: BDD senaryo üretimi (AI)

| Alan | Değer |
|------|-------|
| **ID** | TC-SCN-005 |
| **Başlık** | Analiz metninden BDD senaryosu üretme |
| **Önkoşullar** | Proje mevcut, AI servisi erişilebilir |
| **Öncelik** | P0 |
| **Tür** | FT, IT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/scenarios/generate-bdd` ile analiz metni gönder | HTTP 200 döner |
| 2 | Yanıtta `scenarios` dizisini kontrol et | En az 1 senaryo üretilmiş |
| 3 | Her senaryoda `title`, `description`, `gherkin`, `steps` kontrol et | Tüm alanlar dolu |

---

### TC-SCN-006: BDD senaryoları toplu kaydetme

| Alan | Değer |
|------|-------|
| **ID** | TC-SCN-006 |
| **Başlık** | Üretilen BDD senaryolarını veritabanına kaydetme |
| **Önkoşullar** | BDD üretimi yapılmış |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/scenarios/save-bdd` ile senaryo listesi gönder | HTTP 201 döner |
| 2 | Yanıttaki senaryo sayısını kontrol et | Gönderilen sayı ile eşleşmeli |
| 3 | Her senaryonun `status` alanını kontrol et | `"draft"` olmalı |

---

### TC-SCN-007: Senaryo versiyon geçmişi

| Alan | Değer |
|------|-------|
| **ID** | TC-SCN-007 |
| **Başlık** | Senaryo versiyon geçmişi sorgulama |
| **Önkoşullar** | Senaryo en az 2 kez güncellenmiş |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/{id}/scenarios/{scenarioId}/versions` | HTTP 200, versiyon listesi |
| 2 | Versiyon sırasını kontrol et | Azalan sırada (en yeni en üstte) |
| 3 | Her versiyonda `title`, `description`, `steps`, `status` kontrol et | Tüm snapshot alanları mevcut |

---

### TC-SCN-008: Versiyon karşılaştırma (diff)

| Alan | Değer |
|------|-------|
| **ID** | TC-SCN-008 |
| **Başlık** | İki versiyon arasındaki farkları görüntüleme |
| **Önkoşullar** | Senaryo en az 2 versiyonlu |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../versions/1/diff/2` ile diff isteği gönder | HTTP 200 döner |
| 2 | `title_changed`, `steps_changed` gibi boolean alanları kontrol et | Değişen alanlar `true` |
| 3 | `v1_snapshot` ve `v2_snapshot` kontrol et | Her iki versiyon snapshot'ı mevcut |

---

### TC-SCN-009: Başka projeye ait senaryoya erişim engeli

| Alan | Değer |
|------|-------|
| **ID** | TC-SCN-009 |
| **Başlık** | Farklı projeye ait senaryo erişim kontrolü |
| **Önkoşullar** | İki farklı proje, A projesinin senaryosu |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Proje B ID ile Proje A senaryosunu sorgula | HTTP 404 döner |
| 2 | Yanıt mesajını kontrol et | "Senaryo bulunamadı" |

---

## 4. Onay İş Akışı (Approval Workflow)

### TC-APR-001: Onay listesi sorgulama

| Alan | Değer |
|------|-------|
| **ID** | TC-APR-001 |
| **Başlık** | Proje onay kuyruğunu listeleme |
| **Önkoşullar** | Projede onay kayıtları mevcut |
| **Öncelik** | P1 |
| **Tür** | FT, ST |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/tspm/projects/{id}/approvals` isteği gönder | HTTP 200, onay listesi |
| 2 | Sıralamayı kontrol et | `created_at` azalan sırada |
| 3 | Her onay kaydında `status`, `project_id` kontrol et | Doğru proje ID'sine ait |

---

### TC-APR-002: Onay kararı — Onayla

| Alan | Değer |
|------|-------|
| **ID** | TC-APR-002 |
| **Başlık** | Bekleyen onayı onaylama |
| **Önkoşullar** | `status=pending` olan onay kaydı |
| **Öncelik** | P0 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/approvals/{approvalId}/decide` ile `{"decision": "approved"}` gönder | HTTP 200, `{"ok": true}` |
| 2 | Onayı tekrar sorgula | `status` = `"approved"` |
| 3 | `decided_at` alanını kontrol et | Null değil, güncel zaman damgası |

---

### TC-APR-003: Onay kararı — Reddet

| Alan | Değer |
|------|-------|
| **ID** | TC-APR-003 |
| **Başlık** | Bekleyen onayı reddetme |
| **Önkoşullar** | `status=pending` olan onay kaydı |
| **Öncelik** | P0 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../approvals/{approvalId}/decide` ile `{"decision": "rejected"}` gönder | HTTP 200 |
| 2 | Onay durumunu kontrol et | `status` = `"rejected"` |

---

### TC-APR-004: Olmayan onay ID ile karar

| Alan | Değer |
|------|-------|
| **ID** | TC-APR-004 |
| **Başlık** | Geçersiz onay ID ile karar verme hatası |
| **Önkoşullar** | — |
| **Öncelik** | P1 |
| **Tür** | FT, AT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Olmayan `approvalId` ile decide isteği gönder | HTTP 404, "Onay bulunamadı" |

---

### TC-APR-005: Onay sayfası UI — Split View

| Alan | Değer |
|------|-------|
| **ID** | TC-APR-005 |
| **Başlık** | Onay sayfasında kaynak ve AI taslağı yan yana görüntüleme |
| **Önkoşullar** | Bekleyen onay mevcut |
| **Öncelik** | P1 |
| **Tür** | UT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `/p/{projectId}/approvals` sayfasını aç | Onay listesi görüntülenir |
| 2 | Bir onay kaydına tıkla | Split view açılır |
| 3 | Sol panelde kaynak metni kontrol et | Kaynak doküman/metin gösterilir |
| 4 | Sağ panelde AI taslağını kontrol et | AI tarafından üretilen senaryo taslağı |
| 5 | Onayla/Reddet butonlarını kontrol et | Her iki buton aktif ve tıklanabilir |

---

## 5. İçe Aktarma Akışı (Import Flow)

### TC-IMP-001: Dosya içe aktarma oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-IMP-001 |
| **Başlık** | Dosya ile içe aktarma başlatma |
| **Önkoşullar** | Proje mevcut |
| **Öncelik** | P0 |
| **Tür** | FT, ST |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/imports` ile `{"filename": "test.xlsx", "raw_text": "..."}` gönder | HTTP 201 döner |
| 2 | Yanıtta `id`, `filename`, `status` kontrol et | `status` = `"completed"` |
| 3 | `scenario_count` kontrol et | 0 veya pozitif sayı |

---

### TC-IMP-002: İçe aktarma sayfası UI akışı

| Alan | Değer |
|------|-------|
| **ID** | TC-IMP-002 |
| **Başlık** | İçe aktarma sayfasında dosya yükleme akışı |
| **Önkoşullar** | Proje mevcut |
| **Öncelik** | P1 |
| **Tür** | UT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `/p/{projectId}/import` sayfasını aç | İçe aktarma formu görünür |
| 2 | Dosya seçim alanına test dosyası yükle | Dosya adı görüntülenir |
| 3 | Yükleme butonuna tıkla | İlerleme çubuğu gösterilir |
| 4 | İşlem tamamlanınca | Durum ve log bilgileri gösterilir |

---

### TC-IMP-003: Geçersiz dosya formatı ile içe aktarma

| Alan | Değer |
|------|-------|
| **ID** | TC-IMP-003 |
| **Başlık** | Desteklenmeyen dosya formatı kontrolü |
| **Önkoşullar** | — |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `.exe` uzantılı dosya ile import denemesi | Hata mesajı veya validasyon uyarısı |

---

## 6. Sentetik Veri ve Test Verisi (Synthetic Data)

### TC-SYN-001: Backend veri seti yükleme ve analiz

| Alan | Değer |
|------|-------|
| **ID** | TC-SYN-001 |
| **Başlık** | CSV/JSON dosyası yükleme ve yapı analizi |
| **Önkoşullar** | Geçerli JWT |
| **Öncelik** | P1 |
| **Tür** | FT, AT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/upload` ile CSV dosyası yükle | HTTP 200, dosya ID döner |
| 2 | `POST /api/v1/analyze` ile dosya ID gönder | Sütun tipleri, istatistikler döner |
| 3 | `POST /api/v1/classify` ile dosyayı sınıflandır | Veri sınıflandırma sonuçları |

---

### TC-SYN-002: Sentetik veri üretimi

| Alan | Değer |
|------|-------|
| **ID** | TC-SYN-002 |
| **Başlık** | Yüklenen veri setinden sentetik veri üretme |
| **Önkoşullar** | Veri seti yüklenmiş ve analiz edilmiş |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/generate` ile üretim parametreleri gönder | İş ID döner |
| 2 | `GET /api/v1/jobs/{jobId}` ile durumu sorgula | `status` alanı güncellenmeli |
| 3 | İş tamamlanınca sonuç verisi kontrol et | İstenilen sayıda satır üretilmiş |

---

### TC-SYN-003: PII tespiti

| Alan | Değer |
|------|-------|
| **ID** | TC-SYN-003 |
| **Başlık** | Kişisel veri (PII) tespiti |
| **Önkoşullar** | PII içeren veri seti yüklenmiş |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/detect-pii` ile veri seti gönder | PII alanları tespit edilmeli |
| 2 | TCKN, telefon, e-posta gibi alanları kontrol et | Doğru sınıflandırılmış |

---

### TC-SYN-004: Veri seti dışa aktarma

| Alan | Değer |
|------|-------|
| **ID** | TC-SYN-004 |
| **Başlık** | Üretilen veri setini dışa aktarma |
| **Önkoşullar** | Sentetik veri üretilmiş |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/export` ile dışa aktarma formatı seç (CSV/JSON) | İndirme bağlantısı döner |
| 2 | Dosyayı indir ve içeriği kontrol et | Doğru format ve veri sayısı |

---

### TC-SYN-005: TSPM test verisi oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-SYN-005 |
| **Başlık** | Proje içi test veri seti oluşturma |
| **Önkoşullar** | Proje mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/test-data` ile veri seti oluştur | HTTP 201 |
| 2 | `columns` ve `rows` alanlarını kontrol et | Gönderilen verilerle eşleşmeli |

---

### TC-SYN-006: Senaryoya test verisi bağlama

| Alan | Değer |
|------|-------|
| **ID** | TC-SYN-006 |
| **Başlık** | Senaryoya parametrik test verisi bağlama |
| **Önkoşullar** | Senaryo ve test veri seti mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../scenarios/{id}/bind-data` ile veri seti ve mapping gönder | HTTP 201 |
| 2 | `GET .../scenarios/{id}/expanded` ile genişletilmiş senaryoyu sorgula | `expanded_rows` dolu |
| 3 | Parametrelerin doğru değiştirildiğini kontrol et | Mapping'e göre değerler yerleşmiş |

---

## 7. Test Koşusu ve Sonuçlar (Executions)

### TC-EXC-001: Test koşusu oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-EXC-001 |
| **Başlık** | Yeni test koşusu başlatma |
| **Önkoşullar** | Senaryolar mevcut |
| **Öncelik** | P0 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/executions` ile koşu oluştur | HTTP 201 |
| 2 | `status` kontrol et | `"running"` |
| 3 | `scenario_total` kontrol et | Gönderilen senaryo sayısı |

---

### TC-EXC-002: Koşu sonucu güncelleme

| Alan | Değer |
|------|-------|
| **ID** | TC-EXC-002 |
| **Başlık** | Test sonucu durumunu güncelleme |
| **Önkoşullar** | Koşu mevcut |
| **Öncelik** | P0 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `PATCH .../executions/{runId}/results/{resultId}` ile `{"status": "passed"}` gönder | HTTP 200 |
| 2 | Koşu detayını sorgula | İlgili sonucun durumu `"passed"` |

---

### TC-EXC-003: Koşu yeniden çalıştırma

| Alan | Değer |
|------|-------|
| **ID** | TC-EXC-003 |
| **Başlık** | Önceki koşuyu yeniden çalıştırma |
| **Önkoşullar** | Tamamlanmış koşu mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/executions/{runId}` ile re-run | HTTP 201, yeni koşu |
| 2 | Yeni koşunun adını kontrol et | Orijinal ad + " (re-run)" |
| 3 | Senaryo sayısını kontrol et | Orijinal koşu ile aynı |

---

### TC-EXC-004: Koşu trendleri

| Alan | Değer |
|------|-------|
| **ID** | TC-EXC-004 |
| **Başlık** | Koşu trend verilerini sorgulama |
| **Önkoşullar** | Birden fazla koşu mevcut |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../execution-trends?days=30` isteği gönder | HTTP 200 |
| 2 | `data_points` dizisini kontrol et | Tarih sıralı veri noktaları |
| 3 | Her noktada `total`, `passed`, `failed`, `pass_rate` kontrol et | Tutarlı hesaplama |

---

### TC-EXC-005: Flaky test tespiti

| Alan | Değer |
|------|-------|
| **ID** | TC-EXC-005 |
| **Başlık** | Kararsız (flaky) testlerin tespiti |
| **Önkoşullar** | Aynı senaryo farklı koşularda farklı sonuç vermiş |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../flaky-tests` isteği gönder | HTTP 200 |
| 2 | Flaky testleri kontrol et | `flip_count > 0` olan senaryolar listeli |
| 3 | Sıralamayı kontrol et | `flip_count` azalan sırada |

---

## 8. Regresyon Setleri (Regression Sets)

### TC-REG-001: Regresyon seti oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-REG-001 |
| **Başlık** | Yeni regresyon seti oluşturma |
| **Önkoşullar** | Proje mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/v1/tspm/projects/{id}/regression-sets` ile set oluştur | HTTP 201 |
| 2 | `scenario_count` kontrol et | `0` (boş set) |

---

### TC-REG-002: Regresyon setine senaryo ekleme

| Alan | Değer |
|------|-------|
| **ID** | TC-REG-002 |
| **Başlık** | Mevcut sete senaryo ekleme |
| **Önkoşullar** | Regresyon seti ve senaryolar mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../regression-sets/{setId}/add` ile senaryo ID'leri gönder | HTTP 200 |
| 2 | `count` değerini kontrol et | Eklenen senaryo sayısı |
| 3 | Set detayını sorgula | Eklenen senaryolar listede |

---

### TC-REG-003: AI regresyon seti önerisi

| Alan | Değer |
|------|-------|
| **ID** | TC-REG-003 |
| **Başlık** | AI destekli regresyon set önerisi |
| **Önkoşullar** | Projede senaryolar mevcut, AI servisi erişilebilir |
| **Öncelik** | P2 |
| **Tür** | FT, IT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../regression-sets/suggest` ile istek gönder | HTTP 200 |
| 2 | `sets` dizisini kontrol et | En az 1 set önerisi |
| 3 | Her öneride `name`, `description`, `scenario_ids` kontrol et | Alanlar dolu |

---

### TC-REG-004: Önerilen setleri kabul etme

| Alan | Değer |
|------|-------|
| **ID** | TC-REG-004 |
| **Başlık** | AI önerilerini toplu kabul etme |
| **Önkoşullar** | AI önerisi alınmış |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../regression-sets/accept-suggestions` ile önerileri gönder | HTTP 201 |
| 2 | Oluşturulan set sayısını kontrol et | Gönderilen öneri sayısı kadar |

---

## 9. Gereksinimler ve Kapsam (Requirements & Coverage)

### TC-REQ-001: Gereksinim oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-REQ-001 |
| **Başlık** | Yeni gereksinim oluşturma |
| **Önkoşullar** | Proje mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../requirements` ile gereksinim oluştur | HTTP 201 |
| 2 | `external_id`, `title`, `priority` kontrol et | Gönderilen verilerle eşleşir |

---

### TC-REQ-002: Senaryo-gereksinim bağlama

| Alan | Değer |
|------|-------|
| **ID** | TC-REQ-002 |
| **Başlık** | Senaryoyu gereksinime bağlama |
| **Önkoşullar** | Senaryo ve gereksinim mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../scenarios/{id}/requirements` ile gereksinim ID'leri gönder | HTTP 201 |
| 2 | Bağlantıyı doğrula | Senaryo gereksinimlere bağlı |

---

### TC-REQ-003: Kapsam matrisi

| Alan | Değer |
|------|-------|
| **ID** | TC-REQ-003 |
| **Başlık** | Gereksinim-senaryo kapsam matrisini sorgulama |
| **Önkoşullar** | Gereksinimler ve senaryolar bağlanmış |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../coverage-matrix` isteği gönder | HTTP 200 |
| 2 | `coverage_percent` kontrol et | 0-100 arasında doğru hesaplanmış |
| 3 | `rows` içinde her gereksinim için bağlı senaryo ID'leri | Doğru bağlantılar |

---

### TC-REQ-004: Kapsam boşlukları

| Alan | Değer |
|------|-------|
| **ID** | TC-REQ-004 |
| **Başlık** | Hiçbir senaryoya bağlı olmayan gereksinimleri bulma |
| **Önkoşullar** | En az 1 bağlantısız gereksinim |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../coverage-gaps` isteği gönder | HTTP 200 |
| 2 | Bağlantısız gereksinimleri kontrol et | `scenario_count = 0` |

---

## 10. Zamanlamalar (Schedules)

### TC-SCH-001: Zamanlama oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-SCH-001 |
| **Başlık** | Yeni zamanlama oluşturma |
| **Önkoşullar** | Proje ve senaryolar mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../schedules` ile cron ifadesi ve senaryo ID'leri gönder | HTTP 201 |
| 2 | `cron_expression`, `is_active` kontrol et | Gönderilen değerlerle eşleşir |

---

### TC-SCH-002: Zamanlama tetikleme

| Alan | Değer |
|------|-------|
| **ID** | TC-SCH-002 |
| **Başlık** | Zamanlamayı manuel tetikleme |
| **Önkoşullar** | Zamanlama mevcut, senaryo ID'leri bağlı |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../schedules/{id}/trigger` | HTTP 201, yeni koşu |
| 2 | Koşu adını kontrol et | "Scheduled: {zamanlama adı}" |
| 3 | Senaryo sayısını kontrol et | Zamanlamadaki senaryo sayısı |

---

### TC-SCH-003: Senaryo olmadan zamanlama tetikleme hatası

| Alan | Değer |
|------|-------|
| **ID** | TC-SCH-003 |
| **Başlık** | Boş zamanlamayı tetikleme hatası |
| **Önkoşullar** | Senaryo bağlanmamış zamanlama |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | Senaryo ID'si olmayan zamanlamayı tetikle | HTTP 400, "Zamanlamada senaryo bulunamadı" |

---

## 11. API Test Koleksiyonları (API Testing)

### TC-API-001: API koleksiyonu oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-API-001 |
| **Başlık** | Yeni API test koleksiyonu oluşturma |
| **Önkoşullar** | Proje mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../api-tests/collections` ile koleksiyon oluştur | HTTP 201 |
| 2 | `name`, `base_url`, `request_count` kontrol et | `request_count = 0` |

---

### TC-API-002: API isteği oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-API-002 |
| **Başlık** | Koleksiyona API isteği ekleme |
| **Önkoşullar** | Koleksiyon mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../collections/{colId}/requests` ile istek oluştur | HTTP 201 |
| 2 | `method`, `path`, `headers`, `body` kontrol et | Gönderilen verilerle eşleşir |

---

### TC-API-003: API koleksiyonu çalıştırma

| Alan | Değer |
|------|-------|
| **ID** | TC-API-003 |
| **Başlık** | Koleksiyondaki tüm istekleri çalıştırma |
| **Önkoşullar** | Koleksiyon ve istekler mevcut, hedef API erişilebilir |
| **Öncelik** | P1 |
| **Tür** | FT, IT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../collections/{colId}/run` ile çalıştır | HTTP 200 |
| 2 | `status` kontrol et | `"completed"` |
| 3 | `results` dizisini kontrol et | Her istek için sonuç mevcut |
| 4 | Her sonuçta `status_code`, `duration_ms`, `passed` kontrol et | Doğru HTTP kodları |

---

### TC-API-004: API test koşu geçmişi

| Alan | Değer |
|------|-------|
| **ID** | TC-API-004 |
| **Başlık** | API test koşu geçmişini sorgulama |
| **Önkoşullar** | En az 1 API test koşusu |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET .../api-tests/runs` isteği gönder | HTTP 200, koşu listesi |
| 2 | Sıralamayı kontrol et | Azalan tarih sırası |

---

## 12. Akışlar (Flows)

### TC-FLW-001: Akış oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-FLW-001 |
| **Başlık** | Yeni test akışı oluşturma |
| **Önkoşullar** | Proje mevcut |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../flows` ile akış oluştur | HTTP 201 |
| 2 | `name`, `description` kontrol et | Gönderilen verilerle eşleşir |

---

### TC-FLW-002: Akış graf güncelleme

| Alan | Değer |
|------|-------|
| **ID** | TC-FLW-002 |
| **Başlık** | Akış diyagramını (node/edge) güncelleme |
| **Önkoşullar** | Akış mevcut |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `PUT .../flows/{flowId}/graph` ile nodes ve edges gönder | HTTP 200 |
| 2 | Güncellenen akışın `nodes`, `edges` kontrol et | Gönderilen verilerle eşleşir |

---

## 13. Entegrasyonlar (Integrations)

### TC-INT-001: Entegrasyon oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-INT-001 |
| **Başlık** | Yeni entegrasyon oluşturma (Jira, Jenkins vb.) |
| **Önkoşullar** | Proje mevcut |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../integrations` ile `{"provider": "jira", "config": {...}, "is_active": true}` gönder | HTTP 201 |
| 2 | `provider`, `is_active` kontrol et | Gönderilen değerler |

---

### TC-INT-002: Entegrasyon senkronizasyonu

| Alan | Değer |
|------|-------|
| **ID** | TC-INT-002 |
| **Başlık** | Entegrasyon senkronizasyonu tetikleme |
| **Önkoşullar** | Entegrasyon mevcut |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST .../integrations/{id}/sync` | HTTP 200, `synced_count` ve `message` |

---

## 14. Engine: Feature Dosyaları

### TC-ENG-001: Feature dosyası listeleme

| Alan | Değer |
|------|-------|
| **ID** | TC-ENG-001 |
| **Başlık** | Gherkin feature dosyalarını listeleme |
| **Önkoşullar** | Engine çalışır durumda |
| **Öncelik** | P1 |
| **Tür** | FT, IT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/features/` isteği gönder (Engine :5001) | HTTP 200, feature listesi |
| 2 | Listedeki dosya isimlerini kontrol et | `.feature` uzantılı dosyalar |

---

### TC-ENG-002: Feature dosyası oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-ENG-002 |
| **Başlık** | Yeni Gherkin feature dosyası oluşturma |
| **Önkoşullar** | Engine çalışır durumda |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/features/` ile feature içeriği gönder | HTTP 201 |
| 2 | Oluşturulan dosyayı sorgula | Gönderilen Gherkin içeriği mevcut |

---

## 15. Engine: Test Çalıştırma

### TC-RUN-001: Test koşusu başlatma

| Alan | Değer |
|------|-------|
| **ID** | TC-RUN-001 |
| **Başlık** | Engine üzerinden test koşusu başlatma |
| **Önkoşullar** | Feature dosyası mevcut, Engine çalışır |
| **Öncelik** | P1 |
| **Tür** | FT, IT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/run/` ile feature dosyası ve parametreler gönder | HTTP 200, koşu başlar |
| 2 | SSE stream üzerinden ilerlemeyi takip et | Gerçek zamanlı güncelleme |
| 3 | Koşu tamamlanınca raporu kontrol et | Allure veya JSON rapor |

---

### TC-RUN-002: Regresyon seti koşusu

| Alan | Değer |
|------|-------|
| **ID** | TC-RUN-002 |
| **Başlık** | Regresyon seti içindeki testleri koşma |
| **Önkoşullar** | Regresyon seti ve feature dosyaları mevcut |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/regression-sets/` ile setleri listele | HTTP 200 |
| 2 | Seçilen seti koştur | Tüm senaryolar çalıştırılır |
| 3 | Sonuç raporunu kontrol et | Geçen/kalan/hatalı sayıları doğru |

---

## 16. Engine: AI Test Üretimi

### TC-AI-001: AI ile feature dosyası üretimi

| Alan | Değer |
|------|-------|
| **ID** | TC-AI-001 |
| **Başlık** | AI ile otomatik Gherkin feature üretimi |
| **Önkoşullar** | Engine çalışır, AI servisi erişilebilir |
| **Öncelik** | P2 |
| **Tür** | FT, IT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/generate-feature/` ile URL veya açıklama gönder | HTTP 200 |
| 2 | Üretilen feature içeriğini kontrol et | Geçerli Gherkin formatında |
| 3 | Given/When/Then adımları kontrol et | Mantıklı test senaryosu |

---

## 17. Engine: Görsel Regresyon

### TC-VIS-001: Görsel regresyon testi çalıştırma

| Alan | Değer |
|------|-------|
| **ID** | TC-VIS-001 |
| **Başlık** | İki ekran görüntüsü arasında SSIM karşılaştırma |
| **Önkoşullar** | Baseline ekran görüntüsü mevcut |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/visual/compare` ile baseline ve test görüntüsü gönder | HTTP 200 |
| 2 | SSIM skorunu kontrol et | 0-1 arasında değer |
| 3 | Fark haritasını kontrol et | Farklılıklar vurgulanmış |

---

## 18. Engine: Erişilebilirlik

### TC-A11Y-001: Erişilebilirlik taraması

| Alan | Değer |
|------|-------|
| **ID** | TC-A11Y-001 |
| **Başlık** | WCAG 2.1 erişilebilirlik taraması |
| **Önkoşullar** | Taranacak URL erişilebilir |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/a11y/scan` ile URL gönder | HTTP 200, tarama sonuçları |
| 2 | İhlal listesini kontrol et | Seviye (A, AA, AAA) bilgisi mevcut |
| 3 | Toplam skor kontrol et | 0-100 arasında erişilebilirlik puanı |

---

## 19. Engine: Test Kaydedici (Recorder)

### TC-REC-001: Test kaydı başlatma ve durdurma

| Alan | Değer |
|------|-------|
| **ID** | TC-REC-001 |
| **Başlık** | Kullanıcı aksiyonlarını kaydedip test kodu üretme |
| **Önkoşullar** | Engine çalışır, tarayıcı kullanılabilir |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/recorder/start` ile kayıt başlat | HTTP 200, session ID |
| 2 | Kullanıcı aksiyonları gerçekleştir | Aksiyonlar kaydedilir |
| 3 | `POST /api/recorder/stop` ile kaydı durdur | HTTP 200 |
| 4 | Üretilen test kodunu kontrol et | Playwright/Cucumber/POM formatında |

---

## 20. Engine: Veri Simülasyonu (DataSim)

### TC-DSM-001: Veri simülasyonu çalıştırma

| Alan | Değer |
|------|-------|
| **ID** | TC-DSM-001 |
| **Başlık** | Test verisi simülasyonu oluşturma |
| **Önkoşullar** | Engine çalışır |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/datasim/generate` ile simülasyon parametreleri gönder | HTTP 200 |
| 2 | Üretilen veriyi kontrol et | Belirtilen format ve sayıda veri |

---

## 21. Altyapı ve Sağlık Kontrolleri

### TC-INF-001: Servis sağlık kontrolü

| Alan | Değer |
|------|-------|
| **ID** | TC-INF-001 |
| **Başlık** | Backend sağlık endpoint kontrolü |
| **Önkoşullar** | Backend çalışır |
| **Öncelik** | P0 |
| **Tür** | ST |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /health` isteği gönder | HTTP 200, `{"status": "ok"}` |

---

### TC-INF-002: Veritabanı hazırlık kontrolü

| Alan | Değer |
|------|-------|
| **ID** | TC-INF-002 |
| **Başlık** | Veritabanı bağlantı ve hazırlık kontrolü |
| **Önkoşullar** | Backend ve PostgreSQL çalışır |
| **Öncelik** | P0 |
| **Tür** | ST |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /ready` isteği gönder | HTTP 200, `{"ready": true, "database": "ok"}` |

---

### TC-INF-003: Veritabanı bağlantı hatası durumu

| Alan | Değer |
|------|-------|
| **ID** | TC-INF-003 |
| **Başlık** | PostgreSQL kapalıyken ready endpoint davranışı |
| **Önkoşullar** | PostgreSQL durdurulmuş |
| **Öncelik** | P1 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | PostgreSQL'i durdur | — |
| 2 | `GET /ready` isteği gönder | `{"ready": false, "database": "...hata..."}` |

---

## 22. Bildirimler (Notifications)

### TC-NTF-001: Bildirim listesi sorgulama

| Alan | Değer |
|------|-------|
| **ID** | TC-NTF-001 |
| **Başlık** | Kullanıcı bildirimlerini listeleme |
| **Önkoşullar** | Bildirim kaydı mevcut |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `GET /api/v1/notifications/` isteği gönder | HTTP 200, bildirim listesi |

---

## 23. QA Engine (Backend QA Routes)

### TC-QA-001: Test planı oluşturma

| Alan | Değer |
|------|-------|
| **ID** | TC-QA-001 |
| **Başlık** | Otomatik test planı oluşturma |
| **Önkoşullar** | Geçerli JWT |
| **Öncelik** | P2 |
| **Tür** | FT, AT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/qa/test-plan` ile test planı parametreleri gönder | HTTP 200, test planı |
| 2 | Planın kapsamını kontrol et | Modüller, öncelikler, test tipleri |

---

### TC-QA-002: Otomasyon kodu üretimi

| Alan | Değer |
|------|-------|
| **ID** | TC-QA-002 |
| **Başlık** | Test otomasyonu kodu üretme |
| **Önkoşullar** | Geçerli JWT |
| **Öncelik** | P2 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/qa/generate-automation` ile senaryo gönder | HTTP 200, otomasyon kodu |
| 2 | Üretilen kodun formatını kontrol et | Geçerli Playwright/pytest kodu |

---

### TC-QA-003: Monkey test çalıştırma

| Alan | Değer |
|------|-------|
| **ID** | TC-QA-003 |
| **Başlık** | Rastgele tıklama/gezinme testi |
| **Önkoşullar** | Hedef URL erişilebilir |
| **Öncelik** | P3 |
| **Tür** | FT |

**Adımlar:**

| # | Adım | Beklenen Sonuç |
|---|------|----------------|
| 1 | `POST /api/qa/monkey-test` ile URL ve süre gönder | HTTP 200 |
| 2 | Sonuç raporunu kontrol et | Bulunan hatalar ve crash bilgileri |

---

## Senaryo Özet Tablosu

| Modül | Senaryo Sayısı | P0 | P1 | P2 | P3 |
|-------|---------------|-----|-----|-----|-----|
| Auth | 8 | 6 | 2 | 0 | 0 |
| Projects | 6 | 1 | 4 | 0 | 1 |
| Scenarios | 9 | 3 | 6 | 0 | 0 |
| Approvals | 5 | 2 | 2 | 0 | 1 |
| Import | 3 | 1 | 1 | 1 | 0 |
| Synthetic Data | 6 | 0 | 4 | 2 | 0 |
| Executions | 5 | 2 | 1 | 2 | 0 |
| Regression Sets | 4 | 0 | 2 | 2 | 0 |
| Requirements | 4 | 0 | 3 | 1 | 0 |
| Schedules | 3 | 0 | 2 | 1 | 0 |
| API Testing | 4 | 0 | 3 | 1 | 0 |
| Flows | 2 | 0 | 0 | 2 | 0 |
| Integrations | 2 | 0 | 0 | 2 | 0 |
| Engine Features | 2 | 0 | 2 | 0 | 0 |
| Engine Runner | 2 | 0 | 2 | 0 | 0 |
| Engine AI | 1 | 0 | 0 | 1 | 0 |
| Engine Visual | 1 | 0 | 0 | 1 | 0 |
| Engine A11y | 1 | 0 | 0 | 1 | 0 |
| Engine Recorder | 1 | 0 | 0 | 1 | 0 |
| Engine DataSim | 1 | 0 | 0 | 1 | 0 |
| Infrastructure | 3 | 2 | 1 | 0 | 0 |
| Notifications | 1 | 0 | 0 | 1 | 0 |
| QA Engine | 3 | 0 | 0 | 2 | 1 |
| **Toplam** | **77** | **17** | **35** | **22** | **3** |
