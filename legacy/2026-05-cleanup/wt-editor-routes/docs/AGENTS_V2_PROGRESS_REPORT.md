# Agents v2 — Yapılan İşler Raporu

> **Tarih**: 2026-04-19 · **Branch**: `feat/design-pass-p1-foundation`  
> **Kapsam**: LLM otomasyon (1. öncelik) — 9 ajanlı state machine + API + FE

---

## 📊 Özet

| Kategori | Dosya | Satır | Test |
|---|---|---|---|
| Backend `agents/v2/` | 55 `.py` | **6.513** | 52 pass |
| Frontend | 2 (tsx + ts) | **~800** | ts-check OK |
| Alembic migration | 1 | 150 | — |
| FastAPI router mount | +1 endpoint grup | 6 endpoint | — |

**Toplam yeni kod**: ~7.500 satır  
**Pipeline durumu**: uçtan uca çalışıyor (mock LLM + gerçek locator + gerçek JUnit)  
**Eksik**: Langfuse entegrasyonu, pgvector query, gerçek git/PR auto-merge

---

## 🏗️ Mimari

```
FE (Next.js)                  BE (FastAPI)                     External
─────────────                ──────────────                    ────────

/p/{id}/sifir-bilgi  ──POST──► /api/v1/agents/v2/run
  ▲                             │
  │                             ▼                         ┌─────────┐
  │                       [Run Store]                     │ai-gateway│
  │                             │                         │ :8080   │
  │                             ▼                    ┌───►│ (Ollama,│
  │ SSE /stream ◄──[Event Pub]─[_execute_manual]────┘    │  Groq,  │
  │                             │                         │  Gemini)│
  │                             │                         └─────────┘
  │                             ▼
  │   ┌──────────┬──────────┬───┴──────┬──────────┐
  │   │ Analyst  │ Explorer │ Locator  │ Scenario │
  │   └──────────┴──────────┴──────────┴──────────┘
  │   ┌──────────┬──────────┬──────────┬──────────┬──────────┐
  │   │  Coder   │  Runner  │  Healer  │ Reviewer │ Reporter │
  │   └──────────┴──────────┴──────────┴──────────┴──────────┘
  │                             │
  └──GET /runs/{id}────────────┘
```

---

## 📁 Dizin Yapısı

```
backend/app/domains/agents/v2/
├── __init__.py                        # Public API
├── state.py                           # LangGraph state (TypedDict)
├── config.py                          # Model routing + feature flags
├── orchestrator.py                    # LangGraph state machine + fallback
├── router.py                          # FastAPI 6 endpoint
├── api_schemas.py                     # Request/Response Pydantic
├── run_store.py                       # In-memory run + SSE pub/sub
│
├── schemas/                           # Pydantic v2 domain modeller
│   ├── intent.py                      # IntentGraph (Analyst çıktısı)
│   ├── app_map.py                     # AppMap (Explorer)
│   ├── locator.py                     # ElementCard + LocatorSuggestion
│   ├── scenario.py                    # GherkinFeature (roundtrip)
│   ├── code.py                        # GeneratedCode
│   ├── run.py                         # RunResult + FailureContext
│   ├── heal.py                        # FixHypothesis + HealingResult
│   ├── review.py                      # ReviewResult + ReviewAction
│   └── report.py                      # ReportResult
│
├── prompts/                           # LLM sistem prompt'ları
│   ├── analyst.py                     # Intent Graph üretimi (JSON)
│   ├── scenario.py                    # Gherkin üretimi
│   ├── coder.py                       # Playwright TS üretimi
│   ├── locator.py                     # AI XPath üretimi
│   ├── healer.py                      # Classify + fix hypothesis
│   ├── reviewer.py                    # Kalite değerlendirme
│   └── reporter.py                    # TR yönetim özeti
│
├── agents/                            # 9 ajan (BaseAgent abstract)
│   ├── base.py                        # trace + cost tracking
│   ├── analyst.py                     # PDF/URL → IntentGraph
│   ├── explorer.py                    # Playwright BFS crawl
│   ├── locator.py                     # 5-katman pipeline wrapper
│   ├── scenario.py                    # DSL-grounded Gherkin
│   ├── coder.py                       # Playwright TS üretir
│   ├── runner.py                      # Sandbox koşturucu
│   ├── healer.py                      # Self-heal + auto-PR
│   ├── reviewer.py                    # LLM code review
│   └── reporter.py                    # TR özet
│
├── tools/                             # Ajanların kullanabildiği araçlar
│   ├── ai_gateway.py                  # Async httpx client + retry + cost
│   ├── intake.py                      # PDF/DOCX/URL/Swagger/Postman parse
│   ├── browser.py                     # Playwright wrapper + allowlist
│   ├── gherkin_parser.py              # Gherkin roundtrip parser
│   ├── dsl_grounding.py               # DSL catalog lookup
│   ├── test_runner.py                 # subprocess npx playwright + JUnit
│   └── locator/                       # 5-katmanlı pipeline
│       ├── snapshot.py                # Katman 1: DOM + aria + ss
│       ├── extraction.py              # Katman 2: element cards (JS + bs4)
│       ├── generation.py              # Katman 3: 5 multi-strategy
│       ├── scoring.py                 # Katman 4: stability score
│       ├── verification.py            # Playwright count verify
│       ├── registry.py                # Katman 5: in-memory registry
│       └── pipeline.py                # Orchestrator (run + run_offline)
│
└── tests/                             # 52 pytest (0.58s)
    ├── test_schemas.py                # Pydantic validation
    ├── test_gherkin_parser.py         # TR/EN/Outline parser
    ├── test_locator_pipeline.py       # 5 katman + strategy + scoring
    ├── test_ai_gateway.py             # httpx mock + retry + cost
    └── test_run_store_and_api.py      # SSE pub/sub + FastAPI testclient
```

---

## 🧪 Test Sonuçları

```
pytest app/domains/agents/v2/tests/ -q
  52 passed in 0.58s  ✅
```

Kapsam:
- Pydantic schema doğrulaması (10+ test)
- Gherkin parser roundtrip (TR + EN + Outline + fence)
- Locator pipeline 5 katman (extract → generate → score → aggregate → registry)
- AI Gateway: retry on 503, raise on 400, JSON parse, cost calculation
- RunStore: pub/sub + filter + status transitions
- API: 400 validation, 202 queue, 404 not found, health

---

## 🔌 API Endpointler

`/api/v1/agents/v2/` prefix ile:

| Method | Path | Amaç |
|---|---|---|
| POST | `/run` | Yeni pipeline başlat (async, 202 + run_id) |
| GET | `/runs` | Liste (filter: project_id, page) |
| GET | `/runs/{run_id}` | Detay (tam state snapshot) |
| GET | `/runs/{run_id}/stream` | **SSE** canlı event stream |
| POST | `/runs/{run_id}/cancel` | Çalışan pipeline'ı iptal |
| GET | `/health` | Ajan + gateway sağlığı |

Tüm endpointler Swagger/OpenAPI'de otomatik görünür (`/docs`).

---

## 🎨 Frontend

### Yeni Dosyalar

1. **`apps/web/lib/agents-v2-api.ts`** (200 satır)
   - Async API client — startAgentRun, getAgentRun, listAgentRuns, cancelAgentRun
   - `subscribeAgentRun()` — SSE EventSource wrapper (9 event tipi)

2. **`apps/web/app/(dashboard)/p/[projectId]/sifir-bilgi/page.tsx`** (560 satır)
   - 4 modlu form: URL / Metin / Swagger / Dosya
   - Gelişmiş ayarlar collapsible
   - 9 ajanlı canlı progress (status ikonları + cost/token)
   - Nihai özet: Intent Graph, senaryolar, Reviewer kararı, TR rapor

TypeScript strict mode'da hatasız (`tsc --noEmit`).

---

## 🔑 Öne Çıkan Mühendislik Kararları

### 1. AI Gateway — Mevcut Altyapıyla Uyum
`backend/app/domains/ai/gateway_client.py` zaten **sync httpx** client'tı. Agents/v2 LangGraph async olduğu için, yeni `tools/ai_gateway.py` async wrapper yazıldı. **Aynı `POST /ai/complete` endpoint'i** kullanılıyor; provider fallback (Groq→Gemini→Ollama→g4f) değişmeden çalışıyor.

### 2. 5-Katmanlı Locator — Deterministik + AI Hibrit
- Katman 1-4 **tamamen deterministik** (LLM yok): DOM snapshot + element extraction + 5 strateji + stability scoring
- Katman 5 (registry) in-memory; Alembic migration hazır
- AI XPath **opsiyonel** — sadece `enable_ai_xpath=true` iken (pahalı)
- **Offline mode** var — Playwright olmadan HTML'den test edilebiliyor

### 3. Gherkin Parser — TR/EN Çift Dil
- `Özellik`/`Feature`, `Senaryo`/`Scenario`, `Verilen`/`Given` hepsi destekleniyor
- Outline + Examples + Background + data_table + doc_string
- `to_gherkin_text()` roundtrip: parse → yeniden üret → yeniden parse → aynı sonuç

### 4. SSE Streaming — Her Ajan Event'i
Her ajan başlangıcı/bitişi/hatası Redis'e değil, in-memory pub/sub'a publish ediliyor. FE EventSource ile dinliyor. Faz 4'te Redis Streams'e taşınabilir.

### 5. LangGraph — Graceful Degradation
LangGraph kurulu değilse orchestrator `_execute_manual` fallback'e düşüyor. Pipeline yine çalışıyor (biraz daha az elegant, ama aynı sonuç).

### 6. State Dict Compatibility
Tüm Pydantic modeller `to_state_dict()` metoduyla LangGraph'in TypedDict schema'sına **birebir uyumlu** dict üretiyor. Bu sayede:
- LangGraph node'ları dict ile çalışıyor (performans)
- Her ajan içinde validation için Pydantic (güvenlik)
- Serialize/deserialize sorunsuz

---

## 🎯 Şimdi Çalışan Akış

```
1. Kullanıcı /sifir-bilgi sayfasında URL yapıştırır.
2. "Başlat" → POST /api/v1/agents/v2/run
3. Backend run_id üretir, BackgroundTask başlatır
4. SSE akışı açılır; kullanıcı 9 ajanı görür:
   ┌─ ○ Analyst: pending
   ├─ ○ Explorer: pending
   ...
5. Analyst LLM'e analyze_document task'ı → IntentGraph JSON
6. Explorer Playwright ile BFS crawl (opsiyonel)
7. Locator 5 katman → her element için suggestions
8. Scenario → Gherkin üret (DSL-grounded) → .feature yaz
9. Coder → Playwright TS dosyaları üret
10. Runner → npx playwright test → JUnit parse
11. Healer (fail varsa) → classify + 3 hypothesis
12. Reviewer → LLM code review
13. Reporter → TR yönetim özeti
14. SSE 'completed' event → FE özet gösterir
```

Token + cost her adımda toplanıyor, FE'de canlı.

---

## ⏳ Sıradaki Adımlar (Plan'dan)

### Faz 2 Sprint 5 (Hafta 10-11) — Vision + Locator Prod
- [ ] Ollama `qwen2-vl:7b` provider ai-gateway'e ekle
- [ ] Set-of-Mark prompting (screenshot + numaralı overlay)
- [ ] Locator registry Postgres backend (alembic migration zaten var)
- [ ] pgvector embedding similarity search
- [ ] Explorer ↔ Locator sıkı entegrasyon (Locator agent gerçek page üzerinde koşar)

### Faz 2 Sprint 6 (Hafta 12-13) — Self-Healing Prod
- [ ] Healer sandbox Docker execute (şu an stub)
- [ ] Git branch + patch + auto-PR (GitHub API)
- [ ] Fail context gerçek DOM diff
- [ ] LangFuse trace entegrasyonu

### Faz 2 Sprint 7 — Test Türleri
- [ ] k6 generator (Performance)
- [ ] axe-core + Playwright generator (A11y)
- [ ] OWASP ZAP config generator (Security)
- [ ] Pact contract generator

### Faz 3 — Observability
- [ ] LangFuse self-host
- [ ] OpenTelemetry trace (FastAPI + httpx + Playwright)
- [ ] Grafana dashboard (ajan başına latency + cost)
- [ ] Prometheus custom metrics (`twai_agent_*`)

### Faz 4 — CI/CD
- [ ] Alembic migration'ı prod'a uygula
- [ ] Ephemeral preview env per PR
- [ ] Canary + auto-rollback

---

## 🛡️ Güvenlik

- **URL allowlist** — Explorer sadece whitelistlenmiş host'lara gider (BrowserSecurityError)
- **Cost guard** — `max_cost_usd_per_run: 2.0` default
- **HITL** — Kritik test adlarında (`ödeme`, `transfer`, `production`) auto-fix disabled
- **Sandbox network** — Playwright MCP allowlist ile izole
- **Internal key** — Gateway çağrısı `X-Internal-Key` header ile auth
- **PII filter** — (prompt governance Faz 6'da, şu an temel PII maskelemi yok)

---

## 💰 Maliyet

**Lokal model** (Ollama Qwen 2.5) kullanıldığında pipeline başına **$0.00**.  
**Bulut fallback** (Gemini Flash) aktif olursa tahmini **~$0.02–0.05** / pipeline.

Her çağrıda token + cost takibi:
- `state["tokens_used"]` — toplam (input + output)
- `state["cost_usd"]` — USD
- `state["llm_calls_count"]` — çağrı sayısı
- FE canlı gösterir.

---

## 📦 Stage Durumu (Git)

Tüm değişiklikler `git add`'lendi, commit bekliyor:
- 55 `.py` dosyası (agents/v2)
- 1 Alembic migration
- 1 `main.py` modifikasyonu (router mount)
- 1 `page.tsx` + 1 `agents-v2-api.ts`

**Commit hazır**. Kullanıcı isteği ile tek atomik commit atılacak.

---

*Rapor sonu — 2026-04-19 08:30 UTC*
