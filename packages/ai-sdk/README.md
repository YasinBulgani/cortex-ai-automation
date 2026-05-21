# @neurex/ai-sdk

Neurex'in AI altyapısı — sağlayıcı agnostik LLM router, prompt registry,
gözlemlenebilirlik ve guardrails.

## Modüller

| Modül | Açıklama |
|-------|----------|
| `providers` | Anthropic / Groq / Gemini / Ollama implementasyonları + base sınıf |
| `router`    | Intent + maliyet + latency'e göre sağlayıcı seçimi, fallback chain |
| `prompts`   | Versiyonlanmış prompt template'leri, registry |
| `tools`     | MCP uyumlu tool çağrı altyapısı |
| `observability` | Telemetry sink'leri, cost tracker (tenant/user başı) |
| `guardrails`    | PII redaction, prompt injection tespiti |
| `evals`         | Golden dataset runner + 12 assertion türü |

## Hızlı başlangıç

```ts
import {
  AnthropicProvider, GroqProvider, OllamaProvider,
  IntelligentRouter,
  defaultRegistry, registerBuiltinPrompts, renderPrompt,
  redactPII, detectInjection,
  defaultTelemetry, ConsoleSink, CostTracker, withTelemetry,
} from "@neurex/ai-sdk";

// Provider'ları kur
const router = new IntelligentRouter([
  new AnthropicProvider({ api_key: process.env.ANTHROPIC_API_KEY }),
  new GroqProvider({ api_key: process.env.GROQ_API_KEY }),
  new OllamaProvider(),
]);

// Telemetry + cost tracker
const tracker = new CostTracker();
defaultTelemetry.add(new ConsoleSink());
defaultTelemetry.add(tracker);

// Prompt registry
registerBuiltinPrompts();
const tpl = defaultRegistry.get("scenario.generate-bdd")!;
const prompt = renderPrompt(tpl, {
  project_name: "Banka Kartı",
  domain_context: "Sıfır bilgi giriş akışı",
  requirement: "Kullanıcı 3 yanlış denemede kilitlenir.",
});

// Guardrails — request gelmeden filtrele
const guard = detectInjection(prompt);
if (guard.is_injection) throw new Error("Injection olasılığı: " + guard.score);

// Tek çağrı
const res = await withTelemetry(
  { provider: "anthropic", tenant_id: "t1", intent: "scenario_generation" },
  () => router.complete({
    intent: "scenario_generation",
    messages: [{ role: "user", content: prompt }],
    tenant_id: "t1",
    quality_preference: "high",
  }),
);

console.log(res.content);
console.log("Tenant maliyeti:", tracker.forTenant("t1").total_usd);
```

## Provider tier'ları

| Tier | Sağlayıcı | Kullanım |
|------|-----------|----------|
| Tier 1 — hızlı/ucuz | Groq Llama 8B | Intent classification, form autocomplete |
| Tier 2 — denge | Gemini Flash | Test step suggestion, orta kompleks |
| Tier 3 — kaliteli | Claude Sonnet/Opus | Kod üretimi, kök neden, BDD |
| Tier 4 — lokal | Ollama Qwen / Llama | Gizli veri (PII), air-gapped |

Router intent → tier mapping'ini `INTENT_TIER_MAP` üzerinden uygular,
`latency_sla_ms` ile yavaş sağlayıcıları filtreler, başarısızlıkta sıradakine
düşer. Tüm provider çağrıları **circuit breaker** ile sarmalanır — `5`
ardışık fail sonrası `30s` boyunca "open" olur.

## Guardrails

### PII redaction
Türkçe + uluslararası kalıpları regex tabanlı maskelenir:
TCKN, IBAN, e-posta, GSM, kredi kartı, IP, JWT, API anahtarları (sk-ant-/sk-/AKIA).
Production'da `Microsoft Presidio` benzeri ML-tabanlı çözüm tercih edilir;
mevcut katman sıfır-dep baseline'dır.

### Prompt injection
Heuristic 0..1 skor — `0.5` üstü = "injection". TR + EN kalıpları:
- "ignore previous instructions" / "önceki talimatları unut"
- Role bypass (DAN mode, "you are now root")
- Sistem prompt sızıntı talebi
- Dosya/credential exfil kalıpları

## Observability

`TelemetrySink` interface; built-in sink'ler: `ConsoleSink`, `BufferSink`,
`CostTracker`. `withTelemetry()` wrapper hem başarıyı hem hatayı
kaydeder, response içinde gelen `cost_usd` ile tenant aggregate'i besler.

Tenant başı budget kontrolü:
```ts
if (tracker.isOverBudget("t1", 100)) throw new Error("budget aşıldı");
```

## Eval suite

Prompt regresyon kontrolü için golden case runner:

```ts
import {
  EvalRunner,
  scenarioGenerateBddCases,
  analyzeTestFailureCases,
} from "@neurex/ai-sdk/evals";

const runner = new EvalRunner(req => router.complete({ intent: "scenario_generation", ...req }));
const summary = await runner.run(
  [...scenarioGenerateBddCases, ...analyzeTestFailureCases],
  { concurrency: 2, verbose: true },
);

console.log(`Pass rate: ${(summary.pass_rate * 100).toFixed(1)}%`);
console.log(`Total cost: $${summary.total_cost_usd.toFixed(4)}`);
if (summary.failed > 0) process.exit(1);
```

Desteklenen assertion türleri:
`contains`, `not_contains`, `matches` (regex), `json_valid`, `json_has_keys`,
`min_length`, `max_length`, `max_tokens`, `max_latency_ms`, `max_cost_usd`,
`custom` (kullanıcı fn). Code-fence içindeki JSON otomatik parse edilir.

Filtreleme: `tags_include`, `tags_exclude`, `case_ids`. `skip: { reason }`
ile case devre dışı bırakılabilir (API key yok vb.).

## Test

```bash
npm test -w @neurex/ai-sdk
```
