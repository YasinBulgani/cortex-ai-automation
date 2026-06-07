"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/nexus";

const inputCls =
  "w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";

type Team = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
  member_count: number;
};

type Member = {
  user_id: string;
  email: string;
  full_name: string | null;
  role: string;
  joined_at: string;
};

const teamsQK = ["admin", "teams"] as const;

export default function AdminTeamsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [desc, setDesc] = useState("");
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState("member");

  const { data: teams = [], isLoading: teamsLoading, isError: teamsError } = useQuery<Team[]>({
    queryKey: teamsQK,
    queryFn: () => apiFetch<Team[]>("/api/v1/organizations/me/teams"),
    retry: 1,
  });

  const { data: members = [], isLoading: membersLoading } = useQuery<Member[]>({
    queryKey: ["admin", "teams", selectedTeam, "members"],
    queryFn: () =>
      apiFetch<Member[]>(`/api/v1/organizations/teams/${selectedTeam}/members`),
    enabled: !!selectedTeam,
  });

  const createTeam = useMutation({
    mutationFn: () =>
      apiFetch("/api/v1/organizations/me/teams", {
        method: "POST",
        json: { name, slug, description: desc || undefined },
      }),
    onSuccess: () => {
      setName(""); setSlug(""); setDesc(""); setErr(null);
      qc.invalidateQueries({ queryKey: teamsQK });
    },
    onError: (e: unknown) => setErr(e instanceof Error ? e.message : "Hata"),
  });

  const addMember = useMutation({
    mutationFn: async () => {
      // Resolve user_id by email via users API
      const users = await apiFetch<Array<{ id: string; email: string }>>("/api/v1/auth/users");
      const u = users.find((x) => x.email.toLowerCase() === memberEmail.toLowerCase());
      if (!u) throw new Error("Kullanici bulunamadi (once davet edin)");
      return apiFetch(`/api/v1/organizations/teams/${selectedTeam}/members`, {
        method: "POST",
        json: { user_id: u.id, role: memberRole },
      });
    },
    onSuccess: () => {
      setMemberEmail("");
      qc.invalidateQueries({ queryKey: ["admin", "teams", selectedTeam, "members"] });
      qc.invalidateQueries({ queryKey: teamsQK });
    },
    onError: (e: unknown) => setErr(e instanceof Error ? e.message : "Uye eklenemedi"),
  });

  const removeMember = useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`/api/v1/organizations/teams/${selectedTeam}/members/${userId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "teams", selectedTeam, "members"] });
      qc.invalidateQueries({ queryKey: teamsQK });
    },
  });

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6">
      <PageHeader
        title="Ekipler"
        description="Organizasyon icindeki ekipleri yonetin"
      />

      {/* Create team */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">Yeni Ekip</h2>
        <form
          onSubmit={(e) => { e.preventDefault(); createTeam.mutate(); }}
          className="flex flex-wrap items-end gap-3"
        >
          <div className="min-w-[180px] flex-1 flex flex-col gap-1.5">
            <label className="text-xs text-slate-400">Ad</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required className={inputCls} />
          </div>
          <div className="min-w-[140px] flex flex-col gap-1.5">
            <label className="text-xs text-slate-400">Slug</label>
            <input
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"))}
              required pattern="[a-z0-9-]+"
              className={inputCls}
            />
          </div>
          <div className="min-w-[200px] flex-1 flex flex-col gap-1.5">
            <label className="text-xs text-slate-400">Aciklama</label>
            <input value={desc} onChange={(e) => setDesc(e.target.value)} className={inputCls} />
          </div>
          <button
            type="submit"
            className="px-4 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl"
          >
            Olustur
          </button>
        </form>
        {err && <p className="mt-3 text-sm text-red-400">{err}</p>}
      </div>

      {/* Team list */}
      {teamsLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="h-4 w-28 animate-pulse rounded bg-slate-800" />
              <div className="mt-1 h-3 w-16 animate-pulse rounded bg-slate-800" />
              <div className="mt-3 h-3 w-12 animate-pulse rounded bg-slate-800" />
            </div>
          ))}
        </div>
      ) : teamsError ? (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-center">
          <p className="text-sm font-medium text-red-400">Ekipler yüklenemedi</p>
          <p className="mt-1 text-xs text-slate-500">Sunucuya bağlanılamadı.</p>
        </div>
      ) : teams.length === 0 ? (
        <EmptyState
          icon="👥"
          title="Henüz ekip yok"
          description="Yukarıdaki formu kullanarak ilk ekibi oluşturun"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {teams.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelectedTeam(t.id)}
              className={`text-left rounded-xl border p-4 transition-colors ${
                selectedTeam === t.id
                  ? "border-blue-500 bg-blue-500/10"
                  : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
              }`}
            >
              <div className="text-sm font-semibold text-white">{t.name}</div>
              <div className="text-xs text-slate-500">/{t.slug}</div>
              <div className="text-xs text-slate-400 mt-2">{t.member_count} üye</div>
            </button>
          ))}
        </div>
      )}

      {/* Members panel */}
      {selectedTeam && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">
            Ekip Uyeleri ({members.length})
          </h2>
          <form
            onSubmit={(e) => { e.preventDefault(); addMember.mutate(); }}
            className="flex flex-wrap items-end gap-3 mb-4"
          >
            <div className="min-w-[200px] flex-1 flex flex-col gap-1.5">
              <label className="text-xs text-slate-400">Kullanici e-postasi</label>
              <input
                type="email"
                value={memberEmail}
                onChange={(e) => setMemberEmail(e.target.value)}
                className={inputCls}
                required
              />
            </div>
            <div className="min-w-[120px] flex flex-col gap-1.5">
              <label className="text-xs text-slate-400">Rol</label>
              <select value={memberRole} onChange={(e) => setMemberRole(e.target.value)} className={inputCls}>
                <option value="viewer">Viewer</option>
                <option value="member">Member</option>
                <option value="admin">Admin</option>
                <option value="owner">Owner</option>
              </select>
            </div>
            <button type="submit" className="px-4 py-2.5 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-xl">
              Ekle
            </button>
          </form>

          {membersLoading ? (
            <div className="rounded-lg border border-slate-800">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center justify-between border-b border-slate-800 px-3 py-2.5 last:border-0">
                  <div className="h-3 w-36 animate-pulse rounded bg-slate-800" />
                  <div className="h-5 w-14 animate-pulse rounded-full bg-slate-800" />
                </div>
              ))}
            </div>
          ) : members.length === 0 ? (
            <div className="rounded-lg border border-slate-800 px-3 py-8 text-center">
              <p className="text-xs text-slate-500">Bu ekipte henüz üye yok.</p>
              <p className="mt-1 text-xs text-slate-600">Yukarıdaki formu kullanarak üye ekleyin.</p>
            </div>
          ) : (
            <div className="rounded-lg border border-slate-800 divide-y divide-slate-800">
              {members.map((m) => (
                <div key={m.user_id} className="flex items-center justify-between px-3 py-2 text-xs">
                  <div>
                    <span className="text-white">{m.email}</span>
                    {m.full_name && <span className="text-slate-500 ml-2">— {m.full_name}</span>}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-blue-400">{m.role}</span>
                    <button onClick={() => removeMember.mutate(m.user_id)} className="text-red-400 hover:text-red-300">
                      Kaldır
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
