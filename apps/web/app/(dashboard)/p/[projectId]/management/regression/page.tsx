"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  useRegressionSets,
  useCreateRegressionSet,
  useUpdateRegressionSet,
  useDeleteRegressionSet,
  useAddCasesToRegressionSet,
  useRemoveCaseFromRegressionSet,
  useManagementRepository,
  useCreateManagementRun,
  useManagementCycles,
  type RegressionSet,
  type RegressionSetCase,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { useRouter } from "next/navigation";

const LAST_RUN_DOT: Record<string, string> = {
  passed:  "bg-emerald-500",
  failed:  "bg-red-500",
  blocked: "bg-amber-500",
  not_run: "bg-slate-600",
};
const SET_TYPE_OPTIONS = ["regression","smoke","release","sprint","uat"] as const;
const PRIORITY_DOT: Record<string, string> = {
  P0: "bg-red-500", P1: "bg-orange-400", P2: "bg-slate-500", P3: "bg-slate-600",
};

function IcSearch() { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>; }
function IcClose()  { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>; }
function IcPlus()   { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>; }
function IcTrash()  { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>; }
function IcEdit()   { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>; }
function IcPlay()   { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><circle cx="12" cy="12" r="9"/><path strokeLinecap="round" strokeLinejoin="round" d="M10 8l6 4-6 4V8z"/></svg>; }

// ─── Case Picker Modal ────────────────────────────────────────────────────────

function CasePickerModal({ mpid, existingCaseIds, onAdd, onClose }: {
  mpid: string; existingCaseIds: Set<string>;
  onAdd: (ids: string[]) => Promise<void>; onClose: () => void;
}) {
  const repoQ    = useManagementRepository(mpid || undefined);
  const allCases = (repoQ.data?.cases ?? []).filter(c => !c.archived);
  const suites   = repoQ.data?.suites ?? [];
  const [search, setSearch]     = useState("");
  const [suiteF, setSuiteF]     = useState("");
  const [prioF,  setPrioF]      = useState("");
  const [checked, setChecked]   = useState<Set<string>>(new Set());
  const [saving,  setSaving]    = useState(false);

  const filtered = useMemo(() => {
    let r = allCases.filter(c => !existingCaseIds.has(c.id));
    const q = search.trim().toLowerCase();
    if (q)     r = r.filter(c => c.title.toLowerCase().includes(q) || (c.case_key ?? "").toLowerCase().includes(q));
    if (suiteF) r = r.filter(c => c.suite_id === suiteF);
    if (prioF)  r = r.filter(c => c.priority === prioF);
    return r;
  }, [allCases, existingCaseIds, search, suiteF, prioF]);

  const allSel  = filtered.length > 0 && filtered.every(c => checked.has(c.id));
  const togAll  = () => allSel
    ? setChecked(p => { const n = new Set(p); filtered.forEach(c => n.delete(c.id)); return n; })
    : setChecked(p => new Set([...p, ...filtered.map(c => c.id)]));
  const tog     = (id: string) => setChecked(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const doAdd   = async () => { if (!checked.size) return; setSaving(true); try { await onAdd([...checked]); onClose(); } finally { setSaving(false); } };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose}/>
      <div className="relative z-10 flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-border bg-surface-raised shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h2 className="text-[14px] font-semibold text-fg">Case Seç</h2>
            <p className="mt-0.5 text-[11px] text-fg-muted">{checked.size > 0 ? `${checked.size} seçili` : "Repository'den case seçin"}</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-fg-subtle hover:bg-surface-overlay"><IcClose/></button>
        </div>
        <div className="flex flex-wrap gap-2 border-b border-border px-5 py-3">
          <div className="flex min-w-[180px] flex-1 items-center gap-1.5 rounded-xl border border-border bg-surface-base px-3 py-1.5">
            <IcSearch/>
            <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Ara…"
              className="flex-1 bg-transparent text-[11px] text-fg placeholder-fg-subtle outline-none"/>
            {search && <button onClick={() => setSearch("")} className="text-fg-subtle"><IcClose/></button>}
          </div>
          <select value={suiteF} onChange={e => setSuiteF(e.target.value)}
            className="rounded-xl border border-border bg-surface-raised px-2 py-1.5 text-[11px] text-fg-muted outline-none">
            <option value="">Tüm Suite&apos;ler</option>
            {suites.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <select value={prioF} onChange={e => setPrioF(e.target.value)}
            className="rounded-xl border border-border bg-surface-raised px-2 py-1.5 text-[11px] text-fg-muted outline-none">
            <option value="">Tüm Öncelikler</option>
            {["P0","P1","P2","P3"].map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div className="flex-1 overflow-y-auto">
          {repoQ.isLoading ? (
            <div className="space-y-1 p-4">{Array.from({length:6}).map((_,i) => <div key={i} className="h-10 rounded-lg bg-surface-overlay animate-pulse"/>)}</div>
          ) : filtered.length === 0 ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-[12px] text-fg-muted">{allCases.filter(c=>!existingCaseIds.has(c.id)).length===0 ? "Tüm case'ler sette mevcut" : "Eşleşen case yok"}</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="sticky top-0 border-b border-border bg-surface-raised">
                <tr>
                  <th className="w-10 px-3 py-2.5">
                    <div onClick={togAll} className={cn("flex h-4 w-4 cursor-pointer items-center justify-center rounded border transition-colors", allSel ? "bg-brand border-brand" : "border-border hover:border-fg-subtle")}>
                      {allSel && <svg className="h-2.5 w-2.5 text-brand-fg" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5"/></svg>}
                    </div>
                  </th>
                  {["ID","Başlık","P","Suite","Tür"].map(h => <th key={h} className="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {filtered.map(tc => {
                  const suite = suites.find(s => s.id === tc.suite_id);
                  const isCk  = checked.has(tc.id);
                  return (
                    <tr key={tc.id} onClick={() => tog(tc.id)} className={cn("cursor-pointer border-b border-border/50 transition-colors", isCk ? "bg-brand/5" : "hover:bg-surface-overlay")}>
                      <td className="px-3 py-2.5">
                        <div className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors", isCk ? "bg-brand border-brand" : "border-border")}>
                          {isCk && <svg className="h-2.5 w-2.5 text-brand-fg" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5"/></svg>}
                        </div>
                      </td>
                      <td className="px-3 py-2.5"><span className="font-mono text-[10px] text-fg-subtle">{tc.case_key}</span></td>
                      <td className="px-3 py-2.5"><span className="text-[12px] text-fg line-clamp-1">{tc.title}</span></td>
                      <td className="px-3 py-2.5">
                        <span className="inline-flex items-center gap-1">
                          <span className={cn("h-1.5 w-1.5 rounded-full", PRIORITY_DOT[tc.priority] ?? "bg-slate-500")}/>
                          <span className="font-mono text-[10px] text-fg-muted">{tc.priority}</span>
                        </span>
                      </td>
                      <td className="px-3 py-2.5"><span className="text-[10px] text-fg-muted truncate max-w-[120px] block">{suite?.name ?? "—"}</span></td>
                      <td className="px-3 py-2.5"><span className="text-[10px] text-fg-subtle">{tc.type}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
        <div className="flex items-center justify-between border-t border-border px-5 py-3">
          <span className="text-[11px] text-fg-muted">{filtered.length} case</span>
          <div className="flex gap-2">
            <button onClick={onClose} className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg">İptal</button>
            <button onClick={doAdd} disabled={!checked.size || saving}
              className="rounded-xl bg-brand px-5 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-40">
              {saving ? "Ekleniyor…" : `${checked.size || ""} Case Ekle`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Stats ────────────────────────────────────────────────────────────────────

function SetStats({ cases }: { cases: RegressionSetCase[] }) {
  const total   = cases.length;
  const passed  = cases.filter(c => c.last_run_status === "passed").length;
  const failed  = cases.filter(c => c.last_run_status === "failed").length;
  const blocked = cases.filter(c => c.last_run_status === "blocked").length;
  const notRun  = cases.filter(c => !c.last_run_status || c.last_run_status === "not_run").length;
  const pct     = (n: number) => total > 0 ? Math.round(n/total*100) : 0;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {([["Toplam",passed+failed+blocked+notRun,"text-fg"],["Geçti",passed,"text-emerald-500"],["Başarısız",failed,"text-red-400"],["Engellendi",blocked,"text-amber-400"]] as [string,number,string][]).map(([l,v,c]) => (
          <div key={l} className="rounded-xl border border-border bg-surface-base px-3 py-2.5 text-center">
            <p className="text-[10px] font-medium uppercase tracking-widest text-fg-subtle">{l}</p>
            <p className={cn("mt-1 text-2xl font-semibold", c)}>{v}</p>
            {total > 0 && <p className="text-[10px] text-fg-subtle">{pct(v)}%</p>}
          </div>
        ))}
      </div>
      {total > 0 && (
        <div className="space-y-1.5">
          <div className="flex h-2 overflow-hidden rounded-full bg-surface-overlay">
            {passed  > 0 && <div className="bg-emerald-500" style={{width:`${pct(passed)}%`}}/>}
            {failed  > 0 && <div className="bg-red-500"     style={{width:`${pct(failed)}%`}}/>}
            {blocked > 0 && <div className="bg-amber-500"   style={{width:`${pct(blocked)}%`}}/>}
            {notRun  > 0 && <div className="bg-slate-700"   style={{width:`${pct(notRun)}%`}}/>}
          </div>
          <div className="flex justify-between text-[10px] text-fg-subtle">
            <span>P0: {cases.filter(c=>c.priority==="P0").length} · P1: {cases.filter(c=>c.priority==="P1").length}</span>
            <span>{notRun} koşulmadı</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ManagementRegressionPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid      = useManagementProjectId(projectId || undefined);
  const router    = useRouter();

  const { data: sets, isLoading, isError, refetch: refetchSets } = useRegressionSets(mpid || undefined);
  const createSet  = useCreateRegressionSet(mpid || "");
  const updateSet  = useUpdateRegressionSet(mpid || "");
  const deleteSet  = useDeleteRegressionSet(mpid || "");
  const addCases   = useAddCasesToRegressionSet(mpid || "");
  const removeCase = useRemoveCaseFromRegressionSet(mpid || "");
  const createRun  = useCreateManagementRun(mpid || "");
  const cyclesQ    = useManagementCycles(mpid || undefined);

  const [selectedCycleId, setSelectedCycleId] = useState<string | null>(null);
  const [selectedId,   setSelectedId]   = useState<string | null>(null);
  const [showNew,      setShowNew]      = useState(false);
  const [newName,      setNewName]      = useState("");
  const [newType,      setNewType]      = useState("regression");
  const [newDesc,      setNewDesc]      = useState("");
  const [search,       setSearch]       = useState("");
  const [showPicker,   setShowPicker]   = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [editId,       setEditId]       = useState<string | null>(null);
  const [editName,     setEditName]     = useState("");
  const [editType,     setEditType]     = useState("regression");
  const [caseSearch,   setCaseSearch]   = useState("");
  const [showRun,      setShowRun]      = useState(false);
  const [runName,      setRunName]      = useState("");
  const [launching,    setLaunching]    = useState(false);
  const [launchError,  setLaunchError]  = useState<string | null>(null);

  const refreshAll = () => {
    void refetchSets();
    void cyclesQ.refetch();
  };

  const filtered    = useMemo(() => (sets ?? []).filter(s => !search || s.name.toLowerCase().includes(search.toLowerCase())), [sets, search]);
  const selectedSet = useMemo(() => (sets ?? []).find(s => s.id === selectedId) ?? null, [sets, selectedId]);
  const filteredCases = useMemo(() => {
    if (!selectedSet) return [];
    const q = caseSearch.trim().toLowerCase();
    return q ? selectedSet.cases.filter(c => c.title.toLowerCase().includes(q) || (c.case_key ?? "").toLowerCase().includes(q)) : selectedSet.cases;
  }, [selectedSet, caseSearch]);
  const existingIds = useMemo(() => new Set((selectedSet?.cases ?? []).map(c => c.case_id)), [selectedSet]);

  const doCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    const s = await createSet.mutateAsync({ name: newName.trim(), set_type: newType, description: newDesc.trim() || undefined });
    setNewName(""); setNewType("regression"); setNewDesc(""); setShowNew(false); setSelectedId(s.id);
  };

  const doEditSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editName.trim() || !editId) return;
    await updateSet.mutateAsync({ id: editId, name: editName.trim(), set_type: editType });
    setEditId(null);
  };

  const doDelete = async () => {
    if (!deleteTarget) return;
    await deleteSet.mutateAsync({ id: deleteTarget });
    if (selectedId === deleteTarget) setSelectedId(null);
    setDeleteTarget(null);
  };

  const doLaunchRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSet || !runName.trim()) return;
    const cid = selectedCycleId ?? (cyclesQ.data ?? [])[0]?.id;
    if (!cid) { setLaunchError("Bir döngü seçin"); return; }
    setLaunchError(null);
    setLaunching(true);
    try {
      const run = await createRun.mutateAsync({ cycle_id: cid, name: runName.trim(), case_ids: selectedSet.cases.map(c => c.case_id) });
      router.push(`/p/${projectId}/management/runs/${run.id}/execute`);
    } catch(e) {
      setLaunchError(e instanceof Error ? e.message : "Hata");
    } finally { setLaunching(false); setShowRun(false); }
  };

  return (
    <div className="flex h-[calc(100vh-48px)] overflow-hidden bg-surface-base">
      {/* Left */}
      <aside className="flex w-64 shrink-0 flex-col overflow-hidden border-r border-border bg-surface-raised">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-[12px] font-semibold text-fg">Regresyon Setleri</span>
          <button onClick={() => { setShowNew(true); setSelectedId(null); setEditId(null); }}
            className="flex items-center gap-1 rounded-lg bg-brand px-2 py-1 text-[10px] font-semibold text-brand-fg hover:brightness-105 shadow-sm">
            <IcPlus/> Yeni
          </button>
        </div>
        <div className="border-b border-border px-3 py-2">
          <div className="flex items-center gap-1.5 rounded-lg border border-border bg-surface-base px-2.5 py-1.5">
            <IcSearch/>
            <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Ara…"
              className="flex-1 bg-transparent text-[11px] text-fg placeholder-fg-subtle outline-none"/>
            {search && <button onClick={() => setSearch("")} className="text-fg-subtle hover:text-fg"><IcClose/></button>}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="space-y-2 p-3">{Array.from({length:4}).map((_,i) => <div key={i} className="h-16 rounded-xl bg-surface-overlay animate-pulse"/>)}</div>
          ) : isError ? (
            <p className="p-4 text-center text-[12px] text-red-400">Yüklenemedi</p>
          ) : (sets ?? []).length === 0 ? (
            <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
              <div className="rounded-full bg-surface-overlay p-4">
                <svg className="h-8 w-8 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
              </div>
              <p className="text-[12px] font-medium text-fg-muted">Henüz set yok</p>
            </div>
          ) : (
            <div className="space-y-0.5 p-2">
              {filtered.map((set: RegressionSet) => (
                <button key={set.id} onClick={() => { setSelectedId(set.id); setShowNew(false); setEditId(null); }}
                  className={cn("w-full rounded-xl border px-3 py-2.5 text-left transition-colors",
                    selectedId === set.id ? "border-brand/20 bg-brand-soft" : "border-transparent hover:border-border hover:bg-surface-overlay")}>
                  <div className="flex items-center gap-2">
                    <span className={cn("flex-1 truncate text-[12px] font-medium", selectedId === set.id ? "text-brand" : "text-fg")}>{set.name}</span>
                    <span className={cn("rounded px-1.5 py-0.5 text-[9px]", selectedId === set.id ? "bg-brand/15 text-brand" : "bg-surface-overlay text-fg-subtle")}>{set.set_type}</span>
                  </div>
                  <div className="mt-1 flex justify-between text-[10px] text-fg-subtle">
                    <span>{set.cases.length} case</span>
                    <span>{new Date(set.created_at).toLocaleDateString("tr-TR",{day:"2-digit",month:"short"})}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        {(sets ?? []).length > 0 && (
          <div className="border-t border-border px-4 py-2 flex justify-between text-[10px] text-fg-subtle">
            <span>{(sets ?? []).length} set</span>
            <span>{(sets ?? []).reduce((s,r)=>s+r.cases.length,0)} case</span>
          </div>
        )}
      </aside>

      {/* Right */}
      <div className="flex flex-1 flex-col overflow-hidden">

        {/* New form */}
        {showNew && (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="mx-auto max-w-lg">
              <h2 className="mb-5 text-[15px] font-semibold text-fg">Yeni Regresyon Seti</h2>
              <form onSubmit={doCreate} className="space-y-4 rounded-2xl border border-border bg-surface-raised p-5">
                <div>
                  <label className="mb-1.5 block text-[11px] uppercase tracking-widest text-fg-subtle">Set Adı *</label>
                  <input autoFocus value={newName} onChange={e=>setNewName(e.target.value)} required
                    placeholder="örn. Sprint 24 Regression"
                    className="w-full rounded-xl border border-border bg-surface-base px-3 py-2.5 text-[13px] text-fg outline-none focus:border-brand/50"/>
                </div>
                <div>
                  <label className="mb-1.5 block text-[11px] uppercase tracking-widest text-fg-subtle">Set Tipi</label>
                  <select value={newType} onChange={e=>setNewType(e.target.value)}
                    className="w-full rounded-xl border border-border bg-surface-base px-3 py-2.5 text-[13px] text-fg outline-none">
                    {SET_TYPE_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1.5 block text-[11px] uppercase tracking-widest text-fg-subtle">Açıklama</label>
                  <textarea value={newDesc} onChange={e=>setNewDesc(e.target.value)} rows={2} placeholder="Kapsam açıklaması…"
                    className="w-full resize-none rounded-xl border border-border bg-surface-base px-3 py-2.5 text-[13px] text-fg outline-none"/>
                </div>
                <div className="flex gap-2 pt-1">
                  <button type="button" onClick={()=>setShowNew(false)}
                    className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg">İptal</button>
                  <button type="submit" disabled={!newName.trim()||createSet.isPending}
                    className="rounded-xl bg-brand px-5 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-40">
                    {createSet.isPending ? "Oluşturuluyor…" : "Oluştur"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Detail */}
        {selectedSet && !showNew && (
          <>
            <div className="border-b border-border bg-surface-raised px-6 py-4">
              {editId === selectedSet.id ? (
                <form onSubmit={doEditSave} className="flex items-center gap-3">
                  <input autoFocus value={editName} onChange={e=>setEditName(e.target.value)}
                    className="flex-1 rounded-xl border border-brand/30 bg-surface-base px-3 py-2 text-[13px] text-fg outline-none"/>
                  <select value={editType} onChange={e=>setEditType(e.target.value)}
                    className="rounded-xl border border-border bg-surface-base px-3 py-2 text-[12px] text-fg outline-none">
                    {SET_TYPE_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                  <button type="submit" disabled={updateSet.isPending}
                    className="rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 disabled:opacity-40">
                    {updateSet.isPending ? "…" : "Kaydet"}
                  </button>
                  <button type="button" onClick={()=>setEditId(null)}
                    className="rounded-xl border border-border px-3 py-2 text-[12px] text-fg-muted">İptal</button>
                </form>
              ) : (
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-[16px] font-semibold text-fg">{selectedSet.name}</h2>
                      <span className="rounded-md border border-border px-2 py-0.5 text-[10px] text-fg-muted">{selectedSet.set_type}</span>
                    </div>
                    {selectedSet.description && <p className="mt-1 text-[12px] text-fg-muted">{selectedSet.description}</p>}
                    <p className="mt-1 text-[11px] text-fg-subtle">{selectedSet.cases.length} case · {new Date(selectedSet.created_at).toLocaleDateString("tr-TR",{day:"2-digit",month:"long",year:"numeric"})}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button onClick={()=>setShowPicker(true)}
                      className="flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-[12px] text-fg-muted hover:border-brand/30 hover:text-brand">
                      <IcPlus/> Case Ekle
                    </button>
                    <button onClick={()=>{setRunName(selectedSet.name+" — Run");setShowRun(true);}}
                      className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-2 text-[12px] font-semibold text-white hover:bg-emerald-500 shadow-sm">
                      <IcPlay/> Run Başlat
                    </button>
                    <button onClick={()=>{setEditId(selectedSet.id);setEditName(selectedSet.name);setEditType(selectedSet.set_type);}}
                      className="rounded-lg p-2 text-fg-subtle hover:bg-surface-overlay hover:text-fg"><IcEdit/></button>
                    <button onClick={()=>setDeleteTarget(selectedSet.id)}
                      className="rounded-lg p-2 text-fg-subtle hover:bg-red-500/10 hover:text-red-400"><IcTrash/></button>
                  </div>
                </div>
              )}
            </div>
            <div className="border-b border-border bg-surface-base px-6 py-4">
              <SetStats cases={selectedSet.cases}/>
            </div>
            <div className="flex items-center gap-3 border-b border-border px-6 py-2.5">
              <div className="flex flex-1 items-center gap-1.5 rounded-xl border border-border bg-surface-raised px-2.5 py-1.5">
                <IcSearch/>
                <input type="text" value={caseSearch} onChange={e=>setCaseSearch(e.target.value)} placeholder="Case ara…"
                  className="flex-1 bg-transparent text-[11px] text-fg placeholder-fg-subtle outline-none"/>
                {caseSearch && <button onClick={()=>setCaseSearch("")} className="text-fg-subtle"><IcClose/></button>}
              </div>
              <span className="text-[11px] text-fg-subtle">{filteredCases.length}/{selectedSet.cases.length}</span>
            </div>
            <div className="flex-1 overflow-auto">
              {selectedSet.cases.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
                  <div className="rounded-full bg-surface-overlay p-5">
                    <svg className="h-10 w-10 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
                  </div>
                  <div>
                    <p className="text-[13px] font-semibold text-fg-muted">Bu sette henüz case yok</p>
                    <p className="mt-1 text-[11px] text-fg-subtle max-w-xs mx-auto">Repository&apos;den case ekleyerek regresyon setini oluşturun.</p>
                  </div>
                  <button onClick={()=>setShowPicker(true)}
                    className="flex items-center gap-1.5 rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105">
                    <IcPlus/> Case Ekle
                  </button>
                </div>
              ) : (
                <table className="w-full">
                  <thead className="sticky top-0 z-10 border-b border-border bg-surface-raised/90 backdrop-blur-sm">
                    <tr>
                      {["Key","Başlık","Öncelik","Tür","Son Koşum","Risk Skoru",""].map(h => (
                        <th key={h} className={cn("px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-widest text-fg-subtle", h==="" && "w-10")}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCases.map((c: RegressionSetCase) => (
                      <tr key={c.id} className="group border-b border-border/50 hover:bg-surface-overlay">
                        <td className="px-4 py-3"><span className="font-mono text-[10px] text-fg-subtle">{c.case_key}</span></td>
                        <td className="px-4 py-3"><span className="text-[12px] text-fg line-clamp-1">{c.title}</span></td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1.5">
                            <span className={cn("h-1.5 w-1.5 rounded-full", PRIORITY_DOT[c.priority] ?? "bg-slate-500")}/>
                            <span className="font-mono text-[10px] text-fg-muted">{c.priority}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3"><span className="rounded bg-surface-overlay px-1.5 py-0.5 text-[10px] text-fg-muted">{c.type}</span></td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1.5">
                            <span className={cn("h-1.5 w-1.5 rounded-full", LAST_RUN_DOT[c.last_run_status ?? "not_run"] ?? "bg-slate-600")}/>
                            <span className="text-[10px] text-fg-muted">{c.last_run_status ?? "not_run"}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3"><span className="font-mono text-[10px] text-fg-subtle">{typeof c.risk_score==="number"&&c.risk_score>0?c.risk_score.toFixed(2):"--"}</span></td>
                        <td className="w-10 px-2">
                          <button onClick={()=>removeCase.mutate({setId:selectedSet.id,caseId:c.case_id})} disabled={removeCase.isPending}
                            className="invisible group-hover:visible rounded-lg p-1.5 text-fg-subtle hover:bg-red-500/10 hover:text-red-400">
                            <IcTrash/>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}

        {/* Error */}
        {isError && !selectedSet && !showNew && (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
            <p className="text-[13px] text-red-400">Regresyon setleri yüklenemedi.</p>
            <button
              onClick={() => refreshAll()}
              className="text-[12px] text-brand hover:underline"
            >
              Tekrar dene
            </button>
          </div>
        )}

        {/* Empty */}
        {!isError && !selectedSet && !showNew && (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
            <div className="rounded-full bg-surface-overlay p-6">
              <svg className="h-12 w-12 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
            </div>
            <div>
              <p className="text-[14px] font-semibold text-fg-muted">{(sets??[]).length>0?"Bir set seçin":"İlk seti oluşturun"}</p>
              <p className="mt-1 max-w-xs text-[12px] text-fg-subtle">
                {(sets??[]).length>0?"Sol panelden bir set seçin.":"Regresyon setleri test case'lerini gruplandırır."}
              </p>
            </div>
            {(sets??[]).length===0 && (
              <button onClick={()=>setShowNew(true)}
                className="flex items-center gap-1.5 rounded-xl bg-brand px-5 py-2.5 text-[12px] font-semibold text-brand-fg hover:brightness-105">
                <IcPlus/> Oluştur
              </button>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      {showPicker && selectedSet && (
        <CasePickerModal mpid={mpid} existingCaseIds={existingIds}
          onAdd={async (ids) => { await addCases.mutateAsync({setId:selectedSet.id,caseIds:ids}); }}
          onClose={()=>setShowPicker(false)}/>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={()=>setDeleteTarget(null)}/>
          <div className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-surface-raised p-6 shadow-2xl">
            <h3 className="text-[14px] font-semibold text-fg">Seti Sil</h3>
            <p className="mt-2 text-[12px] text-fg-muted">
              <span className="font-semibold text-fg">{(sets??[]).find(s=>s.id===deleteTarget)?.name}</span> kalıcı olarak silinecek.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={()=>setDeleteTarget(null)} className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg">İptal</button>
              <button onClick={doDelete} className="rounded-xl bg-red-600 px-4 py-2 text-[12px] font-semibold text-white hover:bg-red-500">Sil</button>
            </div>
          </div>
        </div>
      )}

      {showRun && selectedSet && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={()=>setShowRun(false)}/>
          <div className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-surface-raised p-6 shadow-2xl">
            <h3 className="text-[14px] font-semibold text-fg">Run Başlat</h3>
            <p className="mt-1 text-[12px] text-fg-muted">{selectedSet.cases.length} case · <span className="font-semibold text-fg">{selectedSet.name}</span></p>
            {cyclesQ.isLoading ? (
              <div className="mt-4 space-y-2">
                {Array.from({length:2}).map((_,i) => <div key={i} className="h-8 rounded-xl bg-surface-overlay animate-pulse"/>)}
              </div>
            ) : !(cyclesQ.data??[]).length ? (
              <div className="mt-4 space-y-3">
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                  <p className="text-[12px] text-amber-400">
                    Run başlatmak için önce{" "}
                    <Link href={`/p/${projectId}/management/plans`} className="underline hover:text-amber-300">
                      Plans sayfasından Cycle oluşturun
                    </Link>.
                  </p>
                </div>
                <div className="flex justify-end">
                  <button onClick={()=>setShowRun(false)} className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted">Kapat</button>
                </div>
              </div>
            ) : (
              <form onSubmit={doLaunchRun} className="mt-4 space-y-3">
                {(cyclesQ.data??[]).length > 1 && (
                  <div>
                    <label className="mb-1.5 block text-[11px] uppercase tracking-widest text-fg-subtle">Cycle</label>
                    <select
                      value={selectedCycleId ?? (cyclesQ.data??[])[0]?.id ?? ""}
                      onChange={e => setSelectedCycleId(e.target.value)}
                      className="w-full rounded-xl border border-border bg-surface-base px-3 py-2 text-[13px] text-fg outline-none focus:border-brand/50"
                    >
                      {(cyclesQ.data??[]).map(c => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <label className="mb-1.5 block text-[11px] uppercase tracking-widest text-fg-subtle">Run Adı</label>
                  <input autoFocus value={runName} onChange={e=>setRunName(e.target.value)} required
                    className="w-full rounded-xl border border-border bg-surface-base px-3 py-2 text-[13px] text-fg outline-none focus:border-brand/50"/>
                </div>
                {launchError && (
                  <p className="rounded-xl border border-red-500/20 bg-red-500/5 px-3 py-2 text-[11px] text-red-400">{launchError}</p>
                )}
                <div className="flex gap-2 pt-1">
                  <button type="button" onClick={()=>setShowRun(false)} className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted">İptal</button>
                  <button type="submit" disabled={!runName.trim()||launching}
                    className="flex-1 rounded-xl bg-emerald-600 py-2 text-[12px] font-semibold text-white hover:bg-emerald-500 disabled:opacity-40">
                    {launching?"Başlatılıyor…":"Çalıştır"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
