# Veri İşleme Sözleşmesi (DPA) — Şablon

**Belge Türü:** Data Processing Agreement (DPA) — Türkçe Şablon  
**Versiyon:** 1.0  
**Geçerlilik:** Bu şablon 6698 sayılı KVKK ve GDPR Madde 28 kapsamında hazırlanmıştır.  
**Son Güncelleme:** 2026-05-24

---

## 1. Taraflar

| Taraf | Rol | Açıklama |
|---|---|---|
| **Veri Sorumlusu** | Controller | Cortex AI Automation platformunu kullanan müşteri kuruluş |
| **Veri İşleyen** | Processor | Cortex AI Automation hizmetini sağlayan Şirket |

---

## 2. Sözleşmenin Amacı

Bu sözleşme, Veri Sorumlusu adına gerçekleştirilen kişisel veri işleme faaliyetlerine ilişkin koşulları belirler. Cortex AI Automation platformunun kullanımı sırasında aktarılan tüm kişisel veriler bu sözleşme kapsamındadır.

---

## 3. İşlenen Kişisel Veriler

### 3.1 Veri Kategorileri

| Kategori | Örnekler | Saklama Süresi |
|---|---|---|
| Kimlik Verileri | Ad-soyad, e-posta, kullanıcı ID | Hesap aktif olduğu sürece + 90 gün |
| Erişim Verileri | IP adresi, oturum tokenları, tarayıcı bilgisi | 30 gün |
| İşlem Verileri | Test çalışması geçmişi, eylem logları | 365 gün |
| Güvenlik Verileri | MFA durumu, giriş denemeleri, denetim kayıtları | 730 gün (BDDK gereksinimi) |
| İçerik Verileri | Test senaryoları, yapılandırma dosyaları | Hesap silme + 30 gün |

### 3.2 Özel Nitelikli Veriler

Platform, KVKK Madde 6 kapsamındaki özel nitelikli kişisel veri işlememektedir.

### 3.3 İlgili Kişiler

- Müşteri çalışanları (platform kullanıcıları)
- Proje yöneticileri ve test mühendisleri
- Denetçi kullanıcılar (salt okunur erişim)

---

## 4. İşleme Amaç ve Hukuki Dayanağı

| Amaç | Hukuki Dayanak (KVKK) | Hukuki Dayanak (GDPR) |
|---|---|---|
| Platform hizmeti sunumu | Madde 5/1(c) — sözleşme | Madde 6(1)(b) |
| Güvenlik ve doğrulama | Madde 5/1(ç) — meşru menfaat | Madde 6(1)(f) |
| Denetim kaydı tutma | Madde 5/1(ç) — yasal yükümlülük | Madde 6(1)(c) |
| Hizmet iyileştirme (anonim) | Madde 5/1(ç) — meşru menfaat | Madde 6(1)(f) |

---

## 5. Veri İşleyenin Yükümlülükleri

### 5.1 Teknik ve İdari Tedbirler

Veri İşleyen aşağıdaki güvenlik tedbirlerini uygulamaktadır:

**Teknik Tedbirler:**
- [ ] AES-256-GCM ile veri-at-rest şifreleme
- [ ] TLS 1.3 ile transit şifreleme
- [ ] TOTP tabanlı çok faktörlü kimlik doğrulama (RFC 6238)
- [ ] Row-Level Security (RLS) ile çok kiracılı veri izolasyonu
- [ ] HMAC-SHA256 ile bütünlük zincirine bağlı denetim logları
- [ ] Düzenli güvenlik açığı taraması (SAST/DAST)
- [ ] Otomatik oturum yönetimi ve token expiry

**İdari Tedbirler:**
- [ ] Veri erişimi en az yetki prensibi (role-based access)
- [ ] Personel gizlilik taahhütleri
- [ ] Yıllık güvenlik eğitimleri
- [ ] Olay müdahale prosedürü (maks. 72 saat bildirim)

### 5.2 Alt İşleyenler

| Alt İşleyen | Hizmet | Ülke | Güvence |
|---|---|---|---|
| AWS (Amazon Web Services) | Altyapı hosting | EU (Frankfurt) | AWS DPA, SCCs |
| PostgreSQL (self-hosted) | Veri tabanı | Müşteri altyapısı | — |
| Anthropic API | AI modeli (opsiyonel) | ABD | Anthropic DPA |

> **Not:** Alt işleyenlerde değişiklik yapılmadan önce Veri Sorumlusu 30 gün önceden bilgilendirilir.

### 5.3 Veri Aktarımları

EEA / Türkiye dışına aktarım söz konusu ise:
- EU Standart Sözleşme Maddeleri (SCCs) uygulanır
- KVKK Madde 9 kapsamında açık rıza veya Kurul kararı aranır

---

## 6. Veri Sahibi Hakları Desteği

Veri İşleyen, Veri Sorumlusunun aşağıdaki talepleri yerine getirmesine destek sağlar:

| Hak | Destek Mekanizması | SLA |
|---|---|---|
| Erişim hakkı | Admin paneli → kullanıcı raporu | 5 iş günü |
| Düzeltme hakkı | Admin paneli → profil güncelleme | Anlık |
| Silme hakkı | Admin paneli → hesap silme API | 30 gün (yedek silme dahil) |
| Taşınabilirlik | Audit log JSON export, CSV export | 5 iş günü |
| İşlemeyi durdurma | Kullanıcı devre dışı bırakma | Anlık |

---

## 7. Veri İhlali Bildirimi

Kişisel veri ihlali tespitinden sonra:

1. **İlk 24 saat:** Veri İşleyen iç olay kayıtlarını oluşturur
2. **72 saat içinde:** Veri Sorumlusu yazılı olarak bilgilendirilir
3. **Bildirim içeriği:** İhlal türü, etkilenen veriler, alınan önlemler, öneri
4. **Kayıt:** Tüm ihlaller `sd_audit_events` tablosunda `action=security.breach` ile kaydedilir

---

## 8. Denetim Hakları

Veri Sorumlusu, yılda bir kez önceden bildirimle:
- Audit log export talep edebilir (`GET /api/v1/audit/export/json`)
- Güvenlik belgelerini inceleyebilir
- Üçüncü taraf penetrasyon test raporu talep edebilir

---

## 9. Sözleşme Süresi ve Fesih

- Sözleşme, Ana Hizmet Sözleşmesi (MSA) ile birlikte yürürlüğe girer
- Fesih halinde veriler 30 gün içinde iade edilir veya imha edilir
- İmha sertifikası talep üzerine sağlanır

---

## 10. Uygulanacak Hukuk

- Türkiye'deki Veri Sorumluları için: **6698 sayılı KVKK** ve Türk Hukuku
- AB üyesi ülkelerdeki Veri Sorumluları için: **GDPR** ve ilgili üye devlet mevzuatı
- Uyuşmazlıklarda: [Tarafların belirleyeceği mahkeme/tahkim]

---

## 11. İmzalar

| | Veri Sorumlusu | Veri İşleyen |
|---|---|---|
| Kuruluş | `________________________` | Cortex AI Automation |
| Yetkili | `________________________` | `________________________` |
| Unvan | `________________________` | `________________________` |
| Tarih | `________________________` | `________________________` |
| İmza | `________________________` | `________________________` |

---

*Bu şablon, yasal danışmanlık hizmetinin yerini tutmaz. Son haline getirilmeden önce hukuk müşavirinize danışınız.*
