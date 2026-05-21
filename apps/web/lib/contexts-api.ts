/**
 * DDD Bounded Context API Client
 *
 * /api/v1/contexts/projects  — Projects context
 * /api/v1/contexts/scenarios — Scenarios context
 */

import { apiFetch } from "@/lib/api";

// ── Projects ──────────────────────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  description: string;
  base_url: string;
  product_family: string | null;
  status: "active" | "archived";
  version: string;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectInput {
  name: string;
  description?: string;
  base_url?: string;
  product_family?: string;
}

export const projectsApi = {
  list(): Promise<Project[]> {
    return apiFetch<Project[]>("/api/v1/contexts/projects");
  },

  get(id: string): Promise<Project> {
    return apiFetch<Project>(`/api/v1/contexts/projects/${id}`);
  },

  create(input: CreateProjectInput): Promise<Project> {
    return apiFetch<Project>("/api/v1/contexts/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  },

  rename(id: string, name: string): Promise<Project> {
    return apiFetch<Project>(`/api/v1/contexts/projects/${id}/name`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
  },

  archive(id: string): Promise<void> {
    return apiFetch<void>(`/api/v1/contexts/projects/${id}`, {
      method: "DELETE",
    });
  },
};

// ── Scenarios ─────────────────────────────────────────────────────────────────

export type ScenarioStatus = "draft" | "in_review" | "approved";

export interface ScenarioStep {
  keyword: string;
  text: string;
  order: number;
}

export interface Scenario {
  id: string;
  project_id: string;
  title: string;
  status: ScenarioStatus;
  steps: ScenarioStep[];
  version: string;
  created_at: string;
  updated_at: string;
}

export interface CreateScenarioInput {
  project_id: string;
  title: string;
  steps?: ScenarioStep[];
}

export const scenariosApi = {
  list(projectId: string): Promise<Scenario[]> {
    return apiFetch<Scenario[]>(
      `/api/v1/contexts/scenarios?project_id=${projectId}`,
    );
  },

  get(id: string): Promise<Scenario> {
    return apiFetch<Scenario>(`/api/v1/contexts/scenarios/${id}`);
  },

  create(input: CreateScenarioInput): Promise<Scenario> {
    return apiFetch<Scenario>("/api/v1/contexts/scenarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  },

  submit(id: string): Promise<Scenario> {
    return apiFetch<Scenario>(`/api/v1/contexts/scenarios/${id}/submit`, {
      method: "POST",
    });
  },

  approve(id: string): Promise<Scenario> {
    return apiFetch<Scenario>(`/api/v1/contexts/scenarios/${id}/approve`, {
      method: "POST",
    });
  },
};
