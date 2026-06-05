"use client";

import React, { useMemo, useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  useManagementCycles,
  useManagementPlans,
  useManagementRepository,
  useCreateManagementPlan,
  useCreateManagementCycle,
  useCreateManagementRun,
  type TestCase,
  type TestCycle,
  type TestSuite,
} from "@/lib/hooks/use-management";
import { P_DOT, IcClose, IcSearch } from "./shared";

export function NewRunModal({ pid, cases: casesProp, suites: suitesProp, initialCaseIds, onClose, onDone }: {
  pid: string;
  cases?: TestCase[];
  suites?: TestSuite[];
  initialCaseIds: string[];
  onClose: () => void;
  onDone: (runId: string) => void;
}) {
  const { data: cycles } = useManagementCycles(pid || undefined);
  const { data: plans } = useManagementPlans(pid || undefined);
  const { data: repo } = useManagementRepository((!casesProp || !suitesProp) ? pid : undefined);
  const createPlan = useCreateManagementPlan(pid);
  const createCycle = useCreateManagementCycle(pid);
  const createRun = useCreateManagementRun(pid);

  const allCases: TestCase[] = casesProp ?? repo?.cases ?? [];
  const suites: TestSuite[] = suitesProp ?? repo?.suites ?? [];

  const [name,        setName]        = useState("");
  const [environment, setEnvironment] = useState("");
  const [cycleId,     setCycleId]     = useState<string>("");
  const [search,      setSearch]      = useState("");
  const [priorityF,   setPriorityF]   = useState("");
  const [lastRunF,    setLastRunF]    = useState("");
  const [selected,    setSelected]    = useState<Set<string>>(() => new Set(initialCaseIds));
  const [err,         setErr]         = useState("");
  const [busy,        setBusy]        = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  // Pre-select cycle when data loads
  useEffect(() => {
    if (cycles && cycles.length > 0 && !cycleId) setCycleId(cycles[0].id);
  }, [cycles, cycleId]);

  useEffect(() => {
    const el = modalRef.current;
    if (!el) return;
    const focusable = el.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusable[0];
    const last  = focusable[focusable.length - 1];
    first?.focus();
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last?.focus(); }
      } else {
        if (document.activeElement === last)  { e.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let r = allCases.filter(c => !c.archived);
    if (q) r = r.filter(c => c.title.toLowerCase().includes(q) || c.case_key.toLowerCase().includes(q));
    if (priorityF) r = r.filter(c => c.priority === priorityF);
    if (lastRunF === "not_run") r = r.filter(c => !c.last_run_status || c.last_run_status === "not_run");
    else if (lastRunF) r = r.filter(c => c.last_run_status === lastRunF);
    return r;
  }, [allCases, search, priorityF, lastRunF]);

  const bySuite = useMemo(() => {
    const map = new Map<string, TestCase[]>();
    for (const s of suites) map.set(s.id, []);
    for (const c of filtered) {
      const key = c.suite_id ?? "__unassigned__";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(c);
    }
    return map;
  }, [filtered, suites]);

  const toggle = (id: string) => setSelected(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });

  async function ensureCycleId(): Promise<string> {
    if (cycleId) return cycleId;
    if (cycles && cycles.length > 0) return cycles[0].id;
    let planId = plans && plans.length > 0 ? plans[0].id : undefined;
    if (!planId) {
      const plan = await createPlan.mutateAsync({ name: "Workspace Runs", plan_type: "regression" });
      planId = plan.id;
    }
    const cycle = await createCycle.mutateAsync({
      plan_id: planId,
      name: "Default Cycle",
      environment: environment.trim() || null,
    });
    return cycle.id;
  }

  const save = async () => {
    if (!name.trim()) { setErr("Run adı zorunlu."); return; }
    if (selected.size === 0) { setErr("En az bir senaryo seçin."); return; }
    setErr("");
    setBusy(true);
    try {
      const cycleId = await ensureCycleId();
      const run = await createRun.mutateAsync({
        cycle_id: cycleId,
        name: name.trim(),
        case_ids: [...selected],
        environment: environment.trim() || null,
      });
      onDone(run.id);
    } catch {
      setErr("Run oluşturulamadı.");
    } finally {
      setBusy(false);
    }
  };

  const inp = "w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";

  return (
    <div className="fixed inset-0 z-modal flex items-start justify-center overflow-y-auto p-8 bg-black/60 backdrop-blur-sm">
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-run-modal-title"
        className="relative flex max-h-[85vh] w-full max-w-xl flex-col rounded-xl border border-border bg-surface-raised shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 id="new-run-modal-title" className="text-[15px] font-semibold text-fg">Yeni Test Run</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg"><IcClose /></button>
        </div>

        <div className="space-y-3 px-6 py-4">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label htmlFor="new-run-name" className="sr-only">Run adı</label>
              <input id="new-run-name" autoFocus value={name} onChange={e => setName(e.target.value)} placeholder="Run adı * (örn. Sprint 24 Smoke)" className={inp} />
            </div>
            <div>
              <label htmlFor="new-run-env" className="sr-only">Ortam</label>
              <input id="new-run-env" value={environment} onChange={e => setEnvironment(e.target.value)} placeholder="Ortam (staging/prod)" className={inp} />
            </div>
          </div>

          {/* Cycle seçimi */}
          {cycles && cycles.length > 0 && (
            <div>
              <label htmlFor="new-run-cycle" className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Test Cycle</label>
              <select id="new-run-cycle" value={cycleId} onChange={e => setCycleId(e.target.value)}
                className="w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15">
                {(cycles as TestCycle[]).map(c => (
                  <option key={c.id} value={c.id}>{c.name}{c.environment ? ` — ${c.environment}` : ""}</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Senaryolar</span>
            <span className="text-[11px] font-medium text-brand">{selected.size} seçili / {filtered.length} görünür</span>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2 flex-1 min-w-0 rounded-xl border border-border bg-surface-raised px-2.5 py-1.5 shadow-xs transition-colors focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/15">
              <IcSearch />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Senaryo ara…"
                className="min-w-0 flex-1 bg-transparent text-[12px] text-fg placeholder:text-fg-subtle outline-none" />
            </div>
            <div className="flex items-center gap-1">
              {["","P0","P1","P2","P3"].map(p => (
                <button key={p} type="button" onClick={() => setPriorityF(p)}
                  className={cn("rounded-lg px-2 py-1 text-[10px] font-medium transition-colors",
                    priorityF === p ? "bg-brand text-brand-fg" : "bg-surface-overlay text-fg-muted hover:text-fg")}>
                  {p || "Hepsi"}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1">
              {[["","Tümü"],["not_run","Koşulmadı"],["failed","Başarısız"],["passed","Geçti"]].map(([v, label]) => (
                <button key={v} type="button" onClick={() => setLastRunF(v)}
                  className={cn("rounded-lg px-2 py-1 text-[10px] font-medium transition-colors",
                    lastRunF === v ? "bg-brand text-brand-fg" : "bg-surface-overlay text-fg-muted hover:text-fg")}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setSelected(new Set(filtered.map(c => c.id)))} className="text-[11px] text-fg-muted hover:text-fg transition-colors">Görünenleri Seç</button>
            <button type="button" onClick={() => setSelected(new Set())} className="text-[11px] text-fg-subtle hover:text-fg-muted transition-colors">Hiçbiri</button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto border-y border-border">
          {filtered.length === 0 ? (
            <p className="px-6 py-8 text-center text-[13px] text-fg-subtle">Senaryo bulunamadı</p>
          ) : (
            Array.from(bySuite.entries())
              .filter(([, cases]) => cases.length > 0)
              .map(([suiteId, suiteCases]) => {
                const suiteName = suites.find(s => s.id === suiteId)?.name ?? "Atanmamış";
                const allSuiteSelected = suiteCases.every(c => selected.has(c.id));
                const someSuiteSelected = !allSuiteSelected && suiteCases.some(c => selected.has(c.id));
                return (
                  <div key={suiteId}>
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-overlay border-b border-border sticky top-0 z-10">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <span className={cn(
                          "flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors",
                          allSuiteSelected ? "border-brand bg-brand" : someSuiteSelected ? "border-brand bg-brand/30" : "border-border"
                        )}>
                          <input
                            type="checkbox"
                            className="sr-only"
                            checked={allSuiteSelected}
                            onChange={e => {
                              if (e.target.checked) {
                                setSelected(p => new Set([...p, ...suiteCases.map(c => c.id)]));
                              } else {
                                setSelected(p => { const n = new Set(p); suiteCases.forEach(c => n.delete(c.id)); return n; });
                              }
                            }}
                          />
                          {allSuiteSelected && (
                            <svg className="h-2.5 w-2.5 text-brand-fg" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5" />
                            </svg>
                          )}
                          {someSuiteSelected && !allSuiteSelected && (
                            <svg className="h-2 w-2 text-brand" fill="currentColor" viewBox="0 0 10 10">
                              <rect x="1.5" y="4" width="7" height="2" rx="1" />
                            </svg>
                          )}
                        </span>
                        <span className="text-[11px] font-semibold text-fg-muted">{suiteName}</span>
                      </label>
                      <span className="text-[10px] text-fg-subtle">{suiteCases.length} case</span>
                    </div>
                    {suiteCases.map(c => {
                      const on = selected.has(c.id);
                      return (
                        <button key={c.id} type="button" onClick={() => toggle(c.id)}
                          className={cn("flex w-full items-center gap-3 border-b border-border px-6 py-2 text-left transition-colors",
                            on ? "bg-brand-soft" : "hover:bg-surface-overlay")}>
                          <span className={cn("flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                            on ? "border-brand bg-brand" : "border-border")}>
                            {on && <svg className="h-2.5 w-2.5 text-brand-fg" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5" /></svg>}
                          </span>
                          <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", P_DOT[c.priority] ?? P_DOT.P3)} />
                          <span className="font-mono text-[10px] text-fg-subtle">{c.case_key}</span>
                          <span className="flex-1 truncate text-[12px] text-fg-muted">{c.title}</span>
                        </button>
                      );
                    })}
                  </div>
                );
              })
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4">
          {err ? <p className="text-[12px] text-red-400">{err}</p> : <span />}
          <div className="flex items-center gap-2">
            <button type="button" onClick={onClose}
              className="rounded-xl border border-border px-4 py-2 text-[13px] font-medium text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg">İptal</button>
            <button type="button" onClick={save} disabled={busy || !name.trim() || selected.size === 0}
              className="rounded-xl bg-brand px-5 py-2 text-[13px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105 disabled:opacity-40">
              {busy ? "Oluşturuluyor…" : "Run Oluştur"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
