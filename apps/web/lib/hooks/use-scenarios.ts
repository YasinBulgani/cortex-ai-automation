"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
} from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────
export interface Scenario {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  gherkin?: string;
  priority?: string;
  status?: string;
  tags?: string[];
  created_at?: string;
  updated_at?: string;
}

export interface ScenarioCreate {
  title: string;
  description?: string;
  gherkin?: string;
  priority?: string;
  tags?: string[];
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Query Keys ───────────────────────────────────────────────────────
export const scenarioKeys = {
  all: ["scenarios"] as const,
  lists: () => [...scenarioKeys.all, "list"] as const,
  list: (projectId: string, filters?: Record<string, unknown>) =>
    [...scenarioKeys.lists(), projectId, filters] as const,
  infinite: (projectId: string) =>
    [...scenarioKeys.lists(), projectId, "infinite"] as const,
  details: () => [...scenarioKeys.all, "detail"] as const,
  detail: (id: string) => [...scenarioKeys.details(), id] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────

/** Proje senaryolarini listele (sayfalanmis). */
export function useScenarios(
  projectId: string | undefined,
  params?: { page?: number; page_size?: number; status?: string; search?: string },
) {
  const { page = 1, page_size = 20, status, search } = params ?? {};

  return useQuery({
    queryKey: scenarioKeys.list(projectId!, { page, page_size, status, search }),
    queryFn: () => {
      const qs = new URLSearchParams();
      qs.set("page", String(page));
      qs.set("page_size", String(page_size));
      if (status) qs.set("status", status);
      if (search) qs.set("search", search);
      return apiFetch<PaginatedResponse<Scenario>>(
        `/api/v1/tspm/projects/${projectId}/scenarios?${qs}`,
      );
    },
    enabled: !!projectId,
    staleTime: 60 * 1000,
  });
}

/** Sonsuz scroll ile senaryo listesi. */
export function useScenariosInfinite(projectId: string | undefined) {
  return useInfiniteQuery({
    queryKey: scenarioKeys.infinite(projectId!),
    queryFn: ({ pageParam = 1 }) =>
      apiFetch<PaginatedResponse<Scenario>>(
        `/api/v1/tspm/projects/${projectId}/scenarios?page=${pageParam}&page_size=20`,
      ),
    enabled: !!projectId,
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.page < lastPage.total_pages ? lastPage.page + 1 : undefined,
  });
}

/** Tek senaryo detay. */
export function useScenario(projectId: string | undefined, scenarioId: string | undefined) {
  return useQuery({
    queryKey: scenarioKeys.detail(scenarioId!),
    queryFn: () =>
      apiFetch<Scenario>(`/api/v1/tspm/projects/${projectId}/scenarios/${scenarioId}`),
    enabled: !!projectId && !!scenarioId,
  });
}

/** Yeni senaryo oluştur. */
export function useCreateScenario(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ScenarioCreate) =>
      apiFetch<Scenario>(`/api/v1/tspm/projects/${projectId}/scenarios`, {
        method: "POST",
        json: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: scenarioKeys.lists(),
      });
    },
  });
}

/** Senaryo guncelle. */
export function useUpdateScenario(projectId: string, scenarioId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<ScenarioCreate>) =>
      apiFetch<Scenario>(`/api/v1/tspm/projects/${projectId}/scenarios/${scenarioId}`, {
        method: "PUT",
        json: data,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(scenarioKeys.detail(scenarioId), updated);
      queryClient.invalidateQueries({ queryKey: scenarioKeys.lists() });
    },
  });
}

/** Senaryo sil. */
export function useDeleteScenario(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scenarioKeys.lists() });
    },
  });
}
