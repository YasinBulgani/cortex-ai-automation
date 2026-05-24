# BGTS Test Dönüşüm — Kritik Risk Bulguları ve Öneriler

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Bulgu Kaynağı:** Statik analiz dokümanı incelemesi (kod yazılmadı, yalnızca analiz)

---

## Yüksek Riskli Bulgular

### RISK-001: RBAC Endpoint Seviyesinde Enforce Edilmiyor
- **Ciddiyet:** YÜKSEK
- **Konum:** `backend/app/domains/tspm/router.py`
- **Açıklama:** Router dosyasında `get_current_user` dependency mevcut ancak hiçbir endpoint'te izin kontrolü yapılmıyor. `permissions.py` dosyasında `ROLE_PERMISSIONS` tanımlı olmasına rağmen, `viewer` rolündeki bir kullanıcı senaryo oluşturma, silme, onay verme gibi tüm yazma işlemlerini yapabilir.
- **Etki:** Yetkisiz veri değişikliği, veri bütünlüğü kaybı
- **Öneri:** Her endpoint'e `require_permission("scenario.create")` gibi dependency eklenmelidir.

### RISK-002: Proje Bazlı Erişim Kontrolü Eksik (IDOR)
- **Ciddiyet:** YÜKSEK
- **Konum:** `backend/app/domains/tspm/router.py` — `_get_project` fonksiyonu
- **Açıklama:** `_get_project` fonksiyonu proje ID'si ile veritabanından projeyi çeker, ancak projenin mevcut kullanıcıya ait olup olmadığını veya kullanıcının proje üyesi olup olmadığını kontrol etmez. `TspmProjectMember` tablosu mevcut ancak kullanılmıyor.
- **Etki:** Herhangi bir kimlik doğrulanmış kullanıcı, başka kullanıcıların projelerine erişebilir
- **Öneri:** `_get_project` fonksiyonuna `user_id` parametresi ekleyerek `TspmProjectMember` tablosu üzerinden erişim kontrolü yapılmalıdır.

### RISK-003: CORS Tüm Origin'lere Açık
- **Ciddiyet:** ORTA
- **Konum:** `backend/app/main.py` — CORS middleware
- **Açıklama:** Geliştirme ortamında CORS tüm origin'lere açık. Production'a taşındığında bu yapılandırma güvenlik riski oluşturur.
- **Öneri:** Production'da `CORS_ORIGINS` environment variable ile whitelist yapılandırılmalıdır.

### RISK-004: API Test Koleksiyonu Dış HTTP Çağrısı
- **Ciddiyet:** ORTA
- **Konum:** `backend/app/domains/tspm/router.py` — `run_api_collection` endpoint
- **Açıklama:** API test koleksiyonu çalıştırıldığında, sunucu kullanıcının belirttiği URL'lere HTTP isteği gönderiyor. Bu, SSRF (Server-Side Request Forgery) riski oluşturur.
- **Etki:** İç ağdaki servislere erişim, cloud metadata endpoint'lerine erişim
- **Öneri:** URL whitelist/blacklist mekanizması, internal IP aralıklarını engelleme (`127.0.0.1`, `169.254.169.254`, private range'ler)

### RISK-005: JWT Secret Varsayılan Değer
- **Ciddiyet:** YÜKSEK (Production'da)
- **Konum:** `.env.example` — `JWT_SECRET`
- **Açıklama:** Varsayılan JWT_SECRET değeri `change-me-in-production-use-long-random-secret`. Production ortamında değiştirilmezse token'lar tahmin edilebilir.
- **Öneri:** Production deployment sürecinde JWT_SECRET'ın değiştirildiğini kontrol eden CI/CD check'i eklenmelidir.

---

## Orta Riskli Bulgular

### RISK-006: Cascade Delete Performansı
- **Ciddiyet:** ORTA
- **Konum:** `backend/app/domains/tspm/models.py` — `TspmProject` cascade ilişkileri
- **Açıklama:** Proje silindiğinde 11 farklı tablo cascade ile temizlenir. Çok sayıda veri içeren bir proje silindiğinde performans sorunu olabilir.
- **Öneri:** Background task ile asenkron silme veya soft delete mekanizması

### RISK-007: BDD Generator LLM Dependency
- **Ciddiyet:** ORTA
- **Konum:** `backend/app/domains/tspm/bdd_generator.py`
- **Açıklama:** BDD senaryo üretimi LLM servisine bağımlıdır. LLM servisi erişilemez olduğunda fallback mekanizması belirsiz.
- **Öneri:** LLM erişilemezse uygun hata mesajı ve timeout yönetimi

### RISK-008: Senaryo Arama SQL Pattern
- **Ciddiyet:** DÜŞÜK
- **Konum:** `router.py` — `list_scenarios` — `TspmScenario.title.ilike(f"%{q}%")`
- **Açıklama:** SQLAlchemy parametrize query kullandığı için SQL injection riski düşük, ancak `%` ve `_` wildcard karakterleri kullanıcı tarafından manipüle edilebilir.
- **Öneri:** `q` parametresinde `%` ve `_` karakterlerini escape etme

---

## Düşük Riskli Bulgular

### RISK-009: Proje Delete Endpoint Eksik
- **Ciddiyet:** DÜŞÜK
- **Açıklama:** `project.delete` izni tanımlı ancak proje silme endpoint'i mevcut değil.
- **Öneri:** Soft delete (archive) veya hard delete endpoint'i eklenebilir.

### RISK-010: Import Pipeline Stub
- **Ciddiyet:** DÜŞÜK
- **Açıklama:** Import oluşturma her zaman `completed` statusünde kaydediliyor; gerçek dosya işleme yok.
- **Öneri:** n8n pipeline entegrasyonu tamamlandığında güncellenmeli.

---

## Risk Özet Tablosu

| ID | Başlık | Ciddiyet | Etki | Olasılık | Risk Skoru |
|----|--------|----------|------|----------|------------|
| RISK-001 | RBAC enforce edilmiyor | YÜKSEK | YÜKSEK | YÜKSEK | 9/10 |
| RISK-002 | IDOR — proje erişim kontrolü | YÜKSEK | YÜKSEK | YÜKSEK | 9/10 |
| RISK-003 | CORS açık | ORTA | ORTA | ORTA | 5/10 |
| RISK-004 | SSRF — API test runner | ORTA | YÜKSEK | DÜŞÜK | 5/10 |
| RISK-005 | JWT secret varsayılan | YÜKSEK | KRİTİK | DÜŞÜK | 6/10 |
| RISK-006 | Cascade delete performansı | ORTA | DÜŞÜK | ORTA | 4/10 |
| RISK-007 | LLM dependency | ORTA | DÜŞÜK | ORTA | 4/10 |
| RISK-008 | Wildcard arama | DÜŞÜK | DÜŞÜK | DÜŞÜK | 2/10 |
| RISK-009 | Delete endpoint eksik | DÜŞÜK | DÜŞÜK | DÜŞÜK | 1/10 |
| RISK-010 | Import stub | DÜŞÜK | DÜŞÜK | DÜŞÜK | 1/10 |

---

## Aksiyon Planı

| Öncelik | Aksiyon | Sorumlu | Hedef Sprint |
|---------|---------|---------|-------------|
| P0 | RBAC middleware implementasyonu (RISK-001) | Backend Dev | Sprint N |
| P0 | Proje bazlı erişim kontrolü (RISK-002) | Backend Dev | Sprint N |
| P1 | SSRF koruması (RISK-004) | Backend Dev | Sprint N+1 |
| P1 | Production CORS/JWT check (RISK-003, RISK-005) | DevOps | Sprint N+1 |
| P2 | Cascade delete optimizasyonu (RISK-006) | Backend Dev | Sprint N+2 |
| P2 | LLM fallback iyileştirme (RISK-007) | AI Dev | Sprint N+2 |
