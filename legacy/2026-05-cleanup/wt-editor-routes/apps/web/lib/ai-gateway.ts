/**
 * Nexus QA — AI Gateway Client
 * Tüm AI çağrıları bu client üzerinden geçer.
 * Groq → Gemini → Ollama → g4f fallback zinciri otomatik yönetilir.
 */

const GATEWAY_BASE =
  process.env.NEXT_PUBLIC_AI_GATEWAY_BASE?.replace(/\/$/, "") ||
  "http://127.0.0.1:8080";

const INTERNAL_KEY = process.env.AI_GATEWAY_INTERNAL_KEY;

function assertServerGatewayAccess(): string {
  if (typeof window !== "undefined") {
    throw new Error("Tarayicidan dogrudan AI Gateway cagrisi devre disi. Backend API uzerinden cagin.");
  }
  if (!INTERNAL_KEY) {
    throw new Error("AI Gateway internal key sunucu tarafinda yapilandirilmamis.");
  }
  return INTERNAL_KEY;
}

export type TaskType =
  | "analyze_document"
  | "generate_test_cases"
  | "generate_gherkin"
  | "generate_java_steps"
  | "generate_playwright"
  | "suggest_regression"
  | "debug_test"
  | "chat";

export interface AIMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface AIGatewayRequest {
  task_type?: TaskType;
  messages: AIMessage[];
  temperature?: number;
  max_tokens?: number;
  project_id?: string;
}

export interface AIGatewayResponse {
  content: string;
  provider_used: string;
  model_used: string;
  latency_ms: number;
  cached: boolean;
  tokens_used: number;
  attempts: Array<{
    provider: string;
    success: boolean;
    error?: string;
    latency_ms: number;
  }>;
}

export interface ProviderHealth {
  status: "healthy" | "degraded";
  providers: Record<string, boolean>;
  version: string;
}

/**
 * AI Gateway'e istek gönder — tüm AI çağrıları buradan geçmeli.
 */
export async function aiComplete(
  req: AIGatewayRequest
): Promise<AIGatewayResponse> {
  const internalKey = assertServerGatewayAccess();
  const res = await fetch(`${GATEWAY_BASE}/ai/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Key": internalKey,
    },
    body: JSON.stringify({
      task_type: req.task_type || "chat",
      messages: req.messages,
      temperature: req.temperature ?? 0.7,
      max_tokens: req.max_tokens ?? 4000,
      project_id: req.project_id,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const json = JSON.parse(text);
      detail = json.detail?.error || json.detail || text;
    } catch {}
    throw new Error(`AI Gateway hatası (${res.status}): ${detail}`);
  }

  return res.json() as Promise<AIGatewayResponse>;
}

/**
 * AI sağlayıcıları sağlık durumu.
 */
export async function getGatewayHealth(): Promise<ProviderHealth> {
  const res = await fetch(`${GATEWAY_BASE}/ai/health`);
  if (!res.ok) throw new Error("AI Gateway erişilemiyor");
  return res.json() as Promise<ProviderHealth>;
}

// ── Yüksek seviyeli yardımcı fonksiyonlar ─────────────────────────────────

/**
 * Analiz dokümanını AI'ya gönder → modül analizi JSON döndür.
 */
export async function analyzeDocument(
  docText: string,
  projectId: string,
  extraInstructions?: string
): Promise<string> {
  const userContent = extraInstructions
    ? `${docText}\n\n---\nEk Talimatlar:\n${extraInstructions}`
    : docText;

  const res = await aiComplete({
    task_type: "analyze_document",
    messages: [{ role: "user", content: userContent }],
    temperature: 0.3,    // Analiz için düşük — tutarlılık önemli
    max_tokens: 4000,
    project_id: projectId,
  });
  return res.content;
}

/**
 * Modül için test case'leri üret.
 */
export async function generateTestCases(
  moduleInfo: string,
  projectId: string
): Promise<string> {
  const res = await aiComplete({
    task_type: "generate_test_cases",
    messages: [
      {
        role: "user",
        content: `Aşağıdaki modül için kapsamlı test case'leri üret:\n\n${moduleInfo}`,
      },
    ],
    temperature: 0.5,
    max_tokens: 4000,
    project_id: projectId,
  });
  return res.content;
}

/**
 * Test case'lerden Gherkin feature dosyası üret.
 */
export async function generateGherkin(
  testCases: string,
  featureName: string,
  projectId: string,
  language: "tr" | "en" = "tr"
): Promise<string> {
  const res = await aiComplete({
    task_type: "generate_gherkin",
    messages: [
      {
        role: "user",
        content: `Feature adı: ${featureName}\nDil: ${language === "tr" ? "Türkçe" : "English"}\n\nTest case'ler:\n${testCases}`,
      },
    ],
    temperature: 0.4,
    max_tokens: 4000,
    project_id: projectId,
  });
  return res.content;
}

/**
 * Gherkin senaryoları için regresyon seti öner.
 */
export async function suggestRegression(
  scenarios: string,
  projectId: string
): Promise<string> {
  const res = await aiComplete({
    task_type: "suggest_regression",
    messages: [
      {
        role: "user",
        content: `Aşağıdaki test senaryoları için optimal regresyon seti öner:\n\n${scenarios}`,
      },
    ],
    temperature: 0.3,
    max_tokens: 3000,
    project_id: projectId,
  });
  return res.content;
}

/**
 * Java NexusQA step definitions üret.
 */
export async function generateJavaSteps(
  gherkinContent: string,
  projectId: string
): Promise<string> {
  const res = await aiComplete({
    task_type: "generate_java_steps",
    messages: [
      {
        role: "user",
        content: `Aşağıdaki Gherkin senaryoları için Java step definition'ları üret:\n\n${gherkinContent}`,
      },
    ],
    temperature: 0.3,
    max_tokens: 4000,
    project_id: projectId,
  });
  return res.content;
}

/**
 * Playwright TypeScript testi üret.
 */
export async function generatePlaywright(
  testCase: string,
  projectId: string
): Promise<string> {
  const res = await aiComplete({
    task_type: "generate_playwright",
    messages: [
      {
        role: "user",
        content: `Aşağıdaki test case için Playwright TypeScript testi üret:\n\n${testCase}`,
      },
    ],
    temperature: 0.4,
    max_tokens: 4000,
    project_id: projectId,
  });
  return res.content;
}
