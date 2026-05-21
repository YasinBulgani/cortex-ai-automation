"use client";

import { useRouteParam } from "@/lib/use-route-param";
import { useEffect, useState } from "react";
import { useFetch } from "@/lib/useFetch";
import { apiFetch, engineFetch } from "@/lib/api";
import { FlowGuideCard } from "@/components/FlowGuideCard";
import {
  PageHeader,
  SectionCard,
  StatusBadge,
  EmptyState,
  StatCard,
  MetricRow,
  ToolbarActions,
} from "@/components/nexus";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

type Execution = { id: string; name: string; status: string; created_at: string };
type PipelineRun = {
  id: number; test_title: string; status: string;
  mock_mode: boolean; feature_path: string; started_at: string;
};
type SummaryDays = "7" | "30" | "90";

async function downloadCsvSummary(projectId: string) {
  try {
    const blob = await apiFetch<Blob>(
      `/api/v1/tspm/projects/${projectId}/report/summary?format=csv`,
      { headers: { Accept: "text/csv" } }
    );
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([JSON.stringify(blob)]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `proje_${projectId}_ozet.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch { alert("CSV dışa aktarılamadı"); }
}

async function downloadReport(projectId: string, runId: string | null, format: "html" | "json", days?: number) {
  const url = runId
    ? `${API_BASE}/api/v1/tspm/projects/${projectId}/executions/${runId}/report?format=${format}`
    : `${API_BASE}/api/v1/tspm/projects/${projectId}/report/summary?format=${format}&days=${days ?? 30}`;
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) { alert("Rapor indirilemedi"); return; }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  const cd = res.headers.get("Content-Disposition") ?? "";
  const match = cd.match(/filename="([^"]+)"/);
  a.download = match ? match[1] : `rapor.${format}`;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ── Report Type Icon ─────────────────────────────────────────────────────── */
function ReportTypeIcon({ type }: { type: "html" | "json" | "csv" | "allure" }) {
  const icons: Record<string, { icon: string; color: string; label: string }> = {
    html:   { icon: "🌐",  color: "bg-blue-500/10 border-blue-500/20 text-blue-400",       label: "HTML" },
    json:   { icon: "{ }", color: "bg-amber-500/10 border-amber-500/20 text-amber-400",    label: "JSON" },
    csv:    { icon: "📊",  color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", label: "CSV" },
    allure: { icon: "📈",  color: "bg-violet-500/10 border-violet-500/20 text-violet-400",   label: "Allure" },
  };
  const cfg = icons[type];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${cfg.color}`}>
      <span>{cfg.icon}</span> {cfg.label}
    </span>
  );
}

export default function ReportsPage() {
  const projectId = useRouteParam("projectId");
  const { data: executions, loading } = useFetch<Execution[]>(
    `/api/v1/tspm/projects/${projectId}/executions`
  );
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [summaryDays, setSummaryDays] = useState<SummaryDays>("30");

  useEffect(() => {
    setPipelineLoading(true);
    engineFetch<{ runs: PipelineRun[] }>(
      `/api/pipeline/manual-to-automation/runs?project_id=${projectId}&limit=20`
    )
      .then(d => setPipelineRuns(d.runs ?? []))
      .catch(() => {})
      .finally(() => setPipelineLoading(false));
  }, [projectId]);

  const execs = executions ?? [];
  const totalExecutions = execs.length;
  const completedExecutions = execs.filter(e => e.status === "completed" || e.status === "passed").length;
  const totalPipeline = pipelineRuns.length;
  const realPipeline = pipelineRuns.filter(r => !r.mock_mode).length;

  return (
    <div className="min-h-screen bg-slate-950 p-6" data-testid="reports-page">
      <PageHeader
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        }
        title="Raporlar"
        description="Koşum ve proje raporlarını çeşitli formatlarda indirin"
        right={
          <ToolbarActions>
            <button
              onClick={() => downloadCsvSummary(projectId)}
              className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700"
              data-testid="reports-btn-csv"
            >
              <span>📊</span> CSV
            </button>
            <button
              onClick={() => window.open(`${API_BASE}/api/v1/tspm/projects/${projectId}/report/summary?format=html`, "_blank")}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
              data-testid="reports-btn-html"
            >
              🌐 HTML Raporu Aç
            </button>
          </ToolbarActions>
        }
      />

      <div className="mb-4">
        <FlowGuideCard projectId={projectId} stage="observe" />
      </div>

      {/* Stats */}
      <MetricRow cols={4} className="mb-5">
        <StatCard label="Toplam Koşu" value={totalExecutions} color="slate" />
        <StatCard label="Tamamlanan" value={completedExecutions} color="emerald" />
        <StatCard label="Pipeline" value={totalPipeline} color="blue" />
        <StatCard label="Gerçek Koşu" value={realPipeline} color={realPipeline > 0 ? "emerald" : "slate"} sub={`${totalPipeline - realPipeline} mock`} />
      </MetricRow>

      {/* Period summary export */}
      <SectionCard
        title="Dönem Özet Raporu"
        icon={<svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>}
        right={
          <Tabs variant="pill" value={summaryDays} onValueChange={(v) => setSummaryDays(v as SummaryDays)}>
            <TabsList>
              <TabsTrigger value="7">7 gün</TabsTrigger>
              <TabsTrigger value="30">30 gün</TabsTrigger>
              <TabsTrigger value="90">90 gün</TabsTrigger>
            </TabsList>
          </Tabs>
        }
        className="mb-4"
      >
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => downloadReport(projectId, null, "html", Number(summaryDays))}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 transition-all hover:border-slate-500 hover:text-white"
          >
            🌐 Son {summaryDays}g HTML
          </button>
          <button
            onClick={() => downloadReport(projectId, null, "json", Number(summaryDays))}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 transition-all hover:border-slate-500 hover:text-white"
          >
            <span>{"{ }"}</span> Son {summaryDays}g JSON
          </button>
          <button
            onClick={() => downloadCsvSummary(projectId)}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 transition-all hover:border-slate-500 hover:text-white"
          >
            📊 CSV
          </button>
        </div>
      </SectionCard>

      {/* Execution reports */}
      <SectionCard
        title="Koşu Raporları"
        icon={<svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /></svg>}
        noPad
        className="mb-4"
      >
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-blue-400" />
            Yükleniyor...
          </div>
        ) : execs.length === 0 ? (
          <EmptyState icon="📋" title="Henüz koşu yok" description="Execution oluşturduğunuzda raporları buradan indirebilirsiniz" />
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Koşu</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tarih</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Format</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-slate-400">İndir</th>
              </tr>
            </thead>
            <tbody>
              {execs.slice(0, 20).map(ex => (
                <tr key={ex.id} className="group border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                  <td className="px-4 py-3 text-sm font-medium text-white">{ex.name}</td>
                  <td className="px-4 py-3"><StatusBadge status={ex.status} /></td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {new Date(ex.created_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" })}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <ReportTypeIcon type="html" />
                      <ReportTypeIcon type="json" />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      <button
                        onClick={() => downloadReport(projectId, ex.id, "html")}
                        className="rounded-lg px-2 py-1 text-xs text-blue-400 transition-colors hover:bg-blue-500/10"
                      >
                        HTML ↓
                      </button>
                      <button
                        onClick={() => downloadReport(projectId, ex.id, "json")}
                        className="rounded-lg px-2 py-1 text-xs text-amber-400 transition-colors hover:bg-amber-500/10"
                      >
                        JSON ↓
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>

      {/* Pipeline runs */}
      <SectionCard
        title="Pipeline Koşuları"
        icon={<svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
        right={<span className="text-xs text-slate-500">Manuel → Otomasyon geçmişi</span>}
        noPad
      >
        {pipelineLoading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-blue-400" />
            Yükleniyor...
          </div>
        ) : pipelineRuns.length === 0 ? (
          <EmptyState icon="🔧" title="Pipeline koşusu yok" description="Test Koşuları (Engine) sayfasından başlatın" />
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Test</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Mod</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tarih</th>
              </tr>
            </thead>
            <tbody>
              {pipelineRuns.map(run => (
                <tr key={run.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-white">{run.test_title}</p>
                    <p className="mt-0.5 max-w-64 truncate font-mono text-xs text-slate-500">{run.feature_path}</p>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={run.status} /></td>
                  <td className="px-4 py-3">
                    {run.mock_mode ? (
                      <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-400">Mock</span>
                    ) : (
                      <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-400">Gerçek</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {new Date(run.started_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>
    </div>
  );
}
