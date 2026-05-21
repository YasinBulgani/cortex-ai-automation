# AI Test Otomasyonu — En İyi Uygulama Rehberi

**Tarih:** 2026-04-03
**Kapsam:** BGTS platformuna özel AI test otomasyon kuralları, pattern'lar ve rehber ilkeler

---

## İçindekiler

1. [Temel İlkeler](#1-temel-ilkeler)
2. [Locator Stratejisi](#2-locator-stratejisi)
3. [Test Üretimi Kuralları](#3-test-üretimi-kuralları)
4. [Self-Healing Politikası](#4-self-healing-politikası)
5. [BDD Generation Kuralları](#5-bdd-generation-kuralları)
6. [Sentetik Veri Yönetimi](#6-sentetik-veri-yönetimi)
7. [LLM Kullanım Politikası](#7-llm-kullanım-politikası)
8. [CI/CD Entegrasyon Kuralları](#8-cicd-entegrasyon-kuralları)
9. [Test Kalite Kapısı](#9-test-kalite-kapısı)
10. [Güvenlik ve Gizlilik](#10-güvenlik-ve-gizlilik)
11. [Raporlama ve İzlenebilirlik](#11-raporlama-ve-izlenebilirlik)
12. [Anti-Pattern'lar](#12-anti-patternlar)

---

## 1. Temel İlkeler

### 1.1 AI Yardımcıdır, Karar Verici Değil
- AI üretilen her test **mutlaka insan review**'dan geçmelidir
- AI otomatik merge yapmamalıdır — PR oluşturur, insan onaylar
- Self-healing sonuçları loglanmalı ve düzenli denetlenmelidir
- AI'ın gizlediği gerçek bug'lar en tehlikeli regresyondur

### 1.2 Kademeli Benimseme
- Her AI özelliği pilot projede denenmeli, sonra genişletilmelidir
- Tüm sistemi bir anda AI'a geçirmeye çalışmayın
- Ölçülebilir hedefler koyun (ör. "3 ayda self-healing ile %30 bakım azaltma")
- Her fazda geri dönüş planı olmalıdır

### 1.3 Deterministik Test > AI Test
- Deterministik, tekrarlanabilir testler her zaman tercih edilmelidir
- AI, mevcut deterministik testlerin tamamlayıcısıdır, yerine geçmez
- Smoke ve P0 testleri asla AI'a bağımlı olmamalıdır
- AI testler ayrı marker/tag ile işaretlenmelidir (`@ai`, `marker: ai`)

### 1.4 Ölçüm Odaklılık
- Her AI özelliğinin ROI'si ölçülmelidir
- Metrikler: bakım süresi değişimi, flaky oranı, coverage artışı, CI süresi
- Dashboard'da AI etki metrikleri görünür olmalıdır

---

## 2. Locator Stratejisi

### 2.1 Locator Öncelik Zinciri

BGTS projesinde locator seçimi aşağıdaki öncelik sırasıyla yapılmalıdır:

```
1. data-testid  (en güvenilir, BGTS convention)
2. getByRole    (ARIA rolleri, accessibility uyumlu)
3. getByLabel   (form elemanları için)
4. getByText    (benzersiz metin içerikli elementler)
5. AI-generated (LLM tabanlı, acil durum fallback)
6. CSS selector (son çare, en kırılgan)
```

### 2.2 data-testid Kuralları (Mevcut Convention)

Mevcut `.cursor/rules/data-testid-convention.mdc` kuralları geçerlidir:

```
Pattern: {screen}-{element-type}-{identifier}

Örnekler:
  login-input-email
  login-btn-submit
  scenarios-table
  scenarios-row-{id}
  projects-btn-new
```

### 2.3 AI Locator Kuralları

- AI locator sadece 1-4. stratejiler başarısız olduğunda kullanılmalıdır
- Her AI locator çağrısı loglanmalıdır (maliyet ve kalite izleme)
- AI locator başarılıysa, kalıcı locator oluşturulmalıdır (ör. testId eklenmeli)
- AI locator ile sürekli bulunan elementler, testId eksikliğini gösterir — UI'a testId ekleyin

### 2.4 Locator Repository Yönetimi

```
engine/locators/
├── locator_repository.json     # Ana locator veritabanı
├── default/
│   └── bgts_locators.json      # Sayfalar bazlı locator'lar
└── ai_healing/
    └── healing_history.json    # Healing geçmişi ve AI locator'lar
```

- Locator repository version control'da tutulmalıdır
- AI healing sonrası locator değişiklikleri ayrı branch'te PR olarak gönderilmelidir
- Aylık locator health check yapılmalıdır (kullanılmayan locator'ları temizle)

---

## 3. Test Üretimi Kuralları

### 3.1 AI Üretim Test Kodu Standartları

AI tarafından üretilen testler aşağıdaki standartlara uymalıdır:

**Dosya adlandırma:**
```
e2e/ai-generated/{feature}.spec.ts      # TypeScript E2E
engine/features/ai_generated/{f}.feature # Gherkin BDD
engine/tests/ai_generated/test_{f}.py   # Python test
```

**Zorunlu metadatalar:**
```typescript
// Her AI üretim test dosyasının başında:
// @generated-by: ai-test-generator
// @generated-date: 2026-04-03
// @requirement: BGTS-123
// @review-status: pending
```

```python
# Pytest marker'ı:
@pytest.mark.ai
@pytest.mark.generated
def test_example():
    ...
```

### 3.2 AI Üretim Test Kalite Kontrol

AI ürettiği her test aşağıdaki kontrollerden geçmelidir:

1. **Syntax check** — derleme/parse hatası yok
2. **Lint** — proje lint kurallarına uygun (ruff, eslint)
3. **Dry run** — en az bir kez başarıyla çalışır
4. **Assertion count** — en az 1 anlamlı assertion var
5. **Page Object uyumu** — mevcut page object'leri doğru kullanıyor
6. **Locator uyumu** — data-testid convention'a uygun
7. **İnsan review** — SR/QA mühendisi onayı

### 3.3 AI Test İzolasyonu

```
pytest.ini marker'ları:
  ai: AI motor testleri (OPENAI_API_KEY gerektirir)
  generated: AI tarafından üretilmiş testler
  
CI/CD'de:
  PR: -m 'not ai'           # AI testler PR'da çalışmaz
  Nightly: -m 'ai'          # AI testler gece çalışır
  Manuel: --all              # Tümü çalışır
```

---

## 4. Self-Healing Politikası

### 4.1 Healing Kuralları

- **Heal edilebilen hata türleri**: Locator kırılması, element ID/class değişikliği, DOM yapı kayması
- **Heal EDİLEMEYEN türler**: İş mantığı değişikliği, sayfa akışı değişikliği, veri değişikliği, beklenen davranış değişikliği
- Healing sadece **1 retry** ile sınırlandırılmalıdır (sonsuz döngü engellenmeli)
- Her healing event **zorunlu olarak loglanmalıdır**

### 4.2 Healing Onay Akışı

```
Test Başarısız → Self-Heal Dene → 
  Başarılı → Log + PR oluştur (locator güncellemesi) → İnsan review
  Başarısız → Gerçek hata raporu oluştur
```

- Healing PR'ları otomatik merge YAPMAMALIDIR
- Healing PR'ları 48 saat içinde review edilmelidir
- Aynı locator 3 kez üst üste heal edildiyse, kök neden analizi zorunludur

### 4.3 Healing Metrikleri

Aşağıdaki metrikler izlenmelidir:
- Healing oranı (heal edilen / başarısız)
- Yanlış healing oranı (gerçek bug maskeleme)
- En çok heal edilen locator'lar (kök neden adayları)
- Healing maliyeti (LLM çağrı maliyeti)

### 4.4 Karantina Politikası

- Flaky skoru > 0.3 olan testler otomatik karantinaya alınır
- Karantina testleri nightly suite'ten çıkarılır, ayrı raporda görünür
- Karantina süresi max 2 hafta — 2 hafta içinde düzeltilmezse test devre dışı bırakılır
- Karantina listesi haftalık olarak gözden geçirilir

---

## 5. BDD Generation Kuralları

### 5.1 Gereksinim → Gherkin Dönüşüm Standartları

```gherkin
# İyi Örnek:
Feature: Login sayfası güvenlik kontrolleri
  Bankacılık uygulamasına güvenli giriş yapılmasını sağlar.

  Scenario: Geçersiz şifre ile giriş denemesi
    Given kullanıcı "/login" sayfasında
    When "login-input-email" alanına "test@bgts.dev" yazar
    And "login-input-password" alanına "yanlis_sifre" yazar
    And "login-btn-submit" butonuna tıklar
    Then "login-alert-error" görünür olmalı
    And hata mesajı "Geçersiz kimlik bilgileri" içermeli

# Kötü Örnek (çok belirsiz):
  Scenario: Login testi
    Given kullanıcı sayfada
    When giriş yapar
    Then çalışmalı
```

### 5.2 Step Definition Reuse Politikası

- Yeni step yazmadan önce mevcut step kütüphanesi kontrol edilmelidir
- Aynı aksiyonu yapan birden fazla step olmamalıdır
- Step'ler parameterize olmalıdır (hardcoded değer yasak)
- Step isimleri Türkçe ve açıklayıcı olmalıdır

### 5.3 BDD Senaryo Sınırları

- Bir feature dosyasında max 10 senaryo
- Bir senaryo max 10 step
- Her senaryo en az 1 Then (assertion) içermelidir
- Background sadece gerçekten ortak olan step'ler için kullanılmalıdır

---

## 6. Sentetik Veri Yönetimi

### 6.1 Veri Üretim Kuralları

- Gerçek müşteri verisi **ASLA** test ortamında kullanılmamalıdır
- Sentetik veri **etiketlenmelidir** (metadata: `"synthetic": true`)
- Üretim veritabanından sentetik veri veritabanına bağlantı olmamalıdır
- Sentetik veri seed'i sabit tutulmalıdır (tekrarlanabilirlik)

### 6.2 Bankacılık Verisi Özel Kuralları

- TC Kimlik numaraları gerçek değil, format-uyumlu olmalıdır
- IBAN numaraları geçersiz kontrol basamağı ile üretilmelidir
- Telefon numaraları mevcut operatör prefix'leri kullanmamalıdır
- Adres bilgileri gerçek adreslerle eşleşmemelidir

### 6.3 Korelasyon Koruma

```
Korunması gereken korelasyonlar:
- müşteri_segmenti ↔ gelir_aralığı
- gelir_aralığı ↔ hesap_bakiyesi  
- yaş ↔ risk_skoru
- işlem_türü ↔ işlem_tutarı
- hesap_türü ↔ para_birimi
```

### 6.4 Kalite Doğrulama

Her sentetik veri seti üretiminde:
1. FK bütünlüğü kontrol edilmelidir
2. İstatistiksel dağılımlar orijinal ile karşılaştırılmalıdır
3. İş kuralları doğrulanmalıdır (ör. negatif bakiye sadece kredi hesabında)
4. Kalite skoru raporlanmalıdır

---

## 7. LLM Kullanım Politikası

### 7.1 Model Seçim Kuralları

| Görev Karmaşıklığı | Önerilen Model | Gerekçe |
|---------------------|---------------|---------|
| Basit sınıflandırma | Yerel LLM (Ollama) | Maliyet sıfır, gizlilik |
| Locator üretimi | GPT-4o-mini / Haiku | Hızlı, düşük maliyet |
| Test kodu üretimi | GPT-4o | Yüksek kalite |
| BDD senaryo üretimi | GPT-4o | Türkçe kalite, domain bilgisi |
| Güvenlik analizi | Claude 3.5 Sonnet | Analitik yetenek |

### 7.2 PII (Kişisel Bilgi) Koruma

LLM'e gönderilen veride aşağıdaki bilgiler **maskelenmelidir**:
- TC Kimlik numarası → `[TC_KIMLIK]`
- IBAN → `[IBAN]`
- E-posta adresi → `[EMAIL]`
- Telefon numarası → `[TELEFON]`
- Banka hesap numarası → `[HESAP_NO]`

```python
# LLM Gateway PII sanitization kuralı:
PII_PATTERNS = [
    (r"\b\d{11}\b", "[TC_KIMLIK]"),
    (r"\bTR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b", "[IBAN]"),
    (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL]"),
    (r"\b05\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b", "[TELEFON]"),
]
```

### 7.3 Maliyet Yönetimi

- **Bütçe limiti**: Aylık LLM bütçesi belirlenmeli ve izlenmelidir
- **Cache**: Aynı/benzer prompt'lar cache'lenmelidir (%30-50 tasarruf)
- **Batch**: Mümkün olduğunda birden fazla istek tek çağrıda birleştirilmelidir
- **Prompt optimizasyonu**: Gereksiz context minimumda tutulmalıdır
- **Model downgrade**: Düşük karmaşıklıktaki görevler için küçük model kullanılmalıdır

### 7.4 Hata Yönetimi

- LLM API hatası durumunda test **başarısız sayılmamalıdır** (graceful degradation)
- LLM erişilemezse AI özellikler devre dışı kalmalı, temel testler çalışmaya devam etmelidir
- Timeout: LLM çağrıları max 30 saniye, aşarsa skip
- Rate limit: Saatlik max 100 çağrı (konfigüre edilebilir)

---

## 8. CI/CD Entegrasyon Kuralları

### 8.1 PR Pipeline

```
PR Açıldığında:
1. Lint + Type Check (zorunlu, AI bağımsız)
2. Unit test (zorunlu, -m 'not ai')
3. AI Test Prioritization → seçilen testler
4. Smoke test (zorunlu)
5. Seçilen regression testleri
6. Self-healing retry (1 deneme)
7. Sonuç raporu
```

### 8.2 Nightly Pipeline

```
Her Gece (02:00 UTC):
1. Full regression suite
2. AI-generated test suite  
3. Coverage gap analizi
4. Flaky test analizi + karantina güncelleme
5. Anomaly detection
6. Sentetik veri yenileme
7. Dashboard güncelleme
```

### 8.3 Haftalık Pipeline

```
Her Pazartesi (03:00 UTC):
1. k6 performans testleri
2. Güvenlik taraması (ZAP)
3. Model re-training (prioritization)
4. Healing geçmişi analizi
5. Coverage trend raporu
```

### 8.4 AI Feature Flag

```typescript
// e2e/config/environments.ts
const features = {
  ai: process.env.ENABLE_AI_FEATURES === "true",
  selfHealing: process.env.ENABLE_SELF_HEALING === "true",
  syntheticData: process.env.ENABLE_SYNTHETIC_DATA === "true",
  aiPrioritization: process.env.ENABLE_AI_PRIORITIZATION === "true",
};
```

- Her AI özelliği feature flag ile kontrol edilmelidir
- Varsayılan: AI özellikler **kapalı** (opt-in)
- CI ortamında `OPENAI_API_KEY` yoksa AI özellikler otomatik devre dışı kalmalıdır

---

## 9. Test Kalite Kapısı

### 9.1 AI Üretim Testler İçin Kalite Kapısı

| Kriter | Eşik | Zorunlu |
|--------|-------|---------|
| Syntax hatasız | %100 | Evet |
| En az 1 assertion | %100 | Evet |
| Page Object uyumu | %100 | Evet |
| Locator convention uyumu | %100 | Evet |
| Dry run başarılı | %100 | Evet |
| İnsan review onayı | %100 | Evet |
| Flaky değil (5 ardışık geçiş) | %100 | Evet |

### 9.2 Coverage Hedefleri

| Alan | Mevcut (Tahmini) | Hedef (6 ay) | Hedef (12 ay) |
|------|-------------------|-------------|---------------|
| Backend (Python) | %60 | %75 | %85 |
| Engine (Python) | %40 | %60 | %75 |
| E2E akış coverage | %50 | %70 | %85 |
| API endpoint coverage | %55 | %80 | %90 |

### 9.3 Stabilite Hedefleri

| Metrik | Mevcut | Hedef |
|--------|--------|-------|
| Flaky test oranı | Bilinmiyor | < %5 |
| Self-healing oranı | N/A | > %80 |
| CI başarı oranı | Bilinmiyor | > %95 |
| Ortalama CI süresi | Bilinmiyor | < 10 dk (PR) |

---

## 10. Güvenlik ve Gizlilik

### 10.1 KVKK Uyumu

- Test ortamında gerçek müşteri verisi **YASAK**
- LLM'lere gerçek PII gönderimi **YASAK**
- Sentetik veri etiketleme **ZORUNLU**
- Veri maskeleme pipeline'ı **ZORUNLU**
- Log dosyalarında PII otomatik maskelenmeli

### 10.2 API Key Yönetimi

- API key'ler **ASLA** koda yazılmamalıdır
- GitHub Secrets veya vault kullanılmalıdır
- API key rotasyonu: 90 günde bir
- Key erişim logları izlenmelidir

### 10.3 LLM Güvenlik

- LLM çıktıları **güvenilmez girdi** olarak ele alınmalıdır
- LLM üretimi kodda `eval()`, `exec()` veya shell injection riski kontrol edilmelidir
- LLM'e gönderilen prompt'lar loglanmalı ve denetlenebilir olmalıdır

---

## 11. Raporlama ve İzlenebilirlik

### 11.1 AI Test Raporlama

Her AI işlemi için aşağıdaki bilgiler kaydedilmelidir:

```json
{
  "operation": "test_generation",
  "timestamp": "2026-04-03T14:30:00Z",
  "model": "gpt-4o",
  "input_summary": "Login sayfası negatif test senaryosu",
  "output_type": "feature_file",
  "output_path": "engine/features/ai_generated/login_negative.feature",
  "tokens_used": 1250,
  "cost_usd": 0.03,
  "validation_passed": true,
  "review_status": "pending"
}
```

### 11.2 Healing Raporu

```json
{
  "event": "self_healing",
  "test": "login.spec.ts > Geçersiz şifre hatası",
  "timestamp": "2026-04-03T02:15:00Z",
  "old_locator": "[data-testid='login-error']",
  "new_locator": "[data-testid='login-alert-error']",
  "strategy": "testId_fuzzy_match",
  "confidence": 0.92,
  "dom_diff_summary": "Alert component testId değişti",
  "verified": true
}
```

### 11.3 Dashboard Gereksinimleri

- Gerçek zamanlı test durumu
- AI özellik kullanım istatistikleri
- LLM maliyet takibi
- Healing trend grafiği
- Flaky test listesi ve durumu
- Coverage gap heat map
- Test prioritization etkinliği

---

## 12. Anti-Pattern'lar

### YAPMAYIN

| Anti-Pattern | Neden | Doğru Yaklaşım |
|-------------|-------|-----------------|
| AI testleri otomatik merge | Gerçek bug maskeleme riski | PR oluştur, insan review |
| Tüm testleri AI'a bırakma | Güvenilirlik kaybı | AI tamamlayıcıdır |
| LLM'e gerçek müşteri verisi gönderme | KVKK/GDPR ihlali | PII maskeleme |
| Self-healing'i sınırsız retry yapma | Sonsuz döngü, CI blokajı | Max 1 retry |
| AI testleri production'da çalıştırma | Performans etkisi | Test/staging ortamında |
| Coverage'ı tek metrik olarak kullanma | Coverage ≠ kalite | Assertion kalitesi + coverage |
| Tek LLM modeline bağlanma | Vendor lock-in, maliyet | Model router + cache |
| Flaky testleri ignore etme | Test güvenilirliği erozyonu | Karantina + fix |
| AI locator'u kalıcı locator olarak kullanma | Kırılgan, maliyetli | testId eklemeye yönlendir |
| Healing log'ları incelememek | Sessiz regresyon | Haftalık healing review |
