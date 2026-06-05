"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouteParam } from "@/lib/use-route-param";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { apiFetch } from "@/lib/api-client";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

type MemberRole = "owner" | "admin" | "member" | "viewer";

interface ProjectMember {
  user_id: string;
  email: string;
  full_name?: string;
  role: MemberRole;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<MemberRole, string> = {
  owner:  "Owner",
  admin:  "Admin",
  member: "Member",
  viewer: "Viewer",
};

const ROLE_BADGE: Record<MemberRole, string> = {
  owner:  "bg-amber-500/15 text-amber-400 border-amber-500/20",
  admin:  "bg-purple-500/15 text-purple-400 border-purple-500/20",
  member: "bg-teal-500/15 text-teal-400 border-teal-500/20",
  viewer: "bg-slate-500/15 text-slate-400 border-slate-500/20",
};

const SELECTABLE_ROLES: MemberRole[] = ["admin", "member", "viewer"];

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
          <div className="h-8 w-8 rounded-full bg-white/[0.06]" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 w-32 rounded bg-white/[0.06]" />
            <div className="h-2.5 w-48 rounded bg-white/[0.04]" />
          </div>
          <div className="h-5 w-16 rounded-full bg-white/[0.06]" />
        </div>
      ))}
    </div>
  );
}

// ── Invite Modal ──────────────────────────────────────────────────────────────

interface InviteModalProps {
  projectId: string;
  onClose: () => void;
  onInvited: () => void;
}

function InviteModal({ projectId, onClose, onInvited }: InviteModalProps) {
  const [email, setEmail]   = useState("");
  const [role, setRole]     = useState<MemberRole>("member");
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await apiFetch(`/api/v1/organizations/projects/${projectId}/members`, {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), role }),
      });
      onInvited();
      onClose();
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
          <h3 className="text-[14px] font-semibold text-slate-200">Üye Davet Et</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            className="rounded-md p-1 text-slate-500 hover:text-slate-300 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">E-posta</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="kullanici@sirket.com"
              className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
            />
          </div>

          <div>
            <label className="mb-1 block text-[11px] text-slate-500">Rol</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value as MemberRole)}
              className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/50"
            >
              {SELECTABLE_ROLES.map(r => (
                <option key={r} value={r}>{ROLE_LABELS[r]}</option>
              ))}
            </select>
          </div>

          {error && (
            <p className="rounded-lg bg-red-500/10 px-3 py-2 text-[12px] text-red-400">{error}</p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-border px-4 py-2 text-[12px] text-slate-400 hover:text-slate-200 transition-colors"
            >
              İptal
            </button>
            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-50 transition-colors"
            >
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
  const projectId = useRouteParam("projectId");
  const { user: currentUser } = useCurrentUser();
  const qc = useQueryClient();

  const [showInvite, setShowInvite] = useState(false);
  const [openRoleMenu, setOpenRoleMenu] = useState<string | null>(null);

  const membersQuery = useQuery({
    queryKey: ["management", "members", projectId],
    queryFn: () =>
      apiFetch<ProjectMember[]>(
        `/api/v1/organizations/projects/${projectId}/members`
      ).then(data => (Array.isArray(data) ? data : [])),
    enabled: !!projectId,
  });

  const members  = membersQuery.data ?? [];
  const loading  = membersQuery.isLoading;
  const error    = membersQuery.isError
    ? (membersQuery.error instanceof Error
        ? membersQuery.error.message
        : "Üyeler yüklenemedi.")
    : null;

  const roleChangeMut = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: MemberRole }) =>
      apiFetch(`/api/v1/organizations/projects/${projectId}/members/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["management", "members", projectId] }),
  });

  const removeMut = useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`/api/v1/organizations/projects/${projectId}/members/${userId}`, {
        method: "DELETE",
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["management", "members", projectId] }),
  });

  function handleRoleChange(userId: string, newRole: MemberRole) {
    setOpenRoleMenu(null);
    roleChangeMut.mutate({ userId, role: newRole });
  }

  function handleRemove(userId: string) {
    removeMut.mutate(userId);
  }

  const isCurrentUser = (m: ProjectMember) =>
    !!currentUser && currentUser.id === m.user_id;

  return (
    <div className="min-h-[calc(100vh-88px)] bg-bg text-slate-200">

      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-border bg-surface-raised px-6 py-4">
        <div>
          <h1 className="text-[13px] font-semibold text-slate-200">Üyeler</h1>
          <p className="mt-0.5 text-[11px] text-slate-500">
            {loading ? "Yükleniyor…" : `${members.length} üye`}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowInvite(true)}
          className="flex items-center gap-1.5 rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 transition-colors"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
          </svg>
          Üye Davet Et
        </button>
      </div>

      {/* ── Error banner ──────────────────────────────────────────────────── */}
      {error && (
        <div className="flex items-center justify-between border-b border-red-500/20 bg-red-500/10 px-6 py-2.5">
          <p className="text-[12px] text-red-400">{error}</p>
          <button
            type="button"
            onClick={() => membersQuery.refetch()}
            className="text-[11px] text-red-400/60 hover:text-red-400 transition-colors"
          >
            Yeniden dene
          </button>
        </div>
      )}

      {/* ── Members list ──────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-3xl p-6">
        <section className="rounded-xl border border-border bg-surface-raised overflow-hidden">

          {loading ? (
            <MemberSkeleton />
          ) : members.length === 0 ? (
            /* ── Empty state ── */
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/[0.04]">
                <svg className="h-6 w-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"/>
                </svg>
              </div>
              <div>
                <p className="text-[13px] font-medium text-slate-400">Henüz üye yok</p>
                <p className="mt-1 text-[11px] text-slate-600">
                  Projeye üye davet etmek için "Üye Davet Et" butonuna tıklayın.
                </p>
              </div>
            </div>
          ) : (
            /* ── Member rows ── */
            <ul className="divide-y divide-border">
              {members.map(member => {
                const isSelf  = isCurrentUser(member);
                const isOwner = member.role === "owner";
                const canEdit = !isSelf && !isOwner;

                return (
                  <li
                    key={member.user_id}
                    className="flex items-center gap-3 px-6 py-3.5 hover:bg-white/[0.02] transition-colors"
                  >
                    {/* Avatar */}
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft text-[11px] font-bold text-brand select-none">
                      {initials(member)}
                    </div>

                    {/* Name + email */}
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-[13px] font-medium text-slate-200">
                        {member.full_name ?? member.email}
                        {isSelf && (
                          <span className="ml-1.5 text-[10px] font-normal text-slate-500">(siz)</span>
                        )}
                      </p>
                      {member.full_name && (
                        <p className="truncate text-[11px] text-slate-500">{member.email}</p>
                      )}
                    </div>

                    {/* Role badge */}
                    <span className={cn(
                      "rounded-full border px-2.5 py-0.5 text-[10px] font-medium shrink-0",
                      ROLE_BADGE[member.role]
                    )}>
                      {ROLE_LABELS[member.role]}
                    </span>

                    {/* Role change dropdown */}
                    {canEdit && (
                      <div className="relative shrink-0">
                        <button
                          type="button"
                          disabled={roleChangeMut.isPending && roleChangeMut.variables?.userId === member.user_id}
                          onClick={() =>
                            setOpenRoleMenu(prev =>
                              prev === member.user_id ? null : member.user_id
                            )
                          }
                          className="rounded-lg border border-border px-2.5 py-1 text-[11px] text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors disabled:opacity-50"
                        >
                          {roleChangeMut.isPending && roleChangeMut.variables?.userId === member.user_id ? "…" : "Rol Değiştir"}
                        </button>

                        {openRoleMenu === member.user_id && (
                          <div className="absolute right-0 top-full z-20 mt-1 min-w-[120px] rounded-xl border border-border bg-surface-raised shadow-elevated">
                            {SELECTABLE_ROLES.map(r => (
                              <button
                                key={r}
                                type="button"
                                onClick={() => handleRoleChange(member.user_id, r)}
                                className={cn(
                                  "flex w-full items-center px-3 py-2 text-[12px] transition-colors hover:bg-surface-overlay",
                                  r === member.role
                                    ? "text-brand font-medium"
                                    : "text-slate-400 hover:text-slate-200"
                                )}
                              >
                                {r === member.role && (
                                  <svg className="mr-1.5 h-3 w-3 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                                  </svg>
                                )}
                                {ROLE_LABELS[r]}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Remove button */}
                    {canEdit && (
                      <button
                        type="button"
                        disabled={removeMut.isPending && removeMut.variables === member.user_id}
                        onClick={() => handleRemove(member.user_id)}
                        className="shrink-0 rounded-lg px-2.5 py-1 text-[11px] text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50"
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
      </div>

      {/* ── Invite modal ──────────────────────────────────────────────────── */}
      {showInvite && projectId && (
        <InviteModal
          projectId={projectId}
          onClose={() => setShowInvite(false)}
          onInvited={() =>
            qc.invalidateQueries({ queryKey: ["management", "members", projectId] })
          }
        />
      )}

      {/* ── Close role menu on outside click ──────────────────────────────── */}
      {openRoleMenu && (
        <div
          className="fixed inset-0 z-10"
          onClick={() => setOpenRoleMenu(null)}
        />
      )}
    </div>
  );
}
