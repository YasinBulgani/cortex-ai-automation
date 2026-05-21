import { apiFetch } from "./api-client";

export type PromptEnv = "prod" | "staging" | "dev";

export interface PromptOut {
  id: string;
  description: string;
  task_type?: string | null;
  archived: boolean;
  created_at: string;
  created_by?: string | null;
  updated_at: string;
  latest_version?: number | null;
}

export interface PromptVersionOut {
  id: number;
  prompt_id: string;
  version: number;
  system_prompt: string;
  user_template: string;
  model_hint?: string | null;
  temperature?: number | null;
  max_tokens?: number | null;
  notes?: string | null;
  created_at: string;
  created_by?: string | null;
}

export interface RolloutOut {
  prompt_id: string;
  env: PromptEnv;
  active_version: number;
  canary_version?: number | null;
  canary_pct: number;
  updated_at: string;
  updated_by?: string | null;
}

export interface ResolvedPrompt {
  prompt_id: string;
  env: PromptEnv;
  version: number;
  system_prompt: string;
  user_template: string;
  model_hint?: string | null;
  temperature?: number | null;
  max_tokens?: number | null;
  decision_reason: string;
  active_version: number;
  canary_version?: number | null;
  canary_pct: number;
}

export interface PromptIn {
  description: string;
  task_type?: string | null;
}

export interface PromptVersionIn {
  system_prompt: string;
  user_template: string;
  model_hint?: string | null;
  temperature?: number | null;
  max_tokens?: number | null;
  notes?: string | null;
}

export interface RolloutIn {
  active_version: number;
  canary_version?: number | null;
  canary_pct: number;
}

export async function listPrompts(includeArchived = true): Promise<PromptOut[]> {
  return apiFetch<PromptOut[]>(`/api/v1/prompts?include_archived=${includeArchived ? "true" : "false"}`);
}

export async function getPrompt(promptId: string): Promise<PromptOut> {
  return apiFetch<PromptOut>(`/api/v1/prompts/${promptId}`);
}

export async function upsertPrompt(promptId: string, payload: PromptIn): Promise<PromptOut> {
  return apiFetch<PromptOut>(`/api/v1/prompts/${promptId}`, {
    method: "PUT",
    json: payload,
  });
}

export async function archivePrompt(promptId: string, archived: boolean): Promise<void> {
  await apiFetch<void>(`/api/v1/prompts/${promptId}/${archived ? "archive" : "unarchive"}`, {
    method: "POST",
  });
}

export async function listPromptVersions(promptId: string, limit = 100): Promise<PromptVersionOut[]> {
  return apiFetch<PromptVersionOut[]>(`/api/v1/prompts/${promptId}/versions?limit=${limit}`);
}

export async function addPromptVersion(promptId: string, payload: PromptVersionIn): Promise<PromptVersionOut> {
  return apiFetch<PromptVersionOut>(`/api/v1/prompts/${promptId}/versions`, {
    method: "POST",
    json: payload,
  });
}

export async function listPromptRollouts(promptId: string): Promise<RolloutOut[]> {
  return apiFetch<RolloutOut[]>(`/api/v1/prompts/${promptId}/rollouts`);
}

export async function upsertPromptRollout(
  promptId: string,
  env: PromptEnv,
  payload: RolloutIn,
): Promise<RolloutOut> {
  return apiFetch<RolloutOut>(`/api/v1/prompts/${promptId}/rollouts/${env}`, {
    method: "PUT",
    json: payload,
  });
}

export async function resolvePrompt(
  promptId: string,
  env: PromptEnv,
  tenant?: string,
): Promise<ResolvedPrompt> {
  const qs = new URLSearchParams({ env });
  if (tenant?.trim()) qs.set("tenant", tenant.trim());
  return apiFetch<ResolvedPrompt>(`/api/v1/prompts/${promptId}/resolve?${qs.toString()}`);
}
