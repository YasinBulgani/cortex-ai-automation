"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { FlowGuideCard } from "@/components/FlowGuideCard";
import {
  EmptyState,
  MetricRow,
  PageHeader,
  SectionCard,
  StatCard,
  StatusBadge,
  ToolbarActions,
  TrendBadge,
} from "@/components/nexus";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";
import { apiFetch, engineFetch, getToken } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import {
  isRealProvenance,
  normalizeProvenance,
  provenanceBadgeClass,
  provenanceLabel,
  type ProvenanceKind,
} from "@/lib/provenance";
import { useRouteParam } from "@/lib/use-route-param";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

type Execution = { id: string; name: string; status: string; created_at: string };
type PipelineRun = {
  id: number;
  test_title: string;
  status: string;
  mock_mode?: boolean;
  simulated?: boolean;
  provenance?: ProvenanceKind;
  feature_path: string;
  started_at: string;
};
type SummaryDays = "7" | "30" | "90";

async function downloadCsvSummary(projectId: string) {
  try {
    const blob = await apiFetch<Blob>(`/api/v1/tspm/projects/${projectId}/report/summary?format=csv`, {
      headers: { Accept: "text/csv" },
    });
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([JSON.stringify(blob)]));
    const link = document.createElement("a");
    link.href = url;
    link.download = `proje_${projectId}_özet.csv`;
    link.click();
    URL.revokeObjectURL(url);
  } catch {
    alert("CSV dışa aktarılamadı");
  }
}

async function downloadReport(projectId: string, runId: string | null, format: "html" | "json", days?: number) {
  const url = runId
    ? `${API_BASE}/api/v1/tspm/projects/${projectId}/executions/${runId}/report?format=${format}`
    : `${API_BASE}/api/v1/tspm/projects/${projectId}/report/summary?format=${format}&days=${days ?? 30}`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
  if (!res.ok) {
    alert("Rapor indirilemedi");
    return;
  }
  const blob = await res.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  const contentDisposition = res.headers.get("Content-Disposition") ?? "";
  const match = contentDisposition.match(/filename="([^"]+)"/);
  link.download = match ? match[1] : `rapor.${format}`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function ReportTypeIcon({ type }: { type: "html" | "json" | "csv" | "allure" }) {
  const icons: Record<string, { icon: string; color: string; label: string }> = {
    html: { icon: "🌐", color: "bg-blue-500/10 border-blue-500/20 text-blue-400", label: "HTML" },
    json: { icon: "{ }", color: "bg-amber-500/10 border-amber-500/20 text-amber-400", label: "JSON" },
    csv: { icon: "📊", color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", label: "CSV" },
    allure: { icon: "📈", color: "bg-violet-500/10 border-violet-500/20 text-violet-400", label: "Allure" },
  };
  const config = icons[type];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${config.color}`}>
      <span>{config.icon}</span> {config.label}
    </span>
  );
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
}

function getReadinessTone(rate: number): "emerald" | "amber" | "red" | "slate" {
  if (rate === 0) return "slate";
  if (rate >= 80) return "emerald";
  if (rate >= 50) return "amber";
  return "red";
}

export default function ReportsPage() {
  const projectId = useRouteParam("projectId");
  const { data: executions, loading } = useFetch<Execution[]>(`/api/v1/tspm/projects/${projectId}/executions`);
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [summaryDays, setSummaryDays] = useState<SummaryDays>("30");

  useEffect(() => {
    setPipelineLoading(true);
    engineFetch<{ runs: PipelineRun[] }>(
      `/api/pipeline/manual-to-automation/runs?project_id=${projectId}&limit=20`,
    )
      .then((data) => setPipelineRuns(data.runs ?? []))
      .catch((err) => console.warn("[reports]:", err))
      .finally(() => setPipelineLoading(false));
  }, [projectId]);

  const execs = executions ?? [];
  const totalExecutions = execs.length;
  const completedExecutions = execs.filter((execution) =>
    ["completed", "passed", "success"].includes(execution.status),
  ).length;
  const failedExecutions = execs.filter((execution) =>
    ["failed", "error", "broken"].includes(execution.status),
  ).length;
  const completionRate = totalExecutions > 0 ? (completedExecutions / totalExecutions) * 100 : 0;
  const totalPipeline = pipelineRuns.length;
  const realPipeline = pipelineRuns.filter((run) => isRealProvenance(normalizeProvenance(run))).length;
  const reportReadinessTone = getReadinessTone(completionRate);
  const latestExecution = execs[0] ?? null;
  const latestPipeline = pipelineRuns[0] ?? null;
  const actionLinks = [
    { label: "QA Orkestratör", href: `/p/${projectId}/qa-orchestrator`, note: "Yeni kalite turu başlat" },
    { label: "AI Asistan", href: `/p/${projectId}/ai-chat`, note: "Raporu Türkçe yorumlat" },
    { label: "LLM Metrikleri", href: `/p/${projectId}/ai-metrics`, note: "AI kalite etkisini izle" },
    { label: "Manual to Automation", href: `/p/${projectId}/manual-to-automation`, note: "Yeni pipeline üret" },
  ];

  return (
    <div className="min-h-screen space-y-4 bg-slate-950 p-6" data-testid="reports-page">
      <PageHeader
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        }
        title="Raporlar"
        description="Koşu sonuçlarını karar, paylaşım ve denetim çıktısına dönüştüren kalite merkezi."
        badge={
          <TrendBadge
            value={completionRate}
            label={totalExecutions > 0 ? `${completionRate.toFixed(0)}% tamamlanan` : "Veri bekleniyor"}
            direction={completionRate >= 80 ? "up" : completionRate > 0 ? "neutral" : "neutral"}
            size="sm"
          />
        }
        right={
          <ToolbarActions>
            <button
              onClick={() => downloadCsvSummary(projectId)}
              className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700"
              data-testid="reports-btn-csv"
            >
              <span>📊</span> CSV
            </button>
            <button
              onClick={() =>
                window.open(`${API_BASE}/api/v1/tspm/projects/${projectId}/report/summary?format=html`, "_blank")
              }
              className="flex items-center gap-2 rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-2 text-sm font-semibold text-blue-100 transition-colors hover:bg-blue-500/20"
              data-testid="reports-btn-html"
            >
              🌐 HTML Raporu Aç
            </button>
          </ToolbarActions>
        }
      />

      <FlowGuideCard projectId={projectId} stage="observe" />

      <SectionCard
        title="Rapor Karar Özeti"
        subtitle="Release, denetim ve ekip paylaşımı için ilk bakışta gereken sinyaller."
        icon={<span>🧾</span>}
        right={
          <span
            className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${
              reportReadinessTone === "emerald"
                ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                : reportReadinessTone === "amber"
                  ? "border-amber-500/20 bg-amber-500/10 text-amber-300"
                  : reportReadinessTone === "red"
                    ? "border-red-500/20 bg-red-500/10 text-red-300"
                    : "border-slate-700 bg-slate-900 text-slate-400"
            }`}
          >
            {totalExecutions > 0 ? "Rapor üretilebilir" : "Koşu bekleniyor"}
          </span>
        }
      >
        <div className="grid gap-3 xl:grid-cols-[1.2fr,0.8fr]">
          <MetricRow cols={4}>
            <StatCard label="Toplam Koşu" value={totalExecutions} color={totalExecutions > 0 ? "blue" : "slate"} />
            <StatCard
              label="Tamamlanan"
              value={completedExecutions}
              sub={totalExecutions > 0 ? `${completionRate.toFixed(0)}% oran` : "Henüz veri yok"}
              color={reportReadinessTone}
              trend={completionRate >= 80 ? "up" : completionRate > 0 ? "neutral" : undefined}
            />
            <StatCard
              label="Risk Sinyali"
              value={failedExecutions}
              sub={failedExecutions > 0 ? "İnceleme önerilir" : "Kritik hata görünmüyor"}
              color={failedExecutions > 0 ? "red" : "emerald"}
            />
            <StatCard
              label="Gerçek Pipeline"
              value={realPipeline}
              sub={`${Math.max(totalPipeline - realPipeline, 0)} yardımcı/simüle kayıt`}
              color={realPipeline > 0 ? "emerald" : "slate"}
            />
          </MetricRow>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Yönetim Yorumu</p>
            <h3 className="mt-2 text-lg font-semibold text-white">
              {totalExecutions > 0 ? "Paylaşılabilir kalite çıktısı hazır" : "Rapor için önce koşu üretmek gerekiyor"}
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              {totalExecutions > 0
                ? `Son durum ${completedExecutions}/${totalExecutions} tamamlanan koşu gösteriyor. Raporu HTML ile paylaşabilir, JSON ile entegrasyona aktarabilir veya CSV ile yönetim özetine çevirebiliriz.`
                : "Bu ekran raporlama ve denetim çıktısı için hazır; ilk koşu veya pipeline sonucu geldiğinde karar özeti otomatik dolacak."}
            </p>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              {actionLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-3 transition-colors hover:border-slate-600 hover:bg-slate-900"
                >
                  <p className="text-sm font-medium text-white">{link.label}</p>
                  <p className="mt-1 text-xs text-slate-400">{link.note}</p>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Dönem Özet Raporu"
        subtitle="Paylaşım formatını seç; dönemsel çıktıyı HTML, JSON veya CSV olarak al."
        icon={
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
        }
        right={
          <Tabs variant="pill" value={summaryDays} onValueChange={(value) => setSummaryDays(value as SummaryDays)}>
            <TabsList>
              <TabsTrigger value="7">7 gün</TabsTrigger>
              <TabsTrigger value="30">30 gün</TabsTrigger>
              <TabsTrigger value="90">90 gün</TabsTrigger>
            </TabsList>
          </Tabs>
        }
      >
        <div className="grid gap-4 lg:grid-cols-[1fr,0.8fr]">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => downloadReport(projectId, null, "html", Number(summaryDays))}
              className="flex items-center gap-1.5 rounded-xl border border-blue-500/20 bg-blue-500/10 px-4 py-3 text-xs font-semibold text-blue-200 transition-all hover:border-blue-400/40"
            >
              🌐 Son {summaryDays}g HTML
            </button>
            <button
              onClick={() => downloadReport(projectId, null, "json", Number(summaryDays))}
              className="flex items-center gap-1.5 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-xs font-semibold text-amber-200 transition-all hover:border-amber-400/40"
            >
              <span>{"{ }"}</span> Son {summaryDays}g JSON
            </button>
            <button
              onClick={() => downloadCsvSummary(projectId)}
              className="flex items-center gap-1.5 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-xs font-semibold text-emerald-200 transition-all hover:border-emerald-400/40"
            >
              📊 CSV
            </button>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm leading-6 text-slate-400">
            HTML yönetim paylaşımı, JSON entegrasyon ve denetim otomasyonu, CSV ise portföy veya dönemsel özet için en uygun çıktı.
          </div>
        </div>
      </SectionCard>

      <div className="grid gap-4 xl:grid-cols-[1.1fr,0.9fr]">
        <SectionCard
          title="Koşu Raporları"
          subtitle={latestExecution ? `Son koşu: ${latestExecution.name}` : "Execution oluştuğunda burada listelenir."}
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
              />
            </svg>
          }
          noPad
        >
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-blue-400" />
              Yükleniyor...
            </div>
          ) : execs.length === 0 ? (
            <EmptyState icon="📋" title="Henüz koşu yok" description="Execution oluşturduğunda raporlar burada indirilebilir olacak." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px]">
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
                  {execs.slice(0, 20).map((execution) => (
                    <tr key={execution.id} className="group border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                      <td className="px-4 py-3 text-sm font-medium text-white">{execution.name}</td>
                      <td className="px-4 py-3"><StatusBadge status={execution.status} /></td>
                      <td className="px-4 py-3 text-xs text-slate-500">{formatDate(execution.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1">
                          <ReportTypeIcon type="html" />
                          <ReportTypeIcon type="json" />
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => downloadReport(projectId, execution.id, "html")}
                            className="rounded-lg px-2 py-1 text-xs text-blue-400 transition-colors hover:bg-blue-500/10"
                          >
                            HTML ↓
                          </button>
                          <button
                            onClick={() => downloadReport(projectId, execution.id, "json")}
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
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="Pipeline Koşuları"
          subtitle={latestPipeline ? `Son pipeline: ${latestPipeline.test_title}` : "Manuel testten otomasyona geçmişi."}
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          }
          right={
            <Link
              href={`/p/${projectId}/manual-to-automation`}
              className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-300 transition-colors hover:border-slate-500 hover:text-white"
            >
              Yeni Pipeline
            </Link>
          }
          noPad
        >
          {pipelineLoading ? (
            <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-blue-400" />
              Yükleniyor...
            </div>
          ) : pipelineRuns.length === 0 ? (
            <EmptyState icon="🔧" title="Pipeline koşusu yok" description="Manual to Automation sayfasından ilk dönüşümü başlatabilirsin." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Test</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Mod</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tarih</th>
                  </tr>
                </thead>
                <tbody>
                  {pipelineRuns.map((run) => {
                    const provenance = normalizeProvenance(run);
                    return (
                      <tr key={run.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-white">{run.test_title}</p>
                          <p className="mt-0.5 max-w-64 truncate font-mono text-xs text-slate-500">{run.feature_path}</p>
                        </td>
                        <td className="px-4 py-3"><StatusBadge status={run.status} /></td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full border px-2 py-0.5 text-xs ${provenanceBadgeClass(provenance)}`}>
                            {provenanceLabel(provenance)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-500">{formatDate(run.started_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </div>
      <PageFeedbackWidget />

    </div>
  );
}
