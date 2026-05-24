# AI Test Otomasyonu — Proje Yapısı Şablonu

**Tarih:** 2026-04-03
**Kapsam:** BGTS monorepo'suna eklenecek AI test modüllerinin dosya/klasör yapısı ve organizasyonu

---

## İçindekiler

1. [Mevcut Yapı](#1-mevcut-yapı)
2. [Önerilen Yeni Yapı](#2-önerilen-yeni-yapı)
3. [Modül Detayları](#3-modül-detayları)
4. [Konfigürasyon Dosyaları](#4-konfigürasyon-dosyaları)
5. [Bağımlılık Yönetimi](#5-bağımlılık-yönetimi)

---

## 1. Mevcut Yapı

Mevcut BGTS monorepo yapısının AI ile ilgili kısımları:

```
Cortex_Ai_Automation/
├── apps/web/                          # Next.js 14 frontend
├── backend/                           # FastAPI backend
├── engine/                            # Flask otomasyon motoru
│   ├── ai_synthetic_data/             # Sentetik veri modülü (MVP)
│   ├── features/                      # BDD Gherkin feature dosyaları
│   ├── steps/                         # BDD step definitions
│   ├── pages/                         # Python page objects
│   ├── locators/                      # Locator repository
│   ├── tests/                         # Test dosyaları
│   └── test_data/                     # Test verileri
├── e2e/                               # Playwright E2E (TypeScript)
│   ├── pages/                         # TS page objects
│   ├── fixtures/                      # Test fixture'ları
│   └── config/                        # Ortam konfigürasyonu
├── api-tests/                         # API test suite
├── NexusQATestOtomasyon/             # Java/Selenium legacy
├── tests/performance/                 # k6 performans testleri
├── .github/workflows/                 # CI/CD pipeline'ları
├── docs/                              # Dokümantasyon
└── reports/                           # Test raporları
```

---

## 2. Önerilen Yeni Yapı

Mevcut yapıyı bozmadan, AI modüllerinin eklenmesi gereken konumlar:

```
Cortex_Ai_Automation/
│
├── apps/web/
│   └── app/                                   # Next.js App Router (src/ yok)
│       └── ai-dashboard/                      # [YENİ - Faz 4] AI Dashboard sayfaları
│           ├── page.tsx                       # Ana dashboard
│           ├── healing/page.tsx               # Healing istatistikleri
│           ├── coverage/page.tsx              # Coverage heat map
│           ├── flaky/page.tsx                 # Flaky test listesi
│           ├── cost/page.tsx                  # LLM maliyet takibi
│           └── components/                   # Dashboard bileşenleri
│               ├── HealingChart.tsx
│               ├── CoverageHeatMap.tsx
│               ├── FlakyTestTable.tsx
│               └── CostTracker.tsx
│
├── engine/
│   ├── services/                              # [YENİ] AI servis katmanı
│   │   ├── __init__.py
│   │   ├── llm_gateway.py                    # Merkezi LLM erişim katmanı
│   │   ├── ai_test_generator.py              # NL → test kodu üretici
│   │   ├── bdd_generator.py                  # NL → Gherkin üretici
│   │   ├── test_prioritizer.py               # Akıllı test önceliklendirme
│   │   ├── anomaly_detector.py               # Test/performans anomaly tespiti
│   │   ├── flaky_detector.py                 # Flaky test tespiti + karantina
│   │   ├── coverage_analyzer.py              # Coverage gap analizi + öneri
│   │   ├── assertion_engine.py               # Assertion öneri motoru
│   │   ├── self_healer.py                    # Backend healing logic
│   │   └── security_scanner.py               # Güvenlik tarama entegrasyonu
│   │
│   ├── ai_synthetic_data/                     # [MEVCUT + GENİŞLETME]
│   │   ├── app/
│   │   │   ├── analyzer.py                   # Schema analyzer
│   │   │   ├── classifier.py                 # Semantic classifier
│   │   │   ├── rule_engine.py                # Rule engine
│   │   │   └── generator.py                  # Synthetic generator
│   │   ├── generators/                        # [YENİ] Gelişmiş generator'lar
│   │   │   ├── __init__.py
│   │   │   ├── kde_generator.py              # KDE tabanlı üretici
│   │   │   ├── ctgan_generator.py            # CTGAN tabanlı üretici
│   │   │   ├── banking_generator.py          # Bankacılık domain üretici
│   │   │   └── relational_linker.py          # FK bütünlük sağlayıcı
│   │   ├── privacy/                           # [YENİ] Gizlilik katmanı
│   │   │   ├── __init__.py
│   │   │   ├── pii_detector.py               # PII tespit
│   │   │   ├── data_masker.py                # Veri maskeleme
│   │   │   └── differential_privacy.py       # Diferansiyel gizlilik
│   │   └── quality/                           # [YENİ] Kalite metrikleri
│   │       ├── __init__.py
│   │       ├── statistical_fidelity.py       # İstatistiksel sadakat
│   │       ├── correlation_checker.py        # Korelasyon doğrulama
│   │       └── quality_report.py             # Kalite raporu üretici
│   │
│   ├── features/
│   │   ├── login.feature                      # [MEVCUT]
│   │   └── ai_generated/                      # [YENİ] AI üretimi feature'lar
│   │       └── .gitkeep
│   │
│   ├── tests/
│   │   ├── unit/                              # [MEVCUT]
│   │   ├── integration/                       # [MEVCUT]
│   │   └── ai_generated/                      # [YENİ] AI üretimi testler
│   │       └── .gitkeep
│   │
│   ├── locators/
│   │   ├── locator_repository.json            # [MEVCUT]
│   │   ├── default/                           # [MEVCUT]
│   │   └── ai_healing/                        # [YENİ] Healing geçmişi
│   │       ├── healing_history.json
│   │       └── locator_fingerprints.json
│   │
│   ├── config/                                # [YENİ] AI konfigürasyon
│   │   ├── ai_config.yaml                    # AI özellik konfigürasyonu
│   │   ├── llm_models.yaml                   # LLM model tanımları
│   │   └── pii_patterns.yaml                 # PII tespit desenleri
│   │
│   ├── prompts/                               # [YENİ] LLM prompt şablonları
│   │   ├── test_generator_system.md
│   │   ├── bdd_generator_system.md
│   │   ├── self_healer_system.md
│   │   ├── assertion_analyzer_system.md
│   │   └── security_analyzer_system.md
│   │
│   └── routes/                                # [MEVCUT + YENİ] AI API endpoint'leri
│       ├── __init__.py
│       ├── ai_generation_routes.py            # Test/BDD üretim endpoint'leri
│       ├── ai_analysis_routes.py              # Analiz + assertion + security endpoint'leri
│       └── ai_healing_routes.py               # Self-healing endpoint'leri
│
├── e2e/
│   ├── utils/                                 # [YENİ] AI yardımcı modüller
│   │   ├── ai-locator.ts                     # AI locator chain
│   │   ├── self-healer.ts                    # Self-healing middleware
│   │   └── test-metadata.ts                  # AI test metadata helper
│   │
│   ├── config/
│   │   ├── environments.ts                    # [MEVCUT]
│   │   └── mcp-config.ts                     # [YENİ] MCP konfigürasyonu
│   │
│   ├── ai-generated/                          # [YENİ] AI üretimi E2E testler
│   │   └── .gitkeep
│   │
│   └── pages/                                 # [MEVCUT]
│
├── .github/workflows/
│   ├── ci.yml                                 # [MEVCUT]
│   ├── bgts-e2e.yml                           # [MEVCUT]
│   ├── nightly.yml                            # [MEVCUT - GÜNCELLENECEK]
│   └── ai-test-pipeline.yml                  # [YENİ] AI-enhanced pipeline
│
├── reports/                                   # [MEVCUT + GENİŞLETME]
│   ├── e2e-html/                             # [MEVCUT]
│   ├── e2e-results.json                      # [MEVCUT]
│   ├── healing-log.json                      # [YENİ] Healing geçmişi
│   ├── flaky-report.json                     # [YENİ] Flaky analiz raporu
│   ├── anomaly-report.json                   # [YENİ] Anomaly tespitleri
│   ├── coverage-gaps.json                    # [YENİ] Coverage gap raporu
│   ├── ai-cost-report.json                   # [YENİ] LLM maliyet raporu
│   ├── metrics-history.json                  # [YENİ] Metrik zaman serisi
│   ├── test-history.json                     # [YENİ] Test sonuç geçmişi
│   ├── test-dependency-map.json              # [YENİ] Test-kod bağlantı haritası
│   └── dom-snapshots/                        # [YENİ] DOM snapshot'ları (healing)
│
├── docs/
│   ├── ai-test-automation-research.md         # [YENİ] Araştırma raporu
│   ├── ai-test-architecture.md                # [YENİ] Mimari dokümantasyon
│   ├── ai-test-code-examples.md               # [YENİ] Kod örnekleri
│   ├── ai-test-tools-comparison.md            # [YENİ] Araç karşılaştırma
│   ├── ai-test-best-practices.md              # [YENİ] En iyi uygulama rehberi
│   ├── ai-test-roadmap.md                     # [YENİ] Uygulama yol haritası
│   ├── ai-test-project-structure.md           # [YENİ] Bu dosya
│   └── synthetic-data-research.md             # [MEVCUT]
│
└── .cursor/rules/
    ├── data-testid-convention.mdc             # [MEVCUT]
    └── page-object-pattern.mdc                # [MEVCUT]
```

---

## 3. Modül Detayları

### 3.1 engine/services/ — AI Servis Katmanı

Bu dizin, tüm AI test otomasyon servislerini barındırır. Her servis bağımsız bir Python modülüdür ve Flask route'ları aracılığıyla API olarak sunulur.

```
engine/services/
├── __init__.py                     # Servis registry ve factory
├── llm_gateway.py                  # 400-500 satır
│   ├── LLMGateway class
│   ├── PII sanitization
│   ├── Prompt cache
│   ├── Model router
│   ├── Cost tracker
│   └── Rate limiter
│
├── ai_test_generator.py            # 200-300 satır
│   ├── AITestGenerator class
│   ├── Context builder
│   ├── Code validator
│   └── Template engine
│
├── bdd_generator.py                # 200-250 satır
│   ├── BDDGenerator class
│   ├── Step library scanner
│   ├── Step matcher
│   └── Feature formatter
│
├── test_prioritizer.py             # 200-250 satır
│   ├── TestPrioritizer class
│   ├── Git diff parser
│   ├── Dependency analyzer
│   └── Risk scorer
│
├── anomaly_detector.py             # 150-200 satır
│   ├── AnomalyDetector class
│   ├── Z-score detector
│   └── k6 analyzer
│
├── flaky_detector.py               # 150-200 satır
│   ├── FlakyDetector class
│   ├── Flaky scorer
│   └── Quarantine manager
│
├── coverage_analyzer.py            # 200-250 satır
│   ├── CoverageAnalyzer class
│   ├── Gap prioritizer
│   └── LLM test suggester
│
├── assertion_engine.py             # 150-200 satır
│   ├── AssertionEngine class
│   ├── AST parser
│   └── Assertion suggester
│
├── self_healer.py                  # 200-250 satır
│   ├── SelfHealer class
│   ├── DOM diff engine
│   ├── Multi-attribute fingerprint
│   └── Healing logger
│
└── security_scanner.py             # 100-150 satır
    ├── SecurityScanner class
    ├── ZAP integration
    └── Finding parser
```

### 3.2 engine/prompts/ — LLM Prompt Şablonları

Prompt'lar ayrı dosyalarda yönetilir, version control altındadır ve LLM model değişikliğinden bağımsız güncellenir.

```
engine/prompts/
├── test_generator_system.md
│   Kurallar: data-testid convention, page object pattern,
│   framework bilgisi, Türkçe senaryo isimleri
│
├── bdd_generator_system.md
│   Kurallar: Gherkin formatı, step reuse, edge case önerisi,
│   bankacılık terminolojisi
│
├── self_healer_system.md
│   Kurallar: Accessibility tree analizi, locator üretim formatı,
│   element tanıma stratejileri
│
├── assertion_analyzer_system.md
│   Kurallar: Anlamlı assertion kriterleri, false positive önleme,
│   framework-spesifik assertion formatı
│
└── security_analyzer_system.md
    Kurallar: OWASP Top 10, bankacılık güvenlik gereksinimleri,
    bulgu raporlama formatı
```

### 3.3 engine/config/ — AI Konfigürasyon

```yaml
# engine/config/ai_config.yaml
ai:
  enabled: true
  features:
    test_generation: true
    bdd_generation: true
    self_healing: true
    prioritization: true
    anomaly_detection: true
    flaky_detection: true
    coverage_analysis: true
    assertion_analysis: true
    security_scanning: false  # Faz 4'te aktif edilecek

llm:
  default_model: "gpt-4o"
  fallback_model: "gpt-4o-mini"
  cache_enabled: true
  cache_ttl_seconds: 3600
  pii_sanitization: true
  budget_limit_usd: 100.0
  rate_limit_per_hour: 100
  timeout_seconds: 30

healing:
  enabled: true
  max_retries: 1
  strategies:
    - testid_fuzzy
    - role_match
    - label_match
    - text_match
    - ai_assisted
  quarantine_threshold: 0.3
  quarantine_max_days: 14

prioritization:
  time_budget_seconds: 300
  min_score_threshold: 0.1
  weights:
    dependency: 0.4
    failure_rate: 0.35
    recency: 0.25

synthetic_data:
  generator: "faker"  # "faker" | "kde" | "ctgan"
  seed: 42
  default_customer_count: 100
  correlation_preservation: true
  differential_privacy:
    enabled: false  # Faz 4'te aktif edilecek
    epsilon: 1.0
```

```yaml
# engine/config/llm_models.yaml
models:
  gpt-4o:
    provider: openai
    max_tokens: 4096
    temperature: 0.2
    cost_per_1k_input: 0.0025
    cost_per_1k_output: 0.01
    use_for:
      - test_generation
      - bdd_generation
      - coverage_analysis

  gpt-4o-mini:
    provider: openai
    max_tokens: 2048
    temperature: 0.1
    cost_per_1k_input: 0.00015
    cost_per_1k_output: 0.0006
    use_for:
      - locator_generation
      - assertion_analysis

  claude-3-5-sonnet:
    provider: anthropic
    max_tokens: 4096
    temperature: 0.2
    cost_per_1k_input: 0.003
    cost_per_1k_output: 0.015
    use_for:
      - self_healing
      - security_analysis

  claude-3-5-haiku:
    provider: anthropic
    max_tokens: 2048
    temperature: 0.1
    cost_per_1k_input: 0.0008
    cost_per_1k_output: 0.004
    use_for:
      - classification
      - simple_analysis
```

```yaml
# engine/config/pii_patterns.yaml
patterns:
  - name: tc_kimlik
    regex: '\b\d{11}\b'
    replacement: '[TC_KIMLIK]'
    description: TC Kimlik numarası

  - name: iban
    regex: '\bTR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b'
    replacement: '[IBAN]'
    description: Türkiye IBAN

  - name: email
    regex: '\b[\w.+-]+@[\w-]+\.[\w.-]+\b'
    replacement: '[EMAIL]'
    description: E-posta adresi

  - name: telefon
    regex: '\b05\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b'
    replacement: '[TELEFON]'
    description: Türkiye cep telefonu

  - name: hesap_no
    regex: '\b\d{10,16}\b'
    replacement: '[HESAP_NO]'
    description: Banka hesap numarası
    context_required: true  # sadece bankacılık context'inde maskele
```

### 3.4 e2e/utils/ — AI TypeScript Yardımcıları

```
e2e/utils/
├── ai-locator.ts              # ~150 satır
│   ├── findElement()          # 6 strateji locator chain
│   ├── llmFindElement()       # Engine API çağrısı
│   └── recordSuccess()        # Locator geçmişi kayıt
│
├── self-healer.ts             # ~200 satır
│   ├── attemptHealing()       # Healing denemesi
│   ├── logHealing()           # Healing logu
│   └── setupSelfHealing()     # Playwright hook factory
│
└── test-metadata.ts           # ~50 satır
    ├── AI_GENERATED tag       # @generated-by: ai-test-generator
    ├── REVIEW_STATUS enum     # pending | approved | rejected
    └── addAIMetadata()        # Test dosyasına metadata ekle
```

### 3.5 reports/ — AI Rapor Dosyaları

```
reports/
├── healing-log.json            # Self-healing event geçmişi
│   [{testTitle, timestamp, result: {healed, oldLocator, newLocator, strategy}, domSnapshotPath}]
│
├── flaky-report.json           # Flaky test analiz sonuçları
│   [{testId, flakyScore, totalRuns, passCount, failCount, flipCount, recommendation}]
│
├── anomaly-report.json         # Anomaly tespit sonuçları
│   [{metricName, currentValue, expectedRange, zScore, severity, description}]
│
├── coverage-gaps.json          # Coverage gap analiz sonuçları
│   [{filePath, uncoveredLines, lineCoveragePct, priority, suggestedTest}]
│
├── ai-cost-report.json         # LLM maliyet raporu
│   {totalCalls, totalTokens, totalCostUsd, cacheHits, callsByModel}
│
├── metrics-history.json        # Metrik zaman serisi (anomaly detection girdi)
│   [{timestamp, totalDuration, failureRate, avgTestDuration, flakyCount}]
│
├── test-history.json           # Test sonuç geçmişi (flaky detection + prioritization girdi)
│   {"test_id": [{status, duration, error, timestamp, codeChangedDaysAgo}]}
│
├── test-dependency-map.json    # Test-kod bağlantı haritası (prioritization girdi)
│   {"test_id": ["src/file1.py", "src/file2.py"]}
│
└── dom-snapshots/              # Healing sırasında alınan DOM snapshot'ları
    └── {testId}.json
```

---

## 4. Konfigürasyon Dosyaları

### 4.1 Ortam Değişkenleri

Mevcut `.env.example`'a eklenecek AI-spesifik değişkenler:

```bash
# AI / LLM Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
ANTHROPIC_API_KEY=sk-ant-...

# AI Feature Flags
ENABLE_AI_FEATURES=true
ENABLE_SELF_HEALING=true
ENABLE_SYNTHETIC_DATA=true
ENABLE_AI_PRIORITIZATION=true

# LLM Gateway
LLM_CACHE_ENABLED=true
LLM_BUDGET_LIMIT_USD=100
LLM_RATE_LIMIT_PER_HOUR=100
LLM_PII_SANITIZATION=true

# Healing
HEALING_MAX_RETRIES=1
HEALING_QUARANTINE_THRESHOLD=0.3

# Synthetic Data
SYNDATA_GENERATOR=faker
SYNDATA_SEED=42
```

### 4.2 GitHub Actions Secrets

| Secret | Kullanım | Gerekli |
|--------|----------|---------|
| `OPENAI_API_KEY` | LLM Gateway | AI özellikler için |
| `ANTHROPIC_API_KEY` | Claude modelleri | Opsiyonel |
| `SLACK_WEBHOOK_URL` | Anomaly bildirimleri | Opsiyonel |

---

## 5. Bağımlılık Yönetimi

### 5.1 Engine Python Bağımlılıkları (eklenmesi gerekenler)

```
# engine/requirements.txt'e eklenecekler:

# AI Test Services
scikit-learn>=1.4         # Anomaly detection (Isolation Forest)
sdv>=1.10                 # Synthetic Data Vault (CTGAN, CopulaGAN)

# Mevcut (zaten var):
# openai
# anthropic
# faker
# playwright
# pytest-bdd
# allure-pytest
# numpy
# httpx
```

### 5.2 E2E TypeScript Bağımlılıkları

```json
// package.json devDependencies'e eklenmesi gerekenler:
{
  "devDependencies": {
    "@playwright/test": "^1.49.0"
    // Playwright MCP ayrı bir paket gerektirmez;
    // Playwright 1.49+ built-in MCP desteği içerir
  }
}
```

### 5.3 Bağımlılık Yönetim İlkeleri

- Yeni bağımlılıklar **minimum** tutulmalıdır
- Açık kaynak tercih edilmelidir
- Versiyon pinleme yapılmalıdır (güvenlik)
- `sdv` en büyük yeni bağımlılık (~200MB) — Docker image boyutunu etkileyecek
- Yerel LLM (Ollama) opsiyonel — kurulum Docker Compose ile ayrı servis

---

## Ekleme Sırası

Yeni dosya ve dizinlerin fazlara göre ekleme sırası:

| Faz | Eklenecek Dosya/Dizin |
|-----|----------------------|
| **Faz 1** | `engine/services/__init__.py`, `llm_gateway.py`, `bdd_generator.py`, `test_prioritizer.py`, `self_healer.py` |
| **Faz 1** | `engine/config/ai_config.yaml`, `llm_models.yaml`, `pii_patterns.yaml` |
| **Faz 1** | `engine/prompts/` (tüm prompt dosyaları) |
| **Faz 1** | `engine/routes/ai_generation.py`, `ai_healing.py` |
| **Faz 1** | `e2e/utils/ai-locator.ts`, `self-healer.ts` |
| **Faz 1** | `e2e/config/mcp-config.ts` |
| **Faz 1** | `reports/healing-log.json` template |
| **Faz 2** | `engine/services/ai_test_generator.py` |
| **Faz 2** | `engine/ai_synthetic_data/generators/` (tüm generator'lar) |
| **Faz 2** | `engine/features/ai_generated/`, `engine/tests/ai_generated/`, `e2e/ai-generated/` |
| **Faz 2** | `.github/workflows/ai-test-pipeline.yml` |
| **Faz 3** | `engine/services/anomaly_detector.py`, `flaky_detector.py`, `coverage_analyzer.py`, `assertion_engine.py` |
| **Faz 3** | `engine/routes/ai_analysis.py` |
| **Faz 3** | `reports/` (flaky, anomaly, coverage-gaps, metrics-history, test-history JSON'ları) |
| **Faz 4** | `engine/services/security_scanner.py` |
| **Faz 4** | `engine/ai_synthetic_data/privacy/`, `quality/` |
| **Faz 4** | `apps/web/src/app/ai-dashboard/` (tüm dashboard dosyaları) |
