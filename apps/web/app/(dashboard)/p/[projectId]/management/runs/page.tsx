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

const RUN_STATUS: Record<string, { dot: string; label: string }> = {
  in_progress: { dot: "bg-emerald-400 animate-pulse", label: "Devam ediyor" },
  not_started: { dot: "bg-slate-600",                  label: "Başlamadı" },
  completed:   { dot: "bg-slate-400",                  label: "Tamamlandı" },
  failed:      { dot: "bg-red-400",                    label: "Başarısız" },
};

const ENV_EMOJI: Record<string, string> = { staging: "🧪", production: "🚀", dev: "💻", qa: "🔬", uat: "👥" };

type RunRow = { id: string; name: string; status: string; started_at: string | null; completed_at: string | null; environment?: string };

export default function ManagementRunsPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;
  const summary        = useExecutionSummary(projectId);
  const runs           = useManagementRuns(projectId);
  const cycles         = useManagementCycles(projectId);
  const cases          = useManagementCases(projectId);
  const regressionSets = useRegressionSets(projectId);
  const createRun      = useCreateManagementRun(projectId);

  const [runName, setRunName]               = useState("");
  const [cycleId, setCycleId]               = useState("");
  const [regressionSetId, setRegressionSetId] = useState("");
  const [environment, setEnvironment]       = useState("");
  const [showForm, setShowForm]             = useState(false);

  const data    = summary.data;
  const allRuns = (runs.data ?? []) as RunRow[];
  const activeRun = allRuns.find(r => r.status === "in_progress");

  const runnableCases = useMemo(
    () => (cases.data ?? []).filter((c: { status: string; archived: boolean }) =>
      ["active", "ready"].includes(c.status) && !c.archived),
    [cases.data],
  );

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const selectedCycle = cycleId || cycles.data?.[0]?.id;
    const selectedSet = (regressionSets.data ?? []).find(s => s.id === regressionSetId);
    const caseIds = selectedSet
      ? selectedSet.cases.map((c: { case_id: string }) => c.case_id)
      : runnableCases.map((c: { id: string }) => c.id);
    if (!runName.trim() || !selectedCycle || !caseIds.length) return;
    const run = await createRun.mutateAsync({
      cycle_id: selectedCycle,
      name: runName.trim(),
      case_ids: caseIds,
      environment: environment || null,
      source_type: selectedSet ? "regression_set" : "manual",
      source_ref: selectedSet?.id ?? null,
      scope_snapshot: selectedSet
        ? { regression_set_id: selectedSet.id, case_count: selectedSet.cases.length }
        : { source: "ready_active_cases", case_count: caseIds.length },
    });
    setRunName(""); setShowForm(false);
    window.location.href = `/p/${projectId}/management/runs/${run.id}/execute`;
  };

  return (
    <ManagementShell projectId={projectId} title="" description="" active="management/runs">

      {/* Başlık */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-base font-semibold text-white">Test Runs</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {data ? `${data.not_run} bekliyor · ${data.passed} geçti · ${data.failed} başarısız · ${data.blocked} bloke` : "Yükleniyor…"}
          </p>
        </div>
        <button onClick={() => setShowForm(v => !v)}
          className="rounded-lg bg-white hover:bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-900 transition-colors">
          {showForm ? "İptal" : "+ Yeni Run"}
        </button>
      </div>

      {/* İlerleme */}
      {data && data.total > 0 && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-slate-500">
            <span>İlerleme</span>
            <span>{Math.round(data.progress_pct ?? 0)}% · pass {data.pass_rate_pct?.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden flex gap-px">
            {([
              [data.passed,  "bg-emerald-600"],
              [data.failed,  "bg-red-600"],
              [data.blocked, "bg-amber-600"],
              [data.skipped, "bg-slate-600"],
            ] as [number, string][]).map(([cnt, color], i) =>
              cnt > 0 ? <div key={i} className={`${color} h-full`} style={{ width: `${(cnt / data.total) * 100}%` }} /> : null
            )}
          </div>
        </div>
      )}

      {/* Yeni run formu */}
      {showForm && (
        <form onSubmit={handleCreate} className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3">
          <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">Yeni Koşum</p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <input value={runName} onChange={e => setRunName(e.target.value)} placeholder="Run adı *" required
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-slate-500" />
            <select value={cycleId} onChange={e => setCycleId(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none">
              <option value="">Cycle seç</option>
              {(cycles.data ?? []).map((c: { id: string; name: string }) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select value={regressionSetId} onChange={e => setRegressionSetId(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none">
              <option value="">Tüm aktif case'ler</option>
              {(regressionSets.data ?? []).map((s: { id: string; name: string; cases: unknown[] }) =>
                <option key={s.id} value={s.id}>{s.name} ({s.cases.length})</option>)}
            </select>
            <select value={environment} onChange={e => setEnvironment(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none">
              <option value="">Ortam (opsiyonel)</option>
              <option value="staging">🧪 Staging</option>
              <option value="production">🚀 Production</option>
              <option value="dev">💻 Development</option>
              <option value="qa">🔬 QA</option>
              <option value="uat">👥 UAT</option>
            </select>
          </div>
          <button type="submit" disabled={createRun.isPending || !runName.trim()}
            className="rounded-lg bg-white hover:bg-slate-100 disabled:opacity-40 px-4 py-2 text-xs font-semibold text-slate-900 transition-colors">
            {createRun.isPending ? "Oluşturuluyor…" : "Koşumu Başlat"}
          </button>
        </form>
      )}

      {/* Zeka paneli */}
      {activeRun && (
        <div className="rounded-xl border border-slate-800 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <p className="text-xs font-medium text-slate-300">Canlı: {activeRun.name}</p>
            </div>
            <Link href={`/p/${projectId}/management/runs/${activeRun.id}/execute`}
              className="text-xs text-slate-500 hover:text-white transition-colors">Koşuma git →</Link>
          </div>
          <div className="p-4">
            <IntelligencePanel projectId={projectId} runId={activeRun.id} refreshIntervalMs={30_000} />
          </div>
        </div>
      )}

      {/* Run listesi */}
      <div className="rounded-xl border border-slate-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <p className="text-sm font-medium text-white">Tüm Runlar</p>
          <span className="text-xs text-slate-600">{allRuns.length}</span>
        </div>
        <div className="divide-y divide-slate-800/50">
          {runs.isLoading ? (
            <p className="px-4 py-8 text-center text-sm text-slate-600">Yükleniyor…</p>
          ) : allRuns.length === 0 ? (
            <div className="px-4 py-10 text-center">
              <p className="text-sm text-slate-500">Henüz run yok</p>
              <button onClick={() => setShowForm(true)}
                className="mt-2 text-xs text-slate-500 hover:text-white border border-slate-700 hover:border-slate-500 rounded px-3 py-1.5 transition-colors">
                İlk koşumu oluştur
              </button>
            </div>
          ) : (
            allRuns.slice(0, 10).map(run => {
              const cfg = RUN_STATUS[run.status] ?? RUN_STATUS.not_started;
              return (
                <Link key={run.id} href={`/p/${projectId}/management/runs/${run.id}/execute`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-slate-800/30 transition-colors group">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${cfg.dot}`} />
                  <p className="flex-1 text-sm text-slate-300 group-hover:text-white transition-colors truncate">{run.name}</p>
                  {run.environment && (
                    <span className="text-xs text-slate-600">{ENV_EMOJI[run.environment] ?? ""} {run.environment}</span>
                  )}
                  <span className="text-xs text-slate-600 shrink-0">
                    {run.started_at ? new Date(run.started_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" }) : "—"}
                  </span>
                </Link>
              );
            })
          )}
        </div>
      </div>

    </ManagementShell>
  );
}
