# Neurex QA — Frontier Plan 2030

> Önceki planlar Linear/Stripe seviyesine ulaşmayı hedefliyordu. **Bu plan o seviyeyi aşıyor.**
> 5 yıl sonra var olması gereken QA platformunun blueprint'i.
> Pragmatizmden çok cesaret. Risk almak değil, risk önderi olmak.

---

## 0. Vizyon — Neurex 2030

**Neurex 2030 = QA Mühendisinin Dijital Eşi**

Şu anki paradigma:
> "Mühendis test yazar, sistem koşturur, sonuçları gösterir."

2030 paradigması:
> "Sistem testi yazar, koşturur, hataları öngörür, düzeltir, öğrenir. Mühendis stratejik kararları verir."

**Yeni yıldız metrikler:**
- **MTBF (Mean Time Between Failures)** > 30 gün (production'da)
- **MTTR (Mean Time To Resolution)** < 5 dakika
- **Test maintenance overhead** %0 (AI tamamı yapar)
- **Bug discovery rate** uygulamadaki gerçek bug'ların >%95'i
- **Zero-touch deploys** %100 (insan onayı gerekmeden)
- **Customer trust score** > %95 (verifiable trust ile)

---

## 1. ON Frontier Pillarları

### 1.1 AI-Native (Augmented değil)

Mevcut yaklaşım: "AI yardım eder."  
2030: **AI sürer, insan yön gösterir.**

Düzey spektrumu (Autonomy Levels — sürücüsüz araba modeli):

| Düzey | Tanım | Örnek |
|-------|-------|-------|
| L0 | Yardımsız | Manuel test yazımı |
| L1 | Öneri | "Bu senaryoyu öneriyorum" |
| L2 | Kısmi otomasyon | "Sen başlat, ben tamamlarım" |
| L3 | Koşullu otomasyon | İnsan supervisor olarak |
| **L4** | **Yüksek otomasyon** | Sadece exception'larda insan |
| L5 | Tam otomasyon | Hiç insan yok (hedef değil) |

Neurex 2030 hedefi: **L4 yetenek, L3 default davranış**. Müşteri istediğinde L4'e çıkarır.

### 1.2 Multi-Agent Sistem

Tek AI değil, **uzman ajan ekosistemi**:

```
┌─────────────────────────────────────────────────┐
│              Orchestrator Agent                  │
│  (Görev planlama, ajan seçim, sonuç birleştirme) │
└────────────┬────────────────────────────────────┘
             │
   ┌─────────┼─────────┬──────────┬─────────────┐
   ▼         ▼         ▼          ▼             ▼
┌──────┐ ┌──────┐ ┌────────┐ ┌─────────┐ ┌─────────┐
│Plan- │ │Exec- │ │Critic  │ │Heal-   │ │Explorer │
│ner   │ │utor  │ │Agent   │ │er      │ │Agent    │
└──────┘ └──────┘ └────────┘ └─────────┘ └─────────┘
   │         │         │          │             │
   ▼         ▼         ▼          ▼             ▼
- Test       Adım      Kalite      Locator       Hidden
  stratejisi yürütme   skoru,     onarımı,      bug
  kurar      uygular   sebep      otomatik       arar
                       analizi    güncelleme    
```

**Agent yetkinlik matrisi**:

| Agent | Yetenek | LLM | Tool'lar |
|-------|---------|-----|----------|
| Planner | Test stratejisi, kapsam analizi | Claude Opus | code-search, doc-fetch |
| Executor | Step-by-step test koşumu | Llama 70B | browser-control, db-query |
| Critic | Test kalitesi, eksik durum tespiti | Claude Sonnet | coverage-tool, history-search |
| Healer | Kırık locator/test onarımı | Qwen 14B Coder | dom-inspect, history-similarity |
| Explorer | Otonom keşif testi | Gemini Flash | random-walk, anomaly-detect |
| Reporter | Doğal dil rapor üretimi | Claude Haiku | metrics-aggregate |
| Strategist | Risk analizi, önceliklendirme | Claude Opus | bug-history, code-churn |

**Agent Protocol**:
- MCP (Model Context Protocol) tabanlı
- Her agent kendi tool subset'iyle
- Inter-agent communication: structured message passing
- Memory: episodic (Redis) + semantic (pgvector) + procedural (skill library)

### 1.3 Continual Learning

Mevcut: Modeller statik, prompt'lar elle güncellenir.  
2030: **Sistem kendinden öğrenir, her gün daha iyi olur.**

**Reinforcement Learning from Production**:
- Her test koşusu = veri noktası
- Başarılı koşumlar (test gerçek bug yakaladı) → positive reward
- Flaky koşumlar (gereksiz fail) → negative reward
- Replay buffer + offline RL (CQL, BCQ)
- Her gece eğitim (production'a dokunmadan)

**Fine-tuning per tenant**:
- Müşterinin domain'inden örnek toplar (anonymized)
- LoRA adapter eğitir (tam fine-tune değil, hızlı)
- Customer-specific terminology, patterns, anti-patterns öğrenir
- Opt-in, GDPR compliant

**RLHF (Human Feedback)**:
- 👍👎 her AI suggestion'da
- Tercih learning (pair-wise: A vs B hangisi daha iyi?)
- Reward model nightly retrain
- Production'a SLO bazlı deploy

**Self-Improving Test Suite**:
- AI kendi yazdığı test'i değerlendirir
- Yetersiz coverage → yeni test ekler
- Redundant test → birleştirir
- Stale test → arşivler
- Müşterinin onayıyla "Test Garden" — sistem self-cultivates

### 1.4 Time-Travel & Reproducibility

Mevcut: Test bir kere koşar, log kalır.  
2030: **Her şey reproducible event stream. İstediğin ana dön, alternatif gerçekliği test et.**

**Event Sourcing Everywhere**:
- Her aksiyon = immutable event
- State = event'lerin toplamı
- Bir tarih veriyorsun → o andaki state'i görüyorsun
- "Geçen Salı 14:23'te bu test neden başarısızdı?" → tam replay

**What-If Analysis**:
- "Bu test'i farklı locator stratejisiyle çalıştırsam?"
- Branch reality: alternatif gerçeklik yaratır
- Side-by-side karşılaştırma
- "Hangisi daha iyi?" otomatik karar

**Causal Inference**:
- Test başarısız oldu → neden?
- AI causal chain'i kurar:
  - "API endpoint X dün 50ms yavaşladı"
  - "Bu DB indeks değişikliğinden geliyor"
  - "Migration #2347 atomik değildi"
  - "Root cause: PR #5891"
- Otomatik bug report Jira'ya açar, owner'a atar

**Verifiable History**:
- Merkle tree audit log
- Her event hash'i bir öncekine zincir bağlı
- Tampering imkansız (kriptografik garanti)
- Public attestation (Sigstore)
- Customer: "kanıtla bu test gerçekten geçti" → görsel proof

### 1.5 Local-First & Federated

Mevcut: Server-coordinated, online-only.  
2030: **Local-first, sync-engine ile cloud opsiyonel.**

**CRDT-Based Collaboration**:
- Yjs / Automerge backbone
- Hiçbir merge conflict yok (matematiksel garanti)
- Offline'da çalış, online'da sync
- Eventual consistency

**Sync Engine**:
- Linear sync engine modeli
- Her client'ta full state replica
- Sub-100ms UI response (lokal okur)
- Background sync (lokal yazar, async server'a iter)
- Optimistic UI default

**Federated Identity**:
- OIDC + WebAuthn (passkey)
- Self-sovereign identity (DID)
- Customer kendi IdP'sini bağlar
- Multi-org user single login

**Self-Hosted = Full Feature**:
- Cloud version'ı self-host'un bir konfigürasyonu
- Air-gapped deployment desteği (defense, banking)
- Docker single binary
- Kubernetes Operator (CRD)
- Online lisans (offline grace 30g)

### 1.6 Confidential Computing

Mevcut: Veri encrypted at rest + transit.  
2030: **Encrypted in-use de — server bile veriyi göremez.**

**Trusted Execution Environments**:
- Intel TDX, AMD SEV-SNP, ARM CCA
- Customer code TEE içinde çalışır
- Memory encrypted (RAM dahil)
- Remote attestation: "kanıtla TEE'de çalışıyorsun"

**Zero-Knowledge Architecture**:
- Customer encryption key sadece browser'da
- Server şifrelenmiş JSON'u sakl
- Search: encrypted search (homomorphic veya client-side)
- Backup: encrypted, recovery key customer'da

**End-to-End Encryption**:
- Test data, screenshots, video: E2EE
- AI inference: encrypted in TEE
- Sadece müşteri görür
- Subpoena-proof (Apple iCloud Advanced Data Protection benzeri)

**Differential Privacy**:
- Tenant aggregate analytics
- Hiçbir bireysel kullanıcı tespit edilemez
- ε = 1.0 budget
- Apple, Google standartları

### 1.7 Programmability & Plugin Marketplace

Mevcut: Sabit özellik seti.  
2030: **Müşteri ve community kendi özelliklerini ekler.**

**Embedded Runtime**:
- WebAssembly Component Model
- Languages: JS, Python, Rust, Go (WASM compile)
- Sandbox: capability-based security
- Resource limits (CPU, memory, network)

**Plugin Türleri**:
- **Test runner extension** — yeni framework
- **DSL provider** — custom test cümlecikleri
- **Reporter** — özel rapor format'ı
- **Integration** — yeni 3rd party
- **AI agent** — özel görev ajanı
- **UI extension** — dashboard widget'ı

**Marketplace**:
- Web (`marketplace.neurex.io`)
- In-app installation (1-click)
- Review process (security scan + manual)
- Revenue share (70% developer, 30% Neurex)
- Free + paid + freemium
- Verified badge (security audit geçti)

**Plugin Development Kit**:
- `neurex plugin init` (CLI scaffold)
- TypeScript/Python SDK
- Local dev with hot reload
- E2E test framework
- Storybook component lib
- Publishing pipeline

### 1.8 Real-Time Beyond WebSocket

Mevcut: HTTP REST + WebSocket.  
2030: **QUIC, WebTransport, server-sent events, HTTP/3**.

**Transport Modernization**:
- **HTTP/3 + QUIC** primary (lower latency, multiplexing)
- **WebTransport** bidirectional streams
- **Server-Sent Events** AI streaming için (mevcut)
- **gRPC-Web** internal API'lar için

**Sub-100ms Global Latency**:
- Edge compute (Cloudflare Workers, Deno Deploy)
- Anycast routing
- Regional read replicas (Postgres logical replication)
- CDN for everything (static + API responses)

**Real-Time Test Viewing**:
- Müşteri test koşusunu LIVE izler
- Her step canlı highlighted
- Screen recording stream (1-2 fps thumbnail, 30fps on demand)
- Multiple viewer simultaneously
- Multi-cursor on test code (kim neyi düzenliyor)

**Multi-User Test Authoring**:
- Google Docs benzeri eşzamanlı editing
- Cursor presence
- Comment threads inline
- Change attribution
- Conflict-free CRDT

### 1.9 Beyond UI Testing

Mevcut: Web UI ve API testleri.  
2030: **Her şeyin testi, AI ajanları dahil.**

**Test Edilebilen Yeni Yüzeyler**:

| Yüzey | Tool | Tarz |
|-------|------|------|
| Web UI | Playwright + AI vision | Pixel + semantic |
| Mobile | Appium + AI healing | iOS/Android |
| API | OpenAPI fuzzing | Property-based |
| GraphQL | Schema-aware query gen | Auto-discovery |
| WebSocket | Time-travel replay | Sequence verification |
| **LLM Agents** | **Multi-turn eval** | **Hallucination + bias** |
| **Voice UI** | **TTS + STT loop** | **Alexa/Siri testleri** |
| **AR/VR** | **3D scene graph** | **Unity/Unreal entegre** |
| **IoT** | **MQTT/CoAP** | **Embedded simulator** |
| **Blockchain** | **dApp interaction** | **Smart contract test** |
| **CLI** | **PTY automation** | **Terminal apps** |
| **Desktop** | **Native Win/Mac** | **WinAppDriver, Accessibility API** |

**LLM Agent Testing** (önemli yeni alan):
- Müşteri bir AI chatbot inşa etmiş
- Neurex onun kalitesini test eder:
  - **Accuracy**: doğru cevap veriyor mu? (benchmark)
  - **Hallucination**: uydurma var mı? (RAG retrieval check)
  - **Bias**: cinsiyet, ırk biased mi? (eval suite)
  - **Toxicity**: zararlı çıktı? (Perspective API)
  - **Latency**: SLA içinde mi?
  - **Cost**: token başına?
  - **Robustness**: prompt injection'a dayanıklı mı?

**Synthetic Monitoring Beyond Web**:
- API uptime monitor
- Mobile app store rating tracker
- DNS / certificate expiry
- 3rd party dependency health

### 1.10 Sustainability & Ethics

Mevcut: Yeşil hesap kitap yok.  
2030: **Karbon her dashboard'da, etik framework açık.**

**Carbon-Aware Compute**:
- Worker pool: low-carbon region'a kayar
- Test koşumu: gece (yenilenebilir enerji yüksek)
- "ASAP" vs "Carbon-saving" toggle (user choice)
- Carbon Insights API (electricityMap)

**Efficiency Metrics**:
- gCO₂ per test run
- gCO₂ per AI inference
- Tenant carbon dashboard
- Quarterly sustainability report
- B-Corp certification

**AI Ethics Framework**:
- Bias auditing (her AI feature için)
- Explainability (her AI kararı açıklanabilir)
- Human override (her kararı insan geçersiz kılabilir)
- Transparency report (yıllık)
- AI Council (external advisors)

**Open Standards**:
- OpenAPI, OpenTelemetry, OCI, AsyncAPI, GraphQL
- Vendor lock-in yok
- Data portability (her tenant export edebilir)
- Migration tools competitor'lara DOA giriş kolay

---

## 2. Mimari — 2030 Stack

### 2.1 Tüm Stack Görseli

```
┌───────────────────────────────────────────────────────────────┐
│                      EDGE LAYER                                │
│  Cloudflare Workers │ Deno Deploy │ Vercel Edge Functions      │
│  - Static cache, image optimization, auth gate                 │
└─────────────────────┬─────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                    GATEWAY LAYER                               │
│  HTTP/3 + QUIC │ gRPC-Web │ WebTransport │ SSE                 │
│  - Rate limiting, mTLS, request signing                        │
└─────────────────────┬─────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                  APPLICATION LAYER                             │
│  FastAPI (Python 3.13) │ Rust services (perf-critical paths)  │
│  - DDD bounded contexts                                        │
│  - CQRS read/write split                                       │
│  - Event sourcing core                                         │
└─────────────────────┬─────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                     AGENT LAYER                                │
│  Multi-agent orchestrator │ MCP tools │ LangGraph              │
│  Planner │ Executor │ Critic │ Healer │ Explorer │ Reporter    │
└─────────────────────┬─────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                  INFERENCE LAYER                               │
│  Multi-LLM router (cost+latency+quality optimized)             │
│  Anthropic │ Groq │ Gemini │ Ollama (local) │ Custom fine-tune │
│  pgvector + Meilisearch hybrid search                          │
└─────────────────────┬─────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                  EXECUTION LAYER                               │
│  Test runner farm: Kubernetes pods                             │
│  - Playwright workers (per browser)                            │
│  - Appium farm (iOS sim, Android emu, real device)             │
│  - WASM sandbox (plugin runs)                                  │
│  Celery / Temporal workflow                                    │
└─────────────────────┬─────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                     DATA LAYER                                 │
│  Postgres 17 (OLTP, pgvector, FTS, partitioning)              │
│  ClickHouse (OLAP, analytics)                                 │
│  Redis (cache, queue, presence, pubsub)                       │
│  S3-compatible (artifacts, video, screenshot)                 │
│  Apache Iceberg (data lake, time-travel queries)              │
└─────────────────────┬─────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                  OBSERVABILITY                                 │
│  OpenTelemetry → Jaeger / Tempo (traces)                       │
│  Prometheus + Thanos (metrics, long-term)                      │
│  Loki / Elastic (logs)                                         │
│  Grafana (unified)                                             │
│  Sentry (frontend errors)                                      │
│  PostHog (product analytics)                                   │
└─────────────────────┬─────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                    INFRA / OPS                                 │
│  Kubernetes (EKS/GKE) │ Helm │ Argo CD (GitOps)               │
│  Terraform │ Crossplane (infra-as-CRD)                         │
│  Vault (secrets) │ cert-manager (TLS)                          │
│  Istio (service mesh, mTLS)                                    │
│  Chaos Mesh (resilience testing)                               │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 Veri Modelinin Geleceği

**Event Sourcing Core**:
```sql
-- Tek "events" tablosu, immutable append-only
CREATE TABLE events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_id  UUID NOT NULL,
    aggregate_type TEXT NOT NULL,
    sequence_no   BIGINT NOT NULL,
    event_type    TEXT NOT NULL,
    payload       JSONB NOT NULL,
    metadata      JSONB NOT NULL,   -- actor, ip, timestamp, hash, prev_hash
    tenant_id     UUID NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL,
    UNIQUE (aggregate_id, sequence_no)
) PARTITION BY RANGE (occurred_at);

-- Aylık partition
CREATE TABLE events_2026_05 PARTITION OF events
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Hash chain for tamper-evidence
ALTER TABLE events ADD CONSTRAINT events_hash_chain
    CHECK (metadata->>'hash' IS NOT NULL AND metadata->>'prev_hash' IS NOT NULL);
```

**Read Models (CQRS Query Side)**:
```sql
-- Denormalized, query-optimized
CREATE MATERIALIZED VIEW scenario_list_v AS
SELECT
    s.id, s.title, s.project_id,
    p.name AS project_name,
    last_run.passed, last_run.duration_ms,
    (SELECT COUNT(*) FROM runs r WHERE r.scenario_id = s.id) AS run_count
FROM scenarios s
JOIN projects p ON p.id = s.project_id
LEFT JOIN LATERAL (
    SELECT * FROM runs WHERE scenario_id = s.id
    ORDER BY started_at DESC LIMIT 1
) last_run ON TRUE;

CREATE INDEX idx_scenario_list_project ON scenario_list_v (project_id);
-- Refresh via trigger on event publish
```

**Iceberg Data Lake** (uzun vadeli):
- Test execution history (10 yıl saklamayı düşün)
- Parquet format, S3
- Trino/DuckDB ile query
- Time-travel queries: `AS OF '2023-11-15'`

### 2.3 Worker Mimarisi

**Temporal.io workflow orchestration**:
```python
@workflow.defn
class TestSuiteExecution:
    @workflow.run
    async def run(self, suite_id: str) -> SuiteResult:
        # Reliable execution — retries, timeouts, durability built-in
        plan = await workflow.execute_activity(
            plan_tests, suite_id, retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # Parallel execution
        results = await asyncio.gather(*[
            workflow.execute_activity(run_test, t, start_to_close_timeout=timedelta(minutes=10))
            for t in plan.tests
        ])
        
        report = await workflow.execute_activity(generate_report, results)
        return report
```

**Faydası**:
- Durable execution (crash sonrası resume)
- Audit log built-in
- Version migration (running workflow'lar etkilenmez)
- Pause/resume/cancel native
- Time-travel debugging

### 2.4 Sync Engine (Linear-style)

**Client state'i lokal, sync background'da**:
```typescript
// Lokal sayfa: anında render (no spinner)
const projects = useLocalProjects();  // IndexedDB

// Background: server ile diff sync
const sync = useSyncEngine();
useEffect(() => {
  sync.subscribe('projects', (updates) => {
    applyUpdates(updates);  // CRDT merge
  });
}, []);

// Mutation: optimistic, server'a async push
function createProject(name: string) {
  const id = uuid();
  applyLocal({ type: 'CREATE_PROJECT', id, name });
  sync.push({ type: 'CREATE_PROJECT', id, name });
  return id;
}
```

**Sub-100ms UI response garantisi**.

---

## 3. AI Detayı — Frontier Düzey

### 3.1 LLM Router (Maliyet+Latency+Kalite Optimum)

```python
class IntelligentRouter:
    """
    Her isteği en uygun model'e yönlendirir.
    Karar değişkenleri: task type, budget, latency SLA, quality requirement.
    """
    
    async def route(self, request: LLMRequest) -> str:
        # 1. Task classification (cheap model with intent classifier)
        intent = await self.classify(request.prompt)
        
        # 2. Budget check
        tenant_budget = await self.budget.remaining(request.tenant_id)
        
        # 3. Latency requirement
        latency_sla = request.latency_sla_ms or 5000
        
        # 4. Model selection logic
        candidates = self.models[intent]
        # Filter by SLA
        candidates = [m for m in candidates if m.p95_latency_ms <= latency_sla]
        # Filter by budget
        candidates = [m for m in candidates if m.cost_per_request <= tenant_budget.per_request]
        # Sort by quality desc
        candidates.sort(key=lambda m: m.quality_score, reverse=True)
        
        if not candidates:
            return await self.fallback(request)
        
        # 5. Try cheapest of top 3 quality
        for model in candidates[:3]:
            try:
                return await self.execute(model, request)
            except (RateLimitError, ProviderDownError):
                continue
        
        # 6. Last resort: local Ollama
        return await self.local_model(request)
```

**Kalite vs Maliyet Matrix**:

| Task | Tier 1 (cheap) | Tier 2 (balanced) | Tier 3 (premium) |
|------|----------------|-------------------|------------------|
| Intent classification | Groq Llama 8B | — | — |
| Form autocomplete | Groq Llama 8B | Gemini Flash | — |
| Test step suggestion | Gemini Flash | Claude Haiku | Claude Sonnet |
| BDD scenario generation | — | Claude Sonnet | Claude Opus |
| Code generation | — | Qwen Coder 14B | Claude Sonnet |
| Bug root cause | — | — | Claude Opus |
| Vision (screenshot analyze) | — | Gemini 1.5 Pro Vision | Claude 3.5 Sonnet |

### 3.2 RAG (Retrieval-Augmented Generation)

**Multi-source retrieval**:

```python
class HybridRetriever:
    """
    BM25 + Vector + Reranker pipeline.
    Kalite kayıpsız hızlı arama.
    """
    
    async def retrieve(self, query: str, k: int = 20) -> list[Document]:
        # Paralel arama
        async with asyncio.TaskGroup() as tg:
            bm25_task = tg.create_task(self.bm25_search(query, k * 2))
            vector_task = tg.create_task(self.vector_search(query, k * 2))
            graph_task = tg.create_task(self.graph_search(query, k))  # bilgi grafiği
        
        # RRF (Reciprocal Rank Fusion)
        combined = self.rrf_merge([bm25_task.result(), vector_task.result(), graph_task.result()])
        
        # Reranker (cross-encoder)
        top_k = combined[:k * 3]
        scores = await self.reranker.score(query, [d.content for d in top_k])
        top_k = sorted(zip(top_k, scores), key=lambda x: x[1], reverse=True)[:k]
        
        return [doc for doc, _ in top_k]
```

**Knowledge Base İçeriği**:
- Müşterinin DSL kataloğu (kendi step library'si)
- Geçmiş test'leri ve sonuçları
- Code search (müşteri kod tabanı bağlı ise)
- Dokümantasyon (Confluence, Notion entegrasyonu)
- Slack mesajları (#qa kanalı arşivi)
- Jira issue tarihçesi
- Stack Overflow + GitHub public

**Citation Grounding**:
- Her AI cevap kaynak alıntısıyla
- Inline footnote: "Bunu söyledim çünkü senaryo #1234'te aynı pattern var"
- Click → kaynak sayfaya zıpla

### 3.3 Eval Pipeline

**Continuous AI Quality**:

```yaml
# evals/scenario_generation/golden.yaml
- input:
    project_description: "E-commerce checkout"
    requirement: "User adds item to cart and pays with credit card"
  expected:
    scenario_count_min: 3
    must_include_steps:
      - "User adds item to cart"
      - "User proceeds to checkout"
      - "User enters credit card"
      - "User confirms payment"
    quality_criteria:
      - "Gherkin format valid"
      - "No leaked PII in test data"
      - "Includes negative case (decline)"
  judge_prompt: "Score 1-10: scenario completeness for checkout flow"
  
- input: ...
```

**Nightly Eval Run**:
- 200+ golden test cases
- Multiple judges (LLM-as-Judge × 3, consensus)
- Score her metric için
- Trend graph (kalite hangi yöne gidiyor?)
- Regression alert: any metric drops > %5

**A/B Test Prompts**:
- Production'da %10 trafik yeni prompt'a
- 24 saat veri topla
- İstatistiksel anlamlılık testi
- Auto-promote (better) veya rollback (worse)

### 3.4 AI Cost Transparency

**Per-action cost UI**:
```
✨ Scenario öneri (~$0.003) [Onayla]
```
Müşteri AI'ı kullanmadan önce maliyeti görür.

**Budget Manager**:
- Her tenant aylık AI budget
- Soft limit (%80 → warn)
- Hard limit (%100 → pause AI features)
- Top-up self-service

**Cost Attribution**:
- Token-level granular
- Provider, model, prompt template, user, tenant attribute
- Spike detection (anomaly): "Bugün AI maliyeti 5x yükseldi, neden?"

### 3.5 On-Device AI (Privacy-First Tier)

Premium müşteri için: **AI inference müşteri network'ünde**.

**WebGPU/WebNN modeller** (browser-side):
- Küçük modeller (Phi-3 Mini, TinyLlama)
- Form autocomplete, basit suggestion
- Hassas veri server'a hiç gitmez

**Self-hosted LLM Cluster**:
- Müşteri kendi Ollama/vLLM cluster'ını runner
- Neurex sadece coordination
- Veri customer environment'tan çıkmaz

---

## 4. Test Platformuna Özel Frontier

### 4.1 Autonomous Test Generation

**From User Stories**:
```
INPUT: "User can login with email and password"
       ↓
   [Planner Agent]
       ↓
   - Happy path
   - Wrong password
   - Account not found  
   - Account locked
   - Rate limited
   - SQL injection attempt
   - XSS in email
   - Very long password
   - Unicode email
       ↓
   [Executor Agent → Playwright]
       ↓
   8 scenarios oluşturuldu, %93 coverage
```

**From Production Traces**:
- Sentry trace import
- "Bu hata production'da 17 kez oldu" → reproduce eden test üret
- "Bu user journey en sık" → smoke test'e ekle

**From Code Changes**:
- PR açıldı → Neurex etkilenen test'leri belirler
- Yetersiz coverage → AI yeni test önerir
- Otomatik PR comment: "Bu test eklemenizi öneriyorum"

### 4.2 Self-Healing 2.0

**Mevcut**: Locator değişti → AI alternatif önerir.  
**2030**: AI test'i baştan tasarlar.

**Healing Stratejileri** (önceliklendirme ile):
1. **Element ID/test-id** (stabil olmalı)
2. **Role + accessible name** (semantic, dayanıklı)
3. **Visual matching** (ekran görüntüsü embed, vektör similarity)
4. **Neighboring elements** (komşu element'e göre)
5. **Path similarity** (DOM tree XPath fuzzy match)
6. **AI vision** (GPT-4 Vision: "tıklamam gereken butonu göster")

**Healing Tree**:
- 1'den 6'ya kadar otomatik dene
- Confidence skoru tahmin
- < %80 → human review için flag
- > %95 → otomatik update + Git commit

### 4.3 Predictive Quality

**Bug Prediction Model**:
- Input: code change diff + commit message + author history
- Output: probability bu PR bug introduce eder
- Training: tüm geçmiş PR'lar + bug history
- Feature engineering:
  - Code complexity delta
  - File "hotness" (sık değişen riskli)
  - Author "bug rate" (anonymized aggregate)
  - PR size (büyük = riskli)
  - Test coverage delta
  - Time of day (Friday 4pm = riskli)
- Confidence > %80 → "Bu PR için ek QA önerilir" notification

**Test Impact Analysis**:
- Code change → hangi test'leri etkiler
- Static analysis (import graph)
- Dynamic (geçmiş coverage data)
- ML augmentation (semantic similarity)
- Result: "Bu 12 test'i koşur, diğerlerini atla" → CI 80% hızlı

**Flaky Test Detection**:
- ML model: son 100 koşu pattern analiz
- Features: pass/fail history, timing variance, error types, time of day
- Threshold > %85 confidence → "flaky" badge
- Auto-quarantine: failed flaky test build'i kırmaz, asynchronously investigated

### 4.4 Anti-Bug Garden

**Otonom Exploratory Testing**:
- Crawler agent uygulamayı dolaşır
- Her ekran, her interaction tries
- Reinforcement learning: bug bulunca reward
- Bug pattern library (XSS, SQL inj, race condition, off-by-one)

**Continuous Fuzz Testing**:
- API endpoint'leri fuzz (REST API Fuzzer, schemathesis)
- UI input field fuzz (special chars, unicode, very long)
- Performance fuzz (slow network, low memory)
- Coverage-guided (libFuzzer-style)

**Production Mirror Testing**:
- Production traffic'i shadow olarak staging'e replay
- Behavioral diff (response shape, status code)
- Catch regression before deployment
- Privacy-preserving (PII redacted)

### 4.5 Verifiable Test Results

**Cryptographic Attestation**:
```json
{
  "test_run_id": "...",
  "test_id": "...",
  "result": "passed",
  "evidence": {
    "video_hash": "sha256:...",
    "logs_hash": "sha256:...",
    "screenshots": ["sha256:..."]
  },
  "executed_at": "2030-05-15T09:30:00Z",
  "executor_attestation": {
    "tee_quote": "...",   // Intel TDX remote attestation
    "executor_pubkey": "...",
    "signature": "..."
  },
  "merkle_proof": "..."   // Inclusion in tamper-evident log
}
```

**Public Transparency Log**:
- Test result'lar (hashed) public log'a
- Sigstore Rekor tabanlı
- Müşteri kanıtlayabilir: "test gerçekten geçti, kimse manipüle etmedi"
- Compliance avantajı (denetim için)

---

## 5. Developer-Native — GitOps Everywhere

### 5.1 Tests as Code

**Senaryo = Git'te dosya**:
```gherkin
# tests/checkout/credit-card-payment.feature
@critical @smoke
Feature: Credit card checkout

  Background:
    Given user is logged in as customer@example.com

  Scenario: Successful payment
    When user adds product PROD-123 to cart
    And user proceeds to checkout
    And user enters card "4111 1111 1111 1111"
    Then payment confirmation is shown
    And order is recorded in database
```

**Git workflow**:
- Branch → modify tests → PR
- Code review (regular PR review process)
- CI runs only changed tests
- Merge → auto-deploy to production scenarios
- Rollback = git revert

**Tooling**:
- VS Code extension (Cucumber + Neurex DSL highlight)
- CLI: `neurex test run --branch feature/X`
- Git hooks (pre-commit: lint, pre-push: smoke)

### 5.2 Local Development

**Run scenarios locally**:
```bash
$ neurex dev
🟢 Local dev server: http://localhost:42000
🟢 Watching tests/...
🟢 Headless mode (use --headed to see browser)

[14:23] tests/checkout/payment.feature changed
[14:23] Running matching scenarios...
[14:24] ✓ Successful payment (3.2s)
[14:24] ✓ Declined card (2.1s)
```

**Hot reload**:
- Test değişikliği → anında re-run
- Sub-second feedback loop

**Visual regression locally**:
- Baseline screenshots in git
- Pixel diff threshold configurable
- Visual review GUI (neurex review)

### 5.3 Pull Request Workflow

**Bot integration**:
```
🤖 Neurex Bot bumped status:
✓ 247 tests passed
⚠ 3 visual changes (review at neurex.io/pr/5891)
✗ 1 test failed: checkout/decline → see trace
🧠 AI suggests: 2 new tests for /api/v3/refund endpoint
💰 AI cost: $0.42
```

**Per-PR isolated environment**:
- Spin up isolated env per PR (ephemeral)
- Run full test suite
- Tear down on PR merge/close
- Result: smoke test in real env

### 5.4 GitOps Deploy

**Tüm konfigürasyon git'te**:
```
.neurex/
├─ config.yaml       # Project settings
├─ environments.yaml # dev, staging, prod
├─ secrets.enc.yaml  # sops-encrypted
├─ schedules.yaml    # Cron jobs
├─ webhooks.yaml     # Integrations
└─ ai-prompts/       # Custom prompts
```

**ArgoCD-style**:
- Git is source of truth
- Drift detection (eğer UI'dan değiştiyse → warn)
- Auto-sync (git change → apply)

---

## 6. Veri Sahipliği & Sovereign

### 6.1 Data Portability

**Export Everything**:
```bash
$ neurex export --tenant acme --format archive
Exporting...
  ✓ Projects (12)
  ✓ Scenarios (4,231)
  ✓ Runs (89,453)
  ✓ Reports (2,891)
  ✓ Users (45)
  ✓ Integrations (8)
  ✓ AI history (anonymized)
  ✓ Audit log (10y)
  
Output: acme-export-2030-05-15.tar.gz (1.2 GB)
Includes: README.md with import instructions for self-hosted Neurex
```

**Open Format**:
- All exports in OpenAPI-validated JSON
- Re-importable into any Neurex instance
- Migration tool to/from competitors

### 6.2 Right to Be Forgotten

**Erasure Workflow**:
- User requests data deletion
- 30-day grace (legally required notice)
- Cascade delete: events anonymized (preserve aggregate stats), PII removed
- Cryptographic proof of deletion (signed receipt)
- 3rd party audit annually

### 6.3 Sovereign Cloud

**Per-Country Data Residency**:
- EU customers → eu-west-1 (Frankfurt)
- US → us-east-1 (Virginia)
- TR → tr-central-1 (Istanbul) — kendi cloud'umuz
- Çin → tencent cloud (eğer giriyorsak)
- Veri sınırı geçmez (legally enforced)

**Air-Gapped Deployment**:
- Defense, banking, government
- Tek tar.gz binary
- No phone-home
- Offline lisans (30 gün grace, sonra warning)
- Update via airgap (USB ile model güncellemesi)

---

## 7. Ekonomik Model — 2030

### 7.1 Pricing Innovation

**Mevcut**: Aylık abonelik, kullanıcı bazlı.  
**2030**: **Value-based pricing**.

| Tier | Hedef | Fiyat | Özellik |
|------|-------|-------|---------|
| **Community** | Bireysel/açık kaynak | $0 | 1 proje, ay 1k run, AI quota (limited) |
| **Startup** | < 10 kişi | $99/ay flat | Sınırsız proje, ay 50k run, AI Pro |
| **Business** | < 100 kişi | $0.10 / run + $0.05 / AI request | Pay-as-you-go, transparent |
| **Enterprise** | > 100 kişi | Custom | SSO, dedicated, SLA, mTLS |
| **OSS Forever Free** | Açık kaynak projeler | $0 | Sınırsız (verified GitHub org) |

**Yenilik**:
- Run değil, **bulunan bug başına** opsiyon (premium)
- "Bug bulamadık, fatura yok" garantisi (premium tier)
- AI cost transparent + cost-cap
- Marketplace revenue share (plugin developer'ları için)

### 7.2 Open Source Strategy

**Open-core model**:

| Bileşen | Lisans |
|---------|--------|
| Core engine (test runner) | Apache 2.0 |
| Design system | MIT |
| CLI tool | MIT |
| SDKs (JS, Python) | MIT |
| Plugin SDK | MIT |
| AI orchestrator framework | Apache 2.0 |
| Web UI | **BSL** (3 yıl sonra Apache 2.0) |
| Cloud-only features (auth, billing, analytics) | Proprietary |

**Faydası**:
- Topluluk katkısı
- Trust (kod görünür)
- Self-hosted satışı kolay
- Developer mind-share

**Community**:
- GitHub Discussions (community Q&A)
- Discord (canlı sohbet)
- Annual NeurexCon (conference)
- Office hours (monthly engineering Q&A)
- Bug bounty (HackerOne)

---

## 8. Yol Haritası — 5 Yıllık Detay

### Yıl 1 — Foundation + 9+ Quality

**Q1-Q2: Mimari konsolidasyon**
- Monorepo Turborepo
- 3 backend → 1 FastAPI
- httpOnly auth + RBAC
- Design system package
- Storybook + Chromatic

**Q3: Backend olgunlaşma**
- DDD bounded contexts
- CQRS + Event Sourcing
- Temporal workflow
- OpenTelemetry full

**Q4: Frontend devrim**
- RSC migration
- Server Actions
- Real-time presence (Liveblocks)
- i18n TR/EN/AR

### Yıl 2 — Multi-tenant SaaS

**Q1: Production grade**
- k8s + Helm + mTLS
- Vault + cert rotation
- SOC 2 Type II initiate
- Bug bounty (HackerOne)

**Q2: Multi-tenancy**
- RLS + tenant isolation
- Stripe billing
- Self-service signup
- Customer portal

**Q3: Public API + SDK**
- REST API v1 public
- JS + Python SDK
- Webhook system
- CLI tool

**Q4: Integration ecosystem**
- GitHub, GitLab, Bitbucket
- Slack, Teams, Discord
- Jira, Linear, Asana
- Public docs + status page

### Yıl 3 — AI-Native

**Q1: Multi-agent system**
- Planner, Executor, Critic, Healer agents
- MCP protocol
- LangGraph orchestration
- Agent observability

**Q2: Continual learning**
- RLHF infrastructure
- Per-tenant fine-tuning (LoRA)
- Eval pipeline (200+ golden)
- Prompt A/B testing

**Q3: Autonomous testing**
- Test gen from user stories
- Self-healing 2.0
- Predictive quality (bug ML)
- Anti-bug garden (exploratory)

**Q4: AI cost optimization**
- Intelligent LLM router
- Hybrid retrieval (BM25+vector+graph)
- Cost transparency UI
- On-device AI tier (premium)

### Yıl 4 — Frontier Features

**Q1: Local-first sync**
- CRDT sync engine
- Offline-capable
- Sub-100ms UI

**Q2: Time-travel & verifiability**
- Event sourcing core
- Merkle tree audit log
- Sigstore attestation
- Replay debugging

**Q3: Confidential computing**
- TEE (Intel TDX) support
- E2E encryption tier
- Zero-knowledge architecture
- Differential privacy

**Q4: Beyond UI testing**
- LLM agent testing
- Voice UI testing
- AR/VR testing (partner with Unity)
- Synthetic monitoring

### Yıl 5 — Ecosystem & Platform

**Q1: Plugin marketplace**
- Plugin SDK + dev tooling
- Marketplace web
- Revenue share
- 100+ plugins target

**Q2: Sovereign deployment**
- Air-gapped binary
- k8s operator
- Self-hosted parity
- Government compliance (FedRAMP path)

**Q3: Mobile + Edge**
- Native mobile apps (RN)
- Edge compute integration
- Carbon-aware scheduling
- PWA full

**Q4: Open source push**
- Core engine open source
- 1k+ GitHub stars target
- NeurexCon conference
- 10k+ community members

---

## 9. Yatırım & Resourcing

### Phase 1 (Yıl 1): Founding Team
- 1 Tech Lead (full-stack senior)
- 2 Frontend engineers
- 2 Backend engineers
- 1 DevOps / Platform
- 1 Designer (UI/UX + brand)
- 1 PM/Founder
- **Toplam**: 8 kişi

### Phase 2 (Yıl 2): Scale Team
- + 2 Frontend
- + 3 Backend (AI focus)
- + 1 Data engineer
- + 2 SRE
- + 1 Security engineer
- + 1 Designer
- + 2 Customer engineers (DevRel/Support)
- + 1 Tech writer
- **Toplam**: 21 kişi

### Phase 3 (Yıl 3): Mature
- + 5 Engineers
- + 2 Data scientists
- + 3 Sales (enterprise)
- + 2 Marketing
- + 2 Customer success
- + 1 Legal/Compliance
- + 1 People ops
- **Toplam**: ~38 kişi

### Phase 4-5 (Yıl 4-5): Growth
- 50-100 kişi
- Multiple offices (Istanbul HQ + remote globally)

### Funding Roadmap

| Round | Yıl | Tutar | Hedef |
|-------|-----|-------|-------|
| Seed | Y1 başı | $1.5M | 8 kişi, MVP |
| Series A | Y2 başı | $8M | 21 kişi, scale, first 100 customer |
| Series B | Y3-4 | $25M | 38 kişi, enterprise, expand |
| Series C | Y5 | $60M | International, mobile, platform |

**Revenue hedef**:
- Y1: $50k ARR
- Y2: $500k ARR
- Y3: $3M ARR
- Y4: $12M ARR
- Y5: $30M+ ARR

---

## 10. Riskler & Mitigations

### Technical Risk

**1. AI maliyeti yüksek**
- Mitigation: Intelligent router, cache, on-device, smart batching

**2. Test execution farm scalability**
- Mitigation: Auto-scale workers, partitioning, multi-region

**3. Multi-tenant data leak**
- Mitigation: RLS at DB level, regular pen-test, bug bounty

**4. AI hallucination prod'a sızar**
- Mitigation: Citation grounding, eval suite, human-in-loop critical actions

### Business Risk

**1. Cypress/Playwright open-source dominasyon**
- Mitigation: Open-source core, AI-native diferansiyatör

**2. Big tech entry (Microsoft Playwright Pro, Google Test Lab Plus)**
- Mitigation: Speed, focus, community, neutral platform

**3. Enterprise sales döngüsü uzun**
- Mitigation: Strong PLG (product-led growth), self-service first

**4. AI provider lock-in**
- Mitigation: Multi-provider, local opt, vendor-agnostic abstractions

### Compliance Risk

**1. GDPR violation**
- Mitigation: Privacy by design, DPO hire, regular audit

**2. AI Act EU**
- Mitigation: AI council, transparency report, explainability

**3. Country-specific data residency**
- Mitigation: Multi-region from Y2, sovereign deployment opt

---

## 11. Final North Star Metrikleri (2030)

| Boyut | Hedef |
|-------|-------|
| **Müşteri sayısı** | 10,000 paying (free 100k+) |
| **ARR** | $30M+ |
| **NPS** | 70+ |
| **Uptime SLA** | %99.99 (52 dk/yıl downtime) |
| **API p99** | <100ms |
| **Lighthouse score** | 100/100 her sayfada |
| **Open source stars** | 10,000+ (toplam) |
| **Marketplace plugin'leri** | 500+ |
| **Test execution capacity** | 1M run/gün |
| **AI requests** | 100M/ay |
| **Carbon neutral** | %100 (2027 target) |
| **SOC 2 Type II** | Certified |
| **ISO 27001** | Certified |
| **WCAG 2.2 AAA** | Selected pages |
| **Languages** | TR, EN, AR, ES, DE, FR, JA, ZH (8) |
| **Countries** | 50+ paying customers |
| **Employee count** | 75-100 |
| **Engineering blog posts** | 100+ (cumulative) |
| **Conference talks** | 30+/yıl |

---

## 12. Sonsöz — Cesaret

Bu plan **risk-tolere değil, risk-önder**.

Yapacaklarımız çoğu **henüz kimse yapmadı**:
- Multi-agent QA orchestration
- Continual learning per tenant
- Verifiable test attestation
- Confidential computing for QA
- Local-first sync for collaborative tests
- AI-native test generation
- Predictive bug ML
- Carbon-aware test scheduling
- Self-improving test garden
- Plugin marketplace ile genişleyen platform

Bunlar tek başına yapılırsa "iyi feature". Hepsi birleşince **kategori yaratıcısı**.

5 yıl sonra **"Neurex'ten önce QA platformları"** ile **"Neurex'ten sonra"** ayrı kategoriler olacak.

---

## 13. İlk 90 Gün — Eyleme Geçiş

### Hafta 1-2: Vizyon dokümantasyonu
- [ ] Bu plan'ı paylaş + tartış
- [ ] North Star metrikleri seç
- [ ] ADR'leri yaz (12 başlangıç kararı)
- [ ] Pitch deck hazırla
- [ ] Seed funding hazırlığı

### Hafta 3-6: Foundation
- [ ] Monorepo (Turborepo)
- [ ] Design system paketi ayrı
- [ ] httpOnly auth refactor
- [ ] OpenAPI → contracts paketi
- [ ] CI/CD GitHub Actions

### Hafta 7-12: Demo-able MVP
- [ ] 3 backend → 1 (Flask + AI gateway → FastAPI)
- [ ] Multi-tenant temel (tenant_id zorunlu)
- [ ] Stripe placeholder
- [ ] Status page
- [ ] Public docs taslak
- [ ] First customer demo

**Hafta 12 sonu hedefi**: Yatırımcıya canlı demo, kullanılabilir alpha.

---

**Hazır olduğunda haber ver. İlk haftadan başlayalım.**
