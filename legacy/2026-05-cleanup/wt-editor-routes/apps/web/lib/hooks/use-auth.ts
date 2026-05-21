"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch, clearTokens } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────
export interface CurrentUser {
  id: string;
  email: string;
  full_name?: string;
  roles: string[];
  permissions: string[];
}

interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in?: number;
}

// ── Query Keys ───────────────────────────────────────────────────────
export const authKeys = {
  all: ["auth"] as const,
  me: () => [...authKeys.all, "me"] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────

/** Mevcut oturumdaki kullanici bilgisini ceker (cached). */
export function useCurrentUser() {
  const query = useQuery({
    queryKey: authKeys.me(),
    queryFn: () => apiFetch<CurrentUser>("/api/v1/auth/me"),
    enabled: typeof window !== "undefined",
    staleTime: 10 * 60 * 1000, // 10 dk — kullanici bilgisi sik degismez
    retry: false, // 401'de sonsuz dongu olmasin
  });

  const hasPermission = (perm: string) => {
    if (!query.data) return false;
    return (
      query.data.permissions.includes("admin.*") ||
      query.data.permissions.includes(perm)
    );
  };

  return {
    user: query.data ?? null,
    loading: query.isLoading,
    error: query.error?.message ?? null,
    hasPermission,
    refetch: query.refetch,
  };
}

/** Login mutation — basarili olursa token'lari kaydeder, user cache'ini gunceller. */
export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (creds: LoginRequest): Promise<LoginResponse> =>
      apiFetch<LoginResponse>("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(creds),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          body?.detail || body?.error || "E-posta veya sifre hatali",
        );
      }
      return res.json();
    },
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token, data.expires_in);
      // Login sonrasi user bilgisini hemen cek
      queryClient.invalidateQueries({ queryKey: authKeys.me() });
    },
  });
}

/** Logout — tum token'lari siler, cache'i temizler. */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      try {
        await apiFetch("/api/v1/auth/logout-all", { method: "POST" });
      } catch {
        // Backend erisilemez olsa bile local olarak cikis yap
      }
      clearTokens();
    },
    onSettled: () => {
      queryClient.clear();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    },
  });
}
