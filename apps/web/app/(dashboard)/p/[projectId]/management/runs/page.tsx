"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  useCreateManagementRun,
  useExecutionSummary,
  useManagementCases,
  useManagementCycles,
  useManagementRuns,
  useRegressionSets,
} from "@/lib/hooks/use-management";
import { ManagementShell } from "../_components/ManagementShell";
import { IntelligencePanel } from "../_components/IntelligencePanel";

const ENV_CONFIG: Record<string, { icon: string; color: string; bg: string }> = {
  staging:    { icon: "🧪", color: "text-violet-300", bg: "bg-violet-500/10 border-violet-500/30" },
  production: { icon: "🚀", color: "text-rose-300",   bg: "bg-rose-500/10 border-rose-500/30" },
  dev:        { icon: "💻", color: "text-teal-300",   bg: "bg-teal-500/10 border-teal-500/30" },
  qa:         { icon: "🔬", color: "text-amber-300",  bg: "bg-amber-500/10 border-amber-500/30" },
  uat:        { icon: "👥", color: "text-blue-300",   bg: "bg-blue-500/10 border-blue-500/30" },
};

const RUN_STATUS: Record<string, { dot: string; label: string; labelColor: string; rowBg: string }> = {
  in_progress: { dot: "bg-violet-500 animate-pulse", label: "Devam ediyor", labelColor: "text-violet-400", rowBg: "border-violet-500/20 bg-violet-500/5" },
  not_started: { dot: "bg-slate-500",                label: "Başlamadı",    labelColor: "text-slate-400",  rowBg: "border-slate-800" },
  completed:   { dot: "bg-emerald-500",              label: "Tamamlandı",   labelColor: "text-emerald-400",rowBg: "border-emerald-500/10" },
  failed:      { dot: "bg-rose-500",                 label: "Başarısız",    labelColor: "text-rose-400",   rowBg: "border-rose-500/10" },
};

type RunRow = { id: string; name: string; status: string; started_at: string | null; completed_at: string | null; environment?: string };

function RunCard({ run, projectId }: { run: RunRow; projectId: string }) {
  const cfg = RUN_STATUS[run.status] ?? RUN_STATUS.not_started;
  const env = run.environment ? ENV_CONFIG[run.environment] : null;

  return (
    <Link href={`/p/${projectId}/management/runs/${run.id}/execute`}>
      <div className={`group rounded-2xl border ${cfg.rowBg} p-4 flex items-center gap-4 hover:border-slate-600 transition-all`}>
        {/* Status dot */}
        <span className={`w-3 h-3 rounded-full shrink-0 ${cfg.dot}`} />

        {/* İsim + ortam */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white truncate group-hover:text-violet-300 transition-colors">
            {run.name}
          </p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className={`text-xs ${cfg.labelColor}`}>{cfg.label}</span>
            {env && (
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${env.bg} ${env.color}`}>
                {env.icon} {run.environment}
              </span>
            )}
          </div>
        </div>

        {/* Tarihler */}
        <div className="text-right shrink-0 space-y-1">
          {run.started_at ? (
            <p className="text-xs text-slate-400">
              {new Date(run.started_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
              {" "}
              <span className="text-slate-600">{new Date(run.started_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}</span>
            </p>
          ) : (
            <p className="text-xs text-slate-600">Başlamadı</p>
          )}
          {run.completed_at && (
            <p className="text-[10px] text-slate-600">
              → {new Date(run.completed_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
            </p>
          )}
        </div>

        <span className="text-slate-700 group-hover:text-slate-400 transition-colors">›</span>
      </div>
    </Link>
  );
}

export default function ManagementRunsPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const summary      = useExecutionSummary(projectId);
  const runs         = useManagementRuns(projectId);
  const cycles       = useManagementCycles(projectId);
  const cases        = useManagementCases(projectId);
  const regressionSets = useRegressionSets(projectId);
  const createRun    = useCreateManagementRun(projectId);

  const [runName, setRunName]     = useState("");
  const [cycleId, setCycleId]     = useState("");
  const [regressionSetId, setRegressionSetId] = useState("");
  const [environment, setEnvironment] = useState("");
  const [showForm, setShowForm]   = useState(false);

  const data = summary.data;
  const allRuns = (runs.data ?? []) as RunRow[];
  const activeRun = allRuns.find((r) => r.status === "in_progress");

  const runnableCases = useMemo(
    () => (cases.data ?? []).filter((item: { status: string; archived: boolean }) =>
      ["active", "ready"].includes(item.status) && !item.archived),
    [cases.data],
  );

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const selectedCycle = cycleId || cycles.data?.[0]?.id;
    const selectedSet = (regressionSets.data ?? []).find((item) => item.id === regressionSetId);
    const selectedCaseIds = selectedSet
      ? selectedSet.cases.map((item: { case_id: string }) => item.case_id)
      : runnableCases.map((item: { id: string }) => item.id);
    if (!runName.trim() || !selectedCycle || selectedCaseIds.length === 0) return;

    const run = await createRun.mutateAsync({
      cycle_id: selectedCycle,
      name: runName.trim(),
      case_ids: selectedCaseIds,
      environment: environment.trim() || null,
      source_type: selectedSet ? "regression_set" : "manual",
      source_ref: selectedSet?.id ?? null,
      scope_snapshot: selectedSet
        ? { regression_set_id: selectedSet.id, regression_set_name: selectedSet.name, case_count: selectedSet.cases.length }
        : { source: "ready_active_cases", case_count: selectedCaseIds.length },
    });
    setRunName("");
    window.location.href = `/p/${projectId}/management/runs/${run.id}/execute`;
  };

  // KPI hesapla
  const pct      = data ? Math.round(data.progress_pct ?? 0) : 0;
  const passRate = data ? data.pass_rate_pct : 0;

  return (
    <ManagementShell
      projectId={projectId}
      title="Test Runs"
      description=""
      active="management/runs"
    >
      {/* ── KPI bar ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Bekliyor",    value: data ? String(data.not_run)  : "…", accent: "text-slate-300",   icon: "⏳" },
          { label: "Geçti",       value: data ? String(data.passed)   : "…", accent: "text-emerald-400", icon: "✅" },
          { label: "Başarısız",   value: data ? String(data.failed)   : "…", accent: "text-rose-400",    icon: "❌" },
          { label: "Bloke",       value: data ? String(data.blocked)  : "…", accent: "text-amber-400",   icon: "🚫" },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl border border-slate-800 bg-slate-900 p-4 flex items-center gap-3">
            <span className="text-xl">{s.icon}</span>
            <div>
              <p className={`text-2xl font-black ${s.accent}`}>{s.value}</p>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* İlerleme çubuğu */}
      {data && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4 space-y-2">
          <div className="flex justify-between items-center">
            <p className="text-sm font-semibold text-white">Execution İlerlemesi</p>
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-400">Pass rate: <strong className={passRate >= 90 ? "text-emerald-400" : passRate >= 70 ? "text-amber-400" : "text-rose-400"}>{passRate.toFixed(1)}%</strong></span>
              <span className="text-violet-400 font-black">{pct}%</span>
            </div>
          </div>
          <div className="h-2.5 rounded-full bg-slate-800 overflow-hidden flex gap-0.5">
            {data.total > 0 && ([
              [data.passed,  "bg-emerald-500"],
              [data.failed,  "bg-rose-500"],
              [data.blocked, "bg-amber-500"],
              [data.skipped, "bg-slate-500"],
            ] as [number, string][]).map(([cnt, color], i) =>
              cnt > 0 ? <div key={i} className={`${color} h-full`} style={{ width: `${(cnt / data.total) * 100}%` }} /> : null
            )}
          </div>
        </div>
      )}

      {/* ── Intelligence Panel (aktif run varsa) ── */}
      {activeRun && (
        <div className="rounded-2xl border border-violet-500/30 bg-violet-500/5 overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-3 border-b border-violet-500/20">
            <span className="text-violet-400 font-bold text-sm">⚡ Zeka Paneli</span>
            <span className="text-xs text-slate-400 truncate">{activeRun.name}</span>
            <Link href={`/p/${projectId}/management/runs/${activeRun.id}/execute`} className="ml-auto text-xs text-violet-400 hover:text-violet-300">
              Koşuma git →
            </Link>
          </div>
          <div className="p-4">
            <IntelligencePanel projectId={projectId} runId={activeRun.id} refreshIntervalMs={30_000} />
          </div>
        </div>
      )}

      {/* ── Run listesi + yeni run ── */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <div>
            <p className="text-sm font-semibold text-white">Tüm Runlar</p>
            <p className="text-xs text-slate-500 mt-0.5">{allRuns.length} koşum · son 10 gösteriliyor</p>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 rounded-xl bg-violet-600 hover:bg-violet-700 px-4 py-2 text-sm font-semibold text-white transition-colors"
          >
            <span className="text-lg leading-none">+</span>
            Yeni Run
          </button>
        </div>

        {/* Yeni run formu — toggle */}
        {showForm && (
          <form onSubmit={handleCreate} className="border-b border-slate-800 p-4 bg-slate-950/50">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Yeni Koşum Oluştur</p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              <input
                value={runName}
                onChange={(e) => setRunName(e.target.value)}
                placeholder="Run adı *"
                required
                className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-violet-500 transition-colors"
              />
              <select
                value={cycleId}
                onChange={(e) => setCycleId(e.target.value)}
                className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-500"
              >
                <option value="">Cycle seç</option>
                {(cycles.data ?? []).map((c: { id: string; name: string }) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
              <select
                value={regressionSetId}
                onChange={(e) => setRegressionSetId(e.target.value)}
                className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-500"
              >
                <option value="">Tüm aktif case'ler</option>
                {(regressionSets.data ?? []).map((s: { id: string; name: string; cases: unknown[] }) => (
                  <option key={s.id} value={s.id}>{s.name} ({s.cases.length})</option>
                ))}
              </select>
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
                className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-500"
              >
                <option value="">Ortam (opsiyonel)</option>
                <option value="staging">🧪 Staging</option>
                <option value="production">🚀 Production</option>
                <option value="dev">💻 Development</option>
                <option value="qa">🔬 QA</option>
                <option value="uat">👥 UAT</option>
              </select>
              <button
                type="submit"
                disabled={createRun.isPending || !runName.trim()}
                className="rounded-xl bg-violet-600 hover:bg-violet-700 disabled:opacity-40 px-4 py-2.5 text-sm font-bold text-white transition-colors"
              >
                {createRun.isPending ? "Oluşturuluyor…" : "Başlat →"}
              </button>
            </div>
          </form>
        )}

        {/* Run kartları */}
        <div className="p-4 space-y-2">
          {runs.isLoading ? (
            <div className="py-10 flex justify-center">
              <span className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : allRuns.length === 0 ? (
            <div className="py-12 text-center space-y-3">
              <p className="text-4xl">▶️</p>
              <p className="text-slate-300 font-medium">Henüz run yok</p>
              <p className="text-xs text-slate-500">Yukarıdan ilk koşumunuzu oluşturun.</p>
              <button onClick={() => setShowForm(true)} className="text-sm text-violet-400 hover:text-violet-300">
                Yeni Run Oluştur →
              </button>
            </div>
          ) : (
            allRuns.slice(0, 10).map((run) => (
              <RunCard key={run.id} run={run} projectId={projectId} />
            ))
          )}
        </div>
      </div>
    </ManagementShell>
  );
}
