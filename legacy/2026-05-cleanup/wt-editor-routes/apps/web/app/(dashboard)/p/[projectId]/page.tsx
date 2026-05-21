"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";

type Stats = {
  scenario_count: number;
  pending_approvals: number;
  import_count: number;
  ai_run_pending: number;
  execution_count: number;
  latest_run_pass_rate: number | null;
};

const FLOW_STEPS = [
  { step: "1", title: "Senaryo Yaz", description: "Test senaryolarını oluştur veya içe aktar.", href: "scenarios", cta: "Senaryolar" },
  { step: "2", title: "Test Case Üret", description: "AI ile senaryolardan test case'ler türet.", href: "test-cases", cta: "AI Test Case" },
  { step: "3", title: "Otomasyon Üret", description: "Test case'lerden otomatik kod üret.", href: "automation-gen", cta: "Otomasyon Üret" },
  { step: "4", title: "Çalıştır", description: "Oluşan otomasyonları koş ve sonuçları izle.", href: "executions", cta: "Koşular" },
  { step: "5", title: "Rapor Gör", description: "Koşu sonuçlarını ve trendleri incele.", href: "reports", cta: "Raporlar" },
];

export default function ProjectDashboardPage() {
  const projectId = useRouteParam("projectId");
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    if (!projectId) return;
    apiFetch<Stats>(`/api/v1/tspm/projects/${projectId}/dashboard`).then(setStats).catch(() => {});
  }, [projectId]);

  const passRate = stats?.latest_run_pass_rate;
  const passColor = passRate == null ? "text-slate-400" : passRate >= 80 ? "text-emerald-400" : passRate >= 50 ? "text-amber-400" : "text-red-400";

  const statCards = stats
    ? [
        { label: "Senaryolar", value: stats.scenario_count, href: `/p/${projectId}/scenarios`, color: "text-blue-400" },
        { label: "Koşular", value: stats.execution_count, href: `/p/${projectId}/executions`, color: "text-violet-400" },
        { label: "Başarı Oranı", value: passRate != null ? `${passRate}%` : "—", href: `/p/${projectId}/reports`, color: passColor },
      ]
    : null;

  return (
    <div className="min-h-screen bg-bg text-fg p-6 flex flex-col gap-6" data-testid="dashboard-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
        }
        title="Proje Özeti"
        description="Senaryo yaz, test case üret, otomasyon üret, çalıştır ve raporla."
        data-testid="dashboard-heading"
      />

      {statCards ? (
        <div className="grid gap-4 md:grid-cols-3" data-testid="dashboard-stats">
          {statCards.map((card) => (
            <Link
              key={card.label}
              href={card.href}
              className="group rounded-xl border border-slate-800 bg-slate-900/40 p-5 hover:border-slate-700 hover:bg-slate-800/40 transition-all"
            >
              <p className="text-xs font-medium text-slate-400 mb-3">{card.label}</p>
              <p className={`text-3xl font-bold tabular-nums tracking-tight ${card.color}`}>{card.value}</p>
            </Link>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 animate-pulse">
              <div className="mb-3 h-3 w-20 rounded bg-slate-800" />
              <div className="h-8 w-14 rounded bg-slate-800" />
            </div>
          ))}
        </div>
      )}

      <section data-testid="dashboard-flow-steps">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4">Demo Akış</h2>
        <div className="grid gap-3 md:grid-cols-5">
          {FLOW_STEPS.map((step) => (
            <Link
              key={step.step}
              href={`/p/${projectId}/${step.href}`}
              className="group rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-blue-500/40 hover:bg-slate-800/40 transition-all"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/15 text-xs font-bold text-blue-400">
                  {step.step}
                </span>
                <span className="text-sm font-semibold text-white">{step.title}</span>
              </div>
              <p className="text-xs text-slate-400 leading-5">{step.description}</p>
              <p className="mt-3 text-xs font-medium text-blue-400 group-hover:text-blue-300 transition-colors">
                {step.cta} &rarr;
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section data-testid="dashboard-ai-tools">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4">AI Araçları</h2>
        <div className="grid gap-3 md:grid-cols-4">
          {[
            { label: "AI Asistan", href: "ai-chat", desc: "Sohbet tabanlı test asistanı" },
            { label: "NL Test Üretici", href: "nl-test-gen", desc: "Doğal dilden test üret" },
            { label: "QA Orkestratör", href: "qa-orchestrator", desc: "Test süreçlerini orkestre et" },
            { label: "LLM Metrikleri", href: "ai-metrics", desc: "AI performans metrikleri" },
          ].map((tool) => (
            <Link
              key={tool.href}
              href={`/p/${projectId}/${tool.href}`}
              className="group rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-violet-500/40 hover:bg-slate-800/40 transition-all"
            >
              <p className="text-sm font-semibold text-white">{tool.label}</p>
              <p className="mt-1 text-xs text-slate-400">{tool.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
