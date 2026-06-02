"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";

type UserRow = {
  id: string;
  email: string;
  full_name: string | null;
  department: string | null;
  is_active: boolean;
  roles: string[];
  created_at: string | null;
};

const inputCls = "w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition-colors";

const usersQK = ["admin", "users"] as const;
const invitesQK = ["admin", "invitations"] as const;

type InvitationRow = {
  id: string;
  email: string;
  role: string;
  team_id: string | null;
  expires_at: string;
  created_at: string;
};

export default function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("viewer");
  const [err, setErr] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviteErr, setInviteErr] = useState<string | null>(null);

  const { data: users = [] } = useQuery<UserRow[]>({
    queryKey: usersQK,
    queryFn: () => apiFetch<UserRow[]>("/api/v1/auth/users"),
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) => u.email.toLowerCase().includes(q) || (u.full_name ?? "").toLowerCase().includes(q)
    );
  }, [users, search]);

  const createMut = useMutation({
    mutationFn: () =>
      apiFetch("/api/v1/auth/users", {
        method: "POST",
        json: { email, password: pw, full_name: fullName, role },
      }),
    onSuccess: () => {
      setEmail(""); setPw(""); setFullName("");
      queryClient.invalidateQueries({ queryKey: usersQK });
    },
    onError: (e: unknown) => setErr(e instanceof Error ? e.message : "Hata"),
  });

  const { data: invitations = [] } = useQuery<InvitationRow[]>({
    queryKey: invitesQK,
    queryFn: () => apiFetch<InvitationRow[]>("/api/v1/organizations/invitations"),
    staleTime: 60 * 1000,
  });

  const inviteMut = useMutation({
    mutationFn: () =>
      apiFetch("/api/v1/organizations/invitations", {
        method: "POST",
        json: { email: inviteEmail, role: inviteRole },
      }),
    onSuccess: () => {
      setInviteEmail("");
      setInviteErr(null);
      queryClient.invalidateQueries({ queryKey: invitesQK });
    },
    onError: (e: unknown) =>
      setInviteErr(e instanceof Error ? e.message : "Davet gonderilemedi"),
  });

  const revokeInviteMut = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/organizations/invitations/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: invitesQK }),
  });

  const toggleMut = useMutation({
    mutationFn: (u: UserRow) =>
      apiFetch(`/api/v1/auth/users/${u.id}`, { method: "PUT", json: { is_active: !u.is_active } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersQK }),
  });

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    createMut.mutate();
  }

  function toggleActive(u: UserRow) {
    toggleMut.mutate(u);
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6" data-testid="admin-users-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        }
        title="Kullanıcı Yönetimi"
        description="Platform kullanıcılarını yönetin"
        data-testid="admin-users-heading"
      />

      <input
        placeholder="E-posta veya ada göre ara…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className={`${inputCls} max-w-sm`}
        data-testid="admin-users-input-search"
      />

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">Yeni Kullanıcı Ekle</h2>
        <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3" data-testid="admin-users-form">
          <div className="min-w-[160px] flex-1 flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">E-posta</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} required type="email" className={inputCls} data-testid="admin-users-input-email" />
          </div>
          <div className="min-w-[120px] flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">Şifre</label>
            <input value={pw} onChange={(e) => setPw(e.target.value)} required type="password" minLength={6} className={inputCls} data-testid="admin-users-input-password" />
          </div>
          <div className="min-w-[140px] flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">Ad Soyad</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputCls} data-testid="admin-users-input-name" />
          </div>
          <div className="min-w-[100px] flex flex-col gap-1.5">
            <label htmlFor="admin-role-select" className="text-xs font-medium text-slate-400">Rol</label>
            <select id="admin-role-select" value={role} onChange={(e) => setRole(e.target.value)} className={inputCls} data-testid="admin-users-select-role">
              <option value="viewer">Viewer</option>
              <option value="operator">Operator</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button type="submit" data-testid="admin-users-btn-create" className="px-4 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors">
            Ekle
          </button>
        </form>
        {err && <p className="mt-3 text-sm text-red-400" data-testid="admin-users-alert-error">{err}</p>}
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">Ekip Daveti</h2>
        <form
          onSubmit={(e) => { e.preventDefault(); inviteMut.mutate(); }}
          className="flex flex-wrap items-end gap-3"
          data-testid="admin-invite-form"
        >
          <div className="min-w-[200px] flex-1 flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">E-posta</label>
            <input
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
              type="email"
              className={inputCls}
              data-testid="admin-invite-input-email"
            />
          </div>
          <div className="min-w-[120px] flex flex-col gap-1.5">
            <label htmlFor="invite-role-select" className="text-xs font-medium text-slate-400">Rol</label>
            <select
              id="invite-role-select"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className={inputCls}
              data-testid="admin-invite-select-role"
            >
              <option value="viewer">Viewer</option>
              <option value="member">Member</option>
              <option value="operator">Operator</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={inviteMut.isPending}
            data-testid="admin-invite-btn-send"
            className="px-4 py-2.5 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-xl transition-colors disabled:opacity-50"
          >
            {inviteMut.isPending ? "Gonderiliyor..." : "Davet Gonder"}
          </button>
        </form>
        {inviteErr && <p className="mt-3 text-sm text-red-400">{inviteErr}</p>}

        {invitations.length > 0 && (
          <div className="mt-5">
            <h3 className="text-xs font-semibold text-slate-400 mb-2">Bekleyen Davetler ({invitations.length})</h3>
            <div className="rounded-lg border border-slate-800 divide-y divide-slate-800">
              {invitations.map((inv) => (
                <div key={inv.id} className="flex items-center justify-between px-3 py-2 text-xs">
                  <div className="flex items-center gap-3">
                    <span className="text-white">{inv.email}</span>
                    <span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-blue-400">{inv.role}</span>
                    <span className="text-slate-500">Sonlanir: {new Date(inv.expires_at).toLocaleDateString("tr-TR")}</span>
                  </div>
                  <button
                    onClick={() => revokeInviteMut.mutate(inv.id)}
                    className="text-red-400 hover:text-red-300"
                  >
                    Iptal
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
        <div className="border-b border-slate-800 px-5 py-3">
          <span className="text-xs text-slate-500">{filtered.length} / {users.length} kullanıcı</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm" data-testid="admin-users-table">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs text-slate-500">
                <th className="px-5 py-3 font-medium">E-posta</th>
                <th className="px-5 py-3 font-medium">Ad Soyad</th>
                <th className="px-5 py-3 font-medium">Rol</th>
                <th className="px-5 py-3 font-medium">Durum</th>
                <th className="px-5 py-3 font-medium">İşlem</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30 transition-colors" data-testid={`admin-users-row-${u.id}`}>
                  <td className="px-5 py-3 text-white">{u.email}</td>
                  <td className="px-5 py-3 text-slate-400">{u.full_name || "—"}</td>
                  <td className="px-5 py-3">
                    <span className="inline-flex rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[11px] font-medium text-blue-400">
                      {u.roles.join(", ") || "—"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                      u.is_active
                        ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                        : "border-red-500/20 bg-red-500/10 text-red-400"
                    }`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${u.is_active ? "bg-emerald-400" : "bg-red-400"}`} />
                      {u.is_active ? "Aktif" : "Pasif"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <button
                      type="button"
                      onClick={() => toggleActive(u)}
                      className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                      data-testid={`admin-users-btn-toggle-${u.id}`}
                    >
                      {u.is_active ? "Deaktif Et" : "Aktif Et"}
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-10 text-center text-sm text-slate-500">
                    {search ? `"${search}" için sonuç bulunamadı.` : "Kullanıcı yok."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
