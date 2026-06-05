"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api-client";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

type MyCase = {
  run_case_id: string;
  run_id: string;
  run_name: string;
  run_status: string;
  case_id: string;
  case_key: string | null;
  title: string | null;
  status: string;
  priority: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  step_count: number;
  completed_steps: number;
};

const STATUS_CONFIG: Record<string, { label: string; dot: string; badge: string }> = {
  not_run:  { label: "Bekliyor",   dot: "bg-slate-500",   badge: "bg-slate-700 text-slate-300" },
  passed:   { label: "Geçti",      dot: "bg-emerald-500", badge: "bg-emerald-500/20 text-emerald-400" },
  failed:   { label: "Başarısız",  dot: "bg-red-500",    badge: "bg-red-500/20 text-red-400" },
  blocked:  { label: "Bloke",      dot: "bg-amber-500",   badge: "bg-amber-500/20 text-amber-400" },
  skipped:  { label: "Atlandı",    dot: "bg-slate-600",   badge: "bg-slate-700 text-slate-400" },
};

const PRIORITY_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high:     "bg-orange-500",
  medium:   "bg-amber-500",
  low:      "bg-slate-500",
};

function formatDuration(s: number | null) {
  if (!s) return null;
  if (s < 60) return `${s}sn`;
  return `${Math.floor(s / 60)}dk ${s % 60}sn`;
}

function CaseCard({ c, projectId }: { c: MyCase; projectId: string }) {
  const cfg = STATUS_CONFIG[c.status] ?? STATUS_CONFIG.not_run;
  const pct = c.step_count > 0 ? Math.round((c.completed_steps / c.step_count) * 100) : 0;

  return (
    <div className={`rounded-xl border bg-surface-raised overflow-hidden transition-all hover:border-border-strong ${
      c.status === "not_run" ? "border-border" :
      c.status === "failed"  ? "border-red-500/30" :
      c.status === "passed"  ? "border-emerald-500/20" :
      "border-border"
    }`}>
      <div className="p-4 space-y-3">
        {/* Üst satır */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${cfg.dot}`} />
            <div className="min-w-0">
              {c.case_key && (
                <span className="text-xs font-mono text-slate-500 mr-2">{c.case_key}</span>
              )}
              <span className="text-sm font-medium text-white truncate">{c.title ?? c.case_id}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.badge}`}>
              {cfg.label}
            </span>
            <span className={`w-2 h-2 rounded-full ${PRIORITY_DOT[c.priority] ?? "bg-slate-500"}`} title={c.priority} />
          </div>
        </div>

        {/* Run bilgisi */}
        <p className="text-xs text-slate-500 truncate">📋 {c.run_name}</p>

        {/* Adım ilerleme */}
        {c.step_count > 0 && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Adımlar</span>
              <span>{c.completed_steps}/{c.step_count}</span>
            </div>
            <div className="h-1.5 rounded-full bg-surface-overlay overflow-hidden">
              <div
                className="h-full rounded-full bg-teal-500 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )}

        {/* Alt satır */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 text-xs text-slate-500">
            {c.duration_seconds && (
              <span>⏱ {formatDuration(c.duration_seconds)}</span>
            )}
            {c.started_at && !c.completed_at && (
              <span className="text-amber-400 animate-pulse">● Devam ediyor</span>
            )}
          </div>
          {c.status === "not_run" && (
            <Link
              href={`/p/${projectId}/management/runs/${c.run_id}/execute`}
              className="rounded-lg bg-brand hover:brightness-105 px-3 py-1.5 text-xs font-semibold text-white transition-colors"
            >
              Başlat →
            </Link>
          )}
          {c.status === "failed" && (
            <Link
              href={`/p/${projectId}/management/runs/${c.run_id}/execute`}
              className="rounded-lg border border-red-500/40 hover:bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-400 transition-colors"
            >
              Yeniden Dene
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TesterHomePage() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid      = useManagementProjectId(projectId || undefined);
  const [cases, setCases] = useState<MyCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "not_run" | "failed" | "passed">("all");

  const fetchCases = useCallback(async () => {
    const pid = mpid || projectId;
    if (!pid) { setLoading(false); return; }
    setError(null);
    try {
      const data = await apiFetch<MyCase[]>(
        `/api/v1/test-management/projects/${pid}/my-cases`,
      );
      setCases(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Görevler yüklenirken bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }, [mpid, projectId]);

  useEffect(() => { fetchCases(); }, [fetchCases]);

  const filtered = filter === "all" ? cases : cases.filter((c) => c.status === filter);
  const pending  = cases.filter((c) => c.status === "not_run").length;
  const done     = cases.filter((c) => ["passed", "skipped"].includes(c.status)).length;
  const failed   = cases.filter((c) => c.status === "failed").length;
  const pct      = cases.length > 0 ? Math.round((done / cases.length) * 100) : 0;

  const nextCase = cases.find((c) => c.status === "not_run");

  return (
    <div className="min-h-full bg-bg px-5 py-5 space-y-5">
      {/* Özet istatistikler */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Toplam", value: cases.length, color: "text-white" },
          { label: "Bekliyor", value: pending, color: "text-amber-400" },
          { label: "Tamamlandı", value: done, color: "text-emerald-400" },
          { label: "Başarısız", value: failed, color: "text-red-400" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border border-border bg-surface-raised p-4 text-center">
            <p className={`text-2xl font-bold ${stat.color}`}>{loading ? "…" : stat.value}</p>
            <p className="text-xs text-slate-500 mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Genel ilerleme çubuğu */}
      {!loading && cases.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-raised p-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-slate-300 font-medium">Bugünkü İlerleme</span>
            <span className="text-teal-400 font-bold">{pct}%</span>
          </div>
          <div className="h-3 rounded-full bg-surface-overlay overflow-hidden">
            <div
              className="h-full rounded-full bg-teal-500 transition-all duration-700"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs text-slate-500">{done} tamamlandı · {pending} bekliyor · {failed} başarısız</p>
        </div>
      )}

      {/* Sonraki case — büyük aksiyon kartı */}
      {!loading && nextCase && (
        <div className="rounded-xl border border-teal-500/40 bg-teal-500/10 p-5 space-y-3">
          <p className="text-xs font-semibold text-teal-400 uppercase tracking-wide">⚡ Sıradaki Görev</p>
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-white font-semibold">
                {nextCase.case_key && <span className="font-mono text-slate-400 mr-2 text-sm">{nextCase.case_key}</span>}
                {nextCase.title}
              </p>
              <p className="text-xs text-slate-400 mt-1">{nextCase.run_name}</p>
            </div>
            <Link
              href={`/p/${projectId}/management/runs/${nextCase.run_id}/execute`}
              className="shrink-0 rounded-xl bg-brand hover:brightness-105 px-5 py-2.5 text-sm font-bold text-white transition-colors"
            >
              Başlat →
            </Link>
          </div>
          {nextCase.step_count > 0 && (
            <p className="text-xs text-slate-500">{nextCase.step_count} adım</p>
          )}
        </div>
      )}

      {/* Filtreler */}
      <div className="flex gap-2 flex-wrap">
        {(["all", "not_run", "failed", "passed"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${
              filter === f
                ? "bg-brand text-white"
                : "bg-surface-overlay text-slate-400 hover:bg-slate-700"
            }`}
          >
            {f === "all" ? "Tümü" : f === "not_run" ? "Bekleyenler" : f === "failed" ? "Başarısızlar" : "Tamamlananlar"}
            {f !== "all" && (
              <span className="ml-1.5 opacity-70">
                {f === "not_run" ? pending : f === "failed" ? failed : done}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Hata mesajı */}
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 flex items-center gap-2">
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>
          {error}
          <button onClick={fetchCases} className="ml-auto text-xs underline hover:no-underline">Tekrar Dene</button>
        </div>
      )}

      {/* Case listesi */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-slate-500 text-sm">
          <span className="w-5 h-5 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mr-3" />
          Görevler yükleniyor…
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-border bg-surface-raised py-16 text-center">
          <p className="text-4xl mb-3">✅</p>
          <p className="text-slate-300 font-medium">
            {filter === "all" ? "Atanmış görev yok" : "Bu filtrede görev yok"}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {filter === "all" ? "Test yöneticinizden case atamasını bekleyin." : "Filtreyi değiştirin."}
          </p>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {filtered.map((c) => (
            <CaseCard key={c.run_case_id} c={c} projectId={projectId} />
          ))}
        </div>
      )}
    </div>
  );
}
