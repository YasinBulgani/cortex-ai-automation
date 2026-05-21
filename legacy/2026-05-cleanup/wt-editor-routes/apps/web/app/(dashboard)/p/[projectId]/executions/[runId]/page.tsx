"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";

type ExecutionResult = {
  id: string;
  scenario_id: string;
  scenario_title: string;
  status: string;
  note: string | null;
};

type ExecutionDetail = {
  id: string;
  name: string;
  status: string;
  created_at: string | null;
  results: ExecutionResult[];
};

type ExecutionMetrics = {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  pass_rate: number;
  duration_seconds: number | null;
};

const STATUS_META: Record<string, { label: string; color: string; icon: string }> = {
  passed:  { label: "Geçti",    color: "bg-emerald-500/20 text-emerald-400 border-emerald-600/30", icon: "✓" },
  failed:  { label: "Kaldı",    color: "bg-red-500/20 text-red-400 border-red-600/30",             icon: "✗" },
  skipped: { label: "Atlandı",  color: "bg-slate-500/20 text-slate-400 border-slate-600/30",       icon: "⊘" },
  not_run: { label: "Koşulmadı",color: "bg-slate-700/30 text-slate-500 border-slate-700/30",       icon: "○" },
  blocked: { label: "Bloke",    color: "bg-orange-500/20 text-orange-400 border-orange-600/30",    icon: "⚠" },
  running: { label: "Koşuyor",  color: "bg-blue-500/20 text-blue-400 border-blue-600/30",          icon: "⟳" },
  pending: { label: "Bekliyor", color: "bg-slate-600/20 text-slate-500 border-slate-600/30",       icon: "…" },
};

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? { label: status, color: "bg-slate-700 text-slate-400 border-slate-600", icon: "?" };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${meta.color}`}>
      <span>{meta.icon}</span>
      {meta.label}
    </span>
  );
}

function ProgressBar({ passed, failed, skipped, total }: { passed: number; failed: number; skipped: number; total: number }) {
  if (total === 0) return null;
  const pPct = (passed / total) * 100;
  const fPct = (failed / total) * 100;
  const sPct = (skipped / total) * 100;
  return (
    <div className="w-full h-2 rounded-full overflow-hidden bg-slate-800 flex">
      <div className="bg-emerald-500 transition-all duration-500" style={{ width: `${pPct}%` }} />
      <div className="bg-red-500 transition-all duration-500" style={{ width: `${fPct}%` }} />
      <div className="bg-slate-600 transition-all duration-500" style={{ width: `${sPct}%` }} />
    </div>
  );
}

function MetricCard({ icon, label, value, sub, color }: { icon: string; label: string; value: number | string; sub?: string; color: string }) {
  return (
    <div className={`rounded-xl border p-4 text-center ${color}`} data-testid={`metric-${label}`}>
      <div className="text-2xl mb-0.5">{icon}</div>
      <p className="text-xl font-bold text-white">{value}</p>
      <p className="text-xs text-slate-400">{label}</p>
      {sub && <p className="text-[10px] text-slate-600 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function ExecutionDetailPage() {
  const projectId = useRouteParam("projectId");
  const runId = useRouteParam("runId");
  const router = useRouter();

  const [data, setData] = useState<ExecutionDetail | null>(null);
  const [metrics, setMetrics] = useState<ExecutionMetrics | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [completing, setCompleting] = useState(false);

  const load = useCallback(() => {
    apiFetch<ExecutionDetail>(`/api/v1/tspm/projects/${projectId}/executions/${runId}`)
      .then(setData)
      .catch(() => {});
    apiFetch<ExecutionMetrics>(`/api/v1/tspm/projects/${projectId}/executions/${runId}/metrics`)
      .then(setMetrics)
      .catch(() => {});
  }, [projectId, runId]);

  useEffect(() => { load(); }, [load]);

  async function saveRow(resultId: string, status: string, note: string) {
    setBusyId(resultId);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/executions/${runId}/results/${resultId}`, {
        method: "PATCH",
        json: { status, note },
      });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Güncelleme hatası");
    } finally {
      setBusyId(null);
    }
  }

  async function completeRun() {
    setCompleting(true);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/executions/${runId}`, {
        method: "PATCH",
        json: { status: "completed" },
      });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tamamlama hatası");
    } finally {
      setCompleting(false);
    }
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-40" data-testid="execution-loading">
        <div className="flex items-center gap-2 text-slate-400">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.4" strokeDashoffset="10" />
          </svg>
          Yükleniyor...
        </div>
      </div>
    );
  }

  const displayMetrics = metrics ?? {
    total: data.results.length,
    passed: data.results.filter((r) => r.status === "passed").length,
    failed: data.results.filter((r) => r.status === "failed").length,
    skipped: data.results.filter((r) => ["skipped", "not_run"].includes(r.status)).length,
    pass_rate: 0,
    duration_seconds: null,
  };

  return (
    <div className="flex h-full flex-col overflow-hidden" data-testid="execution-detail-page">
      {/* Header */}
      <div className="border-b border-slate-800 px-6 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              <span>🧪</span>
              {data.name || `Koşu ${runId.slice(0, 8)}`}
            </h1>
            <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
              <StatusBadge status={data.status} />
              {data.created_at && <span>{new Date(data.created_at).toLocaleString("tr-TR")}</span>}
              {displayMetrics.duration_seconds !== null && (
                <span>⏱ {displayMetrics.duration_seconds.toFixed(1)}s</span>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={completeRun}
              disabled={data.status === "completed" || completing}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500 transition disabled:opacity-40"
            >
              {completing ? "..." : "✓ Tamamla"}
            </button>
            <Link href={`/p/${projectId}/executions`}>
              <button className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:border-slate-500 transition">
                ← Liste
              </button>
            </Link>
          </div>
        </div>

        {error && (
          <div className="mt-2 rounded-lg border border-red-700/40 bg-red-950/20 px-3 py-2 text-xs text-red-300">
            ⚠ {error}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Metrics */}
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <MetricCard icon="🎯" label="Toplam" value={displayMetrics.total} color="border-slate-700 bg-slate-900/40" />
            <MetricCard
              icon="✅" label="Geçti" value={displayMetrics.passed}
              sub={`${displayMetrics.total > 0 ? ((displayMetrics.passed / displayMetrics.total) * 100).toFixed(0) : 0}%`}
              color="border-emerald-700/30 bg-emerald-950/20"
            />
            <MetricCard icon="❌" label="Kaldı" value={displayMetrics.failed} color="border-red-700/30 bg-red-950/20" />
            <MetricCard icon="⊘" label="Atlandı" value={displayMetrics.skipped} color="border-slate-700/30 bg-slate-900/30" />
          </div>
          <ProgressBar
            passed={displayMetrics.passed}
            failed={displayMetrics.failed}
            skipped={displayMetrics.skipped}
            total={displayMetrics.total}
          />
        </div>

        {/* Results table */}
        <div className="rounded-xl border border-slate-700 overflow-hidden" data-testid="results-table">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 bg-slate-800/30">
            <h2 className="text-sm font-semibold text-white">Senaryo Sonuçları</h2>
            <span className="text-xs text-slate-500">{data.results.length} senaryo</span>
          </div>
          {data.results.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-slate-500">
              Bu execution'da senaryo yok.
            </div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 bg-slate-900/50">
                <tr>
                  <th className="px-4 py-2.5 text-xs font-medium text-slate-400">Senaryo</th>
                  <th className="px-4 py-2.5 text-xs font-medium text-slate-400 w-32">Durum</th>
                  <th className="px-4 py-2.5 text-xs font-medium text-slate-400">Not</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r) => (
                  <tr key={r.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                    <td className="px-4 py-3 text-sm text-white font-medium">
                      {r.scenario_title || "Senaryo"}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {r.note || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
