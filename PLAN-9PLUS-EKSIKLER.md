# Plan'da Eksik Kalan Alanlar — Detaylı Analiz

> Önceki plan teknik mimariye odaklıydı. Ürünü gerçekten **9+** seviyede çalıştırmak için 25+ kategoride daha derinleşme gerek.

---

## 🔴 KRİTİK EKSİKLER

### 1. AI/ML Yaşam Döngüsü Yönetimi

İlk planda AI sadece "router + provider" olarak ele alındı. Gerçek AI-native ürün için:

**Prompt Engineering Disiplini**
- `packages/prompts/` — promptlar versiyonlanmış kod olarak
- Prompt template'leri (Jinja2) + variable validation
- Her prompt'un benchmark suite'i (LLM-as-Judge)
- Prompt A/B testing (PostHog feature flag ile)
- Prompt regression test (eski promptlar regression olunca alarm)
- Prompt cost tracking (token başına maliyet)
- **Dosya yapısı:**
  ```
  packages/prompts/
  ├─ src/
  │  ├─ scenarios/
  │  │  ├─ generate-bdd.v1.txt
  │  │  ├─ generate-bdd.v2.txt
  │  │  └─ generate-bdd.eval.json    # Test cases
  │  ├─ analysis/
  │  ├─ healing/
  │  └─ tools/                       # Function calling tools
  ```

**RAG (Retrieval-Augmented Generation) Altyapısı**
- Vector DB seçimi: **pgvector** (Postgres extension, no extra dep)
- Embedding modeli: **bge-m3** (multi-lingual, TR destekli)
- Reranker: **bge-reranker-v2-m3** (Turkish cross-encoder)
- Chunk stratejisi: semantic chunking (cümle bazlı + 512 token max)
- Hybrid search: vector + BM25 (Postgres FTS)
- Knowledge base: DSL katalog, run history, dokümantasyon, kullanıcı tercihleri

**LLM Cost Optimization**
- Provider routing tier'ları:
  - Tier 1 (hızlı/ucuz): Groq Llama 8B — basit sınıflandırma, intent
  - Tier 2 (denge): Gemini Flash — orta kompleks
  - Tier 3 (kaliteli): Claude Sonnet — final yanıt, kod üretimi
  - Tier 4 (lokal): Ollama Qwen2.5 — gizli veri
- Routing kararı: prompt karmaşıklığı + maliyet bütçesi + latency SLA
- LLM cache: aynı prompt → aynı cevap (semantic similarity ile, 1 saat TTL)
- Streaming: token başına bill, abort opsiyonu

**Guardrails**
- PII redaction (Microsoft Presidio Python)
- Prompt injection detection (rebuff library)
- Output validation (Zod-style schema)
- Toxicity filter (Perspective API)
- Hallucination check (citation grounding)
- Rate limit per-user (AI abuse koruması)

**Eval Suite**
- `evals/` klasörü — her AI feature için
- Golden dataset (50-200 örnek input + beklenen output)
- Otomatik nightly run
- Regression alert (skor %5 düşerse)
- LLM-as-Judge için ayrı eval (multi-judge consensus)

**AI Observability**
- Prompt + response her çağrıda log (PII redacted)
- Trace edilebilir (OTel + custom AI spans)
- Latency breakdown (provider call + tool exec + post-process)
- Cost dashboard (per-user, per-project, per-prompt-template)
- Feedback collection (👍👎 her AI yanıtta + neden)

---

### 2. Multi-Tenancy & Veri İzolasyonu

İlk planda sadece "RBAC" dedim. Multi-tenant SaaS için çok daha derin:

**Tenant Modeli**
```
Organization (tenant)
  └─ Workspaces (1-N)
     └─ Projects (1-N)
        └─ Scenarios, Runs, Reports, ...
```

**Postgres Row-Level Security (RLS)**
- Her tablo `tenant_id` kolonu zorunlu
- RLS policy: `tenant_id = current_setting('app.current_tenant')::uuid`
- Backend her request başında `SET app.current_tenant = '...'`
- Yanlışlıkla cross-tenant data sızıntısı **imkansız** (DB level guarantee)

**Database stratejisi**
- **Faz 1**: Shared DB, shared schema, RLS-isolated (default, ucuz)
- **Faz 2** (büyük müşteri): Shared DB, isolated schema per tenant
- **Faz 3** (enterprise): Isolated DB per tenant (kendi cluster'ı)
- Migration self-service: müşteri tier upgrade edince otomatik move

**Tenant onboarding**
- Self-service signup (kredi kartı veya 14 gün trial)
- Enterprise sales-led (custom contract, dedicated env)
- Tenant provisioning otomasyonu (DB schema, indexes, default users)
- Welcome email + initial setup tour

**Tenant izolasyon test'i**
- E2E: 2 tenant yarat, X tenant'tan Y tenant data'sına erişmeye çalış → 403
- Quarterly security audit specifically for tenant isolation
- Bug bounty kategorisi: cross-tenant leakage (en yüksek payout)

---

### 3. Billing & Pricing Infrastructure

İlk planda hiç yok. SaaS için olmazsa olmaz:

**Pricing Tiers** (örnek)
- **Free**: 1 proje, 100 scenario, 1k run/ay, community AI quota
- **Pro** ($49/ay/user): 10 proje, sınırsız scenario, 10k run/ay, premium AI
- **Team** ($199/ay/5 user): 50 proje, SSO, advanced AI
- **Enterprise** (custom): SSO+SCIM, dedicated env, SLA, mTLS

**Usage Tracking**
- Her API call metered
- LLM token kullanımı detaylı
- Storage (artifacts, screenshots)
- Bandwidth
- Test run minutes
- Webhook delivery counts

**Stripe Integration**
- Stripe Customer + Subscription
- Metered billing (her ay sonu LLM token kullanımı bill)
- Invoice generation
- Failed payment → grace period → suspend
- Tax handling (Stripe Tax)
- Türkiye için iyzico/Paraşüt entegrasyon opsiyonu

**Billing Portal**
- Müşteri kendi sayfasında:
  - Plan değiştir
  - Kullanım grafikleri
  - Fatura geçmişi
  - Ödeme yöntemi yönet
  - Üye davet et / çıkar (seat-based pricing)
- Quota uyarısı: %80'e gelince email + in-app

**Free Tier Spam Koruması**
- Email verification şart
- Hızlı projeksiyon (yeni hesap çok fazla işlem yaparsa → review)
- Captcha (suspicious signups)

---

### 4. Customer-Facing Web Properties

İlk planda sadece "app" var. Müşteri yolu komple eksik:

**Marketing Site** (`neurex.io`)
- Next.js statik + MDX
- Hero, features, social proof, pricing, blog, customers
- Ana CTA: "Free trial" + "Demo iste"
- SEO odaklı (meta, og tags, structured data)
- Performance: Lighthouse 100 zorunlu

**Public Docs** (`docs.neurex.io`)
- Nextra veya Docusaurus
- Quickstart (5 dk hello world)
- Concepts (DSL, AI, agents)
- API reference (OpenAPI auto-render)
- Tutorials (10+ guided)
- Migration guides (Cypress, Playwright, BrowserStack, Sauce)
- Video tutorials embed
- Search (Algolia DocSearch ücretsiz tier)

**Status Page** (`status.neurex.io`)
- statuspage.io veya self-hosted Cachet
- Component bazlı (API, AI, Workers, Web)
- Otomatik incident detection (uptime monitoring → status update)
- Email/Slack subscription
- Historical uptime metric (%99.95)

**Public Changelog** (`neurex.io/changelog`)
- Her release announcement
- Kategori (feature, fix, security, breaking)
- RSS feed
- In-app duyuru (bell ikon → "what's new")

**Public Blog**
- Engineering blog (technical posts)
- Customer stories
- AI in QA thought leadership
- SEO traffic kaynağı

---

### 5. Public API & SDK Stratejisi

İlk plan internal API'ye odaklandı. Müşterilere açılan API ayrı tasarım:

**Public REST API** (`api.neurex.io/v1`)
- Subset of internal API (sadece kararlı endpoint'ler)
- Versioning strict (v1 deprecate ≥ 12 ay önce duyurulur)
- API key auth (per project) — JWT yerine
- Rate limit tier'lı (Free 100 req/min, Pro 1k, Enterprise 10k)
- Quota dashboard customer'a görünür

**API Schema**
- OpenAPI 3.1 publish edilir (docs.neurex.io/api)
- Postman collection
- Insomnia workspace
- HAR examples her endpoint'te

**Official SDK'lar**
- **JavaScript/TypeScript** (`@neurex/sdk-js`)
- **Python** (`neurex-sdk-python`)
- **Go** (`go.neurex.io/sdk` — Y2)
- **Ruby**, **PHP** (community-supported)

**SDK Standartları:**
- Auto-generated from OpenAPI
- Native types
- Async support
- Retry + backoff built-in
- Error class hierarchy
- Logging hooks

**Webhook Sistemi**
- Müşteri event subscribe eder: `scenario.created`, `run.failed`, vs.
- POST delivery + HMAC signature
- Retry: exponential backoff, 24 saat içinde 8 deneme
- Dead letter queue (10 başarısız → muted, müşteri uyarı alır)
- Delivery dashboard (success rate, last attempt, payload preview)
- Replay (manual + automatic dead-letter)

**CLI Tool** (`neurex` CLI)
- `neurex login`
- `neurex run scenarios --project X`
- `neurex import --from playwright`
- `neurex sync` (git-like)
- Mac/Linux/Windows binary
- Auto-update mechanism

---

### 6. Test Platformuna Özel Altyapı

QA platformu için spesifik altyapı parçaları:

**Device Farm**
- **Cloud browsers**: Selenium Grid hub + node'lar
- Browser matrix: Chrome, Firefox, Safari, Edge (her biri 3 son major version)
- **Real device farm**: BrowserStack/Sauce Labs partnership veya self-host (AWS Device Farm)
- **Mobile**: iOS Simulators (Mac mini cluster) + Android Emulators (Linux + KVM)
- Headless + headed mode
- Geo location simulation (network conditions)

**Test Recording Infrastructure**
- Her run için:
  - Video kaydı (WebRTC veya playwright video API)
  - Network HAR
  - Console logs
  - DOM snapshots her step'te
  - Screenshots diff'leri
- Storage: S3 + signed URL (90 gün retention)
- UI'da timeline player (Cypress dashboard tarzı)

**AI-Powered Test Analysis**
- **Flaky test detection**: ML model — son 100 koşu pattern analizi
  - Feature'lar: pass/fail ratio, timing variance, error types
  - Model: gradient boosted tree (lightgbm)
  - Threshold: %90 confidence → "flaky" etiket
- **Test impact analysis**: Hangi kod değişikliği hangi test'i etkiler
  - Static analysis: dosya bağımlılık grafiği
  - Dynamic: önceki koşularda coverage data
- **Visual regression**: AI diff (pixel + semantic)
  - Anti-aliasing, antialias tolerans
  - Layout shift detection
  - Dynamic content masking
- **Auto-healing**: Locator kırılınca AI 3 alternatif önerir, en yakını otomatik dener
  - Stratejiler: XPath, role+text, neighbor element, ML similarity

**Synthetic Monitoring**
- Production'da sürekli koşan testler ("synthetic")
- 5 dk frekansta her ana flow
- Coğrafi dağıtık (US, EU, AP)
- Performance baseline (her endpoint p99 trend)
- Anomali alert (sapma > 2 std dev)

**CI/CD Provider Integrations**
- GitHub Actions: official action `neurex/run-tests@v1`
- GitLab CI: `.gitlab-ci.yml` template
- Jenkins: plugin
- CircleCI: orb
- Bitbucket Pipelines: pipe
- Azure DevOps: extension

**Reporting Format Support**
- JUnit XML
- Allure
- TestRail integration
- Xray (Jira) integration
- Custom webhook to any tool

---

### 7. Resilience & Chaos Engineering

İlk planda "k8s + HA" var ama dayanıklılık derinliği yok:

**Circuit Breaker Pattern**
- AI provider çağrılarında:
  - 10 ardışık fail → circuit "open" (30s)
  - Half-open state'te tek deneme
  - Başarılı → "closed" (normal)
- Library: `pybreaker` veya custom
- Fallback: alternatif provider veya cached response

**Bulkhead Isolation**
- Thread pool / async semaphore başına servis sınıfı
- Bir AI provider yavaşlarsa diğer requestleri etkilemez
- Async asyncio.Semaphore per provider

**Graceful Degradation**
- AI down → "AI şu anda meşgul, lütfen tekrar deneyin" + cached suggestion
- Search down → fallback to LIKE query
- Cache down → direct DB (yavaş ama çalışır)
- Read replica down → primary'e fallback
- Feature flag ile feature'ları kapatma (cascade fail önleme)

**Chaos Engineering**
- **Tools**: chaos-mesh, litmus, Gremlin
- **Practices**:
  - Game day quarterly (planned chaos)
  - Random pod kill (chaos monkey)
  - Network latency injection
  - DB failover drill
- **GameDay senaryoları**:
  - "AI gateway tamamen kapanırsa?"
  - "DB primary 5 dakika down olursa?"
  - "Redis cluster split-brain olursa?"
  - "Auth servis %50 hata dönerse?"

**SLO + Error Budget**
- SLI'lar tanımlı (latency, error rate, availability)
- SLO targetlı (%99.95 availability)
- Error budget: %0.05 = 21 dakika/ay
- Budget bittiğinde release freeze (kalite focus)

---

### 8. Data Warehouse & Analytics Pipeline

İlk planda observability var ama business analytics yok:

**OLTP vs OLAP ayrımı**
- OLTP: PostgreSQL (canlı uygulama)
- OLAP: ClickHouse veya BigQuery (analitik query)
- ETL: Airbyte veya dbt
- Frekans: real-time CDC (Debezium) → analitik DB

**dbt Models**
```
analytics/
├─ models/
│  ├─ staging/         # Raw → cleaned
│  ├─ intermediate/    # Joined, enriched
│  └─ marts/           # Business-ready
│     ├─ scenario_runs_daily.sql
│     ├─ tenant_health.sql
│     └─ ai_cost_attribution.sql
```

**Metabase / Looker**
- Self-service dashboard araç
- Müşteri dashboard'larından ayrı (internal team için)
- Her ekip kendi dashboard'u

**Product Analytics**
- **PostHog** veya **Mixpanel**:
  - User journey
  - Funnel analysis (signup → first scenario → first run)
  - Retention cohorts
  - Feature usage
  - A/B test results

**Data Retention**
- OLTP: 90 gün rolling (eski runs)
- OLAP: 2 yıl
- GDPR delete request: hem OLTP hem OLAP cascade

---

### 9. Notifications Infrastructure

İlk planda toast var ama notification sistemi yok:

**Multi-Channel**
- **In-app** (bell icon, current implementation)
- **Email** (transactional + digest)
- **Slack** (per-workspace incoming webhook)
- **Teams** (Microsoft webhook)
- **Discord** (community)
- **Webhook** (generic)
- **SMS** (Twilio, premium tier)
- **Push** (web push API + PWA)

**Notification Preference Center**
- Kullanıcı her event türü için kanal seçer:
  - "Test failed": email ✓, Slack ✓, in-app ✓
  - "Daily digest": email ✓, others ✗
  - "Test passed": all ✗ (default off)
- Quiet hours (22:00-08:00 sadece kritik)
- Snooze button (1h, 1d, until-resolved)

**Email Infrastructure**
- **Provider**: Resend veya AWS SES
- Templates: React Email (component-based)
- Tracking: open rate, click rate, bounce, complaint
- Unsubscribe link her email'de
- Transactional vs marketing ayrımı
- IP warming (yeni IP için)
- SPF, DKIM, DMARC tam config

**In-App Notification Center**
- Bell icon → 50 son notification
- Read/unread
- Group by type
- Mark all read
- Snooze, archive, delete
- Real-time (WebSocket)

---

### 10. Integration Ecosystem

İlk planda "AI providers" var ama 3rd party integration komple eksik:

**Core Integrations**
- **GitHub**: PR comment, status check, app installation
- **GitLab**: pipeline status, MR comment
- **Bitbucket**: build status
- **Jira**: bug create, test case sync, issue link
- **Linear**: same as Jira
- **Slack**: bot user, slash commands, interactive messages
- **Microsoft Teams**: same as Slack
- **PagerDuty**: incident create on test failure
- **Datadog**: send custom metrics
- **Sentry**: send errors

**Integration Architecture**
- OAuth2 flow her platform için
- Token storage encrypted (Vault)
- Per-tenant credentials
- Reconnect flow (token expire)
- Health check her integration için
- Webhook receive endpoints (incoming events)

**Marketplace** (Y2 hedef)
- Müşteriler kendi integration'larını yayımlasın
- Plugin SDK
- Review process
- Revenue share

---

## 🟡 ÖNEMLİ EKSİKLER

### 11. Internal Tooling (Operations için)

Müşteri-facing değil, **internal team** için:

**Admin Panel** (`admin.neurex.io`)
- Müşteri listesi, plan, kullanım
- Customer impersonation (debug için)
- Manual quota override
- Tenant suspend/resume
- Feature flag override per-tenant
- Refund processing
- Activity log (kim ne yaptı)

**Support Tools**
- Müşteri ticket'ı varken hemen ilgili tenant'a impersonate
- Customer logs viewer (Loki query)
- Recent errors per-tenant
- One-click "send debug bundle" (logs + state + repro)

**Sales Demo Environment**
- `demo.neurex.io` — temizlenebilir sandbox
- Pre-populated demo data (gerçekçi)
- Reset button (her demo sonrası temizler)
- Tracking (kim ne kullandı)

---

### 12. Performance Budget Enforcement

Lighthouse 100 hedefi var ama enforce mekanizması yok:

**Bundle Size Budget**
- Per route limit (örnek `/portfolio` < 180KB gzipped)
- CI'da measure (lighthouse-ci, size-limit)
- PR check'i (limit aşılırsa block)
- Historic graph (trend görmek)

**Database Query Budget**
- Her endpoint için max N+1 query sayısı
- pg_stat_statements monitoring
- Slow query auto-alert (> 100ms)

**Cache Hit Rate Target**
- Redis hit rate > %90
- CDN hit rate > %85
- LLM cache hit rate > %30 (similar queries)

**Tail Latency**
- p50, p95, p99, p99.9 tracking
- p99.9 < 1s (worst case)
- Alert on tail spike

---

### 13. Time Zone & Localization Derin

i18n bahsedildi ama detay eksik:

**Time Zone Handling**
- DB her şey **UTC**
- Frontend kullanıcı tercihine göre göster
- Browser API: `Intl.DateTimeFormat`
- Recurring jobs: cron expression + tz config
- DST gözeterek scheduling

**Number Formatting**
- Locale-aware decimal separator (1,234.56 vs 1.234,56)
- Currency (TRY ₺, USD $, EUR €)
- Percentage formatting

**Date Display**
- Relative ("3 dk önce")
- Absolute ("14 May 2026 09:30")
- User toggle
- "X gün önce" yerine "geçen Çarşamba" (relative natural)

**RTL Support Test'i**
- E2E test'leri RTL locale'de de çalışsın
- Logical CSS properties zorunlu (margin-start vs margin-left)
- Icon flipping (>>> → <<< RTL'de)

---

### 14. Legal & Compliance Detaylı

İlk planda "GDPR, SOC2" yazılı ama implement detayı yok:

**Terms of Service & Privacy Policy**
- Avukat-onaylı template
- Versionlanmış (kullanıcı yeni versiyona accept verir)
- Cookie consent banner (GDPR)
- Data subject rights flow:
  - Right to access (data export)
  - Right to delete (data erasure)
  - Right to portability (JSON export)
  - Right to rectify

**SOC 2 Type II Hazırlık**
- 12 ay process
- Trust principles: Security, Availability, Confidentiality, Processing Integrity, Privacy
- Internal controls dokümante
- 3rd party audit (PwC, Deloitte)
- Trust Center sayfası (rapor link, status)

**HIPAA (sağlık müşteri için, opsiyonel)**
- BAA (Business Associate Agreement)
- PHI handling
- Encryption at rest + transit
- Audit log

**Export Controls**
- ITAR/EAR uyumluluğu (savunma müşteri varsa)
- Sanctioned countries blocking (Crimea, Iran, Cuba, NK, Syria)

**Open Source Compliance**
- License scanning (FOSSA / Snyk)
- AGPL bulaşma kontrolü
- Component inventory (SBOM)
- License notice screen

---

### 15. Team & Engineering Process

Mimari plan yapıldı ama nasıl çalışacağı yok:

**RFC (Request for Comments) Process**
- Büyük değişiklikler için yazılı RFC
- Template: motivation, design, alternatives, downsides, prior art, unresolved
- 5-iş günü comment period
- Merge sonrası tracking

**Definition of Done**
- Kod yazıldı
- Tests yazıldı (unit + integration)
- Code review onaylandı
- Lighthouse/perf budget geçti
- A11y check geçti
- Docs güncellendi
- Storybook eklendi (UI ise)
- Telemetry eklendi
- Feature flag arkasında
- Deployed staging
- Smoke test geçti

**Postmortem Culture**
- Incident sonrası blameless postmortem (24h içinde)
- Template: timeline, root cause, contributing factors, action items
- Public (internal wiki) — herkes okusun
- Action items tracked, deadline'lı

**On-Call Rotation**
- Weekly rotation
- Primary + secondary
- Hand-off meeting (15dk Cuma)
- Compensation (saatlik veya günlük)
- Runbook her alarm için

**Code Review Standards**
- 24 saat içinde first review
- Max 400 satır PR (büyükse böl)
- 2 approval büyük değişiklikler için
- Auto-merge ufak (dependabot, typo)
- "Conventional Comments" (suggestion vs blocker)

**Engineering Principles** (yazılı doc)
- "Make it work, make it right, make it fast" — bu sırayla
- "Optimize for readers, not writers"
- "Make impossible states impossible"
- "Backwards compatible by default"
- "Logs are evidence, metrics are signals"
- ...

---

### 16. FinOps & Cost Management

İlk planda hiç yok. Production'da kritik:

**Cost Attribution**
- Her infra component → tenant-level cost
- Cloud cost dashboard (cost per tenant per month)
- LLM cost özellikle önemli (token bazlı detaylı)
- Storage cost (S3 hot/cold tier)

**Cost Optimization Practices**
- Spot instances (worker pool)
- Reserved instances (DB, primary nodes)
- Auto-shutdown dev/staging gece
- S3 lifecycle (90 gün → glacier)
- Right-sizing (her quarter review)

**Cost Alerts**
- Monthly budget per tenant tier
- Alert at %80, %100, %120
- Hard limits (paid plan suspended at 200%)
- AnomalyDetection (sudden 3x spike)

**Vendor Management**
- Quarterly review (OpenAI, Anthropic, AWS, Stripe)
- Negotiate volume discounts
- Multi-vendor for critical (LLM has 4 providers)
- Exit strategy her vendor için

---

### 17. File/Media Pipeline

Screenshots, videos, reports — büyük dosya handling:

**Upload Flow**
- Direct-to-S3 (signed URL)
- Multipart upload (büyük dosyalar)
- Progress tracking
- Resume (chunk-based)

**Processing**
- Image: thumbnail, resize, AVIF convert (Cloudflare Images veya self-host)
- Video: HLS encode (FFmpeg + worker pool)
- PDF: generate report (Puppeteer/Playwright PDF API)

**Delivery**
- CDN (Cloudflare R2 + Workers)
- Signed URL with expiry
- Tenant-isolated buckets

**Quota**
- Per-tenant storage limit
- Auto-clean eski artifacts (90 gün)
- Müşteri restore opsiyonu (premium)

---

### 18. Migration Tools (Competitor'lardan Geçiş)

Müşterinin Cypress/Playwright/BrowserStack'ten gelmesini kolaylaştır:

**Import Wizards**
- Cypress test suite import
- Playwright test suite import
- Selenium WebDriver test import
- Postman collection import
- Insomnia workspace import
- TestRail test case import

**Format Translators**
- Cypress `cy.get('selector').click()` → Neurex DSL
- Playwright `page.click(...)` → Neurex DSL
- AST-based, accurate translation

**Side-by-Side Comparison**
- Müşteri eski + yeni'i karşılaştırır
- Coverage diff (hangi test'ler import edildi)
- Confidence score per test

---

### 19. White-Label & Custom Domain

Enterprise için zorunlu:

**Custom Domain**
- `tests.acmecorp.com` → Neurex hosting
- SSL otomatik (Let's Encrypt + automation)
- DNS check helper

**Branding**
- Logo upload
- Primary color
- Favicon
- Email template customization
- "Powered by Neurex" footer (opt-out paid)

---

### 20. Bug Bounty & Security Disclosure

**HackerOne / Bugcrowd**
- Public program (Pro tier müşterileri sevdirir)
- Scope: production app, API, marketing site
- Out of scope: SPF, missing security headers (manual triage)
- Payout: $100 - $10k (severity)
- Quarterly metric (n reports, n valid, payout)

**security.txt**
- `/.well-known/security.txt` standart format
- Contact email, PGP key, policy URL

**Responsible Disclosure**
- 90 gün public disclosure
- CVE assignment (CNA olunmak)
- Hall of Fame sayfası

---

## 🟢 İYİ OLUR EKSİKLERİ

### 21. Mobile Native App
- React Native (code share %70 web ile)
- iOS + Android
- Push notifications native
- Offline mode (TanStack Query persistence)
- Biometric auth (Face ID)
- App Store + Play Store submission

### 22. Open Source Strategy
- Hangi parça open: design system? CLI? SDK?
- License decision: BSL (Business Source) vs MIT vs AGPL
- Contribution guide
- Code of Conduct
- Maintainer team
- Sponsorship (GitHub Sponsors)

### 23. Browser Extension
- Chrome / Firefox / Edge
- "Record" button (sayfa kaydet → scenario'ya çevir)
- DOM inspector entegre
- Screenshot annotate

### 24. Sürdürülebilirlik
- Carbon-aware computing (compute time düşük-carbon region'lara kaydır)
- Cost per scenario metric (efficiency)
- Sustainability report yıllık

### 25. Community
- Discord server (canlı destek + community)
- GitHub Discussions (open source repo'lar için)
- Monthly office hours (engineering team Q&A)
- Annual conference (NeurexCon — Y3)

---

## ÖZET: Eklenmeli Listesi (Önem Sırası)

### Mutlaka (Q1-Q2)
1. ✅ AI/ML lifecycle (prompt versioning, eval, RAG, guardrails)
2. ✅ Multi-tenancy + RLS
3. ✅ Billing + Stripe
4. ✅ Public docs site (`docs.neurex.io`)
5. ✅ Status page (`status.neurex.io`)
6. ✅ Email infrastructure
7. ✅ Resilience patterns (circuit breaker, graceful degradation)
8. ✅ Postmortem culture + RFC process

### Yapılmalı (Q3-Q4)
9. ✅ Public REST API + SDK'lar (JS, Python)
10. ✅ Webhook sistemi + retry
11. ✅ Notification preference center
12. ✅ Integration ecosystem (GitHub, Slack, Jira)
13. ✅ Device farm + recording infra
14. ✅ AI-powered test analysis (flaky ML, healing)
15. ✅ Data warehouse + dbt
16. ✅ Admin panel + support tools
17. ✅ SOC 2 Type II prep
18. ✅ Bug bounty

### Yapsak iyi olur (Y2)
19. CLI tool
20. Synthetic monitoring
21. Marketplace (3rd party plugins)
22. White-label
23. Mobile native app
24. Migration wizards
25. Open source strategy
26. Community (Discord, conference)

---

## Son Söz

İlk plan **mimari mükemmellik**e odaklıydı ama bir SaaS sadece kod değil. Yukarıdaki 25 alan eklenmediğinde:

- **AI lifecycle yok** → Prompt regresyon hatası prod'a gider, kimse anlamaz
- **Multi-tenancy yok** → 1. müşteri 2. müşteri data'sını görür, şirket biter
- **Billing yok** → Para kazanılamaz, sürdürülemez
- **Docs/Status yok** → Trust yok, sales çöker
- **Resilience yok** → AI sağlayıcı down → ürün down
- **Postmortem yok** → Aynı hata tekrar tekrar olur
- **FinOps yok** → AWS faturası şirketi batırır
- **SOC2 yok** → Enterprise satışı yok

**Sonuç**: Önceki plan **mimari iskelet**di. Bu eksiklikler eklendiğinde gerçek **9+ ürün** çıkar. Tahmini eklenen iş: **8-12 ay** daha (yani 1.5-2 yıllık tam yol haritası).
