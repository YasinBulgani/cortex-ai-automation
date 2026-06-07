"use client";

import { useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  department: string | null;
  is_active: boolean;
  roles: string[];
  created_at: string | null;
}

export interface CreateUserPayload {
  email: string;
  password: string;
  full_name?: string;
  role?: string;
}

export interface UpdateUserPayload {
  is_active?: boolean;
  full_name?: string;
  role?: string;
}

export interface Invitation {
  id: string;
  email: string;
  role: string;
  team_id: string | null;
  expires_at: string;
  created_at: string;
}

export interface InvitePayload {
  email: string;
  role: string;
  team_id?: string;
}

// ── Query Keys ────────────────────────────────────────────────────────────────

export const adminUserKeys = {
  all: ["admin", "users"] as const,
  list: () => [...adminUserKeys.all] as const,
  invitations: () => ["admin", "invitations"] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

/**
 * GET /api/v1/auth/users — Platform kullanıcı listesi.
 * Opsiyonel `search` ile e-posta/ad filtreleme yapılır.
 */
export function useAdminUsers(search?: string) {
  const { data: users = [], ...rest } = useQuery<AdminUser[]>({
    queryKey: adminUserKeys.list(),
    queryFn: () => apiFetch<AdminUser[]>("/api/v1/auth/users"),
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  const filtered = useMemo(() => {
    if (!search) return users;
    const q = search.toLowerCase();
    return users.filter(
      (u) =>
        u.email.toLowerCase().includes(q) ||
        (u.full_name ?? "").toLowerCase().includes(q)
    );
  }, [users, search]);

  return { users, filtered, ...rest };
}

/**
 * POST /api/v1/auth/users — Yeni kullanıcı oluşturur.
 */
export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateUserPayload) =>
      apiFetch<AdminUser>("/api/v1/auth/users", {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminUserKeys.list() });
    },
  });
}

/**
 * PUT /api/v1/auth/users/:id — Kullanıcı özelliklerini günceller (aktif/pasif vb.)
 */
export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: UpdateUserPayload & { id: string }) =>
      apiFetch<AdminUser>(`/api/v1/auth/users/${id}`, {
        method: "PUT",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminUserKeys.list() });
    },
  });
}

/**
 * DELETE /api/v1/auth/users/:id — Kullanıcı siler.
 */
export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/auth/users/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminUserKeys.list() });
    },
  });
}

// ── Invitations ───────────────────────────────────────────────────────────────

/**
 * GET /api/v1/organizations/invitations — Bekleyen davetleri listeler.
 */
export function useAdminInvitations() {
  return useQuery<Invitation[]>({
    queryKey: adminUserKeys.invitations(),
    queryFn: () => apiFetch<Invitation[]>("/api/v1/organizations/invitations"),
    staleTime: 60_000,
  });
}

/**
 * POST /api/v1/organizations/invitations — Yeni davet gönderir.
 */
export function useSendInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: InvitePayload) =>
      apiFetch<Invitation>("/api/v1/organizations/invitations", {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminUserKeys.invitations() });
    },
  });
}

/**
 * DELETE /api/v1/organizations/invitations/:id — Daveti iptal eder.
 */
export function useRevokeInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/organizations/invitations/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminUserKeys.invitations() });
    },
  });
}
