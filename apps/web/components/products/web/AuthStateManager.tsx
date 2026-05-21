"use client";

import { useState } from "react";
import { useToast } from "@/components/ui/toast";

interface AuthRole {
  id: string;
  role: string;
  user: string;
  storage: "fresh" | "stale" | "expired";
  ageMin: number;
  cookieCount: number;
  lsCount: number;
  lastRefresh: string;
}

const DEMO_ROLES: AuthRole[] = [
  { id: "admin", role: "Admin",      user: "ops@neurex.dev",       storage: "fresh",   ageMin: 12,   cookieCount: 8,  lsCount: 14, lastRefresh: "12 dk" },
  { id: "user",  role: "Standard",   user: "user@example.com",     storage: "fresh",   ageMin: 38,   cookieCount: 6,  lsCount: 9,  lastRefresh: "38 dk" },
  { id: "vip",   role: "Premium",    user: "premium@example.com",  storage: "stale",   ageMin: 124,  cookieCount: 7,  lsCount: 11, lastRefresh: "2 sa" },
  { id: "guest", role: "Guest",      user: "—",                    storage: "expired", ageMin: 1440, cookieCount: 2,  lsCount: 0,  lastRefresh: "24 sa" },
];

function statusBadge(s: AuthRole["storage"]) {
  if (s === "fresh")   return { cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", label: "Taze" };
  if (s === "stale")   return { cls: "bg-amber-500/15 text-amber-300 border-amber-500/30",       label: "Eskidi" };
  return { cls: "bg-rose-500/15 text-rose-300 border-rose-500/30", label: "Süresi doldu" };
}

export function AuthStateManager() {
  const { toast } = useToast();
  const [roles, setRoles] = useState<AuthRole[]>(DEMO_ROLES);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  const refresh = async (id: string) => {
    setRefreshingId(id);
    await new Promise((r) => setTimeout(r, 700));
    const role = roles.find((r) => r.id === id);
    setRoles((rs) =>
      rs.map((r) => (r.id === id ? { ...r, storage: "fresh", ageMin: 0, lastRefresh: "az önce" } : r)),
    );
    setRefreshingId(null);
    toast(`${role?.role ?? "Rol"} storageState yenilendi`, "success");
  };

  const freshCount  = roles.filter((r) => r.storage === "fresh").length;
  const reuseBoost  = Math.round((freshCount / roles.length) * 100);

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-sm flex-shrink-0">
            🔐
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-white truncate">Auth State Manager</h2>
            <p className="text-[11px] text-slate-400 truncate">Login bir kere — testler reuse etsin</p>
          </div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
          {reuseBoost}% reuse
        </span>
      </div>

      {/* Rol listesi */}
      <div className="p-3 space-y-2">
        {roles.map((r) => {
          const b = statusBadge(r.storage);
          const isRefreshing = refreshingId === r.id;
          return (
            <div
              key={r.id}
              className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2.5 flex items-center gap-3"
            >
              <div className="h-8 w-8 rounded-md bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-300">
                {r.role[0]}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-semibold text-white truncate">{r.role}</p>
                  <span className={`text-[9px] uppercase tracking-wider font-bold px-1.5 py-0.5 rounded border ${b.cls}`}>
                    {b.label}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 truncate">
                  {r.user} · {r.cookieCount} cookie · {r.lsCount} ls · {r.lastRefresh} önce
                </p>
              </div>
              <button
                onClick={() => void refresh(r.id)}
                disabled={isRefreshing}
                className="text-[10px] px-2 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-wait"
              >
                {isRefreshing ? "…" : "Yenile"}
              </button>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
        <span>Tahmini tasarruf: <span className="text-emerald-300 font-semibold">~6sn/test</span></span>
        <button className="text-emerald-400 hover:underline">storageState ekle →</button>
      </div>
    </div>
  );
}
