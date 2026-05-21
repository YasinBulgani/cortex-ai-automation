# TestwrightAI — AI Otomasyon & Yazılım Otomasyon Geliştirme Planı

> Kapsam: AI destekli test otomasyonu + sentetik veri + TSPM platformunun
> olgunluk boşluklarını kapatan, bankacılık (BDDK/KVKK) müşterisine
> satılabilir bir sonraki versiyona taşıyan 14 haftalık yol haritası.
>
> **Tarih:** 2026-Q2 · **Sahip:** Platform Core · **Durum:** v1 (yaşayan belge)

---

## 0. Yönetici Özeti

Bugün mevcut olan:
- `ai-gateway/` çoklu provider (OpenAI/Anthropic/vLLM/Ollama/Gemini/Groq/g4f)
- `backend/app/domains/ai/` — `llm_trace`, `llm_rate_limiter`, `smart_model_router`, `quality_metrics`, `knowledge_store`, `few_shot_bank`, `qa_orchestrator` (~9.3K LoC LLMOps temelleri)
- DSL semantik arama + Türkçe cross-encoder reranker
- `coverup/`, `cicd/quality_gate`, `automation_suite`, `tspm/`, `api_testing`, `ai_synthetic_data`

Eksik / Zayıf:
1. Eval harness yok — LLM çıktı kalitesini CI regresyonla yakalayacak altyapı sıfır
2. `audit/service.py` 29 satır — BDDK için yetersiz
3. `feature_flags/`, `prompts/` boştu (feature_flags bu sprint'te tamamlandı — commit `4d3d27f`)
4. Token/cost per-tenant telemetrisi + bütçe limiti yok
5. Self-healing var (`coverup`) ama PR üretme döngüsü yok
6. Flaky karantina, TIA, visual regression, a11y yok
7. PII scanner, prompt injection defans, SBOM/secret-scan CI gate yok
8. OTel trace + SLO dashboard yok

Hedef KPI (14 hafta):

| Metrik | Bugün | Hedef |
|---|---|---|
| LLM test üretim isabet (eval) | Ölçülmüyor | ≥ %92 |
| Flaky oran | ~%8–12 | ≤ %3 |
| CI `test-full` süresi | ~20 dk | ≤ 8 dk (TIA ile) |
| LLM maliyet/tenant görünürlük | Yok | Günlük dashboard + alarm |
| PII leakage testi | Yok | %100 sentetik çıktıda otomatik |
| Mean time to fix flaky | Gün+ | < 1 saat (auto-PR) |

---

## 1. Prensipler

1. **Var olanın üstüne inşa et** — `ai-gateway`, `llm_trace`, `coverup` hazır; yeniden yazma yok.
2. **Feature flag arkasında** — `feature_flags/` artık hazır (commit `4d3d27f`); tüm yeni epic'ler canary → %100.
3. **Opsiyonel bağımlılık** disiplini — paket yoksa pass-through, prod kırılmaz (reranker örneği).
4. **Bankacılık uyumluluğu ilk sınıf vatandaş** — her epic "compliance notu" taşır.
5. **Eval-driven development** — yeni prompt/model/ajan → önce eval set'ine örnek.
6. **Ölçülmeyen gelişme yok** — KPI + Prometheus + alarm.

---

## 2. Dalga Planı (14 Hafta)

| Dalga | Hafta | Tema | Ana Çıktı |
|---|---|---|---|
| **D1** | 1–2 | LLMOps sağlamlaştırma | Eval harness + cost telemetri + prompt versiyonlama |
| **D2** | 3–6 | Test otomasyon olgunluğu | Self-healing auto-PR + flaky karantina + TIA + visual + a11y |
| **D3** | 7–10 | Güvenlik & Uyum | PII scanner + prompt injection + audit hash-chain + SBOM + RBAC |
| **D4** | 11–14 | Ürün & Benimseme | PR bot + marketplace + ROI + migration asistanı |
| Cross | 1–14 | Observability | OTel + SLO dashboard (inkremental) |

---

## 3. Dalga 1 — LLMOps (Hafta 1–2)

### E1.0 · Feature Flags Çekirdeği ✅ Tamamlandı (commit `4d3d27f`)
Redis-backed + memory fallback, deterministik canary, fail-closed default,
audit sink. 17 unit test yeşil.

### E1.1 · LLM Eval Harness (M · P0) — bu sprint
**Amaç:** DSL üretimi, test case üretimi, reranker çıktısı için golden set regresyonu.

**Başarı:**
- `make eval` 3 dk altında 3 suite koşar
- CI'da prompt/model değişince eşik altında düşüş → PR kırmızı
- Baseline: precision@1, precision@5, MRR, p95 latency

**Dosya iskeleti:**
```
backend/app/domains/evals/
  __init__.py
  schemas.py           # EvalCase, Suite, Result, ScorerResult
  scorers/
    base.py            # Protocol + Result dataclass
    exact_match.py
    retrieval_metrics.py  # P@k, MRR, recall@k
  adapters/
    base.py
    dsl_retrieval.py   # alias_index.search wrapper
  loader.py            # YAML → Suite
  runner.py            # orchestrator (concurrent, budgeted)
  reporting.py         # JSON + HTML
  router.py            # REST (admin)
  cli.py               # python -m app.domains.evals.cli --suite X
  suites/
    dsl_retrieval.yaml # ~15 TR/EN golden case
    reranker.yaml
backend/tests/eval/
  test_scorers.py
  test_loader.py
  test_runner.py
```

### E1.2 · Token & Cost Telemetri (M · P0)
`ai_usage_events` tablosu, per-tenant günlük bütçe, Prometheus metrik.
`llm_trace.py` ve `llm_rate_limiter.py` üstüne inşa.

### E1.3 · Prompt Versiyonlama (S · P1)
`prompts/` modülünü doldur — registry + canary % + A/B.

---

## 4. Dalga 2 — Test Otomasyon Olgunluğu (3–6)

| # | Epic | Efor | Öncelik |
|---|---|---|---|
| E2.1 | Self-healing locator + auto-PR (`coverup` üstüne) | L | P0 |
| E2.2 | Flaky karantina + otomatik JIRA | M | P0 |
| E2.3 | Test Impact Analysis (PR diff → ilgili testler) | L | P1 |
| E2.4 | Visual regression (Playwright + pixelmatch) | S | P2 |
| E2.5 | Accessibility (axe-core fixture) | S | P2 |

---

## 5. Dalga 3 — Güvenlik & Uyum (7–10)

| # | Epic | Efor | Öncelik |
|---|---|---|---|
| E3.1 | PII / sentetik veri leakage scanner (TCKN, IBAN, k-anonymity) | M | P0 |
| E3.2 | Prompt injection defans katmanı | M | P0 |
| E3.3 | Audit hash-chain + WORM | M | P0 |
| E3.4 | SBOM + secret scanning CI gate | S | P1 |
| E3.5 | RBAC + Segregation of Duties | M | P1 |
| E3.6 | KVKK/BDDK compliance mapping | S | P2 |

---

## 6. Dalga 4 — Ürün & Benimseme (11–14)

| # | Epic | Efor | Öncelik |
|---|---|---|---|
| E4.1 | Shift-left PR bot (TIA + LLM öneri) | M | P1 |
| E4.2 | Banking marketplace (EFT, FAST, KKB vb. template) | M | P2 |
| E4.3 | ROI dashboard (PDF haftalık) | S | P2 |
| E4.4 | Migration asistanı (Selenium/Katalon → TW-DSL) | L | P3 |

Cross-cutting **E4.5 · OTel + SLO** — D1'den başlayıp inkremental.

---

## 7. Cross-Cutting

### 7.1 Test stratejisi
- Unit %80 coverage (service layer)
- Integration: happy + 2 failure path
- Eval: ≥5 yeni case her AI PR'ında
- E2E: kritik flow'lar

### 7.2 Branch politikası
- `main` protected, 1 review + CI yeşil + SBOM clean
- Feature: `feat/<dalga>-<epic>-<kısa-ad>` (ör. `feat/d1-e1.1-eval-harness`)
- Her PR: eval (varsa), SBOM, lint, unit, integration

### 7.3 Feature flags ✅
`feature_flags/` hazır (commit `4d3d27f`). Tüm yeni epic'ler varsayılan
kapalı → canary tenant → %100.

### 7.4 Dokümantasyon
- Her epic `docs/epics/<id>.md` (ADR)
- `CHANGELOG.md`
- `docs/user-guide/`

---

## 8. Takvim (ASCII Gantt)

```
Hafta:           1  2  3  4  5  6  7  8  9 10 11 12 13 14
E1.0 FFlags      ██  ✅ tamamlandı (4d3d27f)
E1.1 Eval        ██████         ← burada
E1.2 Cost        ██████
E1.3 PromptV.       ████
E2.1 Self-heal         ████████████
E2.2 Flaky             ██████
E2.3 TIA                  ████████
E2.4 Visual                  ████
E2.5 A11y                    ████
E3.1 PII                         ██████
E3.2 Inj                         ██████
E3.3 Audit                         ██████
E3.4 SBOM                                ████
E3.5 RBAC                                ██████
E3.6 Comp                                    ████
E4.1 PRBot                                      ██████
E4.2 Market                                       ██████
E4.3 ROI                                             ████
E4.4 Migr                                                ██████
E4.5 OTel       ██████████████████████████████████████████
```

---

## 9. Kaynak

~163 adam-gün / 315 kapasite (%52). Geri kalan %48 bug fix + refactor + iletişim.

---

## 10. Risk

| # | Risk | Olasılık | Etki | Azaltma |
|---|---|---|---|---|
| R1 | Eval golden set bakımı aksarsa | Y | Y | PR template'te zorunlu + aylık review |
| R2 | Self-heal yanlış PR üretip merge olursa | O | Y | Branch protection + confidence<0.8 → draft |
| R3 | vLLM stabilitesi | Y | O | Healthcheck + OpenAI fallback |
| R4 | Token maliyeti yüksek | O | Y | E1.2 bütçe erken devrede |
| R5 | KVKK denetimi erken | D | Y | Compliance mapping D3 |
| R6 | Flaky karantina bug salar | O | O | Max 5 gün sonra hard fail |

---

## 11. Açık Sorular

1. On-prem LLM baseline: hangi model (Qwen2.5-72B / Llama-3.3-70B / TR fine-tune)?
2. Eval framework: kendi runner mı, promptfoo/deepeval adaptörü mü?
3. Visual regression storage: S3 mi, MinIO self-host mu?
4. GitHub App mi PAT mi (self-heal için)?
5. Marketplace template içerik sahibi?
6. KVKK denetim tarihi?

---

## 12. Hafta 1 İlerleme

- [x] E1.0 Feature Flags (commit `4d3d27f`)
- [ ] E1.1 Eval Harness iskeleti → **aktif**
- [ ] E1.1 DSL retrieval golden set (ilk 15 case)
- [ ] E1.1 CI workflow
- [ ] E1.2 Token telemetri tasarım kararları

---

*v1 · yaşayan belge — her sprint retro'sunda güncellenir*
