"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────
export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface ProjectStats {
  total_scenarios: number;
  total_test_cases: number;
  automation_coverage: number;
  last_run?: string;
}

export interface WeeklyTrendPoint {
  day: string;
  runs: number;
  passed: number;
}

export interface GlobalDashboardProject {
  id: string;
  name: string;
  scenario_count: number;
  last_run: string | null;
  pass_rate: number | null;
  status: string;
}

export interface GlobalDashboardActivity {
  actor: string;
  action: string;
  time: string;
  resource_type: string;
  resource_id: string;
}

export interface GlobalDashboard {
  total_projects: number;
  total_scenarios: number;
  active_executions: number;
  overall_pass_rate: number;
  pending_approvals: number;
  weekly_trend: WeeklyTrendPoint[];
  projects: GlobalDashboardProject[];
  activities: GlobalDashboardActivity[];
}

// ── Query Keys ───────────────────────────────────────────────────────
export const projectKeys = {
  all: ["projects"] as const,
  lists: () => [...projectKeys.all, "list"] as const,
  list: (filters?: Record<string, unknown>) =>
    [...projectKeys.lists(), filters] as const,
  details: () => [...projectKeys.all, "detail"] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
  stats: (id: string) => [...projectKeys.detail(id), "stats"] as const,
  globalDashboard: () => [...projectKeys.all, "global-dashboard"] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────

/** Tüm projeleri listele. */
export function useProjects() {
  return useQuery({
    queryKey: projectKeys.lists(),
    queryFn: () => apiFetch<Project[]>("/api/v1/tspm/projects"),
    staleTime: 2 * 60 * 1000, // 2 dk
  });
}

/** Tek bir projenin detayini getir. */
export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: projectKeys.detail(projectId!),
    queryFn: () => apiFetch<Project>(`/api/v1/tspm/projects/${projectId}`),
    enabled: !!projectId,
  });
}

/** Proje istatistikleri. */
export function useProjectStats(projectId: string | undefined) {
  return useQuery({
    queryKey: projectKeys.stats(projectId!),
    queryFn: () =>
      apiFetch<ProjectStats>(`/api/v1/tspm/projects/${projectId}/stats`),
    enabled: !!projectId,
    staleTime: 60 * 1000, // 1 dk
  });
}

/** Yeni proje oluştur. */
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectCreate) =>
      apiFetch<Project>("/api/v1/tspm/projects", {
        method: "POST",
        json: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}

/** Proje guncelle. */
export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<ProjectCreate>) =>
      apiFetch<Project>(`/api/v1/tspm/projects/${projectId}`, {
        method: "PUT",
        json: data,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(projectKeys.detail(projectId), updated);
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}

/** Proje sil. */
export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/tspm/projects/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}

/**
 * Platform geneli özet dashboard verisi.
 *
 * Performans notları:
 *   - staleTime=30s → backend cache TTL ile eşleştirildi; gereksiz istek atmaz.
 *   - refetchInterval=30s → sayfayı açık tutan kullanıcılar için otomatik yenileme.
 *   - gcTime=5dk → sekmeye dönüldüğünde hemen veri görünür, arka planda refetch gelir.
 */
export function useGlobalDashboard() {
  return useQuery<GlobalDashboard>({
    queryKey: projectKeys.globalDashboard(),
    queryFn: () => apiFetch<GlobalDashboard>("/api/v1/tspm/dashboard/global"),
    staleTime: 30 * 1000,          // 30 saniye — backend cache ile uyumlu
    gcTime: 5 * 60 * 1000,         // 5 dakika memory'de tut
    refetchInterval: 30 * 1000,    // otomatik polling (sayfa açıkken)
    refetchOnWindowFocus: true,
    retry: 1,
  });
}
