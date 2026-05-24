# AI ile Test Otomasyonu — Kapsamlı Araştırma Raporu

**Tarih:** 2026-04-03
**Hazırlayan:** AI Test Otomasyon Mimarı
**Kapsam:** Piyasadaki tüm AI destekli test otomasyon yaklaşımlarının analizi, sınıflandırılması ve BGTS platformuna uygulanabilirlik değerlendirmesi
**Hedef Kitle:** Test mimarları, QA liderleri, DevOps mühendisleri, proje yöneticileri

---

## İçindekiler

1. [Yönetici Özeti](#1-yönetici-özeti)
2. [Test Otomasyon Türleri ve AI Entegrasyon Matrisi](#2-test-otomasyon-türleri-ve-ai-entegrasyon-matrisi)
3. [AI ile Test Otomasyonu Yaklaşımları](#3-ai-ile-test-otomasyonu-yaklaşımları)
4. [Risk ve Sınırlılıklar](#4-risk-ve-sınırlılıklar)
5. [Referanslar](#5-referanslar)

---

## 1. Yönetici Özeti

AI destekli test otomasyonu, 2025-2026 döneminde **agentic QA** paradigmasına geçiş yapmıştır. Artık AI sadece locator öneren veya test koduyla yardım eden bir asistan değil; uygulamayı keşfeden, test planlayan, test üreten, çalıştıran ve başarısız testleri kendi kendine onaran **otonom bir ajan** olarak konumlanmaktadır.

Bu rapor, piyasadaki 13 farklı AI test otomasyon yaklaşımını derinlemesine analiz etmektedir. Her yaklaşım için teknik gereksinimler, çalışma mekanizması, avantaj/dezavantajlar, güncel araçlar, kod örnekleri ve BGTS platformuna uygulanabilirlik değerlendirmesi sunulmaktadır.

**Temel Bulgular:**

- Playwright, 2026 itibarıyla AI test ekosisteminde lider konumda (MCP + Planner/Generator/Healer agent'ları)
- Self-healing testler, test bakım maliyetini %95'e kadar azaltabilmekte
- AI test üretimi, test yazma süresini %40-70 hızlandırmakta
- Sentetik veri üretimi, bankacılık gibi düzenlemeye tabi sektörlerde KVKK/GDPR uyumu için kritik
- Intelligent test prioritization, CI süresini %60-80 kısaltabilmekte
- Agentic QA (Plan-Act-Verify döngüsü), 2026'nın baskın paradigması

---

## 2. Test Otomasyon Türleri ve AI Entegrasyon Matrisi

### 2.1 UI Test Otomasyonu

| Özellik | Detay |
|---------|-------|
| **Tanım** | Web ve mobil uygulamaların kullanıcı arayüzlerinin otomatik test edilmesi |
| **BGTS Mevcut Durum** | Playwright E2E (TypeScript) + Selenium/Cucumber (Java/NexusQA) |
| **AI Entegrasyon Alanları** | Self-healing locator, visual regression AI, screen element tanıma, autonomous test generation, agentic exploration |
| **Hedef Araçlar** | Playwright MCP + Healer Agent, Applitools Eyes AI, TestDino |
| **Öncelik** | Yüksek — mevcut altyapı üzerine doğrudan inşa edilebilir |

**AI Uygulama Senaryoları:**
- Playwright Healer Agent ile kırılan locator'ların otomatik onarımı
- MCP (Model Context Protocol) üzerinden LLM'lerin tarayıcıya yapısal erişimi
- Accessibility snapshot tabanlı element tanıma (screenshot yerine DOM yapısı)
- Codegen + AI optimizasyon ile kayıt-oynat testlerinin Page Object pattern'a dönüşümü

### 2.2 API Test Otomasyonu

| Özellik | Detay |
|---------|-------|
| **Tanım** | REST/GraphQL API endpoint'lerinin işlevsellik, performans ve güvenlik testleri |
| **BGTS Mevcut Durum** | pytest + httpx (`api-tests/`), Postman koleksiyonları |
| **AI Entegrasyon Alanları** | Schema-tabanlı test üretimi, anomaly detection, contract drift tespiti, fuzz testing |
| **Hedef Araçlar** | Schemathesis + LLM, Postman AI Assistant, custom OpenAI chain |
| **Öncelik** | Yüksek |

**AI Uygulama Senaryoları:**
- OpenAPI şemasından otomatik edge-case test üretimi (Schemathesis)
- API yanıt anomaly detection (response time, status code pattern)
- Contract-first testing ile backend-frontend uyumsuzluk erken tespiti
- LLM ile API test senaryosu üretimi (doğal dil → pytest kodu)

### 2.3 BDD / Gherkin Testleri

| Özellik | Detay |
|---------|-------|
| **Tanım** | İş gereksinimlerinin Gherkin formatında yazılıp otomatik test olarak çalıştırılması |
| **BGTS Mevcut Durum** | pytest-bdd (engine), Cucumber (Java/NexusQA), `bdd-generate.spec.ts` E2E akışı |
| **AI Entegrasyon Alanları** | Natural language → Gherkin, step definition üretimi, senaryo tamamlama, domain-aware generation |
| **Hedef Araçlar** | Gherkinizer, custom GPT-4o pipeline, Playwright Test Planner |
| **Öncelik** | Çok Yüksek — mevcut engine entegrasyonu doğrudan genişletilebilir |

**AI Uygulama Senaryoları:**
- Kullanıcı hikayesinden otomatik Gherkin feature dosyası üretimi
- Mevcut step definition kütüphanesinden yeni senaryolar için step eşleştirme
- Edge case ve negatif senaryo önerisi
- Türkçe gereksinim → Türkçe Gherkin dönüşümü (domain-specific)

### 2.4 Performans / Yük Testleri

| Özellik | Detay |
|---------|-------|
| **Tanım** | Uygulamanın yük altındaki davranışının test edilmesi |
| **BGTS Mevcut Durum** | k6 (`tests/performance/` — load, stress, spike, soak senaryoları) |
| **AI Entegrasyon Alanları** | Load profil optimizasyonu, anomaly detection, baseline karşılaştırma, otomatik threshold belirleme |
| **Hedef Araçlar** | k6 + Grafana AI, custom anomaly detector |
| **Öncelik** | Orta |

**AI Uygulama Senaryoları:**
- k6 sonuçlarının AI ile analizi (regression tespiti, darboğaz tanıma)
- Üretim trafiğinden realistic load profil çıkarma
- Anomaly detection ile performans bozulma erken uyarısı

### 2.5 Security Test Otomasyonu

| Özellik | Detay |
|---------|-------|
| **Tanım** | Güvenlik açıklarının otomatik tespiti ve penetrasyon testleri |
| **BGTS Mevcut Durum** | Dokümantasyon seviyesinde (`qa/test-design/security.md`), pytest `security` marker'ı |
| **AI Entegrasyon Alanları** | OWASP vulnerability scanning, AI fuzzing, LLM güvenlik testi, prompt injection testi |
| **Hedef Araçlar** | Shannon (autonomous pentester), AISEC, ZAP + AI plugin |
| **Öncelik** | Yüksek — bankacılık sektörü gereksinimleri |

**AI Uygulama Senaryoları:**
- Shannon ile otonom white-box penetrasyon testi (OWASP Top 10)
- API endpoint'lerinde AI-driven fuzz testing
- LLM kullanılan endpoint'lerde prompt injection testi
- Otomatik güvenlik raporu oluşturma

### 2.6 Mobile Test Otomasyonu

| Özellik | Detay |
|---------|-------|
| **Tanım** | iOS ve Android uygulamalarının otomatik test edilmesi |
| **BGTS Mevcut Durum** | Web-first yaklaşım; Playwright `mobile` projesi mevcut (responsive doğrulama) |
| **AI Entegrasyon Alanları** | Visual element recognition, self-healing Appium, cross-device AI optimizasyon |
| **Hedef Araçlar** | Appium + App Percy, BrowserStack AI, Rapise AI |
| **Öncelik** | Düşük — şu an mobil uygulama yok |

### 2.7 Regression / Smoke / Sanity

| Özellik | Detay |
|---------|-------|
| **Tanım** | Mevcut işlevselliğin korunduğunu doğrulayan testler |
| **BGTS Mevcut Durum** | pytest marker'ları (`smoke`, `regression`, `P0`-`P3`), Playwright projeleri (smoke/regression/full) |
| **AI Entegrasyon Alanları** | Intelligent test selection, impact analysis, risk-based prioritization, flaky test detection |
| **Hedef Araçlar** | Launchable, custom ML model, UnfoldCI |
| **Öncelik** | Yüksek — CI/CD verimliliği için kritik |

### 2.8 End-to-End Testler

| Özellik | Detay |
|---------|-------|
| **Tanım** | Kullanıcı akışlarının baştan sona doğrulanması |
| **BGTS Mevcut Durum** | Playwright E2E suite (`e2e/` — 15+ spec dosyası, page object'ler, fixture'lar) |
| **AI Entegrasyon Alanları** | Autonomous test exploration, agentic QA, flow-based generation |
| **Hedef Araçlar** | Playwright Planner + Generator agents, Octomind, Bug0 |
| **Öncelik** | Çok Yüksek |

---

## 3. AI ile Test Otomasyonu Yaklaşımları

### 3.1 AI ile Locator Üretimi

#### Açıklama
DOM snapshot ve accessibility tree analizi kullanarak en dayanıklı locator stratejisini otomatik oluşturma yaklaşımıdır. Geleneksel CSS/XPath locator'lar UI değişikliklerinde kolayca kırılırken, AI tabanlı locator üretimi birden fazla özniteliği (metin, rol, konum, görsel benzerlik) kullanarak elementi benzersiz şekilde tanımlar.

#### Teknik Gereksinimler
- DOM erişimi (Playwright Page veya Selenium WebDriver)
- Accessibility tree parser veya LLM API
- Locator repository (JSON/DB formatında)
- Önceki başarılı locator geçmişi

#### Nasıl Çalışır
1. Element hedefi belirlenir (ör. "login butonu")
2. DOM snapshot veya accessibility tree alınır
3. Multi-attribute fingerprint oluşturulur (testId, role, label, text, position)
4. Eşleşme skoru hesaplanır ve en güvenilir locator stratejisi seçilir
5. Locator repository'ye kaydedilir

#### Avantajlar
- Test bakım maliyetinde %90'a varan düşüş
- Self-healing testlerle birlikte kullanıldığında CI/CD stabilitesi artar
- Locator kırılması nedeniyle false failure oranı azalır
- Birden fazla locator stratejisi ile yedeklilik sağlanır

#### Dezavantajlar
- Dinamik DOM yapılarında yanlış pozitif üretebilir
- LLM tabanlı çözümlerde API maliyeti ve gecikme
- İlk kurulum ve fine-tuning eforu
- Çok benzer elementlerde (ör. tablo hücreleri) belirsizlik

#### Örnek Araçlar
| Araç | Yaklaşım | Maliyet |
|------|----------|---------|
| Playwright MCP | Accessibility snapshot tabanlı | Ücretsiz |
| Testim Smart Locators | ML tabanlı multi-attribute | ~$300/ay |
| Functionize | 200+ AI sinyal, 99.97% tanıma | Enterprise |
| Healenium (Selenium) | Açık kaynak self-healing | Ücretsiz |

#### BGTS Uyumu
BGTS'de mevcut `data-testid` convention, AI locator chain'in ilk katmanı olarak korunur. Fallback zinciri: `testId → role → label → AI-generated → CSS`. Engine'deki `locators/locator_repository.json` yapısı AI locator metadata'sı ile genişletilebilir.

#### Kullanım Senaryoları
- Sprint sonrası UI refactoring'de kırılan testlerin otomatik düzelmesi
- Yeni eklenen sayfalar için locator önerisi
- Legacy NexusQA Java projesi locator'larının modernizasyonu

#### Riskler
- AI locator'un yanlış element seçmesi (false positive healing)
- LLM maliyetlerinin CI çalıştırma başına artması
- Locator geçmişi veritabanının büyümesi ve yönetimi

---

### 3.2 Screen / DOM Element Tanıma

#### Açıklama
Screenshot veya DOM snapshot üzerinden görsel/yapısal element tespiti. Computer vision veya accessibility tree analizi ile locator olmaksızın element bulma yeteneği sağlar.

#### Teknik Gereksinimler
- Computer vision modeli (görsel yaklaşım) veya accessibility tree parser (yapısal yaklaşım)
- GPU (görsel) veya LLM API (yapısal)
- Referans screenshot veritabanı (görsel)

#### Nasıl Çalışır
**Yapısal Yaklaşım (Önerilen):**
1. Playwright MCP ile accessibility snapshot alınır
2. LLM'e "Bu sayfada login butonu nerede?" gibi soru sorulur
3. LLM, accessibility tree'den doğru elementi tanımlar ve locator döndürür

**Görsel Yaklaşım:**
1. Ekran görüntüsü alınır
2. Computer vision modeli ile element bölgeleri tespit edilir
3. OCR ile metin çıkarılır, element türü sınıflandırılır

#### Avantajlar
- Locator kırılmasından bağımsız element bulma
- Cross-platform uyumluluk (web, mobile, desktop)
- Canvas/WebGL gibi geleneksel locator'ın çalışmadığı alanlarda etkili

#### Dezavantajlar
- Görsel yaklaşımda yavaşlık ve GPU gereksinimi
- Belirsizlik — benzer elementlerin ayırt edilmesi
- Screenshot tabanlı yaklaşımlarda çözünürlük/tema bağımlılığı

#### Örnek Araçlar
| Araç | Yaklaşım | Maliyet |
|------|----------|---------|
| Playwright MCP | Accessibility snapshot (screenshot değil) | Ücretsiz |
| Applitools Eyes | Visual AI + DOM | $100+/ay |
| Test.ai | Computer vision | Enterprise |
| Rapise SmartActions | AI visual recognition + NL | Enterprise |

#### BGTS Uyumu
Playwright MCP entegrasyonu ile accessibility-first yaklaşım benimsenmelidir. Screenshot tabanlı görsel yaklaşım, visual regression testleri (mevcut `numpy` + `Pillow` altyapısı) ile sınırlı kalmalıdır.

#### Riskler
- Görsel yaklaşımda tema değişikliklerinde tüm baseline'lar geçersiz olabilir
- Accessibility tree eksik olan uygulamalarda yapısal yaklaşım yetersiz kalır

---

### 3.3 Model Tabanlı Test Üretimi

#### Açıklama
Uygulamanın davranış modelinden (state machine, flow diagram, karar ağacı) otomatik test yolları oluşturma yaklaşımıdır. Uygulama bir graf olarak modellenir ve graf traversal algoritmaları ile tüm olası yollar veya belirli coverage kriterlerini karşılayan yollar üretilir.

#### Teknik Gereksinimler
- Uygulama flow modeli (state machine, React Flow diyagramı)
- Graf traversal algoritmaları (DFS, BFS, all-paths, random walk)
- LLM (model oluşturma ve path açıklama için)
- Test template engine

#### Nasıl Çalışır
1. Uygulama akışları state machine olarak modellenir (durumlar = sayfalar, geçişler = aksiyonlar)
2. Coverage kriteri belirlenir (state coverage, transition coverage, all-paths)
3. Algoritma, modelden test yolları çıkarır
4. Her yol için somut test kodu üretilir (page object'ler ve test data ile)
5. Model güncellendiğinde testler otomatik yeniden üretilir

#### Avantajlar
- Yüksek test coverage (özellikle edge case'ler)
- Sistematik ve tekrarlanabilir test üretimi
- Model değişikliğinde testler otomatik güncellenir
- İş analistleri modeli anlayabilir ve katkıda bulunabilir

#### Dezavantajlar
- Model oluşturma maliyeti yüksek (ilk yatırım)
- Model ile gerçek uygulama arasında sapma (model drift)
- Karmaşık uygulamalarda state explosion problemi
- Bakım maliyeti: hem uygulama hem model güncellenmelidir

#### Örnek Araçlar
| Araç | Yaklaşım | Maliyet |
|------|----------|---------|
| TestOptimal | Algoritma tabanlı path generation | Enterprise |
| GraphWalker | Açık kaynak model-based testing | Ücretsiz |
| Spec Explorer | Microsoft, formal model | Ücretsiz |
| Custom LLM + React Flow | BGTS'ye özel | Geliştirme maliyeti |

#### BGTS Uyumu
BGTS'deki React Flow editörü (`apps/web/`) test modellemesi için kullanılabilir. Flow editöründen export edilen JSON, model-based test generation pipeline'ına girdi olarak verilebilir. Bu, mevcut altyapının benzersiz bir avantajıdır.

#### Kullanım Senaryoları
- Karmaşık iş akışlarının (onay süreçleri, senaryo versiyonlama) sistematik testi
- Yeni özellik eklendiğinde etki analizi
- Regression test suite'inin otomatik genişletilmesi

#### Riskler
- Model ile gerçeklik arasındaki farkın izlenmemesi
- State explosion nedeniyle test sayısının kontrol dışı artması
- Modelin güncel tutulması için ek bakım eforu

---

### 3.4 Test Case Generation (Natural Language → Test)

#### Açıklama
Doğal dil gereksinimlerinden (kullanıcı hikayesi, kabul kriteri, bug raporu) otomatik test kodu üretimi. LLM'ler, mevcut page object repository'si ve framework bilgisi ile çalıştırılabilir test kodu oluşturur.

#### Teknik Gereksinimler
- LLM API (GPT-4o, Claude 3.5, Gemini)
- Page object repository (element bilgileri, metot imzaları)
- Test framework bilgisi (pytest-bdd, Playwright test, JUnit)
- Template engine ve prompt engineering
- Code validation pipeline (syntax check, lint, dry-run)

#### Nasıl Çalışır
1. Kullanıcı doğal dilde gereksinim yazar (ör. "Kullanıcı login sayfasında geçersiz şifre girdiğinde hata mesajı görmelidir")
2. LLM'e gereksinim, mevcut page object'ler ve framework kuralları gönderilir
3. LLM, Gherkin feature + step definition veya direkt test kodu üretir
4. Üretilen kod syntax kontrolünden geçirilir
5. Test çalıştırılır ve sonuç raporlanır

#### Avantajlar
- Test yazma süresi %40-70 azalır
- Teknik olmayan ekipler (iş analistleri, ürün sahipleri) test tanımlayabilir
- Tutarlı test yapısı (template + rules ile zorunlu)
- Edge case önerisi ile insan gözden kaçırmalarını azaltır

#### Dezavantajlar
- Kalite değişken — hallucination riski
- Üretilen testlerin mutlaka insan review'dan geçmesi gerekir
- Domain-specific bilgi eksikliği (bankacılık terminolojisi)
- LLM API maliyeti

#### Örnek Araçlar
| Araç | Hedef | Dil | Maliyet |
|------|-------|-----|---------|
| Playwright Test Generator Agent | UI E2E | TypeScript | Ücretsiz |
| Playwright Test Planner Agent | Test planı | Markdown | Ücretsiz |
| CoverUp | Python coverage artırma | Python | Ücretsiz |
| Diffblue Cover | Java unit test | Java | Enterprise |
| Gherkinizer | BDD Gherkin | Multi-language | Freemium |
| Cypress cy.prompt() | UI test | JavaScript | Cypress Cloud |

#### BGTS Uyumu
Engine'deki mevcut OpenAI/Anthropic entegrasyonu doğrudan genişletilebilir. `bdd-generate.spec.ts` E2E akışı zaten bu konseptin proof-of-concept'idir. Page object repository (`e2e/pages/`, `engine/pages/`) LLM context'ine enjekte edilerek domain-aware test üretimi sağlanabilir.

#### Kullanım Senaryoları
- Sprint planlama sırasında user story'den otomatik test taslağı oluşturma
- Mevcut manual test case'lerin otomasyona dönüştürülmesi
- Yeni endpoint'ler için API test scaffold'u üretme

#### Riskler
- Hallucination — var olmayan element/endpoint referansı
- Over-generation — gereksiz test kalabalığı
- LLM model değişikliğinde (ör. GPT-4o → GPT-5) çıktı kalitesi sapması

---

### 3.5 Sentetik Test Verisi Üretimi

#### Açıklama
Gerçek veri dağılımlarını koruyarak yapay (sentetik) test verisi üretimi. Bankacılık gibi düzenlemeye tabi sektörlerde gerçek müşteri verisini test ortamında kullanmak KVKK/GDPR ihlali oluşturur; sentetik veri bu problemi çözer.

#### Teknik Gereksinimler
- İstatistiksel modeller (KDE, Gaussian Mixture)
- Derin öğrenme modelleri (CTGAN, CopulaGAN, TVAE)
- Diferansiyel gizlilik mekanizması
- Veri kalite metrikleri (istatistiksel sadakat, korelasyon koruma)
- İlişkisel bütünlük (FK) desteği

#### Nasıl Çalışır
1. Gerçek verinin şeması ve dağılımları analiz edilir
2. Korelasyonlar ve ilişkiler çıkarılır
3. Seçilen modelle (Faker → KDE → CTGAN) sentetik veri üretilir
4. FK bütünlüğü ve iş kuralları doğrulanır
5. Gizlilik garantisi uygulanır (diferansiyel gizlilik)
6. Kalite metrikleri hesaplanır ve raporlanır

#### Avantajlar
- KVKK/GDPR tam uyumluluk
- Sınırsız miktarda test verisi üretimi
- Edge case ve nadir olay simülasyonu (fraud, AML)
- Performans testleri için büyük hacimli veri

#### Dezavantajlar
- Kolonlar arası korelasyon kaybı (temel Faker ile)
- Model eğitim süresi (CTGAN)
- İlişkisel veri yapılarında FK tutarlılığı zor
- Üretilen verinin gerçekçiliğinin doğrulanması gerekli

#### Örnek Araçlar
| Araç | Özellik | Bankacılık | Maliyet |
|------|---------|-----------|---------|
| Synthesized.io | Enterprise TDM | Avaloq/Temenos | Enterprise |
| SDV (open-source) | CTGAN, CopulaGAN, TVAE | Genel | Ücretsiz |
| datasynth-banking | KYC/AML generator | Evet | Ücretsiz |
| DataFramer | Differential privacy | Evet | Enterprise |
| Faker + custom rules | Temel sentetik | Sınırlı | Ücretsiz |

#### BGTS Uyumu
BGTS'de `engine/ai_synthetic_data/` modülü zaten MVP seviyesinde çalışmaktadır. `docs/synthetic-data-research.md` raporundaki 3 fazlı yol haritası (KDE → CTGAN → Diferansiyel Gizlilik) doğrultusunda geliştirilmelidir. Mevcut pipeline: `CSV → SchemaAnalyzer → SemanticClassifier → RuleEngine → SyntheticGenerator → DataFrame`.

#### Kullanım Senaryoları
- E2E testleri için gerçekçi müşteri/hesap/işlem verisi üretimi
- Performans testleri için yüksek hacimli veri seti oluşturma
- Fraud detection model eğitimi için etiketli sentetik veri
- Yeni geliştirici onboarding'i için anonimize demo veri seti

#### Riskler
- Gerçek veri ile karıştırılma (etiketleme eksikliği)
- İstatistiksel sadakat eksikliğinden kaynaklanan yanıltıcı test sonuçları
- Model eğitimi sırasında gerçek veriye erişim gereksinimi (privacy bootstrapping problemi)

---

### 3.6 Self-Healing Testler

#### Açıklama
Test başarısızlıklarında otomatik locator/flow onarımı. UI değişikliklerinde kırılan testleri, önceki başarılı çalışma snapshot'ları ile karşılaştırarak otomatik düzeltme mekanizmasıdır.

#### Teknik Gereksinimler
- Locator geçmişi veritabanı (önceki başarılı locator'lar)
- DOM diff engine (önceki ve mevcut DOM karşılaştırma)
- Multi-attribute element fingerprinting
- ML modeli veya LLM (akıllı eşleştirme)
- Retry mekanizması (CI/CD entegrasyonu)

#### Nasıl Çalışır
1. Test çalışır ve bir locator ile element bulunamaz
2. Önceki başarılı DOM snapshot ile mevcut DOM karşılaştırılır
3. Değişen elementin yeni konumu multi-attribute fingerprinting ile tespit edilir:
   - Metin içeriği
   - ARIA rolleri ve etiketleri
   - Yakın komşu elementler
   - Görsel konum
   - Önceki CSS class/id fragmanları
4. Yeni locator belirlenir ve test yeniden çalıştırılır
5. Başarılıysa locator repository güncellenir ve rapor oluşturulur
6. Başarısızsa gerçek bug olarak raporlanır

#### Avantajlar
- Test bakım maliyetinde %95'e varan azalma
- CI/CD pipeline stabilitesi önemli ölçüde artar
- Geliştirici verimliliği artar (kırık test düzeltme süresi azalır)
- Flaky test oranı düşer

#### Dezavantajlar
- False positive healing — gerçek bug'ların maskelenmesi
- Healing geçmişinin izlenmesi ve denetlenmesi gerekir
- Karmaşık flow değişikliklerinde (sadece locator değil, akış değişimi) yetersiz kalır
- LLM tabanlı healing'de maliyet ve gecikme

#### Örnek Araçlar
| Araç | Healing Yaklaşımı | Doğruluk | Maliyet |
|------|-------------------|----------|---------|
| Playwright Healer Agent | LLM + accessibility snapshot | Yüksek | Ücretsiz |
| Functionize | 200+ AI sinyal | 99.97% | Enterprise |
| Healenium (Selenium) | ML tabanlı | ~85% | Ücretsiz |
| mabl | AI-powered | Yüksek | Enterprise |
| Testim | Smart Locators | ~90% | ~$300/ay |

#### BGTS Uyumu
Playwright Healer Agent entegrasyonu birincil hedef olmalıdır. Mevcut `e2e/` altyapısı (BasePage, testId helpers) ile doğrudan uyumludur. `locators/locator_repository.json` (engine) healing metadata'sı ile genişletilebilir.

#### Kullanım Senaryoları
- Sprint sonrası UI refactoring'de toplu locator kırılması
- CSS framework güncellemesinde (ör. Tailwind v3 → v4) class değişiklikleri
- Üçüncü parti bileşen güncellemelerinde DOM yapı değişiklikleri

#### Riskler
- **Kritik**: Gerçek bug'ların "heal" edilerek atlanması — her healing event'in loglanması ve raporlanması zorunlu
- Healing döngüsü — sürekli kırılıp heal edilen testler altta yatan tasarım sorununa işaret eder
- Locator geçmişi veritabanının büyümesi ve temizlik stratejisi

---

### 3.7 Intelligent Test Prioritization

#### Açıklama
Kod değişikliklerine göre en riskli testleri önce çalıştırarak CI/CD süresini kısaltma yaklaşımıdır. Tüm test suite'i çalıştırmak yerine, değişiklikten etkilenen ve geçmişte en çok başarısız olan testler önceliklendirilir.

#### Teknik Gereksinimler
- Git diff analizi (değişen dosyalar ve satırlar)
- Test-kod bağlantı haritası (hangi test hangi kodu test ediyor)
- Test geçmişi veritabanı (başarı/başarısızlık oranları)
- ML modeli (risk skorlama)
- CI/CD entegrasyonu

#### Nasıl Çalışır
1. PR/commit'teki değişen dosyalar tespit edilir (git diff)
2. Statik analiz veya geçmiş veri ile etkilenen testler belirlenir
3. Her test için risk skoru hesaplanır:
   - Değişiklikle doğrudan ilişki (dosya bağımlılığı)
   - Geçmiş başarısızlık oranı
   - Son değişiklik tarihi
   - Test çalışma süresi
4. Testler risk skoruna göre sıralanır
5. CI/CD pipeline'da öncelikli testler ilk çalıştırılır
6. Zaman bütçesi dolduğunda düşük riskli testler atlanır (veya gece çalıştırılır)

#### Avantajlar
- CI süresi %60-80 azalır
- Erken hata tespiti (yüksek riskli testler önce)
- Geliştirici geri bildirim döngüsü hızlanır
- Kaynak kullanımı optimize olur

#### Dezavantajlar
- Başlangıçta yeterli geçmiş veri gerekir (cold start problemi)
- Model bias — belirli alanları sürekli atlama riski
- Atlanan testlerdeki hataların geç keşfedilmesi
- İlk kurulum ve kalibrasyon eforu

#### Örnek Araçlar
| Araç | Yaklaşım | Maliyet |
|------|----------|---------|
| Launchable | ML tabanlı predictive test selection | Freemium |
| Katalon TrueTest | AI-driven impact analysis | $208+/ay |
| PractiTest | Risk-based prioritization | Enterprise |
| Custom scikit-learn | Proje-spesifik ML modeli | Geliştirme maliyeti |

#### BGTS Uyumu
Mevcut pytest marker sistemi (P0-P3 öncelikleri, smoke/regression ayrımı) ve GitHub Actions workflow'ları ile doğrudan entegre edilebilir. İlk fazda git diff + dosya bağımlılık analizi tabanlı basit bir prioritization, sonraki fazlarda ML modeli.

#### Riskler
- Cold start — yeterli geçmiş olmadan model güvenilmez
- Atlanan testlerdeki gizli regresyon'lar
- False confidence — "tüm öncelikli testler geçti" ≠ "regresyon yok"

---

### 3.8 Anomaly Detection

#### Açıklama
Test sonuçları, performans metrikleri ve log verilerinde normal dışı paternlerin otomatik tespiti. Flaky testler, performans regresyonları ve beklenmedik davranış değişiklikleri erken uyarı ile bildirilir.

#### Teknik Gereksinimler
- Zaman serisi verisi (test süreleri, başarı oranları, API response time)
- İstatistiksel model (Z-score, IQR) veya ML (Isolation Forest, LSTM)
- Veri depolama (test sonuç geçmişi)
- Uyarı/bildirim mekanizması

#### Nasıl Çalışır
1. Her test çalışmasından metrikler toplanır (süre, sonuç, hata türü, kaynak kullanımı)
2. Geçmiş veriye dayalı normal davranış profili oluşturulur
3. Yeni çalışma sonuçları profil ile karşılaştırılır
4. Eşik değerini aşan sapmalar anomaly olarak işaretlenir
5. Anomaly türüne göre aksiyon tetiklenir (flaky karantina, bug raporu, performans uyarısı)

#### Avantajlar
- Flaky testlerin erken ve otomatik tespiti
- Performans regresyonu erken uyarısı
- Sessiz hataların (ör. yavaş yavaş artan response time) keşfi
- Veri odaklı karar verme

#### Dezavantajlar
- False alarm (özellikle başlangıçta)
- Yeterli geçmiş veri gereksinimi
- Model tuning ve bakım eforu
- Gerçek değişiklik ile anomaly ayrımı

#### Örnek Araçlar
| Araç | Yetenek | Maliyet |
|------|---------|---------|
| Grafana ML | Zaman serisi anomaly detection | Ücretsiz (Cloud: ücretli) |
| UnfoldCI | Flaky test detection + fix | SaaS |
| Panto | CI anomaly monitoring | SaaS |
| Custom Isolation Forest | Python scikit-learn | Geliştirme maliyeti |

#### BGTS Uyumu
k6 performans verileri ve pytest/Playwright test sonuçları üzerine anomaly detection katmanı eklenebilir. Mevcut Allure raporlama altyapısına anomaly dashboard entegrasyonu.

#### Riskler
- Alert fatigue — çok fazla false alarm ile ekibin uyarıları görmezden gelmesi
- Baseline kayması (baseline drift) — yavaş değişimlerin normalleşmesi

---

### 3.9 Test Assertion Öneri Engine

#### Açıklama
Uygulama davranışını analiz ederek mevcut testlerdeki eksik assertion'ları tespit eden ve öneren mekanizma. Testlerin "doğru şeyleri kontrol edip etmediğini" değerlendirir.

#### Teknik Gereksinimler
- Runtime trace (API response, DOM state, console log)
- Mevcut test kodu analizi (AST parsing)
- LLM veya kural tabanlı öneri motoru
- Test framework entegrasyonu

#### Nasıl Çalışır
1. Test çalışırken runtime verisi toplanır (response body, DOM snapshot, state)
2. Mevcut assertion'lar ile runtime verisi karşılaştırılır
3. Kontrol edilmeyen kritik alanlar tespit edilir
4. LLM veya kural motoru ile assertion önerileri oluşturulur
5. Öneriler rapor olarak veya inline comment olarak sunulur

#### Avantajlar
- Test kalitesi artar (weak test → strong test)
- Gözden kaçan kontroller yakalanır
- Sistematik assertion coverage değerlendirmesi

#### Dezavantajlar
- Gereksiz assertion kirliliği riski
- Performance overhead (runtime trace toplama)
- LLM önerileri bazen anlamsız olabilir

#### Örnek Araçlar
| Araç | Dil/Framework | Yaklaşım |
|------|---------------|----------|
| Diffblue Cover | Java/JUnit | Otomatik assertion üretimi |
| CoverUp | Python/pytest | LLM ile coverage-driven assertion |
| Custom LLM pipeline | Multi | Runtime trace + GPT-4o analiz |

#### BGTS Uyumu
Engine pytest suite'ine ve E2E Playwright testlerine assertion öneri servisi eklenebilir. Page Object pattern'daki assertion metotları (`assertPageLoaded`, `assertUrlMatches`) ile uyumlu yapı.

---

### 3.10 Coverage Öneri Engine

#### Açıklama
Kod coverage analizi ile test edilmemiş alanları tespit edip, bu alanlar için otomatik test önerisi üreten yaklaşım. Coverage raporları ve kaynak kodu analizi birleştirilerek gap'ler belirlenir.

#### Teknik Gereksinimler
- Coverage aracı (pytest-cov, Istanbul/NYC, JaCoCo)
- Coverage raporu (lcov, cobertura, JSON)
- LLM API
- Kaynak kodu erişimi
- CI/CD entegrasyonu

#### Nasıl Çalışır
1. Mevcut test suite'i coverage ile çalıştırılır
2. Coverage raporu analiz edilir (satır, dal, fonksiyon coverage)
3. Düşük coverage alanları belirlenir ve önceliklendirilir
4. Her gap için LLM'e kaynak kodu + context verilir
5. LLM, gap'i kapatacak test kodu üretir
6. Üretilen test doğrulanır (syntax check + coverage artışı kontrolü)

#### Avantajlar
- Sistematik coverage artışı
- Kritik alanların önceliklendirilmesi
- Tekrarlanabilir ve ölçülebilir ilerleme

#### Dezavantajlar
- Coverage ≠ kalite — %100 coverage hala bug içerebilir
- Anlamsız test üretimi riski (sadece satır coverage'ı artıran ama gerçek doğrulama yapmayan testler)
- LLM hallucination riski

#### Örnek Araçlar
| Araç | Hedef | Yaklaşım | Maliyet |
|------|-------|----------|---------|
| CoverUp | Python | LLM + coverage feedback loop | Ücretsiz |
| Diffblue Cover | Java | AI unit test generation | Enterprise |
| Codium/Qodo | Multi | AI test suggestion | Freemium |

#### BGTS Uyumu
pytest-cov zaten backend testlerinde kullanılmaktadır (`test:backend:full` script'inde `--cov=app --cov-report=term-missing`). CoverUp entegrasyonu ile Python coverage gap'leri otomatik kapatılabilir. NexusQA Java projesi için Diffblue Cover değerlendirilebilir.

---

### 3.11 Test Repair ve Adaptasyon

#### Açıklama
Kırılan testleri analiz edip otomatik düzeltme PR'ları oluşturan yaklaşım. Self-healing'den farklı olarak, runtime'da geçici düzeltme değil, kalıcı kod değişikliği üretir.

#### Teknik Gereksinimler
- Test hata logları (stack trace, screenshot, DOM snapshot)
- Git entegrasyonu (branch oluşturma, PR açma)
- LLM API
- Code review pipeline

#### Nasıl Çalışır
1. CI'da test başarısız olur
2. Hata logu, stack trace, screenshot ve DOM snapshot toplanır
3. LLM'e hata context'i ve mevcut test kodu verilir
4. LLM düzeltme önerisi üretir
5. Otomatik branch oluşturulur ve fix PR'ı açılır
6. İnsan review'dan geçtikten sonra merge edilir

#### Avantajlar
- Hızlı onarım — geliştirici müdahalesi minimuma iner
- Development velocity artar
- CI/CD pipeline blokajı azalır

#### Dezavantajlar
- Yanlış düzeltme riski — gerçek bug'u gizleyebilir
- İnsan review zorunluluğu (otonom merge tehlikeli)
- LLM'in bazen anlamsız düzeltme üretmesi

#### Örnek Araçlar
| Araç | Yetenek | Maliyet |
|------|---------|---------|
| UnfoldCI | Flaky fix PR oluşturma | SaaS |
| OwlityAI | AI test stabilization | SaaS |
| Playwright Healer | Runtime healing + code suggestion | Ücretsiz |
| Custom GH Actions + LLM | Proje-spesifik | Geliştirme maliyeti |

#### BGTS Uyumu
GitHub Actions + LLM chain ile otomatik fix PR oluşturma mümkündür. Mevcut CI workflow'larına (ci.yml, bgts-e2e.yml) post-failure step eklenerek entegre edilebilir.

---

### 3.12 BDD Senaryolarını Otomatik Çıkarma

#### Açıklama
UI akışları, API dokümantasyon veya doğal dil gereksinimlerden Gherkin BDD senaryoları üretme yaklaşımıdır.

#### Teknik Gereksinimler
- LLM API (GPT-4o, Claude)
- Domain context (bankacılık terminolojisi, iş kuralları)
- Mevcut step definition kütüphanesi
- Page object bilgisi

#### Nasıl Çalışır
1. Girdi alınır: kullanıcı hikayesi, ekran akışı veya API spec
2. LLM'e domain context, mevcut step'ler ve Gherkin formatı verilir
3. LLM, Feature + Scenario + Given/When/Then yapısı üretir
4. Mevcut step kütüphanesiyle eşleştirme yapılır
5. Eksik step'ler için step definition taslağı üretilir
6. Review ve onay sonrası repository'ye eklenir

#### Avantajlar
- Manuel yazım süresi %70 azalır
- Tutarlı format ve yapı
- Edge case ve negatif senaryo önerisi
- İş analistleri ile ortak dil

#### Dezavantajlar
- Domain-specific bilgi eksikliği (fine-tuning gerekebilir)
- Over-generation — çok fazla ve önemsiz senaryo üretme
- Step eşleştirme hataları

#### Örnek Araçlar
| Araç | Özellik | Maliyet |
|------|---------|---------|
| Gherkinizer | NL → Gherkin + step code | Freemium |
| BGTS BDD Generation | Mevcut engine entegrasyonu | İç geliştirme |
| Custom Claude pipeline | Domain-aware generation | LLM maliyeti |

#### BGTS Uyumu
Engine'deki mevcut `ai` marker'lı testler ve `bdd-generate.spec.ts` akışı bu altyapının proof-of-concept'idir. Mevcut `features/` dizinindeki Gherkin dosyaları ve `steps/` dizinindeki step definition'lar LLM context'ine enjekte edilerek domain-aware generation sağlanabilir.

---

### 3.13 Test Script Refactoring

#### Açıklama
Mevcut test kodunu analiz edip kalite iyileştirmeleri öneren ve uygulayan yaklaşım. Tekrarlanan kod, kötü pattern'lar, eksik abstraction ve okunabilirlik sorunları tespit edilir.

#### Teknik Gereksinimler
- AST (Abstract Syntax Tree) analizi
- LLM API
- Code quality kuralları (proje-spesifik)
- Linting ve format araçları
- Version control entegrasyonu

#### Nasıl Çalışır
1. Test kodu AST seviyesinde analiz edilir
2. Kötü pattern'lar tespit edilir (hardcoded değerler, tekrarlanan locator, eksik abstraction)
3. LLM ile iyileştirme önerileri üretilir
4. Refactoring PR'ı oluşturulur
5. Mevcut testlerin refactoring sonrası hala geçtiği doğrulanır

#### Avantajlar
- Kod kalitesi ve okunabilirlik artar
- Tekrarlanan kod azalır
- Page Object pattern uyumu sağlanır
- Bakım maliyeti düşer

#### Dezavantajlar
- Refactoring'in mevcut testleri kırma riski
- LLM'in proje-spesifik convention'ları bilmemesi
- Büyük refactoring'lerde incremental yaklaşım gerekli

#### Örnek Araçlar
| Araç | Yaklaşım | Maliyet |
|------|----------|---------|
| SonarQube + LLM | Statik analiz + AI fix | Ücretsiz (Community) |
| Custom AST analyzer | Python ast module + GPT-4o | Geliştirme maliyeti |
| Cursor AI | IDE-integrated refactoring | Freemium |

#### BGTS Uyumu
NexusQA legacy Java/Selenium kodunun Playwright'a modernizasyonunda kritik. Mevcut Java test kodunun (Cucumber feature + step definition) analizi ve TypeScript/Python eşdeğerlerine dönüşüm önerisi.

#### Kullanım Senaryoları
- NexusQA → Playwright migration'da kod dönüşüm asistanı
- Test kodunda DRY principle ihlallerinin tespiti
- data-testid convention uyumsuzluklarının otomatik düzeltilmesi

---

## 4. Risk ve Sınırlılıklar

### 4.1 LLM Hallucination
Tüm LLM tabanlı yaklaşımlarda hallucination riski mevcuttur. Var olmayan element, endpoint veya metot referansları üretilebilir. Mutlaka code validation pipeline (syntax check, lint, dry-run) kullanılmalıdır.

### 4.2 Maliyet Yönetimi
LLM API çağrıları (özellikle GPT-4o/Claude) maliyet oluşturur. CI/CD'de her çalışmada LLM çağrısı yapılması maliyeti artırır. Caching, prompt optimization ve model seçimi (büyük model vs. küçük model) stratejileri gereklidir.

### 4.3 Güvenlik ve Gizlilik
LLM'lere gönderilen veride hassas bilgi bulunmamalıdır. Test verisi, locator bilgisi ve hata logları PII içerebilir. On-premise LLM (ör. Ollama + Code Llama) alternatif olarak değerlendirilmelidir.

### 4.4 Vendor Lock-in
Belirli bir AI test platformuna (Testim, mabl, Functionize) bağımlılık riski. Açık kaynak + custom pipeline yaklaşımı önerilir. Playwright + OpenAI/Anthropic kombinasyonu en esnek seçenek.

### 4.5 Ekip Yetkinliği
AI araçlarının etkin kullanımı için ekibin AI/ML temellerini, prompt engineering'i ve araç konfigürasyonunu bilmesi gerekir. Eğitim ve ramp-up süresi planlanmalıdır.

---

## 5. Referanslar

1. Playwright AI Ecosystem 2026: MCP, Agents & Self-Healing Tests — https://testdino.com/blog/playwright-ai-ecosystem-2026/
2. Agentic QA Architecture: Reasoning Loops, Self-Healing DOM & Autonomous Testing — https://testquality.com/agentic-qa-architecture-autonomous-testing-2026/
3. Best AI Test Generation Tools in 2026: Complete Guide — https://dev.to/rahulxsingh/best-ai-test-generation-tools-in-2026-complete-guide-4o2p
4. Self-Healing Tests: How AI Cuts Test Maintenance by 95% — https://www.test-lab.ai/blog/self-healing-tests-ai-maintenance
5. AI Flaky Test Detection: How AI Identifies Unstable Automation Tests — https://www.neovasolutions.com/2026/02/03/ai-flaky-test-detection/
6. Gherkinizer: AI-Powered BDD Gherkin Test Case Generator — https://gherkinizer.com/
7. CoverUp: LLM-Powered Test Coverage — https://github.com/plasma-umass/coverup
8. Diffblue Cover: AI Testing Agent — https://diffblue.com/
9. Shannon: Autonomous AI Pentester — https://github.com/keygraphhq/shannon
10. Synthesized: AI-Powered Test Data Management — https://synthesized.io/
11. UnfoldCI: AI Fixes Flaky Tests — https://unfoldci.com/
12. Best AI Testing Tools Compared (2026) — https://testcollab.com/blog/ai-testing-tools
13. BGTS Sentetik Veri Araştırma Raporu — `docs/synthetic-data-research.md`
