"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { StatCard, Avatar, EmptyState } from "@neurex/design-system";

// ─── Tip tanımları ────────────────────────────────────────────────────────────

type GlobalDashboard = {
  total_projects: number;
  total_scenarios: number;
  active_executions: number;
  overall_pass_rate: number;
  pending_approvals: number;
  weekly_trend: { date: string; runs: number; pass_rate: number }[];
  projects: { id: string; name: string; scenario_count: number; last_run: string | null; pass_rate: number | null; status: string }[];
  activities: { actor: string; action: string; time: string; resource_type: string; resource_id: string }[];
};

type AiHealth = {
  status: string;
  providers?: Record<string, boolean> | null;  // API bazen null/undefined döndürebilir
  version?: string;
};

// ─── Yardımcılar ──────────────────────────────────────────────────────────────

// Mock sparkline data — gerçek API trendi gelene kadar
function genSparkline(seed: number, length = 7): number[] {
  return Array.from({ length }, (_, i) => Math.floor(seed * 0.7 + Math.sin(i * 0.8 + seed) * 12 + Math.random() * 4));
}

function ActionLabel({ action }: { action: string }) {
  const labels: Record<string, string> = {
    "auth.login":          "Giriş yaptı",
    "auth.logout":         "Çıkış yaptı",
    "project.created":     "Yeni proje oluşturdu",
    "project.updated":     "Projeyi güncelledi",
    "scenario.created":    "Yeni senaryo ekledi",
    "scenario.updated":    "Senaryoyu güncelledi",
    "scenario.executed":   "Senaryo çalıştırdı",
    "execution.completed": "Koşu tamamlandı",
    "execution.failed":    "Koşu başarısız",
  };
  return <span>{labels[action] ?? action}</span>;
}

// ─── Sayfa ────────────────────────────────────────────────────────────────────

export default function AktiviteMonitoru() {
  const [data, setData]         = useState<GlobalDashboard | null>(null);
  const [aiHealth, setAiHealth] = useState<AiHealth | null>(null);
  const [loading, setLoading]   = useState(true);
  const [paused, setPaused]     = useState(false);
  // SSR/Client hydration mismatch'i önlemek için initial null — useEffect içinde set edilir
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [dash, health] = await Promise.allSettled([
        apiFetch<GlobalDashboard>("/api/v1/tspm/dashboard/global"),
        fetch("/api/ai/health").then(r => r.json()).catch(() => null) as Promise<AiHealth | null>,
      ]);
      if (dash.status === "fulfilled") setData(dash.value);
      if (health.status === "fulfilled" && health.value) setAiHealth(health.value);
      setLastUpdate(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  useEffect(() => {
    if (paused) return;
    const t = setInterval(fetchAll, 30_000);
    return () => clearInterval(t);
  }, [paused, fetchAll]);

  const fmt = (d: Date) => d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const activeProviders = aiHealth?.providers ? Object.entries(aiHealth.providers).filter(([, v]) => v) : [];
  const passRatePct = data ? Math.round((data.overall_pass_rate ?? 0) * 100) : 0;

  return (
    <div className="flex flex-col gap-6 p-6">

      {/* Başlık */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Aktivite Monitörü</h1>
          <p className="mt-0.5 text-sm text-slate-500">Test çalışmalarını ve sistem performansını takip edin</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* AI durumu */}
          {aiHealth && (
            <div className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300">
              <span className={`h-1.5 w-1.5 rounded-full ${activeProviders.length > 0 ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
              AI: {activeProviders.length > 0 ? activeProviders.map(([n]) => n).join(", ") : "Pasif"}
            </div>
          )}
          <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            CANLI
          </span>
          <button onClick={() => setPaused(v => !v)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white transition-colors">
            {paused ? "▶ Devam" : "⏸ Duraklat"}
          </button>
          <button onClick={fetchAll}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white transition-colors">
            Yenile
          </button>
          <span className="text-xs text-slate-600" suppressHydrationWarning>
            Son güncelleme: {lastUpdate ? fmt(lastUpdate) : "—"}
          </span>
        </div>
      </div>

      {/* Stat kartları */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard
          label="Toplam Proje"
          value={data?.total_projects ?? "—"}
          loading={loading}
          sparkline={data ? genSparkline(data.total_projects, 7) : undefined}
          tone="brand"
        />
        <StatCard
          label="Toplam Senaryo"
          value={data?.total_scenarios ?? "—"}
          loading={loading}
          sparkline={data ? genSparkline(data.total_scenarios, 7) : undefined}
        />
        <StatCard
          label="Aktif Koşu"
          value={data?.active_executions ?? "—"}
          loading={loading}
          tone="info"
          sparkline={data ? genSparkline(data.active_executions, 7) : undefined}
          trend={+8}
        />
        <StatCard
          label="Geçme Oranı"
          value={data ? `%${passRatePct}` : "—"}
          loading={loading}
          tone={passRatePct >= 90 ? "success" : passRatePct >= 70 ? "warning" : "danger"}
          sparkline={data ? genSparkline(passRatePct + 50, 7) : undefined}
          trend={passRatePct >= 80 ? +2 : -3}
        />
        <StatCard
          label="Bekleyen Onay"
          value={data?.pending_approvals ?? "—"}
          loading={loading}
          tone="warning"
          hint="aksiyon gerek"
        />
        <StatCard
          label="AI Sağlayıcı"
          value={activeProviders.length}
          hint={`${Object.keys(aiHealth?.providers ?? {}).length} mevcut`}
          loading={loading}
          tone="ai"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">

        {/* Top Projeler */}
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900">
          <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-3">
            <h2 className="text-sm font-semibold text-white">Aktif Projeler</h2>
            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-slate-700 px-1.5 text-[10px] font-bold text-slate-300">
              {data?.projects?.length ?? 0}
            </span>
            <Link href="/portfolio" className="ml-auto text-xs text-blue-400 hover:text-blue-300 transition-colors">Tümünü Gör →</Link>
          </div>
          <div className="divide-y divide-slate-800">
            {loading && [1, 2, 3].map(i => (
              <div key={i} className="px-4 py-3 animate-pulse">
                <div className="h-4 w-1/3 rounded bg-slate-800 mb-2" />
                <div className="h-3 w-1/4 rounded bg-slate-800" />
              </div>
            ))}
            {!loading && data?.projects?.slice(0, 6).map(p => (
              <Link key={p.id} href={`/p/${p.id}/scenarios`} className="block px-4 py-3 hover:bg-slate-800/50 transition-colors group">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-white group-hover:text-blue-300 transition-colors">{p.name}</p>
                    <p className="text-xs text-slate-500">
                      {p.scenario_count} senaryo {p.last_run ? `· Son koşu: ${new Date(p.last_run).toLocaleDateString("tr-TR")}` : "· Henüz koşu yok"}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {p.pass_rate !== null && (
                      <span className={`text-xs font-semibold ${p.pass_rate >= 0.9 ? "text-emerald-400" : p.pass_rate >= 0.7 ? "text-amber-400" : "text-red-400"}`}>
                        %{Math.round(p.pass_rate * 100)}
                      </span>
                    )}
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      p.status === "active"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-slate-500/10 text-slate-400 border border-slate-700"
                    }`}>
                      {p.status === "active" ? "AKTİF" : p.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
            {!loading && (!data?.projects || data.projects.length === 0) && (
              <div className="px-4 py-8 text-center text-sm text-slate-500">Henüz proje yok.</div>
            )}
          </div>
        </div>

        {/* AI Sağlayıcı Durumu */}
        <div className="rounded-xl border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-4 py-3">
            <h2 className="text-sm font-semibold text-white">AI Sağlayıcıları</h2>
            <p className="text-xs text-slate-500">Sağlayıcı durumu</p>
          </div>
          <div className="divide-y divide-slate-800">
            {!aiHealth?.providers ? (
              <div className="px-4 py-8 text-center text-sm text-slate-500">AI Gateway erişilemiyor</div>
            ) : (
              Object.entries(aiHealth.providers).map(([name, active]) => (
                <div key={name} className="flex items-center justify-between px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${active ? "bg-emerald-400" : "bg-slate-700"}`} />
                    <span className="text-sm text-slate-300 capitalize">{name}</span>
                  </div>
                  <span className={`text-xs font-semibold ${active ? "text-emerald-400" : "text-slate-600"}`}>
                    {active ? "Aktif" : "Pasif"}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Son Aktiviteler */}
      <div className="rounded-xl border border-slate-800 bg-slate-900">
        <div className="border-b border-slate-800 px-4 py-3">
          <h2 className="text-sm font-semibold text-white">Son Aktiviteler</h2>
          <p className="text-xs text-slate-500">Sistemdeki son hareketler</p>
        </div>
        <div className="divide-y divide-slate-800">
          {loading && [1, 2, 3, 4].map(i => (
            <div key={i} className="px-4 py-3 animate-pulse">
              <div className="h-3 w-1/2 rounded bg-slate-800 mb-2" />
              <div className="h-3 w-1/4 rounded bg-slate-800" />
            </div>
          ))}
          {!loading && data?.activities?.slice(0, 10).map((a, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-2.5">
              <Avatar name={a.actor} size="sm" shape="circle" seed={a.resource_id} />
              <div className="min-w-0 flex-1">
                <p className="text-sm text-slate-200">
                  <span className="font-medium text-white">{a.actor}</span>
                  {" — "}
                  <ActionLabel action={a.action} />
                </p>
              </div>
              <span className="shrink-0 text-xs text-slate-500 tabular-nums">{a.time}</span>
            </div>
          ))}
          {!loading && (!data?.activities || data.activities.length === 0) && (
            <div className="px-4 py-8 text-center text-sm text-slate-500">Henüz aktivite yok.</div>
          )}
        </div>
      </div>

    </div>
  );
}
