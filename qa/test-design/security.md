# BGTS Test Dönüşüm — Güvenlik (Security) Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kapsam:** Authentication, Authorization, Input Validation, Injection, CORS, Rate Limiting, Data Protection

---

## TS-SEC-01: Authentication Güvenlik Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| SEC-0101 | Expired JWT token ile erişim | Negatif | Critical | 1. Süresi dolmuş JWT token oluştur 2. Bu token ile korumalı endpoint'e istek gönder | HTTP 401; token reddedilir |
| SEC-0102 | Manipüle edilmiş JWT payload | Negatif | Critical | 1. Geçerli JWT al 2. Payload'daki user_id'yi değiştir 3. İmzayı koruyarak istek gönder | HTTP 401; signature doğrulaması başarısız |
| SEC-0103 | Geçersiz JWT imza (farklı secret) | Negatif | Critical | 1. Farklı secret key ile JWT oluştur 2. Bu token ile istek gönder | HTTP 401 |
| SEC-0104 | Bearer prefix olmadan token gönderme | Negatif | High | 1. Authorization header'a `"token123"` (Bearer olmadan) yaz | HTTP 401 |
| SEC-0105 | Boş Authorization header | Negatif | High | 1. `Authorization: ""` header ile istek gönder | HTTP 401 |
| SEC-0106 | JWT token içinde SQL injection | Negatif | Critical | 1. JWT payload'a `'; DROP TABLE users; --` ekle 2. İstek gönder | HTTP 401; tablo silinmez |
| SEC-0107 | Brute force login koruması | Negatif | High | 1. Aynı e-posta ile 50 ardışık yanlış parola gönder 2. Rate limit kontrolü yap | Rate limiting devreye girmeli (429) |
| SEC-0108 | Token yenileme sonrası eski token | Negatif | Medium | 1. Login yap (token-1) 2. Tekrar login yap (token-2) 3. token-1 ile istek gönder | Davranış doğrulanmalı (stateless JWT'de her ikisi de çalışır) |

---

## TS-SEC-02: Authorization / Yetkilendirme Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| SEC-0201 | Viewer rolü ile proje oluşturma denemesi | Negatif | Critical | 1. Viewer rolündeki kullanıcı ile login 2. `POST /tspm/projects` çağır | HTTP 403 (izin yok) veya 200 (mevcut impl izin kontrolü yok — risk) |
| SEC-0202 | Viewer rolü ile senaryo silme denemesi | Negatif | Critical | 1. Viewer ile login 2. `POST .../bulk-delete` çağır | HTTP 403 veya unauthorized |
| SEC-0203 | Viewer rolü ile onay kararı verme | Negatif | Critical | 1. Viewer ile login 2. `POST .../decide` çağır | HTTP 403 |
| SEC-0204 | Farklı projeye ait kaynağa erişim (IDOR) | Negatif | Critical | 1. User-A'nın projesi, User-B ile login 2. Proje-A'nın senaryosuna erişim dene | HTTP 404 (mevcut impl proje sahipliği kontrol etmiyor — risk) |
| SEC-0205 | Project member olmayan kullanıcının erişimi | Negatif | High | 1. Projeye member olmayan kullanıcı ile login 2. Proje endpoint'lerine erişim dene | Erişim kontrollü olmalı |
| SEC-0206 | Admin.* izninin tüm operasyonlarda çalışması | Pozitif | High | 1. Admin ile tüm CRUD operasyonları dene | Hepsi başarılı |

---

## TS-SEC-03: Input Validation ve Injection Testleri

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| SEC-0301 | SQL Injection — Proje ismi | Negatif | Critical | 1. `POST /tspm/projects` ile `{ "name": "'; DROP TABLE tspm_projects; --" }` gönder | Proje oluşturulur (string olarak); SQL injection çalışmaz |
| SEC-0302 | SQL Injection — Senaryo arama | Negatif | Critical | 1. `GET .../scenarios?q=' OR 1=1 --` gönder | Parametrize query; injection çalışmaz |
| SEC-0303 | XSS — Senaryo başlığı | Negatif | High | 1. `{ "title": "<script>alert('xss')</script>" }` ile senaryo oluştur 2. UI'da render kontrolü | Script çalışmamalı; HTML encode edilmeli |
| SEC-0304 | XSS — Proje açıklaması | Negatif | High | 1. `{ "description": "<img src=x onerror=alert(1)>" }` gönder | XSS tetiklenmemeli |
| SEC-0305 | NoSQL Injection — JSONB alanları | Negatif | High | 1. Steps alanına `{ "$gt": "" }` gibi NoSQL payload gönder | JSONB olarak kaydedilir; injection yok |
| SEC-0306 | Path Traversal — Import filename | Negatif | Critical | 1. `{ "filename": "../../etc/passwd" }` ile import oluştur | Dosya sistemi erişimi yok; sadece string olarak kaydedilir |
| SEC-0307 | Büyük payload (1MB+) gönderme | Negatif | Medium | 1. 1MB+ JSON body ile POST istek gönder | HTTP 413 veya timeout; sistem çökmemeli |
| SEC-0308 | Unicode/Emoji içeren veriler | Boundary | Medium | 1. Proje adına `"Test 🚀 Proje"`, açıklamaya Türkçe karakterler gönder | Doğru kaydedilip gösterilmeli |
| SEC-0309 | Null byte injection | Negatif | High | 1. `{ "title": "test\x00injection" }` gönder | Temizlenmeli veya reddedilmeli |
| SEC-0310 | CRLF Injection — Header | Negatif | High | 1. E-posta alanına `"test@test.com\r\nX-Injected: true"` gönder | Header injection çalışmamalı |

---

## TS-SEC-04: CORS ve Network Güvenliği

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| SEC-0401 | Farklı origin'den API erişimi | Negatif | High | 1. `http://evil.com` origin header ile istek gönder | CORS politikasına göre reddedilmeli (prod'da) |
| SEC-0402 | OPTIONS preflight request | Pozitif | Medium | 1. OPTIONS method ile API'ye istek gönder | Doğru CORS header'ları dönmeli |
| SEC-0403 | HTTP → HTTPS yönlendirme | Pozitif | High | 1. HTTP üzerinden erişim dene (prod) | HTTPS'e yönlendirilmeli |
| SEC-0404 | Güvenlik header'ları kontrolü | Pozitif | Medium | 1. API yanıtlarında security header'ları kontrol et | X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security mevcut olmalı |

---

## TS-SEC-05: Rate Limiting

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| SEC-0501 | Login endpoint rate limit | Negatif | Critical | 1. 1 saniyede 100 login isteği gönder | Rate limit devreye girmeli; 429 döner |
| SEC-0502 | API endpoint rate limit | Negatif | High | 1. Aynı token ile 1 saniyede 1000 istek gönder | Rate limit devreye girmeli |
| SEC-0503 | Rate limit header'ları | Pozitif | Medium | 1. Normal istek gönder 2. Response header'larını kontrol et | X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset mevcut |
| SEC-0504 | IP whitelist bypass | Negatif | Medium | 1. Farklı IP'lerden rate limit'i aşmaya çalış | Her IP kendi limitini takip etmeli |

---

## TS-SEC-06: Veri Güvenliği ve Gizlilik

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen Sonuç |
|----|--------|-----|---------|---------------|----------------|
| SEC-0601 | Parola hash kontrolü | Pozitif | Critical | 1. Veritabanında user tablosunu kontrol et | Parola plaintext olarak saklanmamalı; bcrypt/argon2 hash kullanılmalı |
| SEC-0602 | JWT payload'da hassas veri | Pozitif | High | 1. JWT token'ı decode et 2. İçeriği kontrol et | Parola, kişisel bilgi gibi hassas veri payload'da olmamalı |
| SEC-0603 | API yanıtlarında password hash sızıntısı | Negatif | Critical | 1. `/auth/me` ve user endpoint'lerinden yanıtları kontrol et | password_hash alanı döndürülmemeli |
| SEC-0604 | Silinen verilerin erişilememesi | Pozitif | High | 1. Senaryo sil 2. Eski ID ile GET isteği gönder | HTTP 404; silinen veriye erişilemez |
| SEC-0605 | Audit log'da hassas veri | Pozitif | Medium | 1. Audit log kayıtlarını kontrol et | Parolalar, token'lar log'lanmamalı |

---

## Güvenlik Risk Matrisi

| Risk Alanı | Mevcut Durum | Risk Seviyesi | Öneri |
|------------|-------------|---------------|-------|
| JWT Token Yönetimi | Implementasyon mevcut | DÜŞÜK | Token expiry süresini doğrula |
| RBAC Endpoint Kontrolü | Permission tanımlı ama router'da enforce edilmiyor | YÜKSEK | Middleware ile permission check ekle |
| IDOR (Insecure Direct Object Reference) | Proje ID kontrolü var ama kullanıcı bazlı değil | YÜKSEK | Project member kontrolü ekle |
| SQL Injection | SQLAlchemy ORM parametrize query kullanıyor | DÜŞÜK | Mevcut durum yeterli |
| XSS | React varsayılan escape kullanıyor | DÜŞÜK | dangerouslySetInnerHTML kullanımını kontrol et |
| Rate Limiting | Middleware implemente edilmiş | DÜŞÜK | Login endpoint için ayrı sıkı limit |
| CORS | Development'ta tüm origin'ler açık | ORTA | Production'da whitelist yapılandır |
| Parola Güvenliği | bcrypt hash kullanılıyor | DÜŞÜK | Parola karmaşıklık kuralı ekle |

---

## Toplam Güvenlik Test Sayısı: 33

| Kategori | Sayı |
|----------|------|
| Authentication | 8 |
| Authorization | 6 |
| Input Validation / Injection | 10 |
| CORS / Network | 4 |
| Rate Limiting | 4 |
| Veri Güvenliği | 5 |
