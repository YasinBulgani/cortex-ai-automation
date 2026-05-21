/**
 * agents/v2 API client.
 *
 * Backend: /api/v1/agents/v2/* endpoints.
 * SSE streaming: EventSource tabanlı.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

export type InputSource =
  | "pdf"
  | "docx"
  | "url"
  | "swagger"
  | "confluence"
  | "jira"
  | "figma"
  | "bpmn"
  | "postman"
  | "manual"
  | "text";

export interface RunAgentV2Request {
  project_id: string;
  input_source: InputSource;
  url?: string;
  file_path?: string;
  text?: string;
  swagger_url?: string;
  extra_context?: string;
  credentials?: Record<string, string>;
  allowed_hosts?: string[];
  max_pages?: number;
  max_depth?: number;
  enable_ai_xpath?: boolean;
  auto_pr?: boolean;
  auto_merge?: boolean;
}

export interface RunAgentV2Response {
  run_id: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
  stream_url: string;
  detail_url: string;
}

export interface RunV2Status {
  run_id: string;
  status: string;
  project_id: string;
  input_source: string;
  created_at: string;
  completed_at?: string | null;
  cost_usd: number;
  tokens_used: number;
  llm_calls_count: number;
  errors: Array<Record<string, unknown>>;
  intent_graph?: Record<string, unknown> | null;
  app_map?: Record<string, unknown> | null;
  scenarios: Array<Record<string, unknown>>;
  generated_code?: Record<string, unknown> | null;
  run_result?: Record<string, unknown> | null;
  healing_result?: Record<string, unknown> | null;
  review?: Record<string, unknown> | null;
  report?: Record<string, unknown> | null;
}

export interface RunV2ListItem {
  run_id: string;
  project_id: string;
  status: string;
  input_source: string;
  created_at: string;
  completed_at?: string | null;
  cost_usd: number;
  scenario_count: number;
  passed_count: number;
  failed_count: number;
}

export interface AgentStreamEvent {
  run_id: string;
  event_type:
    | "started"
    | "agent_started"
    | "agent_finished"
    | "llm_call"
    | "error"
    | "completed"
    | "failed"
    | "progress"
    | "final";
  timestamp: string;
  agent_name?: string;
  message?: string;
  data?: Record<string, unknown>;
}

export async function startAgentRun(
  body: RunAgentV2Request,
): Promise<RunAgentV2Response> {
  const resp = await fetch(`${API_BASE}/api/v1/agents/v2/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Agent run başlatılamadı: ${resp.status} ${text}`);
  }
  return resp.json();
}

export async function getAgentRun(runId: string): Promise<RunV2Status> {
  const resp = await fetch(`${API_BASE}/api/v1/agents/v2/runs/${runId}`);
  if (!resp.ok) throw new Error(`Run bulunamadı: ${runId}`);
  return resp.json();
}

export async function listAgentRuns(params?: {
  projectId?: string;
  page?: number;
  pageSize?: number;
}): Promise<{ runs: RunV2ListItem[]; total: number; page: number; page_size: number }> {
  const qs = new URLSearchParams();
  if (params?.projectId) qs.set("project_id", params.projectId);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.pageSize) qs.set("page_size", String(params.pageSize));
  const resp = await fetch(`${API_BASE}/api/v1/agents/v2/runs?${qs}`);
  if (!resp.ok) throw new Error("Runs listelenemedi");
  return resp.json();
}

export async function cancelAgentRun(runId: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/agents/v2/runs/${runId}/cancel`, {
    method: "POST",
  });
}

/**
 * SSE subscribe.
 *
 * EventSource POST desteklemediği için önce `startAgentRun` ile başlat,
 * sonra `subscribeAgentRun(run_id, onEvent, onError)` çağır.
 *
 * Returns unsubscribe fn.
 */
export function subscribeAgentRun(
  runId: string,
  onEvent: (e: AgentStreamEvent) => void,
  onError?: (err: Event) => void,
): () => void {
  const url = `${API_BASE}/api/v1/agents/v2/runs/${runId}/stream`;
  const es = new EventSource(url);

  const eventTypes = [
    "started",
    "agent_started",
    "agent_finished",
    "llm_call",
    "error",
    "completed",
    "failed",
    "progress",
    "final",
  ];
  for (const type of eventTypes) {
    es.addEventListener(type, (evt) => {
      try {
        const data = JSON.parse((evt as MessageEvent).data);
        onEvent({ ...data, event_type: type as AgentStreamEvent["event_type"] });
      } catch (e) {
        // ignore parse error
      }
    });
  }

  es.onerror = (err) => {
    if (onError) onError(err);
    es.close();
  };

  return () => es.close();
}

export async function getAgentsV2Health(): Promise<{
  status: string;
  langgraph_available: boolean;
  ai_gateway_reachable: boolean;
  active_runs: number;
}> {
  const resp = await fetch(`${API_BASE}/api/v1/agents/v2/health`);
  if (!resp.ok) throw new Error("Health check failed");
  return resp.json();
}
