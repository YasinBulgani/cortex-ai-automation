"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Profile {
  id: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  department: string | null;
  roles: string[];
  created_at: string | null;
}

export interface ProfileUpdatePayload {
  full_name?: string;
  phone?: string;
  department?: string;
}

export interface PasswordChangePayload {
  current_password: string;
  new_password: string;
}

// ── Query Keys ────────────────────────────────────────────────────────────────

export const profileKeys = {
  all: ["user", "profile"] as const,
  me: () => [...profileKeys.all] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

/**
 * GET /api/v1/auth/profile — Mevcut kullanıcının profil bilgilerini getirir.
 */
export function useProfile() {
  return useQuery<Profile>({
    queryKey: profileKeys.me(),
    queryFn: () => apiFetch<Profile>("/api/v1/auth/profile"),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 1,
  });
}

/**
 * PUT /api/v1/auth/profile — Profil bilgilerini günceller.
 */
export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfileUpdatePayload) =>
      apiFetch<Profile>("/api/v1/auth/profile", {
        method: "PUT",
        json: payload,
      }),
    onSuccess: (updated) => {
      qc.setQueryData<Profile>(profileKeys.me(), updated);
    },
  });
}

/**
 * PUT /api/v1/auth/password — Şifre değiştirir.
 */
export function useChangePassword() {
  return useMutation({
    mutationFn: (payload: PasswordChangePayload) =>
      apiFetch<void>("/api/v1/auth/password", {
        method: "PUT",
        json: payload,
      }),
  });
}

// ── System notification prefs (GET/PUT /api/v1/notifications/prefs) ──────────

export interface NotifPrefs {
  notify_on_complete: boolean;
  notify_on_failure: boolean;
  slack_webhook_url: string | null;
}

export const notifPrefsKeys = {
  all: ["user", "notif-prefs"] as const,
};

/**
 * GET /api/v1/notifications/prefs — Bildirim tercihlerini getirir.
 */
export function useNotifPrefs() {
  return useQuery<NotifPrefs>({
    queryKey: notifPrefsKeys.all,
    queryFn: () => apiFetch<NotifPrefs>("/api/v1/notifications/prefs"),
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * PUT /api/v1/notifications/prefs — Bildirim tercihlerini kaydeder.
 */
export function useUpdateNotifPrefs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: NotifPrefs) =>
      apiFetch<NotifPrefs>("/api/v1/notifications/prefs", {
        method: "PUT",
        json: payload,
      }),
    onSuccess: (updated) => {
      qc.setQueryData<NotifPrefs>(notifPrefsKeys.all, updated);
    },
  });
}
