/**
 * agents/v2 API client.
 *
 * Backend: /api/v1/agents/v2/* endpoints.
 * SSE streaming: EventSource tabanlı.
 */

import { apiFetch, ensureValidToken, getToken } from "./api-client";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "").replace(/\/$/, "");

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

export type AIWorkflowType =
  | "test_generation"
  | "analysis"
  | "code_generation"
  | "review"
  | "repair"
  | "report";

export type AIWorkflowStatusValue =
  | "pending_approval"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "failed_validation"
  | "cancelled";

export interface AIWorkflowCreateRequest extends RunAgentV2Request {
  workflow_type?: AIWorkflowType;
  dry_run?: boolean;
  requires_approval?: boolean;
}

export interface AIWorkflowCreateResponse {
  workflow_id: string;
  run_id: string;
  status: AIWorkflowStatusValue;
  created_at: string;
  stream_url: string;
  detail_url: string;
  events_url: string;
  artifacts_url: string;
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

export interface AIWorkflowStatus extends RunV2Status {
  workflow_id: string;
  status: AIWorkflowStatusValue | string;
  error?: string | null;
  event_count: number;
  artifact_count: number;
  approval_count: number;
}

export interface AIWorkflowArtifact {
  artifact_id: string;
  kind: string;
  name: string;
  storage_path: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface AIWorkflowEventListResponse {
  workflow_id: string;
  events: Array<Record<string, unknown>>;
}

export interface AIWorkflowArtifactListResponse {
  workflow_id: string;
  artifacts: AIWorkflowArtifact[];
}

export interface AIWorkflowApprovalResponse {
  workflow_id: string;
  status: AIWorkflowStatusValue | string;
  approval: Record<string, unknown>;
}

export interface AIWorkflowDeadLetterListResponse {
  dead_letters: Array<Record<string, unknown>>;
}

export interface AIWorkflowHealthSummary {
  generated_at: string;
  sample_size: number;
  runs_total: number;
  active_runs: number;
  by_status: Record<string, number>;
  by_workflow_type: Record<string, number>;
  event_counts: Record<string, number>;
  artifact_count: number;
  artifact_bytes: number;
  approval_count: number;
  dead_letters_total: number;
  recent_dead_letters: Array<Record<string, unknown>>;
  queue_depth: number | null;
  oldest_active_seconds: number | null;
  cost_usd: number;
  tokens_used: number;
  llm_calls_count: number;
  ops_evidence?: {
    generated_at?: string;
    release_decision?: string;
    llm_quality_score?: number;
    report_path?: string;
    operator_next_steps?: string[];
    failed_required_checks?: string[];
    soak_report?: {
      path?: string;
      profile?: string;
      runs_total?: number;
      dead_letters_total?: number;
      artifact_count?: number;
      cost_usd?: number;
      tokens_used?: number;
      by_status?: Record<string, number>;
    } | null;
    dr_manifest?: {
      path?: string;
      created_at?: string;
      restore_db?: string;
      artifact_files?: number;
      artifacts?: number;
      events?: number;
      runs?: number;
    } | null;
    checklist?: Array<{
      id: string;
      label: string;
      status: string;
      detail: string;
    }>;
  } | null;
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
  return apiFetch<RunAgentV2Response>("/api/v1/agents/v2/run", {
    method: "POST",
    json: body,
  });
}

export async function createAIWorkflow(
  body: AIWorkflowCreateRequest,
): Promise<AIWorkflowCreateResponse> {
  return apiFetch<AIWorkflowCreateResponse>("/api/v1/ai/workflows", {
    method: "POST",
    json: body,
  });
}

export interface UploadSourceFileResponse {
  file_path: string;
  original_name: string;
  size_bytes: number;
  suffix: string;
}

/**
 * Sıfır-bilgi pipeline için kaynak dosyayı backend'e yükler; `file_path`
 * döner. Dönen path `startAgentRun({ file_path })` içinde kullanılır.
 */
export async function uploadSourceFile(file: File): Promise<UploadSourceFileResponse> {
  const form = new FormData();
  form.append("file", file);
  // JWT zorunlu — backend `get_current_user` bekler; multipart için
  // Content-Type header'ı browser'a bırakıyoruz (boundary otomatik).
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let resp = await fetch(`${API_BASE}/api/v1/agents/v2/upload`, {
    method: "POST",
    body: form,
    headers,
    credentials: "include",
  });
  if (resp.status === 401 && await ensureValidToken()) {
    resp = await fetch(`${API_BASE}/api/v1/agents/v2/upload`, {
      method: "POST",
      body: form,
      headers,
      credentials: "include",
    });
  }
  if (!resp.ok) {
    if (resp.status === 401) {
      throw new Error("Oturumunuz düştü, lütfen yeniden giriş yapın.");
    }
    if (resp.status === 429) {
      throw new Error("Çok fazla yükleme isteği; lütfen 1 dakika bekleyip tekrar deneyin.");
    }
    const text = await resp.text().catch(() => "");
    throw new Error(`Dosya yüklenemedi (${resp.status}): ${text.slice(0, 160)}`);
  }
  return resp.json();
}

export async function getAgentRun(runId: string): Promise<RunV2Status> {
  return apiFetch<RunV2Status>(`/api/v1/agents/v2/runs/${runId}`);
}

export async function getAIWorkflow(workflowId: string): Promise<AIWorkflowStatus> {
  return apiFetch<AIWorkflowStatus>(`/api/v1/ai/workflows/${workflowId}`);
}

export async function getAIWorkflowEvents(
  workflowId: string,
): Promise<AIWorkflowEventListResponse> {
  return apiFetch<AIWorkflowEventListResponse>(
    `/api/v1/ai/workflows/${workflowId}/events`,
  );
}

export async function getAIWorkflowArtifacts(
  workflowId: string,
): Promise<AIWorkflowArtifactListResponse> {
  return apiFetch<AIWorkflowArtifactListResponse>(
    `/api/v1/ai/workflows/${workflowId}/artifacts`,
  );
}

export function getAIWorkflowArtifactDownloadUrl(
  workflowId: string,
  artifactId: string,
): string {
  return `${API_BASE}/api/v1/ai/workflows/${encodeURIComponent(workflowId)}/artifacts/${encodeURIComponent(artifactId)}/download`;
}

export async function downloadAIWorkflowArtifact(
  workflowId: string,
  artifact: Pick<AIWorkflowArtifact, "artifact_id" | "name">,
): Promise<void> {
  const url = getAIWorkflowArtifactDownloadUrl(workflowId, artifact.artifact_id);
  const buildHeaders = () => {
    const headers: Record<string, string> = {};
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  };
  let resp = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: buildHeaders(),
  });
  if (resp.status === 401 && await ensureValidToken()) {
    resp = await fetch(url, {
      method: "GET",
      credentials: "include",
      headers: buildHeaders(),
    });
  }
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`Artifact indirilemedi (${resp.status}): ${text.slice(0, 160)}`);
  }

  const blob = await resp.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = artifact.name || "artifact";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function approveAIWorkflow(
  workflowId: string,
  decision: "approved" | "rejected",
  note?: string,
): Promise<AIWorkflowApprovalResponse> {
  return apiFetch<AIWorkflowApprovalResponse>(
    `/api/v1/ai/workflows/${workflowId}/approve`,
    {
      method: "POST",
      json: { decision, note },
    },
  );
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
  return apiFetch<{ runs: RunV2ListItem[]; total: number; page: number; page_size: number }>(
    `/api/v1/agents/v2/runs?${qs}`,
  );
}

export async function cancelAgentRun(runId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/agents/v2/runs/${runId}/cancel`, {
    method: "POST",
  });
}

export async function cancelAIWorkflow(workflowId: string): Promise<{
  workflow_id: string;
  run_id: string;
  status: AIWorkflowStatusValue | string;
}> {
  return apiFetch<{
    workflow_id: string;
    run_id: string;
    status: AIWorkflowStatusValue | string;
  }>(`/api/v1/ai/workflows/${workflowId}/cancel`, { method: "POST" });
}

export async function listAIWorkflowDeadLetters(
  limit = 100,
): Promise<AIWorkflowDeadLetterListResponse> {
  return apiFetch<AIWorkflowDeadLetterListResponse>(
    `/api/v1/ai/workflows/dead-letters?limit=${limit}`,
  );
}

export async function getAIWorkflowHealth(
  limit = 250,
): Promise<AIWorkflowHealthSummary> {
  return apiFetch<AIWorkflowHealthSummary>(
    `/api/v1/ai/workflows/health?limit=${limit}`,
  );
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
  const es = new EventSource(url, { withCredentials: true });

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
  return apiFetch<{
    status: string;
    langgraph_available: boolean;
    ai_gateway_reachable: boolean;
    active_runs: number;
  }>("/api/v1/agents/v2/health");
}
