"use client";

import Link from "next/link";
import { useState, useMemo, useCallback, memo } from "react";
import { useRouter } from "next/navigation";
import {
  useManagementRuns,
  useCreateManagementRun,
  useManagementCycles,
  type TestRun,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

const STATUS_DOT: Record<string, string> = {
  in_progress: "bg-blue-500 animate-pulse",
  completed:   "bg-emerald-500",
  failed:      "bg-red-500",
  not_started: "bg-slate-600",
};
const STATUS_LABEL: Record<string, string> = {
  in_progress: "Devam ediyor",
  completed:   "Tamamlandı",
  failed:      "Başarısız",
  not_started: "Başlamadı",
};

type RunRowProps = {
  run: TestRun;
  projectId: string;
  onNavigate: (id: string) => void;
};

const RunRow = memo(function RunRow({ run, projectId, onNavigate }: RunRowProps) {
  const status = run.status || "not_started";
  const dot    = STATUS_DOT[status]   ?? "bg-slate-600";
  const label  = STATUS_LABEL[status] ?? status;

  const handleClick = useCallback(() => {
    onNavigate(run.id);
  }, [onNavigate, run.id]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onNavigate(run.id);
    }
  }, [onNavigate, run.id]);

  return (
    <tr
      className="border-b border-white/[0.04] hover:bg-white/[0.04] transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
    >
      <td className="w-6 pl-4 py-3">
        <span className={`inline-block h-1.5 w-1.5 rounded-full ${dot}`} />
      </td>
      <td className="py-3 px-4">
        <span className="text-[13px] text-slate-200">{run.name}</span>
      </td>
      <td className="py-3 px-4">
        <span className="text-[11px] text-slate-500">{run.environment ?? "—"}</span>
      </td>
      <td className="py-3 px-4">
        <span className="text-[11px] text-slate-500">
          {run.started_at
            ? new Date(run.started_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })
            : "—"}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className="text-[11px] text-slate-400">{label}</span>
      </td>
      <td className="py-3 px-4">
        <Link
          href={`/p/${projectId}/management/runs/${run.id}/execute`}
          onClick={e => e.stopPropagation()}
          className="text-[11px] text-blue-500 hover:text-blue-400 transition-colors"
        >
          ▶ Execute
        </Link>
      </td>
    </tr>
  );
});

function Skeleton() {
  return (
    <div className="animate-pulse space-y-2 p-4">
      {[1, 2, 3].map(i => (
        <div key={i} className="h-10 rounded bg-white/[0.04]" />
      ))}
    </div>
  );
}

export default function ManagementRunsPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const { data: runs, isLoading, isError, refetch } = useManagementRuns(mpid || undefined);
  const { data: cycles }          = useManagementCycles(mpid || undefined);
  const createRun                 = useCreateManagementRun(mpid || "");

  const [showModal, setShowModal] = useState(false);
  const [runName, setRunName]     = useState("");
  const [cycleId, setCycleId]     = useState("");
  const [caseCount, setCaseCount] = useState("10");

  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;

  const allRuns = useMemo(() => runs ?? [], [runs]);

  const { total, inProgress, completed, failed } = useMemo(() => ({
    total:      allRuns.length,
    inProgress: allRuns.filter(r => r.status === "in_progress").length,
    completed:  allRuns.filter(r => r.status === "completed").length,
    failed:     allRuns.filter(r => r.status === "failed").length,
  }), [allRuns]);

  const totalPages = useMemo(() => Math.ceil(allRuns.length / PAGE_SIZE), [allRuns.length]);

  const paginatedRuns = useMemo(
    () => allRuns.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [allRuns, page]
  );

  const handleNavigate = useCallback((runId: string) => {
    router.push(`/p/${projectId}/management/runs/${runId}/execute`);
  }, [router, projectId]);

  const handleCreate = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const chosenCycle = cycleId || cycles?.[0]?.id;
    if (!runName.trim() || !chosenCycle) return;
    const count = parseInt(caseCount, 10) || 10;
    const run = await createRun.mutateAsync({
      cycle_id: chosenCycle,
      name: runName.trim(),
      case_ids: [],
      scope_snapshot: { case_count: count },
    });
    setShowModal(false);
    setRunName("");
    router.push(`/p/${projectId}/management/runs/${run.id}/execute`);
  }, [cycleId, cycles, runName, caseCount, createRun, router, projectId]);

  if (isError) {
    return (
      <div className="flex min-h-[calc(100vh-88px)] items-center justify-center bg-[#0a0f1e]">
        <div className="text-center">
          <p className="text-[13px] text-red-400">Run listesi yüklenirken hata oluştu.</p>
          <button onClick={() => refetch()} className="mt-3 rounded-md border border-white/[0.08] px-4 py-2 text-[11px] text-slate-400 hover:text-slate-200 transition-colors">
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  if (createRun.isError) {
    console.error("Run oluşturma hatası:", createRun.error);
  }

  return (
    <div className="min-h-[calc(100vh-48px-40px)] bg-[#0a0f1e] text-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.06] bg-[#0d1221] px-6 py-4">
        <h1 className="text-[13px] font-semibold text-slate-200">Test Runs</h1>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-[11px] font-medium text-white hover:bg-blue-500 transition-colors"
        >
          + Yeni Run
        </button>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-6 border-b border-white/[0.06] px-6 py-3">
        {[
          { dot: "bg-slate-500",                  count: total,      label: "Toplam"       },
          { dot: "bg-blue-500 animate-pulse",      count: inProgress, label: "Devam Eden"  },
          { dot: "bg-emerald-500",                 count: completed,  label: "Tamamlandı"  },
          { dot: "bg-red-500",                     count: failed,     label: "Başarısız"   },
        ].map(({ dot, count, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
            <span className="text-[13px] font-medium text-slate-200">{count}</span>
            <span className="text-[11px] text-slate-500">{label}</span>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        {isLoading ? (
          <Skeleton />
        ) : allRuns.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <svg className="h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
            </svg>
            <p className="text-[13px] text-slate-500">Henüz run yok</p>
            <button
              onClick={() => setShowModal(true)}
              className="rounded-md border border-white/[0.08] px-4 py-2 text-[11px] text-slate-400 hover:border-white/[0.15] hover:text-slate-200 transition-colors"
            >
              Yeni Run Oluştur
            </button>
          </div>
        ) : (
          <>
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/[0.06] bg-[#0d1221]">
                {["", "Run Adı", "Ortam", "Başlangıç", "Durum", ""].map((h, i) => (
                  <th key={i} className="px-4 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider text-slate-600">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedRuns.map(run => (
                <RunRow
                  key={run.id}
                  run={run}
                  projectId={projectId ?? ""}
                  onNavigate={handleNavigate}
                />
              ))}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-white/[0.06] px-4 py-3">
              <span className="text-[11px] text-slate-500">
                {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, allRuns.length)} / {allRuns.length} run
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="rounded-md border border-white/[0.08] px-2.5 py-1 text-[11px] text-slate-400 hover:text-slate-200 disabled:opacity-30 transition-colors"
                >
                  ‹ Önceki
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`rounded-md border px-2.5 py-1 text-[11px] transition-colors ${
                      p === page
                        ? "border-blue-500/50 bg-blue-600/20 text-blue-400"
                        : "border-white/[0.08] text-slate-500 hover:text-slate-200"
                    }`}
                  >
                    {p}
                  </button>
                ))}
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="rounded-md border border-white/[0.08] px-2.5 py-1 text-[11px] text-slate-400 hover:text-slate-200 disabled:opacity-30 transition-colors"
                >
                  Sonraki ›
                </button>
              </div>
            </div>
          )}
          </>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-md rounded-xl border border-white/[0.08] bg-[#0d1221] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
              <span className="text-[13px] font-semibold text-slate-200">Yeni Run</span>
              <button onClick={() => setShowModal(false)} className="text-slate-500 hover:text-slate-300 transition-colors text-lg leading-none">×</button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3 p-5">
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Run Adı</label>
                <input
                  value={runName}
                  onChange={e => setRunName(e.target.value)}
                  placeholder="örn. Sprint 24 Regression"
                  required
                  className="w-full rounded-md border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/50"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Cycle</label>
                <select
                  value={cycleId}
                  onChange={e => setCycleId(e.target.value)}
                  className="w-full rounded-md border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-blue-500/50"
                >
                  <option value="">— Cycle seç —</option>
                  {(cycles ?? []).map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Case Sayısı</label>
                <input
                  type="number"
                  min={1}
                  value={caseCount}
                  onChange={e => setCaseCount(e.target.value)}
                  className="w-full rounded-md border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-blue-500/50"
                />
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => setShowModal(false)}
                  className="rounded-md border border-white/[0.08] px-4 py-2 text-[11px] text-slate-400 hover:text-slate-200 transition-colors">
                  İptal
                </button>
                <button type="submit" disabled={createRun.isPending || !runName.trim()}
                  className="rounded-md bg-blue-600 px-4 py-2 text-[11px] font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors">
                  {createRun.isPending ? "Oluşturuluyor…" : "Oluştur"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
