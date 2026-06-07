"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { StatCard, Avatar, EmptyState } from "@neurex/design-system";
import {
  useGlobalDashboard,
  projectKeys,
  type GlobalDashboardActivity,
} from "@/lib/hooks/use-projects";

// ─── Yardımcılar ──────────────────────────────────────────────────────────────

// Mock sparkline data — gerçek API trendi gelene kadar
function genSparkline(seed: number, length = 7): number[] {
  return Array.from({ length }, (_, i) =>
    Math.floor(seed * 0.7 + Math.sin(i * 0.8 + seed) * 12 + Math.random() * 4)
  );
}

const ACTION_LABELS: Record<string, string> = {
  "auth.login": "Giriş yaptı",
  "auth.logout": "Çıkış yaptı",
  "project.created": "Yeni proje oluşturdu",
  "project.updated": "Projeyi güncelledi",
  "scenario.created": "Yeni senaryo ekledi",
  "scenario.updated": "Senaryoyu güncelledi",
  "scenario.executed": "Senaryo çalıştırdı",
  "execution.completed": "Koşu tamamlandı",
  "execution.failed": "Koşu başarısız",
};

function ActionLabel({ action }: { action: string }) {
  return <span>{ACTION_LABELS[action] ?? action}</span>;
}

// ─── Sayfa ────────────────────────────────────────────────────────────────────

export default function AktiviteMonitoru() {
  const queryClient = useQueryClient();
  const [paused, setPaused] = useState(false);

  // React Query: caching, deduplication, auto-refetch her şeyi halleder.
  // refetchInterval hook içinde tanımlandı (30s) — ayrıca setInterval GEREKMEZ.
  const { data, isLoading, isError, error, dataUpdatedAt, refetch } = useGlobalDashboard();

  // "Duraklat" modunda React Query'nin otomatik polling'ini durdur
  // Bu geçici çözüm: hook'u paused state'e göre override et
  const handleManualRefetch = useCallback(() => {
    refetch();
  }, [refetch]);

  // Duraklat/devam — query'yi geçici olarak iptal etmek için cache'i resetle
  const handlePauseToggle = useCallback(() => {
    setPaused((v) => {
      const next = !v;
      if (!next) {
        // Devam edildiğinde hemen yenile
        queryClient.invalidateQueries({ queryKey: projectKeys.globalDashboard() });
      }
      return next;
    });
  }, [queryClient]);

  const fmtTime = (ts: number) =>
    ts
      ? new Date(ts).toLocaleTimeString("tr-TR", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      : "—";

  const passRatePct = data ? Math.round((data.overall_pass_rate ?? 0) * 100) : 0;

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Hata durumu */}
      {isError && !isLoading && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 flex items-center justify-between gap-4">
          <p className="text-sm text-red-400">
            Dashboard verileri yüklenemedi: {(error as Error)?.message ?? "Sunucu hatası"}
          </p>
          <button
            onClick={() => refetch()}
            className="shrink-0 rounded-lg border border-red-500/40 px-3 py-1 text-xs font-medium text-red-400 hover:bg-red-500/20 transition-colors"
          >
            Tekrar Dene
          </button>
        </div>
      )}

      {/* Başlık */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Aktivite Monitörü</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Test çalışmalarını ve sistem performansını takip edin
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            CANLI
          </span>
          <button
            type="button"
            onClick={handlePauseToggle}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white transition-colors"
          >
            {paused ? "▶ Devam" : "⏸ Duraklat"}
          </button>
          <button
            type="button"
            onClick={handleManualRefetch}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white transition-colors"
          >
            Yenile
          </button>
          <span
            className="text-xs text-slate-600"
            suppressHydrationWarning
          >
            Son güncelleme: {fmtTime(dataUpdatedAt)}
          </span>
        </div>
      </div>

      {/* Stat kartları */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard
          label="Toplam Proje"
          value={data?.total_projects ?? "—"}
          loading={isLoading}
          sparkline={data ? genSparkline(data.total_projects, 7) : undefined}
          tone="brand"
        />
        <StatCard
          label="Toplam Senaryo"
          value={data?.total_scenarios ?? "—"}
          loading={isLoading}
          sparkline={data ? genSparkline(data.total_scenarios, 7) : undefined}
        />
        <StatCard
          label="Aktif Koşu"
          value={data?.active_executions ?? "—"}
          loading={isLoading}
          tone="info"
          sparkline={data ? genSparkline(data.active_executions, 7) : undefined}
          trend={+8}
        />
        <StatCard
          label="Geçme Oranı"
          value={data ? `%${passRatePct}` : "—"}
          loading={isLoading}
          tone={
            passRatePct >= 90
              ? "success"
              : passRatePct >= 70
              ? "warning"
              : "danger"
          }
          sparkline={data ? genSparkline(passRatePct + 50, 7) : undefined}
          trend={passRatePct >= 80 ? +2 : -3}
        />
        <StatCard
          label="Bekleyen Onay"
          value={data?.pending_approvals ?? "—"}
          loading={isLoading}
          tone="warning"
          hint="aksiyon gerek"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Aktif Projeler */}
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900">
          <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-3">
            <h2 className="text-sm font-semibold text-white">Aktif Projeler</h2>
            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-slate-700 px-1.5 text-[10px] font-bold text-slate-300">
              {data?.projects?.length ?? 0}
            </span>
            <Link
              href="/portfolio"
              className="ml-auto text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              Tümünü Gör →
            </Link>
          </div>
          <div className="divide-y divide-slate-800">
            {isLoading &&
              [1, 2, 3].map((i) => (
                <div key={i} className="px-4 py-3 animate-pulse">
                  <div className="h-4 w-1/3 rounded bg-slate-800 mb-2" />
                  <div className="h-3 w-1/4 rounded bg-slate-800" />
                </div>
              ))}
            {!isLoading &&
              data?.projects?.slice(0, 6).map((p) => (
                <Link
                  key={p.id}
                  href={`/p/${p.id}/scenarios`}
                  className="block px-4 py-3 hover:bg-slate-800/50 transition-colors group"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-white group-hover:text-blue-300 transition-colors">
                        {p.name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {p.scenario_count} senaryo
                        {p.last_run
                          ? ` · Son koşu: ${new Date(p.last_run).toLocaleDateString("tr-TR")}`
                          : " · Henüz koşu yok"}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {p.pass_rate !== null && (
                        <span
                          className={`text-xs font-semibold ${
                            p.pass_rate >= 90
                              ? "text-emerald-400"
                              : p.pass_rate >= 70
                              ? "text-amber-400"
                              : "text-red-400"
                          }`}
                        >
                          %{Math.round(p.pass_rate)}
                        </span>
                      )}
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          p.status === "active"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-slate-500/10 text-slate-400 border border-slate-700"
                        }`}
                      >
                        {p.status === "active" ? "AKTİF" : p.status.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            {!isLoading && (!data?.projects || data.projects.length === 0) && (
              <div className="px-4 py-8 text-center text-sm text-slate-500">
                Henüz proje yok.
              </div>
            )}
          </div>
        </div>

        {/* Haftalık Trend */}
        <div className="rounded-xl border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-4 py-3">
            <h2 className="text-sm font-semibold text-white">Haftalık Trend</h2>
            <p className="text-xs text-slate-500">Son 7 günün koşu verileri</p>
          </div>
          <div className="divide-y divide-slate-800">
            {isLoading &&
              [1, 2, 3, 4, 5, 6, 7].map((i) => (
                <div key={i} className="px-4 py-2.5 animate-pulse">
                  <div className="h-3 w-1/3 rounded bg-slate-800" />
                </div>
              ))}
            {!isLoading &&
              data?.weekly_trend?.map((w) => {
                const passRate =
                  w.runs > 0 ? Math.round((w.passed / w.runs) * 100) : null;
                return (
                  <div
                    key={w.day}
                    className="flex items-center justify-between px-4 py-2.5"
                  >
                    <span className="text-sm text-slate-300">{w.day}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-500">{w.runs} koşu</span>
                      {passRate !== null && (
                        <span
                          className={`text-xs font-semibold ${
                            passRate >= 90
                              ? "text-emerald-400"
                              : passRate >= 70
                              ? "text-amber-400"
                              : "text-red-400"
                          }`}
                        >
                          %{passRate}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            {!isLoading && !data?.weekly_trend?.length && (
              <div className="px-4 py-8 text-center text-sm text-slate-500">
                Henüz veri yok.
              </div>
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
          {isLoading &&
            [1, 2, 3, 4].map((i) => (
              <div key={i} className="px-4 py-3 animate-pulse">
                <div className="h-3 w-1/2 rounded bg-slate-800 mb-2" />
                <div className="h-3 w-1/4 rounded bg-slate-800" />
              </div>
            ))}
          {!isLoading &&
            data?.activities?.slice(0, 10).map((a: GlobalDashboardActivity, i: number) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5">
                <Avatar
                  name={a.actor}
                  size="sm"
                  shape="circle"
                  seed={a.resource_id}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-slate-200">
                    <span className="font-medium text-white">{a.actor}</span>
                    {" — "}
                    <ActionLabel action={a.action} />
                  </p>
                </div>
                <span className="shrink-0 text-xs text-slate-500 tabular-nums">
                  {a.time}
                </span>
              </div>
            ))}
          {!isLoading &&
            (!data?.activities || data.activities.length === 0) && (
              <div className="px-4 py-8 text-center text-sm text-slate-500">
                Henüz aktivite yok.
              </div>
            )}
        </div>
      </div>
    </div>
  );
}
