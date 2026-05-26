"use client";

import {
  type DefectLink,
  useExecutionSummary,
  useManagementDefects,
  useUpdateManagementDefect,
} from "@/lib/hooks/use-management";

import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

const CLOSED_STATUSES = new Set(["closed", "done", "resolved", "fixed", "verified"]);
const BLOCKER_PATTERN = /blocker|critical|p0|sev0|sev1|release|prod|production|security|data loss/i;
const RETEST_STATUSES = new Set(["resolved", "fixed", "ready_for_retest", "ready for retest", "verify", "verified"]);
const AGING_TARGET_DAYS = 7;

function normalizedStatus(status: string) {
  return status.trim().toLowerCase();
}

function isClosed(defect: DefectLink) {
  return CLOSED_STATUSES.has(normalizedStatus(defect.status));
}

function isReleaseBlocker(defect: DefectLink) {
  return !isClosed(defect) && BLOCKER_PATTERN.test(`${defect.title} ${defect.status} ${defect.external_key}`);
}

function daysSince(value?: string | null) {
  if (!value) return null;
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return null;
  return Math.max(0, Math.floor((Date.now() - time) / 86_400_000));
}

function ageTone(days: number | null, closed: boolean) {
  if (closed) return "bg-slate-800 text-slate-400 ring-slate-700";
  if (days === null) return "bg-slate-800 text-slate-300 ring-slate-700";
  if (days > 14) return "bg-rose-500/15 text-rose-200 ring-rose-400/30";
  if (days > AGING_TARGET_DAYS) return "bg-amber-500/15 text-amber-200 ring-amber-400/30";
  return "bg-emerald-500/15 text-emerald-200 ring-emerald-400/30";
}

function statusTone(status: string) {
  const normalized = normalizedStatus(status);
  if (CLOSED_STATUSES.has(normalized)) return "bg-emerald-500/15 text-emerald-200 ring-emerald-400/30";
  if (normalized.includes("block")) return "bg-rose-500/15 text-rose-200 ring-rose-400/30";
  if (normalized.includes("progress")) return "bg-sky-500/15 text-sky-200 ring-sky-400/30";
  return "bg-amber-500/15 text-amber-200 ring-amber-400/30";
}

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

export default function ManagementDefectsPage({ params }: { params: { projectId: string } }) {
  const defects = useManagementDefects(params.projectId);
  const summary = useExecutionSummary(params.projectId);
  const updateDefect = useUpdateManagementDefect(params.projectId);
  const rows = defects.data ?? [];
  const openRows = rows.filter((item) => !isClosed(item));
  const open = openRows.length;
  const blockers = rows.filter(isReleaseBlocker);
  const retestQueue = rows.filter((item) => RETEST_STATUSES.has(normalizedStatus(item.status)) && !["closed", "done"].includes(normalizedStatus(item.status)));
  const agingRows = openRows
    .map((defect) => ({ defect, age: daysSince(defect.created_at) }))
    .sort((left, right) => (right.age ?? -1) - (left.age ?? -1));
  const oldestOpenAge = agingRows[0]?.age ?? 0;
  const staleOpen = agingRows.filter((item) => (item.age ?? 0) > AGING_TARGET_DAYS).length;
  const statusCounts = rows.reduce<Record<string, number>>((acc, defect) => {
    const status = normalizedStatus(defect.status) || "unknown";
    acc[status] = (acc[status] ?? 0) + 1;
    return acc;
  }, {});
  const statusSummary = Object.entries(statusCounts).sort((left, right) => right[1] - left[1]);

  const changeStatus = (defect: DefectLink, status: string) => {
    if (defect.status === status || updateDefect.isPending) return;
    updateDefect.mutate({ defectId: defect.id, status });
  };

  return (
    <ManagementShell
      projectId={params.projectId}
      title="Defects"
      description="Failed veya blocked manuel run sonuçlarından gelen defect lifecycle, retest ve release-risk sinyalleri."
      active="management/defects"
    >
      <div className="grid gap-4 md:grid-cols-5">
        <ManagementStat label="Open Defects" value={defects.isLoading ? "..." : String(open)} note="closed dışındaki kayıtlar" />
        <ManagementStat label="Release Blockers" value={defects.isLoading ? "..." : String(blockers.length)} note="critical / blocker sinyali" />
        <ManagementStat label="Retest Needed" value={defects.isLoading ? "..." : String(retestQueue.length || summary.data?.retest || 0)} note="fixed / resolved kuyruğu" />
        <ManagementStat label="Oldest Open" value={defects.isLoading ? "..." : `${oldestOpenAge}d`} note={`${staleOpen} item > ${AGING_TARGET_DAYS}d`} />
        <ManagementStat label="Total Links" value={defects.isLoading ? "..." : String(rows.length)} note="run result bağlantısı" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <ManagementPanel title="Status Summary">
          <div className="space-y-3">
            {statusSummary.map(([status, count]) => {
              const pct = rows.length ? Math.round((count / rows.length) * 100) : 0;
              return (
                <div key={status}>
                  <div className="flex items-center justify-between text-xs">
                    <span className={`rounded-full px-2 py-1 capitalize ring-1 ${statusTone(status)}`}>{statusLabel(status)}</span>
                    <span className="text-slate-400">{count} defects</span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full rounded-full bg-teal-400" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
            {!defects.isLoading && statusSummary.length === 0 ? (
              <p className="py-5 text-sm text-slate-500">Status özeti için henüz defect yok.</p>
            ) : null}
          </div>
        </ManagementPanel>

        <ManagementPanel title="Release Blockers">
          <div className="space-y-3">
            {blockers.slice(0, 5).map((defect) => (
              <div key={defect.id} className="rounded-lg border border-rose-400/20 bg-rose-500/5 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-mono text-xs text-rose-200">{defect.external_key}</p>
                  <span className={`rounded-full px-2 py-1 text-xs capitalize ring-1 ${statusTone(defect.status)}`}>
                    {statusLabel(defect.status)}
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-slate-200">{defect.title}</p>
                <button
                  type="button"
                  onClick={() => changeStatus(defect, "in_progress")}
                  disabled={updateDefect.isPending}
                  className="mt-3 rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 transition hover:border-cyan-500 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Start Fix
                </button>
              </div>
            ))}
            {!defects.isLoading && blockers.length === 0 ? (
              <p className="py-5 text-sm text-slate-500">Release blocker olarak işaretlenen açık defect yok.</p>
            ) : null}
          </div>
        </ManagementPanel>

        <ManagementPanel title="Retest Needed Queue">
          <div className="space-y-3">
            {retestQueue.slice(0, 5).map((defect) => (
              <div key={defect.id} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-mono text-xs text-slate-500">{defect.external_key}</p>
                  <span className="text-xs text-slate-500">{daysSince(defect.created_at) ?? "-"}d old</span>
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-slate-200">{defect.title}</p>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={() => changeStatus(defect, "closed")}
                    disabled={updateDefect.isPending}
                    className="rounded-md border border-emerald-500/40 px-2 py-1 text-xs text-emerald-200 transition hover:bg-emerald-500/10 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Verify Close
                  </button>
                  <button
                    type="button"
                    onClick={() => changeStatus(defect, "blocked")}
                    disabled={updateDefect.isPending}
                    className="rounded-md border border-rose-500/40 px-2 py-1 text-xs text-rose-200 transition hover:bg-rose-500/10 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Retest Blocked
                  </button>
                </div>
              </div>
            ))}
            {!defects.isLoading && retestQueue.length === 0 ? (
              <p className="py-5 text-sm text-slate-500">Resolved/fixed durumda retest bekleyen defect yok.</p>
            ) : null}
          </div>
        </ManagementPanel>
      </div>

      <ManagementPanel title="Defect Links">
        <div className="mb-4 rounded-lg border border-slate-800 bg-slate-950/50 p-3">
          <div className="flex flex-col gap-2 text-sm md:flex-row md:items-center md:justify-between">
            <div>
              <p className="font-medium text-slate-200">Aging focus</p>
              <p className="text-xs text-slate-500">
                Açık defectler {AGING_TARGET_DAYS} gün hedefiyle izlenir; blocker ve retest aksiyonları satırdan güncellenebilir.
              </p>
            </div>
            <div className="flex gap-2 text-xs">
              <span className="rounded-full bg-rose-500/15 px-2 py-1 text-rose-200 ring-1 ring-rose-400/30">{staleOpen} stale</span>
              <span className="rounded-full bg-slate-800 px-2 py-1 text-slate-300 ring-1 ring-slate-700">{open} open</span>
            </div>
          </div>
        </div>
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-950 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Key</th>
                <th>Title</th>
                <th>Status</th>
                <th>Aging</th>
                <th>Risk</th>
                <th>Source</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {rows.map((defect) => {
                const age = daysSince(defect.created_at);
                const closed = isClosed(defect);
                const blocker = isReleaseBlocker(defect);
                const needsRetest = RETEST_STATUSES.has(normalizedStatus(defect.status)) && !["closed", "done"].includes(normalizedStatus(defect.status));
                return (
                  <tr key={defect.id}>
                    <td className="px-3 py-2 font-mono text-xs text-slate-500">{defect.external_key}</td>
                    <td className="min-w-64 text-slate-200">{defect.title}</td>
                    <td>
                      <span className={`rounded-full px-2 py-1 text-xs capitalize ring-1 ${statusTone(defect.status)}`}>
                        {statusLabel(defect.status)}
                      </span>
                    </td>
                    <td>
                      <span className={`rounded-full px-2 py-1 text-xs ring-1 ${ageTone(age, closed)}`}>
                        {closed ? "closed" : age === null ? "unknown" : `${age}d`}
                      </span>
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {blocker ? <span className="rounded-full bg-rose-500/15 px-2 py-1 text-xs text-rose-200">blocker</span> : null}
                        {needsRetest ? <span className="rounded-full bg-cyan-500/15 px-2 py-1 text-xs text-cyan-200">retest</span> : null}
                        {!blocker && !needsRetest ? <span className="text-xs text-slate-600">watch</span> : null}
                      </div>
                    </td>
                    <td className="text-slate-500">{defect.external_source}</td>
                    <td className="text-slate-500">{new Date(defect.created_at).toLocaleDateString("tr-TR")}</td>
                    <td className="pr-3">
                      <div className="flex min-w-72 flex-wrap items-center gap-2">
                        <select
                          value={defect.status}
                          onChange={(event) => changeStatus(defect, event.target.value)}
                          disabled={updateDefect.isPending}
                          className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <option value="open">open</option>
                          <option value="in_progress">in progress</option>
                          <option value="blocked">blocked</option>
                          <option value="resolved">resolved</option>
                          <option value="closed">closed</option>
                        </select>
                        <button
                          type="button"
                          onClick={() => changeStatus(defect, "blocked")}
                          disabled={updateDefect.isPending || normalizedStatus(defect.status) === "blocked"}
                          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 transition hover:border-rose-500 hover:text-rose-200 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Block
                        </button>
                        <button
                          type="button"
                          onClick={() => changeStatus(defect, "resolved")}
                          disabled={updateDefect.isPending || normalizedStatus(defect.status) === "resolved"}
                          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 transition hover:border-cyan-500 hover:text-cyan-200 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Retest
                        </button>
                        <button
                          type="button"
                          onClick={() => changeStatus(defect, "closed")}
                          disabled={updateDefect.isPending || closed}
                          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 transition hover:border-emerald-500 hover:text-emerald-200 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Close
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!defects.isLoading && rows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-slate-500">
                    Henüz defect bağlantısı yok.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </ManagementPanel>
    </ManagementShell>
  );
}
