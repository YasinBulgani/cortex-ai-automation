"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────

export type CheckStatus = "ok" | "warn" | "fail";
export type ReleaseVerdict = "ship" | "caution" | "block";

export interface ReleaseHealthCheck {
  key: string;
  label: string;
  status: CheckStatus;
  detail: string;
  href?: string;
}

export interface ReleaseHealth {
  verdict: ReleaseVerdict;
  release: string;
  checks: ReleaseHealthCheck[];
  updatedAt: string;
}

export type MetricDirection = "up" | "down";

export interface DayDeltaMetric {
  key: string;
  label: string;
  today: string;
  yesterday: string;
  delta: number;
  deltaUnit?: string;
  goodDirection: MetricDirection;
  spark: number[];
}

export interface DayOverDay {
  windowHours: number;
  metrics: DayDeltaMetric[];
  updatedAt: string;
}

export type InboxKind = "review" | "approve" | "fix" | "investigate";
export type InboxPriority = "high" | "med" | "low";

export interface InboxItem {
  id: string;
  kind: InboxKind;
  priority: InboxPriority;
  title: string;
  context: string;
  age: string;
  href?: string;
}

export interface MyInboxResponse {
  items: InboxItem[];
  updatedAt: string;
}

// ── Query keys ───────────────────────────────────────────────────────

export const webDashboardKeys = {
  all: ["web-dashboard"] as const,
  releaseHealth: (projectId: string | null) =>
    [...webDashboardKeys.all, "release-health", projectId] as const,
  dayOverDay: (projectId: string | null) =>
    [...webDashboardKeys.all, "day-over-day", projectId] as const,
  inbox: (projectId: string | null) =>
    [...webDashboardKeys.all, "inbox", projectId] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────

/** Release sağlığı — ship/caution/block verdict + altında check listesi. */
export function useReleaseHealth(projectId: string | null | undefined) {
  return useQuery<ReleaseHealth>({
    queryKey: webDashboardKeys.releaseHealth(projectId ?? null),
    queryFn: () =>
      apiFetch<ReleaseHealth>(
        `/api/v1/products/web/release-health?project_id=${encodeURIComponent(projectId ?? "")}`,
      ),
    enabled: !!projectId,
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

/** Bugün vs dün delta metrikleri. */
export function useDayOverDay(projectId: string | null | undefined) {
  return useQuery<DayOverDay>({
    queryKey: webDashboardKeys.dayOverDay(projectId ?? null),
    queryFn: () =>
      apiFetch<DayOverDay>(
        `/api/v1/products/web/day-over-day?project_id=${encodeURIComponent(projectId ?? "")}`,
      ),
    enabled: !!projectId,
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

/** Kullanıcının inbox'ı — onay/fix/incele/araştır. */
export function useMyInbox(projectId: string | null | undefined) {
  return useQuery<MyInboxResponse>({
    queryKey: webDashboardKeys.inbox(projectId ?? null),
    queryFn: () =>
      apiFetch<MyInboxResponse>(
        `/api/v1/products/web/my-inbox?project_id=${encodeURIComponent(projectId ?? "")}`,
      ),
    enabled: !!projectId,
    staleTime: 30 * 1000,
    refetchInterval: 2 * 60 * 1000,
  });
}
