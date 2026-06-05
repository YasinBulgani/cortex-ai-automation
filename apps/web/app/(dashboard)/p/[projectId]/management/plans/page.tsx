"use client";

import { useState, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { RoleGuard } from "../_components/RoleGuard";
import {
  useManagementPlans,
  useCreateManagementPlan,
  useUpdateManagementPlan,
  useDeleteManagementPlan,
  useManagementCycles,
  useUpdateManagementCycle,
  useDeleteManagementCycle,
  useManagementRuns,
  useUpdateManagementRun,
  useDeleteManagementRun,
  useCreateManagementRun,
  useCreateManagementCycle,
  useAIGeneratePlan,
  useManagementRepository,
  usePlanImpactSummary,
  type TestPlan,
  type TestCycle,
  type TestRun,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { useToast } from "@/lib/useToast";
import { PageErrorBoundary } from "../_components/PageErrorBoundary";

// ── Types ─────────────────────────────────────────────────────────────────────
type PlanType = "release" | "regression" | "sprint" | "smoke" | "uat";

// ── Constants ─────────────────────────────────────────────────────────────────
const PLAN_TYPE_BADGE: Record<string, string> = {
  release:    "bg-teal-500/15 text-teal-400 border-teal-500/20",
  regression: "bg-purple-500/15 text-purple-400 border-purple-500/20",
  sprint:     "bg-blue-500/15 text-blue-400 border-blue-500/20",
  smoke:      "bg-amber-500/15 text-amber-400 border-amber-500/20",
  uat:        "bg-slate-500/15 text-fg-muted border-slate-500/20",
};

const RUN_STATUS_COLOR: Record<string, string> = {
  not_started: "text-fg-muted",
  in_progress: "text-blue-400",
  completed:   "text-emerald-400",
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" });
}

// ── Progress bar component ─────────────────────────────────────────────────────
function RunProgress({ passed, failed, blocked, notRun }: {
  passed: number; failed: number; blocked: number; notRun: number;
}) {
  const total = passed + failed + blocked + notRun;
  if (total === 0) return <span className="text-[11px] text-fg-subtle">Case eklenmemiş</span>;
  const pct = Math.round((passed / total) * 100);

  return (
    <div className="flex items-center gap-2.5 min-w-0">
      {/* Stacked bar */}
      <div className="flex h-1.5 w-28 overflow-hidden rounded-full bg-surface-overlay shrink-0">
        {passed > 0  && <div className="bg-emerald-500/80" style={{ width: `${(passed  / total) * 100}%` }} />}
        {failed > 0  && <div className="bg-red-500/80"     style={{ width: `${(failed  / total) * 100}%` }} />}
        {blocked > 0 && <div className="bg-amber-500/60"   style={{ width: `${(blocked / total) * 100}%` }} />}
      </div>
      {/* Counts */}
      <div className="flex items-center gap-2.5 text-[11px] tabular-nums">
        {passed  > 0 && <span className="text-emerald-400">{passed} <span className="text-fg-subtle">ok</span></span>}
        {failed  > 0 && <span className="text-red-400">{failed} <span className="text-fg-subtle">fail</span></span>}
        {blocked > 0 && <span className="text-amber-400">{blocked} <span className="text-fg-subtle">blk</span></span>}
        {notRun  > 0 && <span className="text-fg-subtle">{notRun} left</span>}
        <span className="text-fg-muted font-medium">{pct}%</span>
      </div>
    </div>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────
function IcChevron({ open }: { open: boolean }) {
  return (
    <svg className={cn("h-3.5 w-3.5 shrink-0 text-fg-subtle transition-transform", open && "rotate-90")}
      fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 18l6-6-6-6"/>
    </svg>
  );
}
function IcPlay() {
  return (
    <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24">
      <path d="M8 5v14l11-7z"/>
    </svg>
  );
}
function IcPlus() {
  return (
    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
    </svg>
  );
}
function IcTrash() {
  return (
    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  );
}

// ── Plan Run Modal — case seçimi ──────────────────────────────────────────────
function PlanStartRunModal({
  cycle,
  cases,
  suites,
  onClose,
  onConfirm,
  busy,
}: {
  cycle: TestCycle;
  cases: import("@/lib/hooks/use-management").TestCase[];
  suites: import("@/lib/hooks/use-management").TestSuite[];
  onClose: () => void;
  onConfirm: (runName: string, caseIds: string[], environment: string) => void;
  busy: boolean;
}) {
  const [name, setName] = useState(`Koşum — ${cycle.name}`);
  const [environment, setEnvironment] = useState(cycle.environment ?? "");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(() => {
    const active = cases.filter(c => !c.archived);
    return new Set(active.map(c => c.id));
  });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const active = cases.filter(c => !c.archived);
    if (!q) return active;
    return active.filter(c =>
      c.title.toLowerCase().includes(q) || c.case_key.toLowerCase().includes(q)
    );
  }, [cases, search]);

  const bySuite = useMemo(() => {
    const map = new Map<string, typeof cases>();
    for (const s of suites) map.set(s.id, []);
    for (const c of filtered) {
      const key = c.suite_id ?? "__unassigned__";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(c);
    }
    return map;
  }, [filtered, suites]);

  const toggle = (id: string) =>
    setSelected(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-6 bg-black/70 backdrop-blur-sm">
      <div className="relative flex max-h-[88vh] w-full max-w-lg flex-col rounded-2xl border border-border bg-surface-raised shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h2 className="text-[14px] font-semibold text-fg">Koşum Başlat</h2>
            <p className="mt-0.5 text-[11px] text-fg-subtle">{cycle.name} cycle'ı için test koşumu oluştur</p>
          </div>
          <button type="button" onClick={onClose}
            className="rounded-lg p-1.5 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Run name + environment */}
        <div className="px-5 pt-4 pb-2 space-y-3">
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">Koşum Adı *</label>
            <input
              autoFocus
              value={name}
              onChange={e => setName(e.target.value)}
              maxLength={200}
              className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-fg-muted">Ortam (Opsiyonel)</label>
            <input
              value={environment}
              onChange={e => setEnvironment(e.target.value)}
              maxLength={100}
              placeholder="prod / staging / dev"
              className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
            />
          </div>
        </div>

        {/* Search + header */}
        <div className="flex items-center justify-between px-5 pb-2">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
            Senaryolar ({selected.size} seçili / {cases.filter(c => !c.archived).length} toplam)
          </span>
          <div className="flex items-center gap-3">
            <button type="button"
              onClick={() => setSelected(new Set(filtered.map(c => c.id)))}
              className="text-[11px] text-brand hover:underline">
              Tümünü Seç
            </button>
            <button type="button"
              onClick={() => setSelected(new Set())}
              className="text-[11px] text-fg-subtle hover:text-fg-muted">
              Hiçbiri
            </button>
          </div>
        </div>

        {/* Search input */}
        <div className="mx-5 mb-2 flex items-center gap-2 rounded-xl border border-border bg-surface-raised px-2.5 py-1.5">
          <svg className="h-3.5 w-3.5 shrink-0 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Senaryo ara…"
            className="flex-1 bg-transparent text-[12px] text-fg placeholder:text-fg-subtle outline-none"
          />
        </div>

        {/* Case list */}
        <div className="flex-1 overflow-y-auto border-y border-border">
          {filtered.length === 0 ? (
            <p className="py-8 text-center text-[13px] text-fg-subtle">Senaryo bulunamadı</p>
          ) : (
            Array.from(bySuite.entries())
              .filter(([, cs]) => cs.length > 0)
              .map(([suiteId, suiteCases]) => {
                const sName = suites.find(s => s.id === suiteId)?.name ?? "Atanmamış";
                const allSel = suiteCases.every(c => selected.has(c.id));
                const someSel = !allSel && suiteCases.some(c => selected.has(c.id));
                return (
                  <div key={suiteId}>
                    <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-border bg-surface-overlay px-4 py-1.5">
                      <label className="flex cursor-pointer items-center gap-2 select-none">
                        <span className={cn(
                          "flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors",
                          allSel ? "border-brand bg-brand" : someSel ? "border-brand bg-brand/30" : "border-border"
                        )}>
                          <input type="checkbox" className="sr-only" checked={allSel}
                            onChange={e => {
                              if (e.target.checked)
                                setSelected(p => new Set([...p, ...suiteCases.map(c => c.id)]));
                              else
                                setSelected(p => { const n = new Set(p); suiteCases.forEach(c => n.delete(c.id)); return n; });
                            }}
                          />
                          {allSel && <svg className="h-2.5 w-2.5 text-brand-fg" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5"/></svg>}
                          {someSel && !allSel && <svg className="h-2 w-2 text-brand" fill="currentColor" viewBox="0 0 10 10"><rect x="1.5" y="4" width="7" height="2" rx="1"/></svg>}
                        </span>
                        <span className="text-[11px] font-semibold text-fg-muted">{sName}</span>
                      </label>
                      <span className="text-[10px] text-fg-subtle">{suiteCases.length} senaryo</span>
                    </div>
                    {suiteCases.map(c => {
                      const on = selected.has(c.id);
                      return (
                        <button key={c.id} type="button" onClick={() => toggle(c.id)}
                          className={cn(
                            "flex w-full items-center gap-3 border-b border-border px-5 py-2 text-left transition-colors",
                            on ? "bg-brand/5" : "hover:bg-surface-overlay"
                          )}>
                          <span className={cn("flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                            on ? "border-brand bg-brand" : "border-border")}>
                            {on && <svg className="h-2.5 w-2.5 text-brand-fg" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5"/></svg>}
                          </span>
                          <span className="font-mono text-[10px] text-fg-subtle">{c.case_key}</span>
                          <span className="flex-1 truncate text-[12px] text-fg-muted">{c.title}</span>
                          <span className={cn("shrink-0 text-[10px] font-medium",
                            c.priority === "P0" ? "text-red-400" : c.priority === "P1" ? "text-orange-400" : "text-fg-subtle")}>
                            {c.priority}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                );
              })
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-4">
          <p className="text-[11px] text-fg-subtle">
            {selected.size === 0 ? (
              <span className="text-amber-400">En az 1 senaryo seçin</span>
            ) : (
              <span className="text-emerald-400">{selected.size} senaryo dahil edilecek</span>
            )}
          </p>
          <div className="flex items-center gap-2">
            <button type="button" onClick={onClose}
              className="rounded-xl border border-border px-4 py-2 text-[13px] text-fg-muted hover:text-fg transition-colors">
              İptal
            </button>
            <button type="button"
              disabled={busy || !name.trim() || selected.size === 0}
              onClick={() => onConfirm(name.trim(), [...selected], environment.trim())}
              className="rounded-xl bg-brand px-5 py-2 text-[13px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-40 transition-colors">
              {busy ? "Oluşturuluyor…" : "Koşumu Başlat"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Pencil / Trash inline icons ───────────────────────────────────────────────
function IcPencil({ className }: { className?: string }) {
  return (
    <svg className={cn("h-3 w-3", className)} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
    </svg>
  );
}

// ── Run row (with inline rename + delete confirm) ─────────────────────────────
function RunRow({
  run, projectId, onUpdate, onDelete, onComplete,
}: {
  run: TestRun;
  projectId: string;
  onUpdate: (id: string, name: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onComplete?: (id: string) => void;
}) {
  const [renaming,   setRenaming]   = useState(false);
  const [renameVal,  setRenameVal]  = useState(run.name);
  const [saving,     setSaving]     = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const [deleting,   setDeleting]   = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const commitRename = async () => {
    const trimmed = renameVal.trim();
    if (!trimmed || trimmed === run.name) { setRenaming(false); setRenameVal(run.name); return; }
    setSaving(true);
    try {
      await onUpdate(run.id, trimmed);
    } finally {
      setSaving(false);
      setRenaming(false);
    }
  };

  const confirmDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(run.id);
    } finally {
      setDeleting(false);
      setConfirmDel(false);
    }
  };

  return (
    <div className="group flex items-center gap-2 border-b border-border/30 px-6 py-1.5 last:border-0 hover:bg-white/[0.015] transition-colors">
      {/* Run link / inline input */}
      {renaming ? (
        <form
          className="flex flex-1 items-center gap-1.5"
          onSubmit={async e => { e.preventDefault(); await commitRename(); }}
        >
          <input
            ref={inputRef}
            autoFocus
            value={renameVal}
            onChange={e => setRenameVal(e.target.value)}
            onBlur={commitRename}
            onKeyDown={e => { if (e.key === "Escape") { setRenaming(false); setRenameVal(run.name); } }}
            className="min-w-[140px] flex-1 rounded-md border border-brand bg-surface-overlay px-2 py-0.5 text-[12px] text-fg outline-none ring-1 ring-brand/20"
          />
          <button type="submit" disabled={saving || !renameVal.trim()}
            className="rounded px-1.5 py-0.5 text-[10px] font-semibold text-brand disabled:opacity-40">
            {saving ? "…" : "✓"}
          </button>
          <button type="button" onClick={() => { setRenaming(false); setRenameVal(run.name); }}
            className="rounded px-1 py-0.5 text-[10px] text-fg-subtle hover:text-fg">✕</button>
        </form>
      ) : (
        <Link
          href={`/p/${projectId}/management/runs/${run.id}/execute`}
          className={cn(
            "flex flex-1 items-center gap-1.5 text-[11px] transition-colors hover:text-fg min-w-0 truncate",
            run.status === "in_progress" ? "text-blue-400" :
            run.status === "completed"   ? "text-emerald-400" : "text-fg-muted",
          )}
          title={run.name}
        >
          <IcPlay />
          <span className="truncate">{run.name}</span>
          <span className={cn("shrink-0 rounded-full border px-1.5 py-px text-[9px]",
            run.status === "in_progress" ? "border-blue-500/20 text-blue-400" :
            run.status === "completed"   ? "border-emerald-500/20 text-emerald-400" :
                                           "border-border text-fg-muted",
          )}>
            {run.status === "in_progress" ? "Devam" : run.status === "completed" ? "Tamam" : "Run"}
          </span>
        </Link>
      )}

      {/* Action buttons — only visible on hover */}
      {!renaming && !confirmDel && (
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          {run.status !== "completed" && onComplete && (
            <button
              type="button"
              title="Koşumu Tamamla ve Rapora Git"
              onClick={e => { e.stopPropagation(); onComplete(run.id); }}
              className="rounded px-1.5 py-0.5 text-[10px] font-medium text-emerald-400 hover:bg-emerald-500/10 transition-colors"
            >
              ✓
            </button>
          )}
          <button
            type="button"
            title="Yeniden Adlandır"
            onClick={e => { e.stopPropagation(); setRenaming(true); }}
            className="rounded p-1 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors"
          >
            <IcPencil />
          </button>
          <button
            type="button"
            title="Koşumu Sil"
            onClick={e => { e.stopPropagation(); setConfirmDel(true); }}
            className="rounded p-1 text-fg-subtle hover:bg-red-500/10 hover:text-red-400 transition-colors"
          >
            <IcTrash />
          </button>
        </div>
      )}

      {/* Inline delete confirm */}
      {confirmDel && (
        <div className="flex items-center gap-1.5 ml-auto">
          <span className="text-[10px] text-fg-muted">Koşumu sil?</span>
          <button type="button" onClick={confirmDelete} disabled={deleting}
            className="rounded bg-red-600 px-2 py-0.5 text-[10px] text-white hover:bg-red-500 disabled:opacity-40 transition-colors">
            {deleting ? "…" : "Evet"}
          </button>
          <button type="button" onClick={() => setConfirmDel(false)}
            className="rounded border border-border px-2 py-0.5 text-[10px] text-fg-muted hover:text-fg transition-colors">
            Hayır
          </button>
        </div>
      )}
    </div>
  );
}

// ── Cycle / Run row ───────────────────────────────────────────────────────────
function CycleRow({
  cycle, runs, projectId, onStartRun, loading, onUpdateCycle, onUpdateRun, onDeleteRun, onDeleteCycle, onCompleteRun,
}: {
  cycle: TestCycle;
  runs: TestRun[];
  projectId: string;
  onStartRun: (cycle: TestCycle) => void;
  loading: boolean;
  onUpdateCycle: (id: string, name: string) => Promise<void>;
  onUpdateRun: (id: string, name: string) => Promise<void>;
  onDeleteRun: (id: string) => Promise<void>;
  onDeleteCycle: (id: string) => void;
  onCompleteRun?: (id: string) => void;
}) {
  const total   = runs.reduce((n, r) => n + ((r.scope_snapshot as { case_ids?: string[] })?.case_ids?.length ?? 0), 0);
  const running = runs.some(r => r.status === "in_progress");

  // Cycle inline rename state
  const [renamingCycle,  setRenamingCycle]  = useState(false);
  const [cycleRenameVal, setCycleRenameVal] = useState(cycle.name);
  const [cycleSaving,    setCycleSaving]    = useState(false);

  // Cycle delete confirm state
  const [confirmDeleteCycle, setConfirmDeleteCycle] = useState(false);

  const commitCycleRename = async () => {
    const trimmed = cycleRenameVal.trim();
    if (!trimmed || trimmed === cycle.name) { setRenamingCycle(false); setCycleRenameVal(cycle.name); return; }
    setCycleSaving(true);
    try {
      await onUpdateCycle(cycle.id, trimmed);
    } finally {
      setCycleSaving(false);
      setRenamingCycle(false);
    }
  };

  return (
    <div className="border-b border-border/50 last:border-0">
      {/* Cycle header row */}
      <div className="flex items-center gap-3 px-5 py-2.5 hover:bg-white/[0.02] transition-colors">
        {/* Status dot */}
        <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full",
          running                       ? "bg-blue-400 animate-pulse" :
          cycle.status === "completed"  ? "bg-emerald-500" : "bg-slate-600",
        )} />

        {/* Name / inline rename */}
        <div className="flex-1 min-w-0">
          {renamingCycle ? (
            <form
              className="flex items-center gap-1.5"
              onSubmit={async e => { e.preventDefault(); await commitCycleRename(); }}
            >
              <input
                autoFocus
                value={cycleRenameVal}
                onChange={e => setCycleRenameVal(e.target.value)}
                onBlur={commitCycleRename}
                onKeyDown={e => { if (e.key === "Escape") { setRenamingCycle(false); setCycleRenameVal(cycle.name); } }}
                className="min-w-[160px] rounded-md border border-brand bg-surface-overlay px-2 py-0.5 text-[13px] font-medium text-fg outline-none ring-1 ring-brand/20"
              />
              <button type="submit" disabled={cycleSaving || !cycleRenameVal.trim()}
                className="rounded px-1.5 py-0.5 text-[11px] font-semibold text-brand disabled:opacity-40">
                {cycleSaving ? "…" : "✓"}
              </button>
              <button type="button" onClick={() => { setRenamingCycle(false); setCycleRenameVal(cycle.name); }}
                className="rounded px-1 py-0.5 text-[11px] text-fg-subtle hover:text-fg">✕</button>
            </form>
          ) : (
            <p className="truncate text-[13px] text-fg">{cycle.name}</p>
          )}
          <p className="text-[11px] text-fg-subtle">
            {cycle.environment ? `${cycle.environment} · ` : ""}{cycle.build_version ?? ""}{total > 0 ? ` · ${total} case` : ""}
          </p>
        </div>

        {/* Status pill */}
        <span className={cn("rounded-full border px-2 py-0.5 text-[10px] shrink-0",
          cycle.status === "completed" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400" :
          cycle.status === "active"    ? "border-blue-500/20    bg-blue-500/10    text-blue-400"    :
                                         "border-border         bg-surface-overlay text-fg-muted",
        )}>
          {cycle.status}
        </span>

        {/* Cycle rename button */}
        {!renamingCycle && (
          <button
            type="button"
            title="Cycle Adını Değiştir"
            onClick={() => setRenamingCycle(true)}
            className="shrink-0 rounded-md p-1.5 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors"
          >
            <IcPencil />
          </button>
        )}

        {/* Cycle delete button */}
        {!renamingCycle && (
          <button
            type="button"
            title="Döngüyü Sil"
            onClick={() => setConfirmDeleteCycle(true)}
            className="shrink-0 rounded-md p-1.5 text-fg-subtle hover:bg-red-500/10 hover:text-red-400 transition-colors"
          >
            <IcTrash />
          </button>
        )}

        {/* Start run */}
        <button
          onClick={() => onStartRun(cycle)}
          disabled={loading}
          title="Run Başlat"
          className="shrink-0 flex items-center gap-1.5 rounded-lg border border-teal-500/25 px-3 py-1.5 text-[11px] font-medium text-teal-400 hover:bg-teal-500/10 hover:border-teal-500/40 disabled:opacity-40 transition-colors"
        >
          <IcPlay /> Run
        </button>
      </div>

      {/* Cycle delete confirm modal */}
      {confirmDeleteCycle && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-surface-raised rounded-xl border border-border p-6 max-w-sm w-full">
            <h3 className="text-sm font-semibold text-fg mb-2">Döngüyü Sil</h3>
            <p className="text-xs text-fg-subtle mb-4">
              Bu döngü altındaki tüm koşumlar da silinecek. Bu işlem geri alınamaz.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmDeleteCycle(false)}
                className="px-3 py-1.5 rounded-lg border border-border text-xs text-fg-muted hover:text-fg transition-colors"
              >
                İptal
              </button>
              <button
                onClick={() => { onDeleteCycle(cycle.id); setConfirmDeleteCycle(false); }}
                className="px-3 py-1.5 rounded-lg bg-red-500 text-white text-xs hover:bg-red-400 transition-colors"
              >
                Sil
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Run rows */}
      {runs.length > 0 && (
        <div className="bg-white/[0.01]">
          {runs.map(run => (
            <RunRow
              key={run.id}
              run={run}
              projectId={projectId}
              onUpdate={onUpdateRun}
              onDelete={onDeleteRun}
              onComplete={onCompleteRun}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Delete confirm modal ──────────────────────────────────────────────────────
function DeletePlanModal({ plan, onConfirm, onClose, loading, impactLoading, impactData }: {
  plan: TestPlan;
  onConfirm: () => void;
  onClose: () => void;
  loading: boolean;
  impactLoading: boolean;
  impactData?: { cycle_count: number; run_count: number; run_case_count: number; evidence_count: number };
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-sm rounded-xl border border-border bg-surface-raised p-6 shadow-2xl">
        <h2 className="text-[14px] font-semibold text-fg">Planı Sil</h2>
        <p className="mt-2 text-[13px] text-fg-muted">
          <span className="text-fg font-medium">{plan.name}</span> planını silmek istediğinizden emin misiniz?
          Bu işlem geri alınamaz.
        </p>
        {impactLoading && <p className="mt-3 text-xs text-fg-subtle">Etki hesaplanıyor...</p>}
        {impactData && (
          <div className="mt-3 rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-xs text-red-300 space-y-1">
            <p className="font-medium">Bu işlem geri alınamaz. Silinecekler:</p>
            <ul className="list-disc pl-4 space-y-0.5">
              <li>{impactData.cycle_count} döngü</li>
              <li>{impactData.run_count} koşum</li>
              <li>{impactData.run_case_count} koşum adımı</li>
              {impactData.evidence_count > 0 && <li>{impactData.evidence_count} kanıt dosyası</li>}
            </ul>
          </div>
        )}
        <div className="mt-5 flex gap-2">
          <button onClick={onConfirm} disabled={loading}
            className="flex-1 rounded-lg bg-red-600 py-2 text-[13px] font-medium text-white hover:bg-red-500 disabled:opacity-40 transition-colors">
            {loading ? "Siliniyor…" : "Sil"}
          </button>
          <button onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-[13px] text-fg-muted hover:text-fg transition-colors">
            İptal
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Plan row ──────────────────────────────────────────────────────────────────
function PlanRow({
  plan, cycles, runs, projectId, onStartRun, runCreating,
  onAddCycle, onDelete, onRenamePlan, onUpdateCycle, onUpdateRun, onDeleteRun, onDeleteCycle, onCompleteRun,
}: {
  plan: TestPlan;
  cycles: TestCycle[];
  runs: TestRun[];
  projectId: string;
  onStartRun: (cycle: TestCycle) => void;
  runCreating: boolean;
  onAddCycle: (planId: string) => void;
  onDelete: (plan: TestPlan) => void;
  onRenamePlan: (plan: TestPlan, newName: string) => Promise<void>;
  onUpdateCycle: (id: string, name: string) => Promise<void>;
  onUpdateRun: (id: string, name: string) => Promise<void>;
  onDeleteRun: (id: string) => Promise<void>;
  onDeleteCycle: (id: string) => void;
  onCompleteRun?: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [renameVal, setRenameVal] = useState(plan.name);
  const [renameSaving, setRenameSaving] = useState(false);

  // Aggregate run stats for inline progress bar
  const allRunCases = runs.flatMap(r => {
    const snap = r.scope_snapshot as { passed?: number; failed?: number; blocked?: number; not_run?: number; case_ids?: string[] };
    return [snap];
  });
  const passed  = allRunCases.reduce((n, s) => n + (s.passed  ?? 0), 0);
  const failed  = allRunCases.reduce((n, s) => n + (s.failed  ?? 0), 0);
  const blocked = allRunCases.reduce((n, s) => n + (s.blocked ?? 0), 0);
  const notRun  = allRunCases.reduce((n, s) => n + (s.not_run ?? 0), 0);

  const typeCls = PLAN_TYPE_BADGE[plan.plan_type] ?? PLAN_TYPE_BADGE.regression;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface-raised">
      {/* Header row */}
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.025] transition-colors"
      >
        <IcChevron open={open} />

        <div className="flex flex-1 min-w-0 items-center gap-3 flex-wrap">
          {renaming ? (
            <form onSubmit={async e => { e.preventDefault(); setRenameSaving(true); await onRenamePlan(plan, renameVal); setRenaming(false); setRenameSaving(false); }}
              onClick={e => e.stopPropagation()} className="flex items-center gap-1.5">
              <input autoFocus value={renameVal} onChange={e => setRenameVal(e.target.value)}
                onKeyDown={e => { if (e.key === "Escape") { setRenaming(false); setRenameVal(plan.name); } }}
                className="rounded-lg border border-brand bg-surface-overlay px-2 py-0.5 text-[13px] font-semibold text-fg outline-none ring-2 ring-brand/20 min-w-[180px]" />
              <button type="submit" disabled={renameSaving || !renameVal.trim()}
                className="rounded-md bg-brand px-2 py-0.5 text-[11px] font-semibold text-brand-fg disabled:opacity-40">
                {renameSaving ? "…" : "Kaydet"}
              </button>
              <button type="button" onClick={() => { setRenaming(false); setRenameVal(plan.name); }}
                className="text-[11px] text-fg-subtle hover:text-fg">İptal</button>
            </form>
          ) : (
            <p className="text-[13px] font-semibold text-fg truncate">{plan.name}</p>
          )}
          <span className={cn("shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium", typeCls)}>
            {plan.plan_type}
          </span>
          {plan.release_name && (
            <span className="shrink-0 rounded bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-muted">{plan.release_name}</span>
          )}
          {plan.scope_summary && (
            <span className="hidden lg:block truncate text-[11px] text-fg-subtle max-w-xs">{plan.scope_summary}</span>
          )}
        </div>

        {/* Inline progress */}
        <div className="hidden md:block">
          <RunProgress passed={passed} failed={failed} blocked={blocked} notRun={notRun} />
        </div>

        {/* Meta */}
        <span className="hidden md:inline shrink-0 text-[11px] text-fg-subtle">{fmtDate(plan.created_at)}</span>
        <span className="hidden sm:inline shrink-0 text-[11px] text-fg-subtle">{cycles.length} cycle</span>
        <button
          type="button"
          onClick={e => { e.stopPropagation(); setRenaming(v => !v); setRenameVal(plan.name); }}
          className="shrink-0 rounded-md p-1.5 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors"
          title="Planı Yeniden Adlandır"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
          </svg>
        </button>
        <button
          type="button"
          onClick={e => { e.stopPropagation(); onDelete(plan); }}
          className="shrink-0 rounded-md p-1.5 text-fg-subtle hover:bg-red-500/10 hover:text-red-400 transition-colors"
          title="Planı Sil"
        >
          <IcTrash />
        </button>
      </button>

      {/* Expanded cycles */}
      {open && (
        <div className="border-t border-border">
          {cycles.length === 0 ? (
            <div className="flex items-center justify-between px-6 py-4">
              <p className="text-[11px] text-fg-subtle">Bu plana ait cycle yok.</p>
              <button
                disabled
                title="Önce cycle oluşturun"
                className="flex items-center gap-1.5 rounded-lg border border-teal-500/25 px-3 py-1.5 text-[11px] font-medium text-teal-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <IcPlay /> Run Başlat
              </button>
            </div>
          ) : (
            cycles.map(cycle => {
              const cycleRuns = runs.filter(r => r.cycle_id === cycle.id);
              return (
                <CycleRow
                  key={cycle.id}
                  cycle={cycle}
                  runs={cycleRuns}
                  projectId={projectId}
                  onStartRun={onStartRun}
                  loading={runCreating}
                  onUpdateCycle={onUpdateCycle}
                  onUpdateRun={onUpdateRun}
                  onDeleteRun={onDeleteRun}
                  onDeleteCycle={onDeleteCycle}
                  onCompleteRun={onCompleteRun}
                />
              );
            })
          )}
          <div className="border-t border-border/50 px-5 py-2">
            <button
              type="button"
              onClick={() => onAddCycle(plan.id)}
              className="flex items-center gap-1.5 text-[12px] text-fg-subtle hover:text-fg transition-colors py-1"
            >
              <IcPlus /> Yeni Cycle
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function ManagementPlansPage() {
  const router    = useRouter();
  const projectId = useRouteParam("projectId");
  const mpid      = useManagementProjectId(projectId || undefined);
  const toast     = useToast();

  const { data: plans, isLoading, isError: plansError, refetch: refetchPlans } = useManagementPlans(mpid || undefined);
  const { data: allCycles }        = useManagementCycles(mpid || undefined);
  const { data: allRuns }          = useManagementRuns(mpid || undefined);
  const createPlan   = useCreateManagementPlan(mpid || "");
  const updatePlan   = useUpdateManagementPlan(mpid || "");
  const deletePlan   = useDeleteManagementPlan(mpid || "");
  const createRun    = useCreateManagementRun(mpid || "");
  const updateRun    = useUpdateManagementRun(mpid || "");
  const deleteRun    = useDeleteManagementRun(mpid || "");
  const createCycle  = useCreateManagementCycle(mpid || "");
  const updateCycle  = useUpdateManagementCycle(mpid || "");
  const deleteCycle  = useDeleteManagementCycle(mpid || "");
  const aiGenPlan    = useAIGeneratePlan(mpid || "");
  const repoQ        = useManagementRepository(mpid || undefined);
  const suites       = repoQ.data?.suites ?? [];

  const [showPlanForm,     setShowPlanForm]     = useState(false);
  const [planName,         setPlanName]         = useState("");
  const [planType,         setPlanType]         = useState<PlanType>("regression");
  const [planRelease,      setPlanRelease]       = useState("");
  const [planScope,        setPlanScope]         = useState("");
  const [selectedSuiteIds, setSelectedSuiteIds] = useState<string[]>([]);

  const [addCycleForPlan, setAddCycleForPlan] = useState<string | null>(null);
  const [cycleName,       setCycleName]       = useState("");
  const [cycleEnv,        setCycleEnv]        = useState("");
  const [cycleBuild,      setCycleBuild]      = useState("");

  const [activeCycleId,   setActiveCycleId]   = useState("");
  const [deletingPlan,    setDeletingPlan]     = useState<TestPlan | null>(null);
  const [deleteLoading,   setDeleteLoading]    = useState(false);
  const impactQ = usePlanImpactSummary(mpid ?? undefined, deletingPlan?.id ?? undefined);
  const [creating,        setCreating]         = useState(false);
  const [runCycleForModal, setRunCycleForModal] = useState<TestCycle | null>(null);
  const [runCreatingFlag, setRunCreatingFlag]  = useState(false);
  const [cycleCreating,   setCycleCreating]    = useState(false);
  const [error,           setError]            = useState<string | null>(null);

  const handleRenamePlan = async (plan: TestPlan, newName: string) => {
    if (!newName.trim() || newName === plan.name) return;
    try {
      await updatePlan.mutateAsync({ id: plan.id, name: newName.trim() });
    } catch (err: unknown) {
      console.error("[Plans] Rename failed:", err);
      toast.error("Plan adı değiştirilemedi");
    }
  };

  const handleUpdateCycle = async (id: string, name: string) => {
    try {
      await updateCycle.mutateAsync({ id, name: name.trim() });
      toast.success("Cycle yeniden adlandırıldı");
    } catch {
      toast.error("Cycle adı değiştirilemedi");
    }
  };

  const handleUpdateRun = async (id: string, name: string) => {
    try {
      await updateRun.mutateAsync({ id, name: name.trim() });
      toast.success("Koşum yeniden adlandırıldı");
    } catch {
      toast.error("Koşum adı değiştirilemedi");
    }
  };

  const handleDeleteRun = async (id: string) => {
    try {
      await deleteRun.mutateAsync(id);
      toast.success("Koşum silindi");
    } catch {
      toast.error("Koşum silinemedi");
    }
  };

  const handleDeleteCycle = async (id: string) => {
    try {
      await deleteCycle.mutateAsync(id);
      toast.success("Döngü silindi");
    } catch {
      toast.error("Döngü silinemedi");
    }
  };

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!planName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const suiteScope = selectedSuiteIds.length > 0
        ? "Kapsam: " + selectedSuiteIds.map(id => suites.find(s => s.id === id)?.name ?? id).join(", ")
        : (planScope.trim() || null);
      await createPlan.mutateAsync({
        name: planName.trim(),
        plan_type: planType,
        release_name: planRelease.trim() || null,
        scope_summary: suiteScope,
      });
      setPlanName(""); setPlanRelease(""); setPlanScope(""); setSelectedSuiteIds([]); setShowPlanForm(false);
      toast.success("Plan oluşturuldu");
    } catch {
      setError("Plan oluşturulamadı.");
      toast.error("Plan oluşturulamadı");
    } finally {
      setCreating(false);
    }
  };

  const handleStartRun = async (cycle: TestCycle, caseIds: string[], runName?: string, environment?: string) => {
    setActiveCycleId(cycle.id);
    setRunCreatingFlag(true);
    setError(null);
    try {
      const run = await createRun.mutateAsync({
        cycle_id: cycle.id,
        name: runName?.trim() || `Koşum — ${cycle.name}`,
        case_ids: caseIds,
        environment: environment?.trim() || cycle.environment || null,
      });
      setRunCycleForModal(null);
      setActiveCycleId("");
      router.push(`/p/${projectId}/management/runs/${run.id}/execute`);
    } catch {
      setError("Koşum başlatılamadı.");
      setActiveCycleId("");
    } finally {
      setRunCreatingFlag(false);
    }
  };

  const handleCompleteRun = (runId: string) => {
    updateRun.mutate(
      { id: runId, status: "completed" },
      {
        onSuccess: () => {
          router.push(`/p/${projectId}/management/reports`);
        },
      },
    );
  };

  const handleCreateCycle = async (planId: string) => {
    if (!cycleName.trim() || !mpid) return;
    setCycleCreating(true);
    setError(null);
    try {
      await createCycle.mutateAsync({
        plan_id: planId,
        name: cycleName.trim(),
        environment: cycleEnv.trim() || null,
        build_version: cycleBuild.trim() || null,
      });
      setCycleName(""); setCycleEnv(""); setCycleBuild(""); setAddCycleForPlan(null);
    } catch {
      setError("Cycle oluşturulamadı.");
    } finally {
      setCycleCreating(false);
    }
  };

  const handleDeletePlan = async () => {
    if (!deletingPlan || !mpid) return;
    setDeleteLoading(true);
    setError(null);
    try {
      await deletePlan.mutateAsync(deletingPlan.id);
      setDeletingPlan(null);
    } catch {
      setError("Plan silinemedi.");
    } finally {
      setDeleteLoading(false);
    }
  };

  const cyclesFor = (planId: string) => (allCycles ?? []).filter((c: TestCycle) => c.plan_id === planId);
  const runsFor   = (cycles: TestCycle[]) => {
    const cids = new Set(cycles.map(c => c.id));
    return (allRuns ?? []).filter((r: TestRun) => cids.has(r.cycle_id));
  };

  return (
    <PageErrorBoundary>
    <div className="min-h-[calc(100vh-88px)] bg-bg text-fg">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-border bg-surface-raised px-6 py-4">
        <div>
          <h1 className="text-[13px] font-semibold text-fg">Test Planları</h1>
          <p className="mt-0.5 hidden text-[11px] text-fg-muted sm:block">
            {(plans ?? []).length} plan · {(allCycles ?? []).length} cycle · {(allRuns ?? []).length} run
          </p>
        </div>
        {/* ── Stats chips ── */}
        <div className="hidden sm:flex items-center gap-2 flex-1 justify-center">
          {[
            { label: "Toplam",    value: (plans ?? []).length,                                                         color: "text-fg-muted  border-slate-700" },
            { label: "Aktif",     value: (plans ?? []).filter((p: TestPlan) => p.status === "active").length,          color: "text-blue-400   border-blue-500/20 bg-blue-500/10" },
            { label: "Tamamlandı",value: (plans ?? []).filter((p: TestPlan) => p.status === "completed").length,       color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/10" },
          ].map(stat => (
            <div key={stat.label} className={cn("flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px]", stat.color)}>
              <span className="font-semibold tabular-nums">{stat.value}</span>
              <span className="text-current opacity-70">{stat.label}</span>
            </div>
          ))}
        </div>
        <RoleGuard minRole="member" projectId={projectId ?? undefined}>
          <button
            onClick={() => setShowPlanForm(v => !v)}
            className="flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-[12px] font-medium text-brand-fg hover:brightness-105 transition-colors"
          >
            <IcPlus /> {showPlanForm ? "İptal" : "Yeni Plan"}
          </button>
        </RoleGuard>
      </div>

      {/* ── Error banner ──────────────────────────────────────────────────── */}
      {error && (
        <div className="flex items-center justify-between border-b border-red-500/20 bg-red-500/10 px-6 py-2.5">
          <p className="text-[12px] text-red-400">{error}</p>
          <button onClick={() => setError(null)} className="text-[11px] text-red-400/60 hover:text-red-400 transition-colors">Kapat</button>
        </div>
      )}

      {/* ── Create plan form ───────────────────────────────────────────────── */}
      {showPlanForm && (
        <div className="border-b border-border bg-surface-raised px-6 py-4">
          <form onSubmit={handleCreatePlan} className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-40">
              <label className="mb-1 block text-[11px] text-fg-muted">Plan Adı *</label>
              <input
                autoFocus
                value={planName}
                onChange={e => setPlanName(e.target.value)}
                placeholder="örn. Q3 Release Plan"
                required
                maxLength={200}
                className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder-slate-600 outline-none focus:border-teal-500/50"
              />
            </div>
            <div className="w-36">
              <label className="mb-1 block text-[11px] text-fg-muted">Tip</label>
              <select
                value={planType}
                onChange={e => setPlanType(e.target.value as PlanType)}
                className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/50"
              >
                {(["release","regression","sprint","smoke","uat"] as PlanType[]).map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="w-36">
              <label className="mb-1 block text-[11px] text-fg-muted">Release adı</label>
              <input
                value={planRelease}
                onChange={e => setPlanRelease(e.target.value)}
                placeholder="v2.4.0"
                maxLength={100}
                className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder-slate-600 outline-none focus:border-teal-500/50"
              />
            </div>
            {suites.length > 0 && (
              <div className="w-full">
                <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">
                  Kapsam — Suite Seçin <span className="normal-case text-fg-subtle font-normal">(opsiyonel)</span>
                </label>
                <div className="space-y-1.5 rounded-xl border border-border bg-surface-base p-3 max-h-40 overflow-y-auto">
                  {suites.map(s => {
                    const caseCount = (repoQ.data?.cases ?? []).filter(c => c.suite_id === s.id && !c.archived).length;
                    return (
                      <label key={s.id} className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-surface-overlay">
                        <input type="checkbox" className="h-3.5 w-3.5 accent-brand rounded"
                          checked={selectedSuiteIds.includes(s.id)}
                          onChange={e => setSelectedSuiteIds(p => e.target.checked ? [...p, s.id] : p.filter(x => x !== s.id))}
                        />
                        <span className="flex-1 text-[12px] text-fg">{s.name}</span>
                        <span className="text-[10px] text-fg-subtle">{caseCount} case</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            )}
            <div className="w-full flex gap-2">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] text-fg-muted">Kapsam Özeti</label>
                <textarea
                  value={planScope}
                  onChange={e => setPlanScope(e.target.value)}
                  placeholder="Bu planın kapsamı ve hedefleri hakkında kısa bir açıklama…"
                  rows={2}
                  maxLength={1000}
                  className="w-full resize-none rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder-slate-600 outline-none focus:border-teal-500/50"
                />
              </div>
              <div className="flex flex-col justify-end">
                <button type="button"
                  disabled={isLoading || aiGenPlan.isPending || !planRelease.trim()}
                  title={!planRelease.trim() ? "AI önerisi için önce Release adı girin" : "AI ile plan özeti oluştur"}
                  onClick={async () => {
                    const res = await aiGenPlan.mutateAsync({ release_name: planRelease.trim(), plan_type: planType });
                    if (!planName) setPlanName(res.name);
                    setPlanScope(res.scope_summary);
                  }}
                  className="flex items-center gap-1.5 rounded-lg border border-teal-500/30 bg-teal-500/10 px-3 py-2 text-[11px] font-medium text-teal-400 hover:bg-brand-soft disabled:opacity-40 transition-colors whitespace-nowrap">
                  {aiGenPlan.isPending ? "AI üretiyor…" : "✦ AI Öner"}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={creating || createPlan.isPending || !planName.trim()}
              className="rounded-lg bg-brand px-4 py-2 text-[12px] font-medium text-brand-fg hover:brightness-105 disabled:opacity-40 transition-colors"
            >
              {creating || createPlan.isPending ? "Oluşturuluyor…" : "Oluştur"}
            </button>
          </form>
        </div>
      )}

      {/* ── Plan list ──────────────────────────────────────────────────────── */}
      <div className="p-6 space-y-3">
        {plansError ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-[13px] text-red-400">Planlar yüklenemedi.</p>
            <button onClick={() => void refetchPlans()} className="text-[12px] text-brand hover:underline">
              Tekrar dene
            </button>
          </div>
        ) : isLoading ? (
          <div className="space-y-2">
            {[1,2,3].map(i => (
              <div key={i} className="h-14 animate-pulse rounded-xl bg-surface-raised" />
            ))}
          </div>
        ) : (plans ?? []).length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-surface-overlay">
              <svg className="h-7 w-7 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
              </svg>
            </div>
            <div>
              <p className="text-[14px] font-semibold text-fg">Henüz plan oluşturulmadı</p>
              <p className="mt-1 text-[12px] text-fg-subtle max-w-xs">Test planları; release&apos;leri, döngüleri ve koşumları organize eder.</p>
            </div>
            <button
              onClick={() => setShowPlanForm(true)}
              className="flex items-center gap-2 rounded-xl bg-brand px-4 py-2 text-[13px] font-semibold text-brand-fg shadow-sm hover:brightness-105 transition-all"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>
              Yeni plan oluştur
            </button>
          </div>
        ) : (
          (plans ?? []).map((plan: TestPlan) => {
            const cycles = cyclesFor(plan.id);
            const runs   = runsFor(cycles);
            return (
              <PlanRow
                key={plan.id}
                plan={plan}
                cycles={cycles}
                runs={runs}
                projectId={projectId ?? ""}
                onStartRun={setRunCycleForModal}
                runCreating={(createRun.isPending || runCreatingFlag) && activeCycleId !== ""}
                onAddCycle={id => { setAddCycleForPlan(id); }}
                onDelete={setDeletingPlan}
                onRenamePlan={handleRenamePlan}
                onUpdateCycle={handleUpdateCycle}
                onUpdateRun={handleUpdateRun}
                onDeleteRun={handleDeleteRun}
                onDeleteCycle={handleDeleteCycle}
                onCompleteRun={handleCompleteRun}
              />
            );
          })
        )}
      </div>

      {/* ── Plan Run Modal — case seçimi ──────────────────────────────────── */}
      {runCycleForModal && (
        <PlanStartRunModal
          cycle={runCycleForModal}
          cases={repoQ.data?.cases ?? []}
          suites={repoQ.data?.suites ?? []}
          onClose={() => setRunCycleForModal(null)}
          onConfirm={(runName, caseIds, environment) => void handleStartRun(runCycleForModal, caseIds, runName, environment)}
          busy={createRun.isPending || runCreatingFlag}
        />
      )}

      {/* ── Delete plan modal ─────────────────────────────────────────────── */}
      {deletingPlan && (
        <DeletePlanModal
          plan={deletingPlan}
          onConfirm={handleDeletePlan}
          onClose={() => setDeletingPlan(null)}
          loading={deleteLoading}
          impactLoading={impactQ.isLoading}
          impactData={impactQ.data}
        />
      )}

      {/* ── Add cycle modal (inline) ───────────────────────────────────────── */}
      {addCycleForPlan && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-6 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-border bg-surface-raised p-6 shadow-2xl">
            <h2 className="mb-4 text-[14px] font-semibold text-fg">Yeni Cycle</h2>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-[11px] text-fg-muted">Cycle Adı *</label>
                <input
                  autoFocus
                  value={cycleName}
                  onChange={e => setCycleName(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === "Enter") void handleCreateCycle(addCycleForPlan);
                    if (e.key === "Escape") { setAddCycleForPlan(null); setCycleName(""); }
                  }}
                  placeholder="örn. Sprint 5 Regression"
                  maxLength={200}
                  className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder-slate-600 outline-none focus:border-teal-500/50"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-[11px] text-fg-muted">Ortam</label>
                  <input value={cycleEnv} onChange={e => setCycleEnv(e.target.value)}
                    placeholder="prod / staging" maxLength={100} className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg placeholder-slate-600 outline-none focus:border-teal-500/50"/>
                </div>
                <div>
                  <label className="mb-1 block text-[11px] text-fg-muted">Build</label>
                  <input value={cycleBuild} onChange={e => setCycleBuild(e.target.value)}
                    placeholder="v2.1.0" maxLength={100} className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[12px] text-fg placeholder-slate-600 outline-none focus:border-teal-500/50"/>
                </div>
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => void handleCreateCycle(addCycleForPlan)}
                  disabled={!cycleName.trim() || cycleCreating || createCycle.isPending}
                  className="flex-1 rounded-lg bg-brand py-2 text-[13px] font-medium text-brand-fg hover:brightness-105 disabled:opacity-40 transition-colors"
                >
                  {cycleCreating || createCycle.isPending ? "Oluşturuluyor…" : "Cycle Oluştur"}
                </button>
                <button
                  onClick={() => { setAddCycleForPlan(null); setCycleName(""); setCycleEnv(""); setCycleBuild(""); }}
                  className="rounded-lg border border-border px-4 py-2 text-[13px] text-fg-muted hover:text-fg transition-colors"
                >
                  İptal
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
    </PageErrorBoundary>
  );
}
