"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

// ─── Types ─────────────────────────────────────────────────────────────────

interface ProjectSummary {
  project_id: string;
  project_name: string;
  total_cases: number;
  active_runs: number;
  pass_rate: number;
  failed_cases: number;
  blocked_cases: number;
  critical_defects: number;
  open_defects: number;
  requirements_coverage: number;
  last_run_at: string | null;
  health: "healthy" | "at_risk" | "critical" | "no_data";
}

interface PortfolioProject {
  id: string;
  name: string;
}

// ─── Health badge ───────────────────────────────────────────────────────────

const HEALTH_CFG = {
  healthy: { cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20", label: "Sağlıklı" },
  at_risk: { cls: "bg-amber-500/15 text-amber-400 border-amber-500/20", label: "Riskli" },
  critical: { cls: "bg-red-500/15 text-red-400 border-red-500/20", label: "Kritik" },
  no_data: { cls: "bg-surface-overlay text-fg-subtle border-border", label: "Veri Yok" },
};

function HealthBadge({ health }: { health: keyof typeof HEALTH_CFG }) {
  const cfg = HEALTH_CFG[health] ?? HEALTH_CFG.no_data;
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

// ─── Progress bar ───────────────────────────────────────────────────────────

function MiniBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-surface-overlay">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
      <span className="tabular-nums text-[11px] text-fg-muted">{pct.toFixed(0)}%</span>
    </div>
  );
}

// ─── Stats card ─────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums ${color ?? "text-fg"}`}>{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-fg-subtle">{sub}</p>}
    </div>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function QaReportsPage() {
  const [dateRange, setDateRange] = useState<"7" | "30" | "90">("30");

  const { data: projects = [], isLoading: projLoading } = useQuery<PortfolioProject[]>({
    queryKey: ["projects", "list"],
    queryFn: () => apiFetch<PortfolioProject[]>("/api/v1/tspm/projects"),
    staleTime: 60_000,
  });

  // Tüm projelerin özet verilerini çek
  const { data: summaries = [], isLoading: sumLoading } = useQuery<ProjectSummary[]>({
    queryKey: ["qa-reports", "cross-project", dateRange],
    queryFn: async () => {
      const results = await Promise.allSettled(
        projects.map(p =>
          apiFetch<ProjectSummary>(`/api/v1/test-management/projects/${p.id}/dashboard-summary`).catch(() => null)
        )
      );
      return results
        .map((r, i) => {
          if (r.status === "fulfilled" && r.value) return r.value;
          return {
            project_id: projects[i]?.id ?? "",
            project_name: projects[i]?.name ?? "Bilinmiyor",
            total_cases: 0,
            active_runs: 0,
            pass_rate: 0,
            failed_cases: 0,
            blocked_cases: 0,
            critical_defects: 0,
            open_defects: 0,
            requirements_coverage: 0,
            last_run_at: null,
            health: "no_data" as const,
          };
        })
        .filter(s => s.project_id !== "");
    },
    enabled: projects.length > 0,
    staleTime: 30_000,
  });

  const isLoading = projLoading || sumLoading;

  // Toplam istatistikler
  const totals = summaries.reduce(
    (acc, s) => ({
      cases: acc.cases + s.total_cases,
      runs: acc.runs + s.active_runs,
      defects: acc.defects + s.open_defects,
      critical: acc.critical + s.critical_defects,
    }),
    { cases: 0, runs: 0, defects: 0, critical: 0 }
  );
  const avgPassRate =
    summaries.length > 0
      ? summaries.reduce((a, s) => a + s.pass_rate, 0) / summaries.length
      : 0;

  const healthCounts = summaries.reduce(
    (acc, s) => ({ ...acc, [s.health]: (acc[s.health] ?? 0) + 1 }),
    {} as Record<string, number>
  );

  return (
    <div className="min-h-screen bg-surface-base px-6 py-6">
      <div className="mx-auto max-w-6xl space-y-6">

        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-fg">Çapraz Proje QA Raporu</h1>
            <p className="mt-0.5 text-sm text-fg-subtle">
              {projects.length} proje genelinde test kalitesi özeti
            </p>
          </div>
          <div className="flex items-center gap-2">
            {(["7", "30", "90"] as const).map(d => (
              <button
                key={d}
                onClick={() => setDateRange(d)}
                className={`rounded-lg border px-3 py-1.5 text-[12px] font-medium transition-colors ${
                  dateRange === d
                    ? "border-brand bg-brand-soft text-brand"
                    : "border-border text-fg-muted hover:bg-surface-overlay hover:text-fg"
                }`}
              >
                {d} gün
              </button>
            ))}
          </div>
        </div>

        {/* Global KPI'ler */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
          <StatCard label="Toplam Senaryo" value={totals.cases} sub="tüm projeler" />
          <StatCard label="Aktif Koşum" value={totals.runs} color="text-blue-400" />
          <StatCard
            label="Ort. Geçme Oranı"
            value={`${avgPassRate.toFixed(0)}%`}
            color={avgPassRate >= 80 ? "text-emerald-400" : avgPassRate >= 60 ? "text-amber-400" : "text-red-400"}
          />
          <StatCard label="Açık Defekt" value={totals.defects} color={totals.defects > 10 ? "text-amber-400" : "text-fg"} />
          <StatCard label="Kritik Defekt" value={totals.critical} color={totals.critical > 0 ? "text-red-400" : "text-emerald-400"} />
        </div>

        {/* Sağlık dağılımı */}
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Sağlık Dağılımı</p>
          {Object.entries(healthCounts).map(([h, count]) => {
            const cfg = HEALTH_CFG[h as keyof typeof HEALTH_CFG] ?? HEALTH_CFG.no_data;
            return (
              <span key={h} className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-medium ${cfg.cls}`}>
                {cfg.label}
                <span className="rounded-full bg-current/20 px-1 font-bold">{count}</span>
              </span>
            );
          })}
        </div>

        {/* Proje tablosu */}
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-14 animate-pulse rounded-xl bg-surface-raised" style={{ opacity: 1 - i * 0.18 }} />
            ))}
          </div>
        ) : summaries.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-border bg-surface-raised py-20 text-center">
            <svg className="h-12 w-12 text-fg-subtle/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <p className="text-[14px] font-semibold text-fg-muted">Henüz proje yok</p>
            <p className="text-[12px] text-fg-subtle">
              Test yönetimi başlatılmış projeler burada görünür.
            </p>
            <Link href="/portfolio" className="mt-2 rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg">
              Portfolio&apos;ya Git →
            </Link>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border bg-surface-raised">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-surface-overlay">
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Proje</th>
                  <th className="hidden px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-widest text-fg-subtle sm:table-cell">Senaryo</th>
                  <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Geçme Oranı</th>
                  <th className="hidden px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-widest text-fg-subtle md:table-cell">Defekt</th>
                  <th className="hidden px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle lg:table-cell">Kapsam</th>
                  <th className="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Sağlık</th>
                  <th className="w-10 px-2 py-3" />
                </tr>
              </thead>
              <tbody>
                {summaries.map((s, idx) => (
                  <tr key={s.project_id}
                    className={`border-b border-border transition-colors hover:bg-surface-overlay last:border-0 ${idx % 2 === 0 ? "" : "bg-white/[0.01]"}`}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border bg-surface-overlay text-[11px] font-bold text-fg-muted">
                          {s.project_name[0]?.toUpperCase() ?? "?"}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-[13px] font-medium text-fg">{s.project_name}</p>
                          {s.active_runs > 0 && (
                            <p className="text-[10px] text-blue-400">{s.active_runs} aktif koşum</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="hidden px-4 py-3 text-center text-[13px] tabular-nums text-fg-muted sm:table-cell">
                      {s.total_cases}
                    </td>
                    <td className="px-4 py-3">
                      <MiniBar
                        pct={s.pass_rate}
                        color={s.pass_rate >= 80 ? "bg-emerald-500" : s.pass_rate >= 60 ? "bg-amber-500" : "bg-red-500"}
                      />
                    </td>
                    <td className="hidden px-4 py-3 text-center md:table-cell">
                      <div className="flex flex-col items-center gap-0.5">
                        {s.critical_defects > 0 && (
                          <span className="text-[11px] font-bold text-red-400">{s.critical_defects} kritik</span>
                        )}
                        <span className="text-[11px] text-fg-muted">{s.open_defects} açık</span>
                      </div>
                    </td>
                    <td className="hidden px-4 py-3 lg:table-cell">
                      <MiniBar pct={s.requirements_coverage} color="bg-blue-500" />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <HealthBadge health={s.health} />
                    </td>
                    <td className="px-2 py-3">
                      <Link
                        href={`/p/${s.project_id}/management/dashboard`}
                        className="flex items-center justify-center rounded-lg p-1.5 text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg"
                        title="Projeye Git"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7"/>
                        </svg>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Trend chart placeholder — tüm projeler */}
        <div className="rounded-xl border border-border bg-surface-raised p-5">
          <h3 className="mb-4 text-[12px] font-semibold uppercase tracking-widest text-fg-subtle">
            Geçme Oranı Trendi — Tüm Projeler
          </h3>
          {summaries.length === 0 ? (
            <p className="py-6 text-center text-[13px] text-fg-subtle">Veri yükleniyor…</p>
          ) : (
            <div className="flex h-32 items-end gap-2">
              {summaries.map(s => (
                <div key={s.project_id} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className={`w-full rounded-t-sm transition-all ${
                      s.pass_rate >= 80 ? "bg-emerald-500/70" :
                      s.pass_rate >= 60 ? "bg-amber-500/70" : "bg-red-500/70"
                    }`}
                    style={{ height: `${Math.max(4, s.pass_rate)}%` }}
                    title={`${s.project_name}: %${s.pass_rate.toFixed(0)}`}
                  />
                  <p className="w-full truncate text-center text-[9px] text-fg-subtle">
                    {s.project_name.split(" ")[0]}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
