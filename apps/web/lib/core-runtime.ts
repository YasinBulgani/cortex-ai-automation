"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/api-client";

export type CoreBlockingReason =
  | "backend_down"
  | "auth_required"
  | "auth_preparing"
  | "unknown_runtime_error"
  | null;

export type CoreServiceStatus = {
  name: string;
  state: "running" | "starting" | "stopped" | "unhealthy" | "unknown";
  running: boolean;
  healthUrl?: string;
  healthOk: boolean | null;
  healthDetail: string;
};

export type CoreRuntimeStatus = {
  loading: boolean;
  backendReady: boolean;
  services: CoreServiceStatus[];
  checkedAt: string | null;
  authState: "ready" | "preparing" | "missing";
  canQueryProjects: boolean;
  blockingReason: CoreBlockingReason;
  error: string | null;
  refresh: () => Promise<void>;
};

type ServicesResponse = {
  ok: boolean;
  checkedAt: string;
  backendReady: boolean;
  services: CoreServiceStatus[];
  compose?: { error?: string };
};

function getAuthState(): CoreRuntimeStatus["authState"] {
  if (typeof window === "undefined") return "missing";
  const bootstrapping = (window as unknown as { __bgtsAuthBootstrapping?: boolean }).__bgtsAuthBootstrapping;
  if (bootstrapping) return "preparing";
  return getToken() ? "ready" : "missing";
}

export function useCoreRuntime(): CoreRuntimeStatus {
  const [loading, setLoading] = useState(true);
  const [backendReady, setBackendReady] = useState(false);
  const [services, setServices] = useState<CoreServiceStatus[]>([]);
  const [checkedAt, setCheckedAt] = useState<string | null>(null);
  const [authState, setAuthState] = useState<CoreRuntimeStatus["authState"]>("missing");
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setAuthState(getAuthState());
    try {
      const response = await fetch("/api/dev/services/status", { cache: "no-store" });
      const data = (await response.json()) as ServicesResponse;
      setBackendReady(Boolean(data.backendReady));
      setServices(data.services ?? []);
      setCheckedAt(data.checkedAt ?? null);
      setError(response.ok ? null : data.compose?.error ?? "Servis durumu okunamadı.");
    } catch (err) {
      setBackendReady(false);
      setServices([]);
      setCheckedAt(null);
      setError(err instanceof Error ? err.message : "Servis durumu okunamadı.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      setAuthState(getAuthState());
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  // auth_required artık blocking değil — middleware zaten authentication'ı garanti eder.
  const blockingReason: CoreBlockingReason = !backendReady
    ? "backend_down"
    : authState === "preparing"
      ? "auth_preparing"
      : null;

  return {
    loading,
    backendReady,
    services,
    checkedAt,
    authState,
    canQueryProjects: backendReady,
    blockingReason,
    error,
    refresh,
  };
}
