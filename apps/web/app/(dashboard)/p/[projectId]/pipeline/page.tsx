"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";

type StageStatus = "complete" | "in_progress" | "pending" | "blocked";

type Stage = {
  id: string;
  title: string;
  icon: string;
  description: string;
  status: StageStatus;
  metric_label: string;
  metric_value: string | number;
  actions: { label: string; href: string; primary?: boolean }[];
};

type PipelineSummary = {
  project_id: string;
  total_scenarios: number;
  total_executions: number;
  last_run_pass_rate: number | null;
  open_failures: number;
  ai_generated_count: number;
};

function statusColor(s: StageStatus): string {
  switch (s) {
    case "complete":
      return "border-emerald-500/30 bg-emerald-500/5";
    case "in_progress":
      return "border-amber-500/30 bg-amber-500/5";
    case "blocked":
      return "border-red-500/30 bg-red-500/5";
    default:
      return "border-slate-700 bg-slate-900/40";
  }
}

function statusLabel(s: StageStatus): string {
  switch (s) {
    case "complete":
      return "✓ Tamamlandı";
    case "in_progress":
      return "⏳ Sürüyor";
    case "blocked":
      return "🚫 Engellenmiş";
    default:
      return "○ Bekliyor";
  }
}

export default function PipelinePage() {
  const projectId = useRouteParam("projectId");
  const [summary, setSummary] = useState<PipelineSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.allSettled([
      apiFetch<any[]>(`/api/v1/tspm/projects/${projectId}/scenarios`),
      apiFetch<any[]>(`/api/v1/tspm/projects/${projectId}/executions`),
    ])
      .then(([scenariosResult, executionsResult]) => {
        if (cancelled) return;
        const scenarios = scenariosResult.status === "fulfilled" ? scenariosResult.value : [];
        const executions = executionsResult.status === "fulfilled" ? executionsResult.value : [];

        const lastRun = executions[0];
        const passRate =
          lastRun && lastRun.scenario_total > 0
            ? Math.round((100 * (lastRun.passed_count ?? 0)) / lastRun.scenario_total)
            : null;

        const openFailures = executions.reduce(
          (acc: number, e: any) => acc + (e.failed_count ?? 0),
          0,
        );

        setSummary({
          project_id: projectId,
          total_scenarios: scenarios.length,
          total_executions: executions.length,
          last_run_pass_rate: passRate,
          open_failures: openFailures,
          ai_generated_count: scenarios.filter((s: any) =>
            (s.tags || []).includes("ai-generated"),
          ).length,
        });
        setError(null);
      })
      .catch((e: any) => {
        if (!cancelled) setError(e?.message ?? "Veri yüklenemedi");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const stages: Stage[] = [
    {
      id: "analyze",
      title: "1. Analiz",
      icon: "🔍",
      description:
        "Gereksinim toplama, doküman analizi, API spec içe aktarma. AI ile niyet grafikleri çıkar.",
      status: summary && summary.total_scenarios > 0 ? "complete" : "pending",
      metric_label: "Yüklenen kaynak",
      metric_value: summary?.ai_generated_count ?? "—",
      actions: [
        { label: "İçe aktar", href: `/p/${projectId}/import` },
        { label: "Gereksinimler", href: `/p/${projectId}/requirements` },
        { label: "Sıfır Bilgi AI", href: `/p/${projectId}/sifir-bilgi`, primary: true },
      ],
    },
    {
      id: "design",
      title: "2. Tasarım",
      icon: "✍️",
      description:
        "Senaryo yazma, locator yönetimi, BDD Gherkin (Türkçe destekli), version kontrolü.",
      status: summary && summary.total_scenarios > 0 ? "complete" : "pending",
      metric_label: "Senaryolar",
      metric_value: summary?.total_scenarios ?? "—",
      actions: [
        { label: "Senaryolar", href: `/p/${projectId}/scenarios`, primary: true },
        { label: "Locators", href: `/p/${projectId}/locators` },
        { label: "Page Objects", href: `/p/${projectId}/page-objects` },
      ],
    },
    {
      id: "data",
      title: "3. Veri",
      icon: "💾",
      description: "Sentetik veri üretimi, parametrelendirme, gizlilik (KVKK) testleri.",
      status: "pending",
      metric_label: "Veri setleri",
      metric_value: "—",
      actions: [
        { label: "Sentetik Veri", href: `/p/${projectId}/synthetic` },
        { label: "Test Verisi", href: `/p/${projectId}/test-data` },
        { label: "Gizlilik", href: `/p/${projectId}/privacy` },
      ],
    },
    {
      id: "execute",
      title: "4. Koşum",
      icon: "▶️",
      description:
        "Web (Playwright), Mobil (Appium), API testleri. Paralel + dry-run + failed-only re-run.",
      status:
        summary && summary.total_executions > 0
          ? summary.open_failures > 0
            ? "blocked"
            : "complete"
          : "pending",
      metric_label: "Bu hafta koşum",
      metric_value: summary?.total_executions ?? "—",
      actions: [
        { label: "Yeni Koşum", href: `/p/${projectId}/executions/new`, primary: true },
        { label: "Mobil", href: `/p/${projectId}/mobile` },
        { label: "API", href: `/p/${projectId}/api-tests` },
        { label: "Zamanlayıcı", href: `/p/${projectId}/schedules` },
      ],
    },
    {
      id: "observe",
      title: "5. Gözlem",
      icon: "📊",
      description:
        "Raporlama, flaky tespit, self-healing PR, AI debug analizi, anomali tespiti.",
      status: summary && summary.last_run_pass_rate !== null ? "complete" : "pending",
      metric_label: "Son koşum başarı",
      metric_value:
        summary?.last_run_pass_rate !== null && summary?.last_run_pass_rate !== undefined
          ? `%${summary.last_run_pass_rate}`
          : "—",
      actions: [
        { label: "Raporlar", href: `/p/${projectId}/reports`, primary: true },
        { label: "Flaky", href: `/p/${projectId}/flaky` },
        { label: "Healing", href: `/p/${projectId}/healing` },
        { label: "Debug", href: `/p/${projectId}/debug-report` },
      ],
    },
    {
      id: "iterate",
      title: "6. İyileştirme",
      icon: "🔄",
      description:
        "CI/CD entegrasyonu, approval workflow, knowledge base, sürekli iyileştirme.",
      status: "pending",
      metric_label: "Açık hata",
      metric_value: summary?.open_failures ?? "—",
      actions: [
        { label: "CI/CD", href: `/p/${projectId}/cicd` },
        { label: "Onaylar", href: `/p/${projectId}/approvals` },
        { label: "Knowledge Base", href: `/kb` },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100" data-testid="pipeline-page">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">🔄 Test Otomasyon Pipeline</h1>
          <p className="mt-2 text-sm text-slate-400">
            Analiz → Tasarım → Veri → Koşum → Gözlem → İyileştirme — uçtan uca akış.
          </p>
        </header>

        {error && (
          <div
            className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
            data-testid="pipeline-error"
          >
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-center text-sm text-slate-500" data-testid="pipeline-loading">
            Yükleniyor…
          </p>
        ) : (
          <div className="space-y-4" data-testid="pipeline-stages">
            {stages.map((stage, idx) => (
              <div
                key={stage.id}
                className={`rounded-2xl border p-5 ${statusColor(stage.status)}`}
                data-testid={`pipeline-stage-${stage.id}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className="text-3xl">{stage.icon}</div>
                    <div className="min-w-0">
                      <h2 className="text-lg font-semibold text-white">{stage.title}</h2>
                      <p className="mt-1 text-sm text-slate-400">{stage.description}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-4 text-xs">
                        <span
                          className={`rounded px-2 py-0.5 ${
                            stage.status === "complete"
                              ? "bg-emerald-500/20 text-emerald-300"
                              : stage.status === "in_progress"
                                ? "bg-amber-500/20 text-amber-300"
                                : stage.status === "blocked"
                                  ? "bg-red-500/20 text-red-300"
                                  : "bg-slate-700 text-slate-400"
                          }`}
                          data-testid={`pipeline-stage-${stage.id}-status`}
                        >
                          {statusLabel(stage.status)}
                        </span>
                        <span className="text-slate-500">
                          {stage.metric_label}:{" "}
                          <span className="font-medium text-white">{stage.metric_value}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {stage.actions.map((action) => (
                    <Link
                      key={action.href}
                      href={action.href}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                        action.primary
                          ? "bg-indigo-600 text-white hover:bg-indigo-500"
                          : "border border-slate-700 text-slate-300 hover:bg-slate-800"
                      }`}
                      data-testid={`pipeline-action-${stage.id}-${action.label.toLowerCase().replace(/\s+/g, "-")}`}
                    >
                      {action.label}
                    </Link>
                  ))}
                </div>

                {idx < stages.length - 1 && (
                  <div className="mt-4 flex justify-center text-slate-700">
                    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 5v14M5 12l7 7 7-7" />
                    </svg>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
