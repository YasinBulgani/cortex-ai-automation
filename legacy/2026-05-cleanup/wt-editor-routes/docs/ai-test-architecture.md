# AI Destekli Test Otomasyonu — Mimari Dokümantasyon

**Tarih:** 2026-04-03
**Kapsam:** BGTS platformunun mevcut altyapısı üzerine inşa edilecek AI test otomasyon mimarisi

---

## İçindekiler

1. [Genel Mimari](#1-genel-mimari)
2. [AI Test Engine](#2-ai-test-engine)
3. [Data Pipeline](#3-data-pipeline)
4. [Test Yürütme Katmanı](#4-test-yürütme-katmanı)
5. [Self-Learning Feedback Loop](#5-self-learning-feedback-loop)
6. [CI/CD Entegrasyon Mimarisi](#6-cicd-entegrasyon-mimarisi)
7. [Raporlama ve Dashboard](#7-raporlama-ve-dashboard)
8. [LLM Gateway Mimarisi](#8-llm-gateway-mimarisi)
9. [Veri Akış Diyagramları](#9-veri-akış-diyagramları)

---

## 1. Genel Mimari

BGTS AI Test Otomasyon mimarisi, mevcut monorepo yapısının üzerine 6 ana katmandan oluşur:

```mermaid
graph TB
    subgraph userLayer ["Kullanici Katmani"]
        WebUI["apps/web<br/>Next.js 14"]
        FlowEditor["React Flow<br/>Test Modeller"]
        Dashboard["AI Test<br/>Dashboard"]
    end

    subgraph aiEngine ["AI Test Engine"]
        TestPlanner["Test Planner<br/>Agent"]
        TestGenerator["Test Generator<br/>Agent"]
        TestHealer["Self-Healer<br/>Agent"]
        BDDGen["BDD<br/>Generator"]
        AssertionEngine["Assertion<br/>Oneri Engine"]
        CoverageEngine["Coverage<br/>Analyzer"]
        Prioritizer["Test<br/>Prioritizer"]
    end

    subgraph dataPipeline ["Data Pipeline"]
        SynDataGen["Sentetik Veri<br/>Generator"]
        DataMasker["Veri<br/>Maskeleme"]
        SchemaAnalyzer["Sema<br/>Analizci"]
        DataValidator["Veri Kalite<br/>Dogrulama"]
    end

    subgraph executionLayer ["Test Yurutme Katmani"]
        PlaywrightRunner["Playwright<br/>Runner - TS"]
        PytestRunner["pytest-bdd<br/>Runner - Python"]
        K6Runner["k6<br/>Performans"]
        SecurityScanner["Guvenlik<br/>Tarayici"]
        APITester["API<br/>Tester"]
    end

    subgraph infrastructure ["Altyapi"]
        CICD["GitHub Actions"]
        Redis["Redis Queue"]
        PostgreSQL["PostgreSQL"]
        LLMGateway["LLM Gateway<br/>OpenAI / Claude"]
        Allure["Allure<br/>Raporlama"]
    end

    subgraph feedbackLoop ["Self-Learning Feedback"]
        ResultCollector["Sonuc<br/>Toplayici"]
        AnomalyDetector["Anomaly<br/>Dedektoru"]
        FlakyDetector["Flaky Test<br/>Dedektoru"]
        ModelTrainer["Model<br/>Egitici"]
    end

    WebUI --> aiEngine
    FlowEditor --> TestPlanner
    Dashboard --> feedbackLoop

    TestPlanner --> TestGenerator
    TestGenerator --> executionLayer
    TestHealer --> executionLayer
    BDDGen --> PytestRunner
    Prioritizer --> CICD

    SynDataGen --> executionLayer
    DataMasker --> SynDataGen

    executionLayer --> ResultCollector
    ResultCollector --> AnomalyDetector
    ResultCollector --> FlakyDetector
    AnomalyDetector --> ModelTrainer
    FlakyDetector --> TestHealer
    ModelTrainer --> Prioritizer

    aiEngine --> LLMGateway
    dataPipeline --> PostgreSQL
    executionLayer --> Redis
    executionLayer --> Allure
```

### Katman Açıklamaları

| Katman | Görev | Mevcut Durum |
|--------|-------|--------------|
| **Kullanıcı Katmanı** | Test yönetimi UI, flow editörü, dashboard | Next.js 14 + React Flow mevcut |
| **AI Test Engine** | Akıllı test planlama, üretme, onarım | BDD generation MVP mevcut; genişletilecek |
| **Data Pipeline** | Sentetik veri üretimi ve maskeleme | `ai_synthetic_data/` MVP mevcut |
| **Test Yürütme** | Testlerin çalıştırılması | Playwright, pytest-bdd, k6 mevcut |
| **Altyapı** | Veritabanı, kuyruk, CI/CD, LLM | Tamamı mevcut |
| **Feedback Loop** | Sonuç analizi ve model iyileştirme | Yeni — inşa edilecek |

---

## 2. AI Test Engine

AI Test Engine, 7 adet özelleşmiş servisten oluşur. Her servis `engine/` Flask uygulaması altında bir modül olarak konumlanır.

```mermaid
graph LR
    subgraph aiEngine ["AI Test Engine - engine/services/"]
        TP["TestPlanner"]
        TG["TestGenerator"]
        TH["TestHealer"]
        BG["BDDGenerator"]
        AE["AssertionEngine"]
        CE["CoverageAnalyzer"]
        PR["TestPrioritizer"]
    end

    subgraph inputs ["Girdiler"]
        URL["Uygulama URL"]
        REQ["Gereksinimler"]
        PO["Page Objects"]
        DIFF["Git Diff"]
        HIST["Test Gecmisi"]
        ERR["Hata Loglari"]
        COV["Coverage Raporu"]
    end

    subgraph outputs ["Ciktilar"]
        PLAN["Test Plani - MD"]
        CODE["Test Kodu - ts/py"]
        FIX["Fix PR"]
        FEAT["Feature Dosyasi"]
        ASRT["Assertion Onerileri"]
        GAPS["Coverage Gap Raporu"]
        ORDER["Oncelik Sirasi"]
    end

    URL --> TP
    REQ --> TP
    REQ --> BG
    PO --> TG
    PO --> BG
    DIFF --> PR
    HIST --> PR
    ERR --> TH
    COV --> CE

    TP --> PLAN
    PLAN --> TG
    TG --> CODE
    TH --> FIX
    BG --> FEAT
    AE --> ASRT
    CE --> GAPS
    PR --> ORDER
```

### 2.1 Test Planner Agent

Uygulamayı explore ederek kapsamlı test planı çıkaran agent.

**Mimari:**
```
URL + Gereksinimler
    ↓
Playwright MCP → Accessibility Snapshot
    ↓
LLM (GPT-4o) → Test Planı (Markdown)
    ↓
Review & Onay
    ↓
Test Generator Agent'a İlet
```

**Bileşenler:**
- `engine/services/test_planner.py` — Ana planlama servisi
- Playwright MCP client — tarayıcı erişimi
- LLM client — plan üretimi
- Plan template — tutarlı çıktı formatı

**Girdi/Çıktı:**
| Girdi | Çıktı |
|-------|-------|
| Uygulama URL'si | Markdown test planı |
| Gereksinim dokümanı | Sayfa listesi ve akışlar |
| Kapsam parametreleri | Öncelikli test senaryoları |

### 2.2 Test Generator Agent

Test planından çalıştırılabilir test kodu üreten agent.

**Mimari:**
```
Test Planı (MD) + Page Object Repository
    ↓
Context Builder → LLM Prompt Assembly
    ↓
LLM (GPT-4o / Claude) → Raw Test Code
    ↓
Code Validator → Syntax Check + Lint
    ↓
Dry Run → Çalışabilirlik Doğrulama
    ↓
.spec.ts / .feature + step_defs
```

**Bileşenler:**
- `engine/services/test_generator.py` — Ana üretim servisi
- Context builder — page object + framework bilgisi derleme
- Code validator — syntax check, lint, import validation
- Template engine — framework-spesifik şablonlar

### 2.3 Self-Healer Agent

Başarısız testleri otomatik onaran agent.

**Mimari:**
```
Test Failure
    ↓
Error Collector → Hata Logu + DOM Snapshot + Screenshot
    ↓
Locator History DB → Önceki Başarılı Locator
    ↓
DOM Diff Engine → Değişiklik Analizi
    ↓
Multi-Attribute Fingerprint → Yeni Element Tespiti
    ↓
LLM (gerekirse) → Locator Üretimi
    ↓
Retry → Test Yeniden Çalıştırma
    ↓
┌─ Başarılı → Locator Repository Güncelle + Healing Raporu
└─ Başarısız → Gerçek Bug Raporu
```

**Healing Stratejileri (Öncelik Sırasıyla):**

1. **data-testid fallback** — Element'in testId'si değişmişse yakın eşleşme ara
2. **Role + Label eşleşme** — ARIA role ve label ile bul
3. **Text content eşleşme** — Görünen metin ile bul
4. **Positional heuristic** — DOM tree'deki konum ile bul
5. **LLM-assisted** — Tüm strateji başarısızsa LLM'e sor

### 2.4 BDD Generator

Doğal dil gereksinimlerden Gherkin senaryoları üreten servis.

**Mimari:**
```
Doğal Dil Gereksinim
    ↓
Domain Context Loader → Bankacılık terminolojisi + İş kuralları
    ↓
Step Library Scanner → Mevcut step definition'lar
    ↓
LLM → Gherkin Feature + Scenario
    ↓
Step Matcher → Mevcut step'lerle eşleştir
    ↓
Missing Step Generator → Eksik step taslakları
    ↓
.feature + step_defs.py
```

### 2.5 Test Prioritizer

Kod değişikliklerinden etkilenen testleri risk skoruna göre sıralayan servis.

**Mimari:**
```
Git Diff + Test Geçmişi
    ↓
File Dependency Analyzer → Değişen dosyaların test bağlantıları
    ↓
Risk Scorer
    ├── Dosya bağımlılığı skoru (0-1)
    ├── Geçmiş başarısızlık oranı (0-1)
    ├── Son değişiklik yakınlığı (0-1)
    └── Test süresi faktörü (0-1)
    ↓
Weighted Score → Sıralı Test Listesi
    ↓
CI/CD Pipeline → Öncelikli yürütme
```

---

## 3. Data Pipeline

Sentetik veri üretimi, maskeleme ve kalite doğrulama pipeline'ı.

```mermaid
graph LR
    subgraph inputPhase ["Girdi"]
        CSV["CSV Dosya"]
        DB["Veritabani"]
        Schema["OpenAPI Schema"]
    end

    subgraph analysisPhase ["Analiz"]
        SA["SchemaAnalyzer"]
        SC["SemanticClassifier"]
        RE["RuleEngine"]
        CA["CorrelationAnalyzer"]
    end

    subgraph generationPhase ["Uretim"]
        FG["Faker Generator"]
        KDE["KDE Generator"]
        CTGAN["CTGAN Generator"]
        RL["Relational Linker"]
    end

    subgraph qualityPhase ["Kalite"]
        DM["Data Masker"]
        DP["Differential Privacy"]
        QM["Quality Metrics"]
        VL["Validator"]
    end

    subgraph outputPhase ["Cikti"]
        SDF["Sentetik DataFrame"]
        RPT["Kalite Raporu"]
        API["API Response"]
    end

    CSV --> SA
    DB --> SA
    Schema --> SA
    SA --> SC
    SC --> RE
    RE --> CA

    CA --> FG
    CA --> KDE
    CA --> CTGAN
    FG --> RL
    KDE --> RL
    CTGAN --> RL

    RL --> DM
    DM --> DP
    DP --> QM
    QM --> VL

    VL --> SDF
    VL --> RPT
    VL --> API
```

### Pipeline Fazları

| Faz | Açıklama | Mevcut Durum | Hedef |
|-----|----------|--------------|-------|
| **Analiz** | Şema ve dağılım çıkarma | SchemaAnalyzer + SemanticClassifier mevcut | CorrelationAnalyzer eklenmeli |
| **Üretim** | Sentetik veri oluşturma | Faker-based MVP | KDE → CTGAN progression |
| **Kalite** | Gizlilik ve doğrulama | PII detection mevcut | Diferansiyel gizlilik + kalite metrikleri |
| **Çıktı** | Veri dağıtımı | DataFrame + API | Kalite raporu eklenmeli |

---

## 4. Test Yürütme Katmanı

Mevcut runner'ların AI ile zenginleştirilmiş versiyonu.

```mermaid
graph TB
    subgraph orchestrator ["Test Orchestrator"]
        TO["Test<br/>Orchestrator"]
        TS["Test<br/>Selector"]
        TD["Test Data<br/>Provider"]
    end

    subgraph runners ["Runner'lar"]
        PW["Playwright E2E<br/>TypeScript"]
        PB["pytest-bdd<br/>Python"]
        K6["k6<br/>Performans"]
        SEC["Guvenlik<br/>Scanner"]
        APT["API<br/>Tester"]
    end

    subgraph enhancements ["AI Zenginlestirmeler"]
        SH["Self-Healing<br/>Middleware"]
        REC["AI<br/>Recorder"]
        VR["Visual<br/>Regression AI"]
    end

    subgraph reporting ["Raporlama"]
        AL["Allure"]
        JU["JUnit XML"]
        HT["HTML Report"]
        JS["JSON Results"]
    end

    TO --> TS
    TS --> runners
    TD --> runners

    PW --> SH
    SH --> PW
    PW --> REC
    PW --> VR

    runners --> AL
    runners --> JU
    runners --> HT
    runners --> JS
```

### Runner Detayları

| Runner | Dosya Konumu | AI Zenginleştirme |
|--------|-------------|-------------------|
| **Playwright E2E** | `e2e/*.spec.ts` | Self-healing, AI recorder, visual regression |
| **pytest-bdd** | `engine/tests/`, `engine/steps/` | BDD generation, assertion önerisi |
| **k6** | `tests/performance/*.js` | Anomaly detection, profil optimizasyon |
| **Güvenlik** | Yeni modül | Shannon/ZAP entegrasyonu |
| **API** | `api-tests/tests/` | Schema-based generation, fuzz testing |

---

## 5. Self-Learning Feedback Loop

Test sonuçlarından öğrenen ve sürekli iyileşen kapalı döngü sistemi.

```mermaid
graph LR
    A["Test Calistir"] --> B["Sonuclari Topla"]
    B --> C["Analiz Engine"]

    C --> D{"Anomaly<br/>Tespit?"}
    D -->|Evet| E{"Flaky mi?"}
    D -->|Hayir| F["Normal<br/>Kayit"]

    E -->|Evet| G["Flaky<br/>Karantina"]
    E -->|Hayir| H{"Gercek<br/>Bug?"}

    H -->|Evet| I["Bug<br/>Raporu"]
    H -->|Hayir| J["Model<br/>Guncelle"]

    G --> K["AI<br/>Self-Heal"]
    K --> L{"Heal<br/>Basarili?"}
    L -->|Evet| M["Locator<br/>Guncelle"]
    L -->|Hayir| I

    M --> A
    J --> N["Prioritization<br/>Modeli"]
    N --> A
    F --> O["Trend<br/>Analiz"]
    O --> N
```

### Feedback Loop Bileşenleri

**1. Sonuç Toplayıcı (Result Collector)**
- Allure JSON, JUnit XML, k6 JSON sonuçlarını toplar
- Test metadata (süre, retry sayısı, hata türü) ile zenginleştirir
- PostgreSQL'e zaman serisi olarak yazar

**2. Anomaly Dedektörü**
- Z-score tabanlı basit anomaly detection (Faz 1)
- Isolation Forest ile gelişmiş tespit (Faz 2)
- Kategori: performans anomaly, başarı oranı anomaly, süre anomaly

**3. Flaky Test Dedektörü**
- Geçmiş N çalışmada başarı/başarısızlık varyansını analiz eder
- Flaky skoru: 0 (stabil) — 1 (tamamen rastgele)
- Eşik değeri (ör. 0.3) aşanlar karantinaya alınır

**4. Model Eğitici**
- Test sonuç geçmişinden prioritization modeli eğitir
- Feature'lar: dosya bağımlılığı, değişiklik sıklığı, başarısızlık oranı
- Periyodik re-training (haftalık)

---

## 6. CI/CD Entegrasyon Mimarisi

Mevcut GitHub Actions workflow'larının AI ile zenginleştirilmesi.

```mermaid
graph TB
    subgraph trigger ["Tetikleyici"]
        PR["Pull Request"]
        PUSH["Push to Main"]
        SCHED["Zamanlanmis"]
        MANUAL["Manuel"]
    end

    subgraph preTest ["Pre-Test Faz"]
        DIFF["Git Diff<br/>Analiz"]
        PRIO["AI Test<br/>Prioritization"]
        DATA["Sentetik<br/>Veri Uret"]
    end

    subgraph execution ["Yurutme Faz"]
        SMOKE["Smoke<br/>Oncelikli"]
        REG["Regression<br/>Skorlu"]
        FULL["Full<br/>Gece"]
        PERF["Performans<br/>Haftalik"]
    end

    subgraph postTest ["Post-Test Faz"]
        HEAL["Self-Healing<br/>Retry"]
        ANOMALY["Anomaly<br/>Detection"]
        FLAKY["Flaky<br/>Analiz"]
        REPORT["Rapor<br/>Uretim"]
    end

    subgraph actions ["Aksiyonlar"]
        FIXPR["Fix PR<br/>Olustur"]
        NOTIFY["Bildirim<br/>Gonder"]
        DASH["Dashboard<br/>Guncelle"]
        QUARANTINE["Flaky<br/>Karantina"]
    end

    PR --> DIFF
    PUSH --> DIFF
    SCHED --> FULL
    MANUAL --> execution

    DIFF --> PRIO
    PRIO --> DATA
    DATA --> execution

    SMOKE --> postTest
    REG --> postTest
    FULL --> postTest

    HEAL --> FIXPR
    ANOMALY --> NOTIFY
    FLAKY --> QUARANTINE
    REPORT --> DASH
```

### CI/CD Akışı (Detay)

**PR Açıldığında:**
1. Git diff analizi → değişen dosyalar belirlenir
2. AI Test Prioritizer → etkilenen testler sıralanır
3. Sentetik veri üretici → gerekli test data hazırlanır
4. Smoke testler + en yüksek skorlu regression testleri çalışır
5. Başarısız testler → self-healing retry (1 deneme)
6. Heal edilemeyenler → fix PR önerisi veya bug raporu
7. Anomaly detection → performans/stabilite sapması kontrolü
8. Dashboard güncellenir

**Nightly (Her Gece):**
1. Full regression suite çalışır
2. Coverage gap analizi → yeni test önerileri
3. Flaky test analizi → karantina listesi güncellenir
4. AI test generation → yeni coverage gap'leri için test üretir
5. Trend raporu oluşturulur

**Haftalık:**
1. k6 performans testleri çalışır
2. Baseline karşılaştırma + anomaly detection
3. Güvenlik taraması (Shannon/ZAP)
4. Model re-training (prioritization)

---

## 7. Raporlama ve Dashboard

```mermaid
graph TB
    subgraph dataSources ["Veri Kaynaklari"]
        AllureData["Allure JSON"]
        JUnitData["JUnit XML"]
        K6Data["k6 JSON"]
        CovData["Coverage lcov"]
        HealData["Healing Log"]
        FlakyData["Flaky DB"]
    end

    subgraph processing ["Isleme"]
        Aggregator["Veri<br/>Agregator"]
        TrendCalc["Trend<br/>Hesaplayici"]
        ScoreCalc["Skor<br/>Hesaplayici"]
    end

    subgraph dashboard ["Dashboard Panelleri"]
        OverviewPanel["Genel Bakis"]
        HealingPanel["AI Healing<br/>Istatistikleri"]
        CoveragePanel["Coverage<br/>Heat Map"]
        FlakyPanel["Flaky Test<br/>Listesi"]
        PerfPanel["Performans<br/>Trendi"]
        PrioPanel["Prioritization<br/>Etkinligi"]
    end

    dataSources --> Aggregator
    Aggregator --> TrendCalc
    Aggregator --> ScoreCalc

    TrendCalc --> OverviewPanel
    TrendCalc --> PerfPanel
    ScoreCalc --> HealingPanel
    ScoreCalc --> CoveragePanel
    ScoreCalc --> FlakyPanel
    ScoreCalc --> PrioPanel
```

### Dashboard Panelleri

| Panel | İçerik | Veri Kaynağı |
|-------|--------|-------------|
| **Genel Bakış** | Toplam test, başarı oranı, trend, son çalışma | Allure + JUnit |
| **AI Healing** | Heal edilen test sayısı, healing oranı, locator değişiklikleri | Healing log |
| **Coverage Heat Map** | Modül bazlı coverage, gap'ler, öneriler | Coverage raporu |
| **Flaky Testler** | Flaky skor, karantina listesi, trend | Flaky DB |
| **Performans** | Response time trend, anomaly'ler, SLA uyumu | k6 JSON |
| **Prioritization** | Sıralama etkinliği, tahmin doğruluğu, zaman tasarrufu | Test geçmişi |

---

## 8. LLM Gateway Mimarisi

Tüm AI servislerinin merkezi LLM erişim noktası.

```mermaid
graph TB
    subgraph consumers ["Tuketiciler"]
        TP2["Test Planner"]
        TG2["Test Generator"]
        TH2["Test Healer"]
        BG2["BDD Generator"]
        AE2["Assertion Engine"]
    end

    subgraph gateway ["LLM Gateway"]
        Router["Model Router"]
        Cache["Prompt Cache"]
        RateLimit["Rate Limiter"]
        CostTracker["Maliyet Takip"]
        Sanitizer["PII Sanitizer"]
    end

    subgraph providers ["LLM Saglayicilar"]
        OpenAI["OpenAI<br/>GPT-4o"]
        Anthropic["Anthropic<br/>Claude 3.5"]
        Local["Yerel LLM<br/>Ollama"]
    end

    consumers --> Sanitizer
    Sanitizer --> Cache
    Cache --> Router
    Router --> RateLimit
    RateLimit --> CostTracker

    CostTracker --> OpenAI
    CostTracker --> Anthropic
    CostTracker --> Local
```

### Gateway Bileşenleri

| Bileşen | Görev |
|---------|-------|
| **PII Sanitizer** | LLM'e gönderilmeden önce hassas verileri maskeler |
| **Prompt Cache** | Aynı/benzer prompt'lar için cache (maliyet azaltma) |
| **Model Router** | Görev karmaşıklığına göre model seçimi (basit → küçük model, karmaşık → GPT-4o) |
| **Rate Limiter** | API çağrı limitlerini yönetir |
| **Maliyet Takip** | LLM kullanım maliyetini izler ve bütçe uyarısı verir |

### Model Seçim Stratejisi

| Görev | Önerilen Model | Gerekçe |
|-------|---------------|---------|
| Test planı oluşturma | GPT-4o | Yüksek kalite, detaylı analiz |
| Locator üretimi | Claude 3.5 Haiku | Hızlı, düşük maliyet |
| BDD senaryo üretimi | GPT-4o | Domain bilgisi, Türkçe kalite |
| Self-healing | Claude 3.5 Sonnet | DOM analiz yeteneği |
| Assertion önerisi | GPT-4o | Kod kalitesi |
| Basit sınıflandırma | Yerel LLM (Ollama) | Maliyet sıfır, gizlilik |

---

## 9. Veri Akış Diyagramları

### 9.1 Test Üretim Akışı

```mermaid
sequenceDiagram
    participant U as Kullanici
    participant W as Web UI
    participant E as Engine API
    participant LLM as LLM Gateway
    participant R as Repository

    U->>W: Gereksinim girer
    W->>E: POST /api/ai/generate-test
    E->>R: Page object listesi al
    R-->>E: Page objects + step defs
    E->>LLM: Prompt gonder (gereksinim + context)
    LLM-->>E: Ham test kodu
    E->>E: Syntax check + lint
    E->>E: Dry run (opsiyonel)
    E-->>W: Test kodu + validation sonucu
    W-->>U: Review ekraninda goster
    U->>W: Onayla
    W->>R: Dosyaya kaydet
```

### 9.2 Self-Healing Akışı

```mermaid
sequenceDiagram
    participant CI as CI Pipeline
    participant PW as Playwright
    participant SH as Self-Healer
    participant LR as Locator Repository
    participant LLM as LLM Gateway
    participant RPT as Rapor

    CI->>PW: Test calistir
    PW-->>CI: FAIL - Element bulunamadi
    CI->>SH: Hata logu + DOM snapshot
    SH->>LR: Onceki basarili locator al
    LR-->>SH: Locator gecmisi
    SH->>SH: DOM diff analizi
    SH->>SH: Multi-attribute fingerprint

    alt Fingerprint ile bulundu
        SH->>PW: Yeni locator ile tekrar dene
    else Fingerprint basarisiz
        SH->>LLM: DOM + hata context gonder
        LLM-->>SH: Onerilen locator
        SH->>PW: LLM locator ile tekrar dene
    end

    alt Heal basarili
        PW-->>SH: PASS
        SH->>LR: Locator guncelle
        SH->>RPT: Healing raporu
    else Heal basarisiz
        PW-->>SH: FAIL
        SH->>RPT: Gercek bug raporu
    end
```

### 9.3 Feedback Loop Akışı

```mermaid
sequenceDiagram
    participant CI as CI Pipeline
    participant RC as Result Collector
    participant AD as Anomaly Detector
    participant FD as Flaky Detector
    participant MT as Model Trainer
    participant DB as PostgreSQL

    CI->>RC: Test sonuclari (JSON/XML)
    RC->>DB: Sonuclari kaydet
    RC->>AD: Metrikler gonder
    RC->>FD: Basari/basarisizlik gecmisi

    AD->>AD: Z-score / Isolation Forest
    alt Anomaly tespit edildi
        AD->>CI: Uyari bildirim
    end

    FD->>FD: Varyans analizi
    alt Flaky tespit edildi
        FD->>DB: Flaky olarak isaretle
        FD->>CI: Karantina listesi guncelle
    end

    Note over MT: Haftalik re-training
    MT->>DB: Gecmis verileri oku
    MT->>MT: Model egit
    MT->>DB: Guncel modeli kaydet
```
