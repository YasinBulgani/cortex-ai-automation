"use client";

import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

interface ResourceHooksConfig<T, CreateInput = Partial<T>, UpdateInput = Partial<T>> {
  /** API path factory — projectId zorunlu versiyon */
  path: (projectId: string) => string;
  /** TanStack Query key factory — projectId undefined olabilir (enabled=false için) */
  queryKey: (projectId: string | undefined) => QueryKey;
  staleTime?: number;
  /** List endpoint döneceği tip override (genelde T[]) */
  listTransform?: (raw: unknown) => T[];
}

/**
 * Tekrar eden CRUD hook kalıplarını tek bir factory ile üretir.
 *
 * Kullanım:
 *   export const planHooks = createResourceHooks<TestPlan, CreatePlanInput>({
 *     path:     (pid) => `${BASE(pid)}/plans`,
 *     queryKey: (pid) => managementKeys.plans(pid),
 *   });
 *   // Sayfalarda:
 *   const { data } = planHooks.useList(mpid);
 *   const create   = planHooks.useCreate(mpid);
 */
export function createResourceHooks<
  T,
  CreateInput = Partial<T>,
  UpdateInput = Partial<T>,
>(config: ResourceHooksConfig<T, CreateInput, UpdateInput>) {
  const { path, queryKey, staleTime = 30_000 } = config;

  function useList(projectId: string | undefined) {
    return useQuery({
      queryKey: queryKey(projectId),
      queryFn: () => apiFetch<T[]>(path(projectId!)),
      enabled: !!projectId,
      staleTime,
    });
  }

  function useDetail(projectId: string | undefined, id: string | undefined) {
    return useQuery({
      queryKey: [...(queryKey(projectId) as unknown[]), id] as QueryKey,
      queryFn: () => apiFetch<T>(`${path(projectId!)}/${id!}`),
      enabled: !!projectId && !!id,
      staleTime,
    });
  }

  function useCreate(projectId: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (payload: CreateInput) =>
        apiFetch<T>(path(projectId!), { method: "POST", json: payload }),
      onSuccess: () => {
        void qc.invalidateQueries({ queryKey: queryKey(projectId) });
      },
    });
  }

  function useUpdate(projectId: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: ({ id, ...payload }: UpdateInput & { id: string }) =>
        apiFetch<T>(`${path(projectId!)}/${id}`, { method: "PATCH", json: payload }),
      onSuccess: () => {
        void qc.invalidateQueries({ queryKey: queryKey(projectId) });
      },
    });
  }

  function useDelete(projectId: string | undefined) {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (id: string) =>
        apiFetch<void>(`${path(projectId!)}/${id}`, { method: "DELETE" }),
      onSuccess: () => {
        void qc.invalidateQueries({ queryKey: queryKey(projectId) });
      },
    });
  }

  return { useList, useDetail, useCreate, useUpdate, useDelete };
}
