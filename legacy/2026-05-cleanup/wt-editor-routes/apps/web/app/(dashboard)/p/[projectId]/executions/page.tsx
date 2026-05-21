"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { FlowGuideCard } from "@/components/FlowGuideCard";
import { useRealtimeExecution } from "@/lib/useRealtimeExecution";
import {
  PageHeader,
  StatCard,
  StatusBadge,
  ProgressBar,
  EmptyState,
  FilterBar,
  MetricRow,
  ToolbarActions,
} from "@/components/nexus";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

type Row = {
  id: string;
  name: string;
  status: string;
  created_at: string | null;
  scenario_total: number;
  passed_count: number;
  failed_count: number;
};

type PlatformTab = "all" | "desktop" | "ios" | "android";

const PLATFORM_TABS: { key: PlatformTab; label: string }[] = [
  { key: "all", label: "Tümü" },
  { key: "desktop", label: "🖥 Masaüstü" },
  { key: "ios", label: "🍎 iOS" },
  { key: "android", label: "🤖 Android" },
];

export default function ExecutionsListPage() {
  const projectId = useRouteParam("projectId");
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [platformTab, setPlatformTab] = useState<PlatformTab>("all");

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<Row[]>(`/api/v1/tspm/projects/${projectId}/executions`);
      setRows(data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);
  useRealtimeExecution(projectId, load);

  const filtered = rows.filter(r => {
    const matchSearch = r.name.toLowerCase().includes(search.toLowerCase());
    const matchStatus = !statusFilter || r.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const totalRuns = rows.length;
  const running = rows.filter(r => r.status === "running").length;
  const completed = rows.filter(r => r.status === "completed").length;
  const mobileRuns = rows.filter(r => r.platform != null).length;
  const totalTests = rows.reduce((acc, r) => acc + (r.scenario_total || 0), 0);
  const totalPassed = rows.reduce((acc, r) => acc + (r.passed_count || 0), 0);
  const successRate = totalTests > 0 ? Math.round((totalPassed / totalTests) * 100) : 0;
  const successColor: "emerald" | "amber" | "red" | "slate" =
    totalTests === 0 ? "slate" : successRate >= 80 ? "emerald" : successRate >= 50 ? "amber" : "red";

  function exportCSV() {
    if (filtered.length === 0) return;
    const header = ["ID", "Ad", "Durum", "Platform", "Cihaz", "Senaryo", "Geçti", "Başarısız", "Başarı%", "Tarih"];
    const csvRows = [
      header.join(","),
      ...filtered.map(r => {
        const tot = r.scenario_total || 0;
        const passed = r.passed_count || 0;
        const rate = tot > 0 ? Math.round((passed / tot) * 100) : 0;
        const date = r.created_at ? new Date(r.created_at).toLocaleString("tr-TR") : "";
        return [r.id, `"${r.name}"`, r.status, r.platform ?? "desktop", r.device_name ?? "", tot, passed, r.failed_count || 0, `${rate}%`, date].join(",");
      }),
    ].join("\n");
    const blob = new Blob(["\uFEFF" + csvRows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kosular-${projectId}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const [exportingAllure, setExportingAllure] = useState<string | null>(null);
  async function exportAllure(execId: string) {
    setExportingAllure(execId);
    try {
      const data = await apiFetch<{ allure_results: unknown[]; execution_id: string }>(
        `/api/v1/tspm/projects/${projectId}/executions/${execId}/allure`,
      );
      const json = JSON.stringify(data.allure_results, null, 2);
      const blob = new Blob([json], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `allure-${execId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* ignore */ }
    finally { setExportingAllure(null); }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6" data-testid="executions-page">
      <PageHeader
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
        title="Execution Koşuları"
        description="Senaryo bazlı test koşumlarını yönetin ve sonuçları takip edin"
        right={
          <ToolbarActions>
            {filtered.length > 0 && (
              <button
                onClick={exportCSV}
                className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700"
                title="CSV olarak indir"
                data-testid="executions-btn-export-csv"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                CSV
              </button>
            )}
            <Link
              href={`/p/${projectId}/executions/new`}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
              data-testid="executions-btn-new"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Yeni Koşu
            </Link>
          </ToolbarActions>
        }
      />

      <div className="mb-5">
        <FlowGuideCard projectId={projectId} stage="execute" />
      </div>

      {/* Stats row */}
      <MetricRow cols={5} className="mb-5">
        <StatCard label="Toplam Koşu" value={totalRuns} color="slate" />
        <StatCard label="Aktif" value={running} color="blue" />
        <StatCard label="Tamamlanan" value={completed} color="emerald" />
        <StatCard label="Visium Farm" value={mobileRuns} color="violet" sub="Mobile" />
        <StatCard
          label="Başarı Oranı"
          value={totalTests === 0 ? "—" : `${successRate}%`}
          color={successColor}
        />
      </MetricRow>

      {/* Platform tabs (pill) */}
      <div className="mb-3">
        <Tabs variant="pill" value={platformTab} onValueChange={(v) => setPlatformTab(v as PlatformTab)}>
          <TabsList>
            {PLATFORM_TABS.map(({ key, label }) => (
              <TabsTrigger key={key} value={key}>{label}</TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Filters */}
      <div className="mb-4">
        <FilterBar
          search={search}
          onSearch={setSearch}
          searchPlaceholder="Koşu ara..."
          filters={[
            {
              key: "status",
              label: "Tüm Durumlar",
              value: statusFilter,
              onChange: setStatusFilter,
              options: [
                { label: "Koşuyor", value: "running" },
                { label: "Tamamlandı", value: "completed" },
                { label: "Hata", value: "error" },
                { label: "Bekliyor", value: "pending" },
              ],
            },
          ]}
        />
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-slate-700 bg-slate-900/40" data-testid="executions-table">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Koşu Adı</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">İlerleme</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Başarı</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tarih</th>
              <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-slate-400" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="py-16 text-center text-sm text-slate-500">
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-blue-400" />
                    Yükleniyor...
                  </div>
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <EmptyState
                    icon="🧪"
                    title="Henüz koşu yok"
                    description="İlk test koşumunuzu başlatın"
                    action={
                      <Link
                        href={`/p/${projectId}/executions/new`}
                        className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
                      >
                        Koşu Oluştur
                      </Link>
                    }
                  />
                </td>
              </tr>
            ) : (
              filtered.map((r) => {
                const tot = r.scenario_total || 0;
                const passed = r.passed_count || 0;
                const failed = r.failed_count || 0;
                const skipped = Math.max(0, tot - passed - failed);
                const passRate = tot > 0 ? Math.round((passed / tot) * 100) : 0;
                const createdAt = r.created_at
                  ? new Date(r.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })
                  : "—";

                return (
                  <tr
                    key={r.id}
                    className="group border-b border-slate-800 transition-colors hover:bg-slate-800/40"
                    data-testid={`executions-row-${r.id}`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/p/${projectId}/executions/${r.id}`}
                          className="text-sm font-medium text-white transition-colors hover:text-blue-400"
                        >
                          {r.name}
                        </Link>
                        {r.platform === "ios" && (
                          <span className="inline-flex items-center gap-0.5 rounded bg-slate-700 px-1.5 py-0.5 text-[10px] font-medium text-slate-300">
                            🍎 iOS
                          </span>
                        )}
                        {r.platform === "android" && (
                          <span className="inline-flex items-center gap-0.5 rounded bg-slate-700 px-1.5 py-0.5 text-[10px] font-medium text-slate-300">
                            🤖 Android
                          </span>
                        )}
                      </div>
                      <div className="mt-0.5 text-xs text-slate-500">
                        {tot} senaryo
                        {r.device_name && (
                          <span className="ml-2 text-violet-400">📱 {r.device_name}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="min-w-32 px-4 py-3">
                      <ProgressBar passed={passed} failed={failed} skipped={skipped} total={tot} height="sm" />
                      <div className="mt-1 text-xs text-slate-500">{passed}/{tot}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-sm font-semibold ${
                          tot === 0
                            ? "text-slate-500"
                            : passRate >= 80
                            ? "text-emerald-400"
                            : passRate >= 50
                            ? "text-amber-400"
                            : "text-red-400"
                        }`}
                      >
                        {tot === 0 ? "—" : `${passRate}%`}
                      </span>
                      {tot > 0 && failed > 0 && (
                        <div className="mt-0.5 text-xs text-red-400/70">{failed} hata</div>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">{createdAt}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1 opacity-0 transition-all group-hover:opacity-100">
                        {r.status === "completed" && (
                          <button
                            onClick={() => exportAllure(r.id)}
                            disabled={exportingAllure === r.id}
                            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-700 hover:text-amber-300"
                            title="Allure JSON indir"
                          >
                            {exportingAllure === r.id ? (
                              <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-600 border-t-amber-400" />
                            ) : (
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                              </svg>
                            )}
                          </button>
                        )}
                        <Link
                          href={`/p/${projectId}/executions/${r.id}`}
                          className="inline-flex rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-700 hover:text-white"
                          title="Detay"
                        >
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
        {filtered.length > 0 && (
          <div className="border-t border-slate-800 px-4 py-2.5">
            <span className="text-xs text-slate-500">{filtered.length} koşu</span>
          </div>
        )}
      </div>
    </div>
  );
}
