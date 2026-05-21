# AI Test Otomasyon Araçları — Kapsamlı Karşılaştırma

**Tarih:** 2026-04-03
**Kapsam:** Piyasadaki AI destekli test otomasyon araçlarının detaylı özellik, fiyat ve BGTS uyumu karşılaştırması

---

## İçindekiler

1. [UI Test Otomasyon Platformları](#1-ui-test-otomasyon-platformları)
2. [AI Test Üretim Araçları](#2-ai-test-üretim-araçları)
3. [Self-Healing Araçları](#3-self-healing-araçları)
4. [BDD / Gherkin Araçları](#4-bdd--gherkin-araçları)
5. [Sentetik Veri Araçları](#5-sentetik-veri-araçları)
6. [Güvenlik Test Araçları](#6-güvenlik-test-araçları)
7. [Performans Analiz Araçları](#7-performans-analiz-araçları)
8. [Flaky Test / Anomaly Araçları](#8-flaky-test--anomaly-araçları)
9. [Coverage ve Kalite Araçları](#9-coverage-ve-kalite-araçları)
10. [Visual Test Araçları](#10-visual-test-araçları)
11. [Mobil Test Araçları](#11-mobil-test-araçları)
12. [BGTS İçin Önerilen Araç Seti](#12-bgts-için-önerilen-araç-seti)

---

## 1. UI Test Otomasyon Platformları

| Araç | AI Özellikleri | Self-Healing | Desteklenen Platformlar | Programlama Dili | Açık Kaynak | Fiyat (Aylık) | BGTS Uyumu |
|------|---------------|-------------|------------------------|-----------------|-------------|---------------|------------|
| **Playwright + MCP** | Planner/Generator/Healer agent'ları, accessibility snapshot, MCP protocol | Evet (Healer Agent) | Web (Chromium, Firefox, WebKit) | TypeScript, Python, Java, C# | Evet | Ücretsiz | ★★★★★ |
| **Selenium + Healenium** | Healenium self-healing eklentisi | Evet (ML tabanlı) | Web (tüm tarayıcılar) | Java, Python, C#, Ruby | Evet | Ücretsiz | ★★★★☆ |
| **Testim (Tricentis)** | Smart Locators, AI stabilization, agentic otomasyon | Evet | Web | JavaScript, codeless | Hayır | ~$300 | ★★★☆☆ |
| **mabl** | Agentic Tester, Auto TFA, low-code | Evet | Web, Mobile, API | Codeless + JS | Hayır | Özel fiyat ($500+) | ★★★☆☆ |
| **Functionize** | 200+ AI sinyal, Digital Workers, NL test oluşturma | Evet (99.97%) | Web, API | NL + codeless | Hayır | Enterprise ($1000+) | ★★☆☆☆ |
| **Katalon** | StudioAssist, TrueTest, AI test önerisi | Sınırlı | Web, Mobile, API, Desktop | Groovy, codeless | Kısmen | $208+ | ★★★☆☆ |
| **Cypress** | cy.prompt() (NL → test), AI rekorder | Hayır | Web (Chromium) | JavaScript | Kısmen | Ücretsiz (Cloud: ücretli) | ★★☆☆☆ |

### Değerlendirme Kriterleri

| Kriter | Playwright MCP | Testim | mabl | Functionize | Katalon |
|--------|---------------|--------|------|-------------|---------|
| Kurulum kolaylığı | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★☆☆ | ★★★★☆ |
| Esneklik | ★★★★★ | ★★★☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★★★☆ |
| CI/CD entegrasyon | ★★★★★ | ★★★★☆ | ★★★★★ | ★★★★☆ | ★★★★☆ |
| Topluluk desteği | ★★★★★ | ★★★☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★★★★☆ |
| Vendor bağımlılığı | Yok | Yüksek | Yüksek | Çok Yüksek | Orta |
| Maliyet/performans | ★★★★★ | ★★★☆☆ | ★★☆☆☆ | ★☆☆☆☆ | ★★★★☆ |

---

## 2. AI Test Üretim Araçları

| Araç | Hedef | Üretim Türü | Dil/Framework | Kalite | Fiyat | BGTS Uyumu |
|------|-------|-------------|---------------|--------|-------|------------|
| **Playwright Test Generator** | UI E2E | Codegen + AI optimizasyon | TypeScript | Yüksek | Ücretsiz | ★★★★★ |
| **Playwright Test Planner** | Test planı | URL exploration → MD plan | Markdown | Yüksek | Ücretsiz | ★★★★★ |
| **CoverUp** | Coverage artırma | LLM + coverage loop | Python/pytest | Orta-Yüksek | Ücretsiz | ★★★★☆ |
| **Diffblue Cover** | Unit test | AI agent, otomatik üretim | Java/JUnit | Çok Yüksek | Enterprise ($500+) | ★★★★☆ |
| **Codium/Qodo** | Unit + integration | IDE entegre AI test önerisi | Multi-language | Orta | Freemium | ★★★☆☆ |
| **TestPilot (GitHub)** | Unit test | Copilot tabanlı öneriler | Multi-language | Orta | GitHub Copilot | ★★★☆☆ |

### Detay Karşılaştırma

**Playwright Test Generator Agent:**
- Girdi: URL + test planı (Markdown)
- Çıktı: .spec.ts dosyası
- Entegrasyon: Playwright CLI
- Avantaj: Mevcut BGTS altyapısı ile tam uyumlu
- Dezavantaj: Karmaşık iş mantığı testlerinde insan müdahalesi gerekir

**CoverUp:**
- Girdi: Python kaynak kodu + mevcut coverage raporu
- Çıktı: Test fonksiyonları (pytest)
- Döngü: LLM test üretir → çalıştırılır → coverage arttı mı kontrol → tekrar
- Avantaj: Otomatik coverage artışı, OpenAI/Anthropic/Bedrock desteği
- Dezavantaj: Bazen anlamsız test üretebilir

**Diffblue Cover:**
- Girdi: Java sınıfları
- Çıktı: JUnit test dosyaları
- Avantaj: %80+ line coverage, enterprise kalite garantisi
- Dezavantaj: Sadece Java, yüksek maliyet
- BGTS: NexusQA Java projesi için uygun

---

## 3. Self-Healing Araçları

| Araç | Healing Yaklaşımı | Doğruluk Oranı | Desteklenen Framework | Açık Kaynak | Fiyat | BGTS Uyumu |
|------|-------------------|----------------|----------------------|-------------|-------|------------|
| **Playwright Healer Agent** | LLM + accessibility snapshot | ~95% | Playwright | Evet | Ücretsiz | ★★★★★ |
| **Healenium** | ML tabanlı, DOM diff | ~85% | Selenium Java/Python | Evet | Ücretsiz | ★★★★☆ |
| **Functionize** | 200+ AI sinyal | 99.97% | Proprietary | Hayır | Enterprise | ★★☆☆☆ |
| **Testim** | Smart Locators, multi-attribute | ~90% | Testim platform | Hayır | $300+/ay | ★★★☆☆ |
| **mabl** | AI-powered element identification | ~92% | mabl platform | Hayır | $500+/ay | ★★☆☆☆ |
| **OwlityAI** | Multi-dimensional signal analysis | ~90% | Playwright, Selenium, Cypress | Hayır | SaaS | ★★★☆☆ |

### Healing Kapsamı Karşılaştırma

| Hata Türü | Playwright Healer | Healenium | Functionize | Testim |
|-----------|-------------------|-----------|-------------|--------|
| CSS selector değişikliği | ✅ | ✅ | ✅ | ✅ |
| ID/testId değişikliği | ✅ | ✅ | ✅ | ✅ |
| Element yeri değişikliği | ✅ | ⚠️ | ✅ | ✅ |
| Text content değişikliği | ✅ | ⚠️ | ✅ | ✅ |
| DOM yapı değişikliği | ✅ | ⚠️ | ✅ | ⚠️ |
| Sayfa akışı değişikliği | ⚠️ | ❌ | ⚠️ | ❌ |
| Zamanlama sorunları | ⚠️ | ❌ | ✅ | ⚠️ |

✅ = Tam destek, ⚠️ = Kısmi destek, ❌ = Destek yok

---

## 4. BDD / Gherkin Araçları

| Araç | Yaklaşım | Girdi | Çıktı | Desteklenen Diller | Fiyat | BGTS Uyumu |
|------|----------|-------|-------|-------------------|-------|------------|
| **Gherkinizer** | NL → Gherkin + step code | İngilizce/Türkçe metin | Feature + step defs | Java, JS, Python, C#, Ruby | Freemium | ★★★★☆ |
| **BGTS BDD Generator** | Custom LLM pipeline | Doğal dil gereksinim | Feature + Python steps | Python (pytest-bdd) | İç geliştirme | ★★★★★ |
| **Playwright Test Planner** | URL exploration | Uygulama URL | Markdown test planı | Framework-agnostic | Ücretsiz | ★★★★★ |
| **Cypress cy.prompt()** | NL → Cypress test | Doğal dil komut | Cypress komutları | JavaScript | Cypress Cloud | ★☆☆☆☆ |

---

## 5. Sentetik Veri Araçları

| Araç | Teknik | Bankacılık Desteği | Gizlilik | Açık Kaynak | Fiyat | BGTS Uyumu |
|------|--------|-------------------|----------|-------------|-------|------------|
| **SDV (Synthetic Data Vault)** | CTGAN, CopulaGAN, TVAE, GaussianCopula | Genel (konfigüre edilebilir) | Diferansiyel gizlilik desteği | Evet | Ücretsiz | ★★★★★ |
| **Synthesized.io** | Enterprise TDM, AI masking | Avaloq, Temenos, Fiserv | GDPR/KVKK tam uyum | Hayır | Enterprise ($2000+) | ★★★☆☆ |
| **datasynth-banking** | Kural tabanlı KYC/AML | KYC, AML, fraud | Yapay veri (gerçek veri yok) | Evet (Rust) | Ücretsiz | ★★★★☆ |
| **DataFramer** | Differential privacy, GAN | Fraud, AML, kredi | Differential privacy | Hayır | Enterprise | ★★★☆☆ |
| **Faker + Custom** | Kural tabanlı, template | Sınırlı (korelasyon yok) | PII-free | Evet | Ücretsiz | ★★★☆☆ |
| **Gretel.ai** | LSTM, ACTGAN | Genel | Differential privacy | Kısmen | Freemium | ★★★☆☆ |

### Özellik Karşılaştırma

| Özellik | SDV | Synthesized | datasynth-banking | BGTS Mevcut |
|---------|-----|-------------|-------------------|-------------|
| Korelasyon koruma | ✅ | ✅ | ⚠️ | ❌ |
| FK bütünlüğü | ✅ | ✅ | ⚠️ | ❌ |
| Diferansiyel gizlilik | ✅ | ✅ | ❌ | ❌ |
| Kalite metrikleri | ✅ | ✅ | ❌ | ❌ |
| API entegrasyon | ✅ | ✅ | ❌ | ✅ |
| Bankacılık şablonları | ❌ | ✅ | ✅ | ⚠️ |
| Dağılım modelleme | ✅ (CTGAN) | ✅ | ❌ | ❌ (Faker) |

---

## 6. Güvenlik Test Araçları

| Araç | Yaklaşım | Otonom | OWASP Kapsamı | API Test | Fiyat | BGTS Uyumu |
|------|----------|--------|---------------|----------|-------|------------|
| **Shannon** | Otonom white-box AI pentester | Tam otonom | OWASP Top 10 | Evet | Ücretsiz (Beta) | ★★★★☆ |
| **AISEC** | AI agent pentester | Tam otonom | OWASP Top 10 + ekstra | Evet (GraphQL dahil) | SaaS | ★★★☆☆ |
| **OWASP ZAP** | Tarama + aktif saldırı | Yarı otonom | OWASP Top 10 | Evet (OpenAPI) | Ücretsiz | ★★★★★ |
| **Burp Suite + AI** | Proxy + AI analiz | Yarı otonom | Geniş | Evet | $449+/yıl | ★★★☆☆ |
| **Snyk** | SAST + SCA + Container | Otonom tarama | Kod güvenliği | API yok | Freemium | ★★★★☆ |

### Bankacılık Güvenlik Gereksinimleri

| Gereksinim | Shannon | AISEC | ZAP | Snyk |
|-----------|---------|-------|-----|------|
| SQL injection | ✅ | ✅ | ✅ | ✅ |
| XSS | ✅ | ✅ | ✅ | ✅ |
| Auth bypass | ✅ | ✅ | ⚠️ | ❌ |
| IDOR | ✅ | ✅ | ⚠️ | ❌ |
| Business logic flaws | ⚠️ | ✅ | ❌ | ❌ |
| Prompt injection (LLM) | ❌ | ⚠️ | ❌ | ❌ |
| KVKK data exposure | ⚠️ | ⚠️ | ⚠️ | ✅ |
| 2FA/TOTP handling | ✅ | ⚠️ | ❌ | N/A |

---

## 7. Performans Analiz Araçları

| Araç | AI Özelliği | Entegrasyon | Anomaly Detection | Fiyat | BGTS Uyumu |
|------|------------|-------------|-------------------|-------|------------|
| **k6 + Grafana Cloud** | AI anomaly detection, trend analiz | k6 native | Evet | Freemium | ★★★★★ |
| **Gatling Enterprise** | AI baseline, SLA monitoring | Standalone | Evet | Enterprise | ★★☆☆☆ |
| **Artillery** | Plugin tabanlı | Node.js | Sınırlı | Ücretsiz | ★★★☆☆ |
| **Custom (Python)** | Z-score, Isolation Forest | pytest/k6 | Tam özelleştirme | Geliştirme maliyeti | ★★★★★ |

---

## 8. Flaky Test / Anomaly Araçları

| Araç | Yaklaşım | Otomatik Fix | CI Entegrasyon | Fiyat | BGTS Uyumu |
|------|----------|-------------|----------------|-------|------------|
| **UnfoldCI** | AI analiz + fix PR oluşturma | Evet | GitHub Actions | SaaS | ★★★★☆ |
| **Panto** | CI anomaly monitoring | Hayır (sadece tespit) | GitHub, GitLab | SaaS | ★★★☆☆ |
| **OwlityAI** | Multi-signal analiz | Evet | Multi-CI | SaaS | ★★★☆☆ |
| **Custom (Python)** | Z-score + Isolation Forest | Özelleştirilebilir | GitHub Actions | Geliştirme maliyeti | ★★★★★ |
| **Launchable** | ML test selection + flaky detection | Hayır | GitHub, Jenkins | Freemium | ★★★★☆ |

---

## 9. Coverage ve Kalite Araçları

| Araç | AI Özelliği | Dil Desteği | Coverage Türü | Fiyat | BGTS Uyumu |
|------|------------|-------------|---------------|-------|------------|
| **CoverUp** | LLM-driven coverage artırma | Python | Satır, dal | Ücretsiz | ★★★★★ |
| **Diffblue Cover** | AI unit test üretimi | Java | Satır, dal, metot | Enterprise | ★★★★☆ |
| **SonarQube** | Statik analiz + kalite kapısı | Multi-language | Satır, dal + kalite | Freemium | ★★★★☆ |
| **Codacy** | AI code review + coverage | Multi-language | Satır, dal | Freemium | ★★★☆☆ |
| **Qodo (Codium)** | AI test önerisi | Multi-language | Davranış odaklı | Freemium | ★★★☆☆ |

---

## 10. Visual Test Araçları

| Araç | AI Özelliği | Platform | Baseline Yönetimi | Fiyat | BGTS Uyumu |
|------|------------|----------|-------------------|-------|------------|
| **Applitools Eyes** | Visual AI (layout/content ayrımı) | Web, Mobile | AI-powered | $100+/ay | ★★★★☆ |
| **Percy (BrowserStack)** | AI Visual Review Agent | Web, Mobile | Otomatik | Percy plan | ★★★★☆ |
| **Playwright Screenshots** | Pixel diff (built-in) | Web | Manuel | Ücretsiz | ★★★★★ |
| **Chromatic** | Storybook visual test | Web (React) | AI-assisted | Freemium | ★★☆☆☆ |

---

## 11. Mobil Test Araçları

| Araç | AI Özelliği | Platform | Cihaz | Fiyat | BGTS Uyumu |
|------|------------|----------|-------|-------|------------|
| **Appium + App Percy** | Visual AI review | iOS, Android | 30,000+ gerçek cihaz | BrowserStack plan | ★★☆☆☆ |
| **Rapise 9.0** | SmartActions, AI visual recognition | iOS, Android, Web | Simülatör + gerçek | Enterprise | ★★☆☆☆ |
| **Detox** | React Native native test | iOS, Android | Simülatör | Ücretsiz | ★☆☆☆☆ |
| **Playwright Mobile** | Responsive emulation | Web (responsive) | Emulated | Ücretsiz | ★★★★★ |

---

## 12. BGTS İçin Önerilen Araç Seti

### Tier 1: Temel (Hemen Uygulanacak)

| Kategori | Araç | Gerekçe |
|----------|------|---------|
| UI Test Platformu | **Playwright + MCP** | Zaten kullanımda, AI agent'ları ücretsiz |
| Self-Healing | **Playwright Healer Agent** | Native entegrasyon, sıfır maliyet |
| BDD Generation | **BGTS Custom + Gherkinizer** | Mevcut engine genişletmesi |
| Sentetik Veri | **SDV (open-source)** | CTGAN, korelasyon koruma, ücretsiz |
| Güvenlik | **OWASP ZAP** | Açık kaynak, API scan, CI entegrasyon |
| Coverage | **CoverUp** | Python coverage artırma, ücretsiz |

### Tier 2: Gelişmiş (3-6 Ay İçinde)

| Kategori | Araç | Gerekçe |
|----------|------|---------|
| Java Test Üretimi | **Diffblue Cover** | NexusQA migration desteği |
| Flaky Test | **UnfoldCI** veya **Custom** | Otomatik fix PR, CI entegrasyon |
| Visual Test | **Applitools Eyes** veya **Percy** | AI-powered visual regression |
| Performans | **k6 + Grafana AI** | Mevcut k6 altyapısı üzerine |

### Tier 3: İleri Düzey (6-12 Ay İçinde)

| Kategori | Araç | Gerekçe |
|----------|------|---------|
| Otonom Güvenlik | **Shannon** | Bankacılık sektörü gereksinimleri |
| Enterprise TDM | **Synthesized.io** | KVKK tam uyum, bankacılık şablonları |
| ML Prioritization | **Launchable** veya **Custom** | CI optimizasyonu |
| Mobil | **Appium + App Percy** | Mobil uygulama geliştirildiğinde |

### Maliyet Özeti

| Tier | Aylık Maliyet | Yıllık Maliyet | Değer |
|------|--------------|----------------|-------|
| Tier 1 | ~$50 (LLM API) | ~$600 | Temel AI test yetenekleri |
| Tier 1 + 2 | ~$500-800 | ~$6,000-10,000 | Gelişmiş otomasyon |
| Tier 1 + 2 + 3 | ~$2,000-3,000 | ~$24,000-36,000 | Enterprise düzey |

> **Not:** LLM API maliyeti kullanıma bağlıdır. GPT-4o ile günlük ~100 çağrı için aylık ~$30-50 öngörülmektedir. Cache ve model routing ile bu maliyet %50 azaltılabilir.
