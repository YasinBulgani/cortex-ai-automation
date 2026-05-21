/**
 * Neurex QA — AI Gateway Client
 * Tüm AI çağrıları bu client üzerinden geçer.
 * Groq → Gemini → Ollama → g4f fallback zinciri otomatik yönetilir.
 */

const BROWSER_PROXY_BASE = "/api/ai";

function isBrowserRuntime(): boolean {
  return typeof window !== "undefined";
}

function serverGatewayBase(): string {
  return (process.env.AI_GATEWAY_BASE_URL || "http://127.0.0.1:8080").replace(/\/$/, "");
}

function gatewayUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (isBrowserRuntime()) {
    return `${BROWSER_PROXY_BASE}${normalizedPath}`;
  }
  return `${serverGatewayBase()}/ai${normalizedPath}`;
}

function assertServerGatewayAccess(): string {
  const internalKey = process.env.GATEWAY_INTERNAL_KEY || "";
  if (!internalKey) {
    throw new Error("GATEWAY_INTERNAL_KEY ortam değişkeni tanımlı değil");
  }
  return internalKey;
}

function gatewayHeaders(options: { json?: boolean; internal?: boolean } = {}): Record<string, string> {
  const { json = true, internal = false } = options;
  const headers: Record<string, string> = {};
  if (json) headers["Content-Type"] = "application/json";
  if (internal && !isBrowserRuntime()) {
    headers["X-Internal-Key"] = assertServerGatewayAccess();
  }
  return headers;
}

export type TaskType =
  | "analyze_document"
  | "generate_test_cases"
  | "generate_gherkin"
  | "generate_java_steps"
  | "generate_playwright"
  | "suggest_regression"
  | "debug_test"
  | "chat"
  | "nexus_code_analyze";

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
  schema_version?: string;
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
  const taskType = req.task_type || "chat";
  const schemaVersion =
    req.schema_version ||
    (taskType === "analyze_document" ||
    taskType === "generate_test_cases" ||
    taskType === "suggest_regression" ||
    taskType === "debug_test"
      ? "v1"
      : undefined);
  const res = await fetch(gatewayUrl("/complete"), {
    method: "POST",
    headers: gatewayHeaders({ internal: true }),
    body: JSON.stringify({
      task_type: taskType,
      messages: req.messages,
      temperature: req.temperature ?? 0.7,
      max_tokens: req.max_tokens ?? 4000,
      project_id: req.project_id,
      schema_version: schemaVersion,
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
  const res = await fetch(gatewayUrl("/health"));
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

export interface NexusCodeInput {
  mode: "code" | "web";
  content: string;        // kod metni veya URL + açıklama
  domain?: "banking" | "finance" | "general";
  extraContext?: string;  // rol, yetki, iş kuralları
}

/**
 * Neurex Code Agent — SSE streaming ile tam QA analizi.
 * Callback her token'da çağrılır; done=true olduğunda analiz tamamlanmıştır.
 */
export async function nexusCodeStream(
  input: NexusCodeInput,
  onToken: (token: string, done: boolean) => void,
  signal?: AbortSignal
): Promise<void> {
  const domainLabel =
    input.domain === "banking" ? "Bankacılık"
    : input.domain === "finance" ? "Finans"
    : "Genel";

  const userContent = [
    `Analiz Modu: ${input.mode === "code" ? "Kod Analizi" : "Web Sayfası Analizi"}`,
    `Domain: ${domainLabel}`,
    "",
    input.content,
    input.extraContext ? `\n---\nEk Bağlam / İş Kuralları:\n${input.extraContext}` : "",
  ]
    .filter(Boolean)
    .join("\n");

  const res = await fetch(gatewayUrl("/stream"), {
    method: "POST",
    headers: gatewayHeaders({ internal: true }),
    body: JSON.stringify({
      task_type: "nexus_code_analyze",
      messages: [{ role: "user", content: userContent }],
      temperature: 0.35,
      max_tokens: 6000,
      stream: true,
    }),
    signal,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Neurex Code Gateway hatası (${res.status}): ${text}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("Stream okuyucu alınamadı");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const data = trimmed.slice(5).trim();
      if (data === "[DONE]") {
        onToken("", true);
        return;
      }
      try {
        const parsed = JSON.parse(data) as { token?: string; error?: string };
        if (parsed.error) throw new Error(parsed.error);
        if (parsed.token) onToken(parsed.token, false);
      } catch {
        // malformed chunk — skip
      }
    }
  }

  onToken("", true);
}

/**
 * Generic SSE streaming — her task tipi için kullanılabilir.
 * nexusCodeStream ile aynı SSE protokolü; daha genel amaçlı.
 *
 * @param req         AI Gateway istek gövdesi
 * @param onToken     Her token geldiğinde çağrılır; done=true → bitti
 * @param signal      AbortController sinyali (opsiyonel)
 */
export async function aiStream(
  req: AIGatewayRequest,
  onToken: (token: string, done: boolean) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(gatewayUrl("/stream"), {
    method: "POST",
    headers: gatewayHeaders({ internal: true }),
    body: JSON.stringify({
      task_type: req.task_type ?? "chat",
      messages: req.messages,
      temperature: req.temperature ?? 0.5,
      max_tokens: req.max_tokens ?? 6000,
      stream: true,
    }),
    signal,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`AI Stream hatası (${res.status}): ${text}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("Stream okuyucu alınamadı");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const data = trimmed.slice(5).trim();
      if (data === "[DONE]") { onToken("", true); return; }
      try {
        const parsed = JSON.parse(data) as { token?: string; error?: string };
        if (parsed.error) throw new Error(parsed.error);
        if (parsed.token) onToken(parsed.token, false);
      } catch { /* malformed chunk — skip */ }
    }
  }

  onToken("", true);
}
