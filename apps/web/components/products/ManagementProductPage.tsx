"use client";

import Link from "next/link";
import { useProductTelemetry } from "@/lib/products/useProductTelemetry";
import { PRODUCT_BRAND } from "@/lib/products/brand";
import { LiveStatsBar } from "./_shared/LiveStatsBar";
import { AiInsightFeed } from "./_shared/AiInsightFeed";
import { RecentActivity } from "./_shared/RecentActivity";
import { OnboardingChecklist } from "./_shared/OnboardingChecklist";

const brand = PRODUCT_BRAND.management;

const REPOSITORY_HEALTH = [
  { label: "Login & Auth", total: 84, ready: 76, failed: 3 },
  { label: "Checkout", total: 126, ready: 101, failed: 11 },
  { label: "Customer", total: 73, ready: 69, failed: 2 },
  { label: "Mobile Smoke", total: 58, ready: 44, failed: 5 },
];

const RUN_BOARD = [
  { status: "Not Run", value: 42, tone: "bg-slate-500" },
  { status: "Passed", value: 186, tone: "bg-emerald-500" },
  { status: "Failed", value: 19, tone: "bg-rose-500" },
  { status: "Blocked", value: 7, tone: "bg-amber-500" },
];

function RepositoryHealth() {
  return (
    <div className="space-y-3">
      {REPOSITORY_HEALTH.map((item) => {
        const readyRate = Math.round((item.ready / item.total) * 100);
        return (
          <div key={item.label} className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-white">{item.label}</span>
              <span className="text-xs text-slate-400">{item.ready}/{item.total} ready</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full bg-teal-500" style={{ width: `${readyRate}%` }} />
            </div>
            <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
              <span>{readyRate}% repository health</span>
              <span>{item.failed} failed in last run</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RunBoard() {
  const total = RUN_BOARD.reduce((sum, item) => sum + item.value, 0);
  return (
    <div className="grid grid-cols-2 gap-3">
      {RUN_BOARD.map((item) => (
        <div key={item.status} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${item.tone}`} />
            <span className="text-xs font-medium uppercase tracking-wide text-slate-400">{item.status}</span>
          </div>
          <div className="text-2xl font-bold text-white">{item.value}</div>
          <div className="text-xs text-slate-500">{Math.round((item.value / total) * 100)}% of active run</div>
        </div>
      ))}
    </div>
  );
}

export function ManagementProductPage() {
  const { telemetry, loading, isDemo } = useProductTelemetry("management");

  return (
    <div className="flex flex-col gap-6 p-6 pb-12">
      <section className="relative overflow-hidden rounded-3xl border border-teal-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-teal-950/30 p-8 lg:p-10">
        <div className="relative grid grid-cols-1 items-center gap-8 lg:grid-cols-2">
          <div>
            <div className="mb-4 flex items-center gap-2">
              <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-widest ${brand.badge}`}>
                Manuel QA Yönetimi
              </span>
              {isDemo && (
                <span className="rounded-full border border-amber-500/25 bg-amber-500/15 px-2 py-0.5 text-xs text-amber-300">
                  Demo Data
                </span>
              )}
            </div>
            <h1 className="mb-4 text-4xl font-extrabold leading-tight text-white lg:text-5xl">
              Neurex <span className="bg-gradient-to-r from-teal-300 to-emerald-400 bg-clip-text text-transparent">Management</span>
              <br />
              Manuel Test Operasyonu
            </h1>
            <p className="mb-8 text-lg leading-relaxed text-slate-400">
              Test case repository, test plan, cycle, run, tester atama, evidence, defect ve coverage görünürlüğünü tek yönetim yüzeyinde topla.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/p/00000000-0000-0000-0000-000000000001/management" className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-500/20 transition-opacity hover:opacity-90">
                Management Alanını Aç
              </Link>
              <Link href="/p/00000000-0000-0000-0000-000000000001/management/repository" className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-800 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-700">
                Repository İncele
              </Link>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Aktif Run Özeti</p>
              <span className="rounded-full border border-teal-500/25 bg-teal-500/10 px-2 py-0.5 text-xs text-teal-300">Sprint 12</span>
            </div>
            <RunBoard />
          </div>
        </div>
      </section>

      <section>
        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Management Metrikleri</p>
        <LiveStatsBar stats={telemetry?.stats ?? []} loading={loading} brandText={brand.text} />
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 lg:col-span-3">
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Repository Sağlığı</h2>
            <span className="text-xs text-slate-400">Suite bazlı manuel test hafızası</span>
          </div>
          <RepositoryHealth />
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 lg:col-span-2">
          <h2 className="mb-5 text-sm font-semibold text-white">AI Operasyon Önerileri</h2>
          <AiInsightFeed insights={telemetry?.aiInsights ?? []} brandBorder={brand.border} brandText={brand.text} loading={loading} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="mb-5 text-sm font-semibold text-white">Son Aktiviteler</h2>
          <RecentActivity events={telemetry?.recentActivity ?? []} brandText={brand.text} loading={loading} />
        </div>
        <OnboardingChecklist steps={telemetry?.onboarding ?? []} brandGradient={brand.gradient} brandText={brand.text} loading={loading} />
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="mb-5 text-sm font-semibold text-white">MVP Omurgası</h2>
          <div className="space-y-3 text-sm text-slate-300">
            {["Test case repository", "Plan / cycle / run", "Adım bazlı evidence", "Defect ve coverage linkleri"].map((item) => (
              <div key={item} className="flex items-center justify-between rounded-xl bg-slate-950/60 px-3 py-2">
                <span>{item}</span>
                <span className="text-xs font-medium text-teal-300">Faz 1</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
