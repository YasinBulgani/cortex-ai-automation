"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouteParam } from "@/lib/use-route-param";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { apiFetch } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { useProjectRole } from "@/lib/hooks/use-management-role";

// ── Types ─────────────────────────────────────────────────────────────────────

type MemberRole = "owner" | "admin" | "member" | "viewer";

interface ProjectMember {
  user_id: string;
  email: string;
  full_name?: string;
  role: MemberRole;
}

// ── Role config — maps backend role to QA-friendly display ────────────────────

const ROLE_CONFIG: Record<MemberRole, {
  label: string;
  qaLabel: string;
  description: string;
  badge: string;
  dotColor: string;
}> = {
  owner: {
    label:       "Owner",
    qaLabel:     "Proje Sahibi",
    description: "Tüm işlemler + proje silme, sahiplik devri",
    badge:       "border-amber-500/30 bg-amber-500/10 text-amber-400",
    dotColor:    "bg-amber-400",
  },
  admin: {
    label:       "Admin",
    qaLabel:     "Test Lead / Admin",
    description: "Tüm QA işlemleri, üye yönetimi, proje ayarları, release signoff",
    badge:       "border-purple-500/30 bg-purple-500/10 text-purple-400",
    dotColor:    "bg-purple-400",
  },
  member: {
    label:       "Member",
    qaLabel:     "QA Engineer",
    description: "Test case yaz, run başlat, defect aç, rapor görüntüle",
    badge:       "border-brand/30 bg-brand-soft text-brand",
    dotColor:    "bg-brand",
  },
  viewer: {
    label:       "Viewer",
    qaLabel:     "İzleyici / Developer",
    description: "Sadece görüntüleme — test case, run, defect, rapor",
    badge:       "border-border bg-surface-overlay text-fg-muted",
    dotColor:    "bg-fg-disabled",
  },
};

const SELECTABLE_ROLES: MemberRole[] = ["admin", "member", "viewer"];

const ROLE_CAPABILITIES: Record<MemberRole, string[]> = {
  owner: [
    "Tüm Admin yetkileri",
    "Projeyi silme",
    "Sahiplik devri",
  ],
  admin: [
    "Test Case: Oluştur, Düzenle, Arşivle, İncele",
    "Test Koşumu: Oluştur, Çalıştır, Sonuç Gir, Sil",
    "Defect: Oluştur, Kapat, Sil",
    "Plan + Regresyon Seti yönet",
    "Release Signoff",
    "Proje Ayarları ve Üye Yönetimi",
    "Audit Log, API Anahtarları",
  ],
  member: [
    "Test Case: Oluştur, Düzenle, AI Üret",
    "Test Koşumu: Oluştur, Çalıştır, Sonuç Gir",
    "Defect: Oluştur",
    "Regresyon Seti: Kısıtlı erişim",
    "Gereksinim: Görüntüle + TC Bağla",
    "Raporlar: Görüntüle + Export",
  ],
  viewer: [
    "Test Case: Sadece görüntüle",
    "Test Koşumu: Sadece görüntüle",
    "Defect: Görüntüle",
    "Gereksinim: Görüntüle",
    "Raporlar: Görüntüle",
  ],
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function initials(member: ProjectMember): string {
  const name = member.full_name ?? member.email;
  return name
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join("");
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function MemberSkeleton() {
  return (
    <div className="animate-pulse">
      {[1, 2, 3].map(i => (
        <div key={i} className="flex items-center gap-3 border-b border-border px-6 py-3.5">
          <div className="h-8 w-8 rounded-full bg-surface-accent" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 w-32 rounded bg-surface-accent" />
            <div className="h-2.5 w-48 rounded bg-surface-overlay" />
          </div>
          <div className="h-5 w-20 rounded-full bg-surface-accent" />
        </div>
      ))}
    </div>
  );
}

// ── Role info panel ───────────────────────────────────────────────────────────

function RoleInfoPanel() {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-[11px] text-brand hover:underline"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Rol açıklamaları
      </button>
      {open && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {(["admin", "member", "viewer"] as MemberRole[]).map(role => {
            const cfg = ROLE_CONFIG[role];
            return (
              <div key={role} className={cn("rounded-xl border p-4", cfg.badge.replace("text-", "border-").split(" ")[0], "bg-surface-raised")}>
                <div className="mb-2 flex items-center gap-2">
                  <span className={cn("h-2 w-2 rounded-full shrink-0", cfg.dotColor)} />
                  <span className="text-[12px] font-semibold text-fg">{cfg.qaLabel}</span>
                </div>
                <ul className="space-y-0.5">
                  {ROLE_CAPABILITIES[role].map(cap => (
                    <li key={cap} className="flex items-start gap-1.5 text-[11px] text-fg-muted">
                      <span className="mt-0.5 text-[9px] text-fg-subtle">→</span>
                      <span>{cap}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Invite Modal ──────────────────────────────────────────────────────────────

function InviteModal({
  projectId,
  existingEmails,
  onClose,
  onInvited,
}: {
  projectId: string;
  existingEmails: string[];
  onClose: () => void;
  onInvited: () => void;
}) {
  const [email, setEmail]   = useState("");
  const [role, setRole]     = useState<MemberRole>("member");
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);

  const isDuplicate = email.trim() !== "" && existingEmails.includes(email.trim().toLowerCase());

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    if (isDuplicate) { setError("Bu e-posta adresi zaten projeye üye."); return; }
    setLoading(true); setError(null);
    try {
      await apiFetch(`/api/v1/organizations/projects/${projectId}/members`, {
        method: "POST",
        json: { email: email.trim(), role },
      });
      onInvited(); onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Davet gönderilemedi.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-surface-raised p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-[14px] font-semibold text-fg">Üye Davet Et</h3>
          <button type="button" onClick={onClose} aria-label="Kapat"
            className="rounded-md p-1 text-fg-subtle hover:text-fg transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-[11px] text-fg-subtle">E-posta</label>
            <input
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              required autoFocus placeholder="kullanici@sirket.com"
              className={cn(
                "w-full rounded-xl border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none transition-colors",
                isDuplicate ? "border-amber-500/50 focus:border-amber-500/70" : "border-border focus:border-brand/50"
              )}
            />
            {isDuplicate && <p className="mt-1 text-[11px] text-amber-400">Bu e-posta zaten projeye üye.</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] text-fg-subtle">Rol</label>
            <div className="space-y-2">
              {SELECTABLE_ROLES.map(r => {
                const cfg = ROLE_CONFIG[r];
                return (
                  <label key={r} className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors",
                    role === r ? cfg.badge : "border-border bg-surface-overlay hover:border-border-strong"
                  )}>
                    <input type="radio" name="role" value={r} checked={role === r}
                      onChange={() => setRole(r)} className="mt-0.5 accent-brand" />
                    <div>
                      <p className="text-[12px] font-semibold text-fg">{cfg.qaLabel}</p>
                      <p className="mt-0.5 text-[11px] text-fg-muted">{cfg.description}</p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {error && <p className="rounded-lg bg-danger-subtle border border-danger/20 px-3 py-2 text-[12px] text-danger">{error}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg transition-colors">
              İptal
            </button>
            <button type="submit" disabled={loading || !email.trim() || isDuplicate}
              className="rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-50 transition-colors">
              {loading ? "Gönderiliyor…" : "Davet Et"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ManagementMembersPage() {
  const projectId  = useRouteParam("projectId");
  const { user: currentUser } = useCurrentUser();
  const qc = useQueryClient();
  const currentRole = useProjectRole(projectId ?? "");
  const canInvite = currentRole === "owner" || currentRole === "admin";

  const [showInvite, setShowInvite]       = useState(false);
  const [openRoleMenu, setOpenRoleMenu]   = useState<string | null>(null);

  const membersQuery = useQuery({
    queryKey: ["management", "members", projectId],
    queryFn: () =>
      apiFetch<ProjectMember[]>(`/api/v1/organizations/projects/${projectId}/members`)
        .then(data => (Array.isArray(data) ? data : [])),
    enabled: !!projectId,
  });

  const members = membersQuery.data ?? [];
  const loading = membersQuery.isLoading;
  const error   = membersQuery.isError
    ? (membersQuery.error instanceof Error ? membersQuery.error.message : "Üyeler yüklenemedi.")
    : null;

  const existingEmails = members.map(m => m.email.toLowerCase());

  const adminCount  = members.filter(m => m.role === "admin").length;
  const isLastAdmin = (m: ProjectMember) => m.role === "admin" && adminCount === 1;

  const roleChangeMut = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: MemberRole }) =>
      apiFetch(`/api/v1/organizations/projects/${projectId}/members/${userId}`, {
        method: "PATCH", json: { role },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["management", "members", projectId] }),
  });

  const removeMut = useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`/api/v1/organizations/projects/${projectId}/members/${userId}`, {
        method: "DELETE",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["management", "members", projectId] }),
  });

  function handleRoleChange(userId: string, newRole: MemberRole) {
    setOpenRoleMenu(null);
    roleChangeMut.mutate({ userId, role: newRole });
  }

  function handleRemove(member: ProjectMember) {
    if (isLastAdmin(member)) return;
    removeMut.mutate(member.user_id);
  }

  const isCurrentUser = (m: ProjectMember) => !!currentUser && currentUser.id === m.user_id;

  // Stats
  const roleCount: Record<string, number> = {};
  members.forEach(m => { roleCount[m.role] = (roleCount[m.role] ?? 0) + 1; });

  return (
    <div className="min-h-full bg-surface-base">
      {/* ── Page header ── */}
      <div className="flex items-center justify-between border-b border-border bg-surface-raised px-6 py-4">
        <div>
          <h1 className="text-[15px] font-semibold text-fg">Proje Üyeleri</h1>
          <p className="mt-0.5 text-[11px] text-fg-subtle">
            {loading ? "Yükleniyor…" : `${members.length} üye · Rol bazlı erişim kontrolü`}
          </p>
        </div>
        {canInvite && (
          <button
            type="button"
            onClick={() => setShowInvite(true)}
            className="flex items-center gap-1.5 rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 transition-colors"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/>
            </svg>
            Üye Davet Et
          </button>
        )}
      </div>

      {error && (
        <div className="flex items-center justify-between border-b border-danger/20 bg-danger-subtle px-6 py-2.5">
          <p className="text-[12px] text-danger">{error}</p>
          <button type="button" onClick={() => membersQuery.refetch()} className="text-[11px] text-danger/60 hover:text-danger">
            Yeniden dene
          </button>
        </div>
      )}

      <div className="mx-auto max-w-3xl space-y-5 p-6">
        {/* ── Stats row ── */}
        {!loading && members.length > 0 && (
          <div className="flex flex-wrap gap-3">
            {(["owner", "admin", "member", "viewer"] as MemberRole[]).map(role => {
              const count = roleCount[role] ?? 0;
              if (!count) return null;
              const cfg = ROLE_CONFIG[role];
              return (
                <div key={role} className={cn("flex items-center gap-2 rounded-lg border px-3 py-2", cfg.badge)}>
                  <span className={cn("h-2 w-2 rounded-full", cfg.dotColor)} />
                  <span className="text-[12px] font-medium">{cfg.qaLabel}</span>
                  <span className="ml-1 rounded-full bg-current/10 px-1.5 py-0.5 text-[10px] font-bold">
                    {count}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* ── Members list ── */}
        <section className="rounded-xl border border-border bg-surface-raised overflow-hidden">
          {loading ? (
            <MemberSkeleton />
          ) : members.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-accent">
                <svg className="h-6 w-6 text-fg-disabled" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"/>
                </svg>
              </div>
              <div>
                <p className="text-[13px] font-medium text-fg-muted">Henüz üye yok</p>
                <p className="mt-1 text-[11px] text-fg-subtle">
                  Projeye üye davet etmek için &quot;Üye Davet Et&quot; butonuna tıklayın.
                </p>
              </div>
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {members.map(member => {
                const isSelf    = isCurrentUser(member);
                const isOwner   = member.role === "owner";
                const lastAdmin = isLastAdmin(member);
                const canEdit   = !isSelf && !isOwner;
                const canRemove = canEdit && !lastAdmin;
                const cfg       = ROLE_CONFIG[member.role];

                return (
                  <li key={member.user_id}
                    className="flex items-center gap-3 px-6 py-3.5 hover:bg-surface-overlay transition-colors">
                    {/* Avatar */}
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft text-[11px] font-bold text-brand select-none">
                      {initials(member)}
                    </div>

                    {/* Name + email */}
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-[13px] font-medium text-fg">
                        {member.full_name ?? member.email}
                        {isSelf && <span className="ml-1.5 text-[10px] font-normal text-fg-subtle">(siz)</span>}
                      </p>
                      {member.full_name && (
                        <p className="truncate text-[11px] text-fg-subtle">{member.email}</p>
                      )}
                      <p className="mt-0.5 text-[10px] text-fg-disabled">{cfg.description}</p>
                    </div>

                    {/* Role badge */}
                    <span className={cn("rounded-full border px-2.5 py-0.5 text-[10px] font-medium shrink-0", cfg.badge)}>
                      {cfg.qaLabel}
                    </span>

                    {/* Role change dropdown */}
                    {canEdit && (
                      <div className="relative shrink-0">
                        <button
                          type="button"
                          disabled={lastAdmin || (roleChangeMut.isPending && roleChangeMut.variables?.userId === member.user_id)}
                          title={lastAdmin ? "Projede en az bir admin bulunmalı" : undefined}
                          onClick={() => setOpenRoleMenu(prev => prev === member.user_id ? null : member.user_id)}
                          className="rounded-lg border border-border px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg hover:border-border-strong transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          {roleChangeMut.isPending && roleChangeMut.variables?.userId === member.user_id ? "…" : "Rol Değiştir"}
                        </button>

                        {openRoleMenu === member.user_id && (
                          <div className="absolute right-0 top-full z-20 mt-1 min-w-[200px] rounded-xl border border-border bg-surface-raised shadow-elevated">
                            {SELECTABLE_ROLES.map(r => {
                              const rc = ROLE_CONFIG[r];
                              return (
                                <button key={r} type="button"
                                  onClick={() => handleRoleChange(member.user_id, r)}
                                  className={cn(
                                    "flex w-full items-start gap-2 px-3 py-2.5 text-left transition-colors hover:bg-surface-overlay first:rounded-t-xl last:rounded-b-xl",
                                    r === member.role ? "bg-surface-overlay" : ""
                                  )}>
                                  <span className={cn("mt-1 h-2 w-2 shrink-0 rounded-full", rc.dotColor)} />
                                  <div>
                                    <p className={cn("text-[12px] font-medium", r === member.role ? "text-brand" : "text-fg")}>
                                      {rc.qaLabel}
                                      {r === member.role && <span className="ml-1.5 text-[10px] text-brand/60">(mevcut)</span>}
                                    </p>
                                    <p className="text-[10px] text-fg-subtle">{rc.description}</p>
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Remove button */}
                    {canEdit && (
                      <button
                        type="button"
                        disabled={!canRemove || (removeMut.isPending && removeMut.variables === member.user_id)}
                        onClick={() => handleRemove(member)}
                        title={lastAdmin ? "Projede en az bir admin bulunmalı" : undefined}
                        className="shrink-0 rounded-lg px-2.5 py-1 text-[11px] text-fg-subtle hover:text-danger hover:bg-danger-subtle transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        {removeMut.isPending && removeMut.variables === member.user_id ? "…" : "Kaldır"}
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {/* ── Role info panel ── */}
        <RoleInfoPanel />
      </div>

      {showInvite && projectId && (
        <InviteModal
          projectId={projectId}
          existingEmails={existingEmails}
          onClose={() => setShowInvite(false)}
          onInvited={() => qc.invalidateQueries({ queryKey: ["management", "members", projectId] })}
        />
      )}

      {openRoleMenu && (
        <div className="fixed inset-0 z-10" onClick={() => setOpenRoleMenu(null)} />
      )}
    </div>
  );
}
