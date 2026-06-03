"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import {
  DndContext, DragOverlay, PointerSensor, KeyboardSensor,
  useSensor, useSensors, closestCenter, type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext, sortableKeyboardCoordinates,
  verticalListSortingStrategy, useSortable, arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  useManagementRepository,
  useManagementCase,
  useCreateManagementCase,
  useUpdateManagementCase,
  useCreateManagementSuite,
  useCreateManagementFolder,
  useMoveManagementCase,
  useArchiveManagementCase,
  type TestCase, type TestFolder, type TestSuite,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";

// ─── Config ───────────────────────────────────────────────────────────────────

const P_DOT: Record<string, string> = {
  P0: "bg-red-500/80", P1: "bg-orange-400/60",
  P2: "bg-slate-500",  P3: "bg-slate-600",
};
const S_DOT: Record<string, { dot: string; label: string }> = {
  active:   { dot: "bg-emerald-500/70", label: "Aktif"  },
  draft:    { dot: "bg-slate-600",      label: "Taslak" },
  review:   { dot: "bg-blue-500/60",    label: "Review" },
  archived: { dot: "bg-slate-700",      label: "Arşiv"  },
};
const R_DOT: Record<string, { dot: string; label: string }> = {
  passed:  { dot: "bg-emerald-500/70", label: "Passed"  },
  failed:  { dot: "bg-red-500/80",     label: "Failed"  },
  blocked: { dot: "bg-amber-500/60",   label: "Blocked" },
  not_run: { dot: "bg-slate-700",      label: "—"       },
};

const TYPE_OPTIONS = [
  "manual","smoke","regression","uat","exploratory",
  "integration","performance","security","accessibility","api","e2e",
] as const;

type Node = { type: "all" } | { type: "suite"; id: string } | { type: "folder"; id: string; suiteId: string };
type DraftStep = { id: string; action: string; expected_result: string; test_data: string; is_required: boolean };

function step(o?: Partial<DraftStep>): DraftStep {
  return { id: `s${Math.random().toString(36).slice(2,7)}`, action: "", expected_result: "", test_data: "", is_required: true, ...o };
}
function slugify(s: string) { return `/${s.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"") || s}`; }

// ─── Icons ────────────────────────────────────────────────────────────────────

function IcChev({ open }: { open: boolean }) { return <svg className={cn("h-2.5 w-2.5 shrink-0 transition-transform", open && "rotate-90")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7"/></svg>; }
function IcPlus() { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>; }
function IcClose() { return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>; }
function IcGrip() { return <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 16 16"><circle cx="5" cy="4" r="1.2"/><circle cx="11" cy="4" r="1.2"/><circle cx="5" cy="8" r="1.2"/><circle cx="11" cy="8" r="1.2"/><circle cx="5" cy="12" r="1.2"/><circle cx="11" cy="12" r="1.2"/></svg>; }
function IcSearch() { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>; }

// ─── Left Tree ────────────────────────────────────────────────────────────────

function LeftTree({ suites, folders, cases, node, onNode, projectId, pid }: {
  suites: TestSuite[]; folders: TestFolder[]; cases: TestCase[];
  node: Node; onNode: (n: Node) => void; projectId: string; pid: string;
}) {
  const [expanded,    setExpanded]    = useState<Set<string>>(() => new Set(suites.slice(0,3).map(s => s.id)));
  const [addSuite,    setAddSuite]    = useState(false);
  const [suiteName,   setSuiteName]   = useState("");
  const [addFolder,   setAddFolder]   = useState<string|null>(null);
  const [folderName,  setFolderName]  = useState("");

  const createSuite  = useCreateManagementSuite(pid);
  const createFolder = useCreateManagementFolder(pid);

  const toggle = (id: string) => setExpanded(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const saveSuite = async () => {
    if (!suiteName.trim()) return;
    const s = await createSuite.mutateAsync({ name: suiteName.trim() });
    setExpanded(p => new Set([...p, s.id]));
    setSuiteName(""); setAddSuite(false);
  };
  const saveFolder = async (sid: string) => {
    if (!folderName.trim()) return;
    await createFolder.mutateAsync({ suite_id: sid, name: folderName.trim(), path: slugify(folderName.trim()) });
    setFolderName(""); setAddFolder(null);
  };

  const total = cases.filter(c => !c.archived).length;

  return (
    <div className="flex h-full flex-col border-r border-white/[0.06]">
      {/* Search */}
      <div className="border-b border-white/[0.06] px-3 py-2.5">
        <div className="flex items-center gap-2 rounded-lg bg-white/[0.04] px-2.5 py-1.5">
          <IcSearch/><input type="text" placeholder="Ara…" className="flex-1 bg-transparent text-[12px] text-slate-300 placeholder-slate-600 outline-none"/>
        </div>
      </div>

      {/* All */}
      <div className="px-2 pt-2">
        <button type="button" onClick={() => onNode({ type: "all" })}
          className={cn("flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition-colors",
            node.type === "all" ? "bg-white/[0.07] text-slate-100" : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300")}>
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded bg-slate-700 text-[9px] font-bold text-slate-400">∑</span>
          <span className="flex-1 text-left font-medium">Tüm Senaryolar</span>
          <span className="text-[11px] text-slate-600 tabular-nums">{total}</span>
        </button>
      </div>

      {/* Suite list */}
      <div className="flex-1 overflow-y-auto space-y-0.5 px-2 pb-2 pt-1">
        {suites.map(suite => {
          const sf  = folders.filter(f => f.suite_id === suite.id && !f.parent_id);
          const sc  = cases.filter(c => c.suite_id === suite.id && !c.archived).length;
          const exp = expanded.has(suite.id);
          const sel = node.type === "suite" && node.id === suite.id;

          return (
            <div key={suite.id}>
              <div className="group flex items-center gap-0.5">
                <button type="button" onClick={() => toggle(suite.id)}
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-slate-700 hover:text-slate-400 transition-colors">
                  <IcChev open={exp}/>
                </button>
                <button type="button" onClick={() => onNode({ type: "suite", id: suite.id })}
                  className={cn("flex flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-[13px] transition-colors",
                    sel ? "bg-white/[0.07] text-slate-100" : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200")}>
                  <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded bg-slate-700/80 text-[9px] font-bold text-slate-300">S</span>
                  <span className="flex-1 truncate text-left font-medium">{suite.name}</span>
                  {sc > 0 && <span className="text-[11px] text-slate-600 tabular-nums">{sc}</span>}
                </button>
                <button type="button"
                  onClick={() => { setAddFolder(suite.id); setExpanded(p => new Set([...p, suite.id])); }}
                  className="opacity-0 group-hover:opacity-100 flex h-5 w-5 shrink-0 items-center justify-center rounded text-slate-700 hover:text-slate-400 transition-all">
                  <IcPlus/>
                </button>
              </div>

              {exp && (
                <div className="ml-5 border-l border-white/[0.05] pl-2 mt-0.5 space-y-0.5">
                  {sf.map(folder => {
                    const fc = cases.filter(c => c.folder_id === folder.id && !c.archived).length;
                    const fsel = node.type === "folder" && node.id === folder.id;
                    return (
                      <button key={folder.id} type="button"
                        onClick={() => onNode({ type: "folder", id: folder.id, suiteId: suite.id })}
                        className={cn("flex w-full items-center gap-2 rounded-lg px-2 py-1 text-[12px] transition-colors",
                          fsel ? "bg-white/[0.07] text-slate-100" : "text-slate-500 hover:bg-white/[0.04] hover:text-slate-300")}>
                        <svg className="h-3 w-3 shrink-0 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"/></svg>
                        <span className="flex-1 truncate text-left">{folder.name}</span>
                        {fc > 0 && <span className="text-[10px] text-slate-700 tabular-nums">{fc}</span>}
                      </button>
                    );
                  })}

                  {addFolder === suite.id ? (
                    <div className="flex items-center gap-1 rounded-lg border border-blue-500/20 bg-blue-500/5 px-2 py-1">
                      <input autoFocus type="text" value={folderName} onChange={e => setFolderName(e.target.value)}
                        placeholder="Folder adı…"
                        onKeyDown={e => { if (e.key === "Enter") saveFolder(suite.id); if (e.key === "Escape") { setAddFolder(null); setFolderName(""); }}}
                        className="flex-1 bg-transparent text-[12px] text-slate-200 placeholder-slate-600 outline-none"/>
                      <button type="button" onClick={() => saveFolder(suite.id)} className="text-[10px] text-blue-400 hover:text-blue-300">✓</button>
                      <button type="button" onClick={() => { setAddFolder(null); setFolderName(""); }} className="text-[10px] text-slate-600 hover:text-slate-400">✕</button>
                    </div>
                  ) : (
                    <button type="button" onClick={() => setAddFolder(suite.id)}
                      className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] text-slate-700 hover:text-slate-400 transition-colors">
                      <IcPlus/> Folder ekle
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {addSuite ? (
          <div className="flex items-center gap-1 rounded-lg border border-blue-500/20 bg-blue-500/5 px-2 py-1.5 ml-5">
            <input autoFocus type="text" value={suiteName} onChange={e => setSuiteName(e.target.value)}
              placeholder="Suite adı…"
              onKeyDown={e => { if (e.key === "Enter") saveSuite(); if (e.key === "Escape") { setAddSuite(false); setSuiteName(""); }}}
              className="flex-1 bg-transparent text-[13px] text-slate-200 placeholder-slate-600 outline-none"/>
            <button type="button" onClick={saveSuite} className="text-[10px] text-blue-400 hover:text-blue-300">✓</button>
            <button type="button" onClick={() => { setAddSuite(false); setSuiteName(""); }} className="text-[10px] text-slate-600 hover:text-slate-400">✕</button>
          </div>
        ) : (
          <button type="button" onClick={() => setAddSuite(true)}
            className="ml-5 flex w-full items-center gap-1.5 rounded-lg border border-dashed border-white/[0.06] px-2 py-1.5 text-[11px] text-slate-700 hover:border-white/[0.1] hover:text-slate-400 transition-colors mt-1">
            <IcPlus/> Yeni Suite
          </button>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-white/[0.06] px-4 py-2">
        <div className="flex items-center justify-between text-[10px] text-slate-700">
          <span>{suites.length} suite</span>
          <span>{folders.length} folder</span>
          <span>{total} case</span>
        </div>
      </div>
    </div>
  );
}

// ─── Case Row ─────────────────────────────────────────────────────────────────

function CaseRow({ tc, selected, onSelect, checked, onCheck, projectId }: {
  tc: TestCase; selected: boolean; onSelect: () => void;
  checked: boolean; onCheck: (e: React.MouseEvent) => void; projectId: string;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: tc.id });
  const pd = P_DOT[tc.priority] ?? P_DOT.P3;
  const sd = S_DOT[tc.status]   ?? S_DOT.draft;
  const rd = tc.last_run_status ? (R_DOT[tc.last_run_status] ?? R_DOT.not_run) : null;

  return (
    <tr ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.3 : 1 }}
      onClick={onSelect}
      className={cn("group border-b border-white/[0.04] cursor-pointer transition-colors",
        selected ? "bg-blue-500/[0.06] border-l-2 border-l-blue-500/50" : "hover:bg-white/[0.03] border-l-2 border-l-transparent")}>
      <td className="hidden w-5 pl-1.5 sm:table-cell">
        <button type="button" {...attributes} {...listeners}
          className="invisible group-hover:visible cursor-grab active:cursor-grabbing touch-none text-slate-700 hover:text-slate-500">
          <IcGrip/>
        </button>
      </td>
      <td className="w-8 px-2">
        <button type="button" onClick={onCheck}
          className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
            checked ? "bg-blue-600 border-blue-600" : "border-slate-700 hover:border-slate-500")}>
          {checked && <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5"/></svg>}
        </button>
      </td>
      <td className="w-[5.5rem] px-3 py-3">
        <span className="select-all font-mono text-[10px] text-slate-600">{tc.case_key}</span>
      </td>
      <td className="px-3 py-3">
        <p className="text-[13px] text-slate-300 line-clamp-1 group-hover:text-slate-100 transition-colors">{tc.title}</p>
        {tc.tags && tc.tags.length > 0 && (
          <div className="mt-1 flex gap-1">
            {tc.tags.slice(0,3).map(t => <span key={t} className="rounded bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-slate-600">{t}</span>)}
          </div>
        )}
      </td>
      <td className="w-16 px-3 py-3">
        <span className="flex items-center gap-1.5">
          <span className={cn("h-1.5 w-1.5 rounded-full", pd)}/>
          <span className="font-mono text-[11px] text-slate-500">{tc.priority}</span>
        </span>
      </td>
      <td className="hidden w-24 px-3 py-3 lg:table-cell">
        <span className="rounded bg-white/[0.04] px-1.5 py-0.5 text-[11px] text-slate-500">{tc.type}</span>
      </td>
      <td className="hidden w-20 px-3 py-3 md:table-cell">
        <span className="flex items-center gap-1.5">
          <span className={cn("h-1.5 w-1.5 rounded-full", sd.dot)}/>
          <span className="text-[11px] text-slate-500">{sd.label}</span>
        </span>
      </td>
      <td className="hidden w-24 px-3 py-3 lg:table-cell">
        {rd ? (
          <span className="flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 rounded-full", rd.dot)}/>
            <span className="text-[11px] text-slate-500">{rd.label}</span>
          </span>
        ) : <span className="text-[11px] text-slate-700">—</span>}
      </td>
      <td className="hidden w-16 px-3 py-3 text-[11px] text-slate-600 tabular-nums xl:table-cell">
        {tc.steps?.length ?? 0}
      </td>
      <td className="hidden w-20 px-3 py-3 xl:table-cell">
        <span className="text-[11px] text-slate-600">
          {tc.updated_at ? new Date(tc.updated_at).toLocaleDateString("tr-TR",{day:"2-digit",month:"short"}) : "—"}
        </span>
      </td>
      <td className="w-10 px-2">
        <Link href={`/p/${projectId}/management/cases/${tc.id}`} onClick={e => e.stopPropagation()}
          className="invisible group-hover:visible inline-flex rounded p-1 text-slate-600 hover:bg-white/[0.06] hover:text-slate-300 transition-all">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
        </Link>
      </td>
    </tr>
  );
}

// ─── Sortable Step Item (extracted to obey Rules of Hooks) ───────────────────

function SortableStepItem({ s, index, onUpdate, onRemove }: {
  s: DraftStep; index: number;
  onUpdate: (patch: Partial<DraftStep>) => void;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: s.id });
  return (
    <div ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.35 : 1 }}
      className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
      <div className="mb-2 flex items-center gap-2">
        <button type="button" {...attributes} {...listeners}
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/[0.06] font-mono text-[10px] font-bold text-slate-500 cursor-grab active:cursor-grabbing touch-none">
          {index + 1}
        </button>
        <label className="ml-auto flex items-center gap-1.5 text-[10px] text-slate-600">
          <input type="checkbox" checked={s.is_required} onChange={e => onUpdate({ is_required: e.target.checked })} className="h-3 w-3 accent-blue-500"/>
          Zorunlu
        </label>
        <button type="button" onClick={onRemove} className="text-slate-700 hover:text-slate-400 transition-colors"><IcClose/></button>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <textarea value={s.action} onChange={e => onUpdate({ action: e.target.value })}
          placeholder="Aksiyon…" rows={2} className="rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-[12px] text-slate-200 placeholder-slate-700 focus:border-blue-500/30 focus:outline-none resize-none"/>
        <textarea value={s.expected_result} onChange={e => onUpdate({ expected_result: e.target.value })}
          placeholder="Beklenen sonuç…" rows={2} className="rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-[12px] text-slate-200 placeholder-slate-700 focus:border-blue-500/30 focus:outline-none resize-none"/>
      </div>
    </div>
  );
}

// ─── New Case Modal ───────────────────────────────────────────────────────────

function NewCaseModal({ pid, suites, folders, defSuiteId, defFolderId, onClose, onDone }: {
  pid: string; suites: TestSuite[]; folders: TestFolder[];
  defSuiteId?: string; defFolderId?: string;
  onClose: () => void; onDone: (tc: TestCase) => void;
}) {
  const createCase = useCreateManagementCase(pid);
  const [title, setTitle] = useState(""); const [obj, setObj] = useState("");
  const [pre, setPre] = useState(""); const [suiteId, setSuiteId] = useState(defSuiteId ?? "");
  const [folderId, setFolderId] = useState(defFolderId ?? ""); const [priority, setPriority] = useState("P1");
  const [severity, setSeverity] = useState("major"); const [type, setType] = useState("manual");
  const [status, setStatus] = useState("draft"); const [tagsText, setTagsText] = useState("");
  const [steps, setSteps] = useState<DraftStep[]>([step(), step()]); const [err, setErr] = useState("");

  const avFolders = folders.filter(f => !suiteId || f.suite_id === suiteId);
  const sensors = useSensors(useSensor(PointerSensor,{activationConstraint:{distance:8}}),useSensor(KeyboardSensor,{coordinateGetter:sortableKeyboardCoordinates}));

  const save = async () => {
    if (!title.trim()) { setErr("Başlık zorunlu."); return; }
    setErr("");
    try {
      const tc = await createCase.mutateAsync({
        title: title.trim(), objective: obj.trim()||null, preconditions: pre.trim()||null,
        suite_id: suiteId||null, folder_id: folderId||null,
        priority, severity, type, status, source_type: "manual",
        tags: tagsText.split(",").map(t=>t.trim()).filter(Boolean),
        steps: steps.filter(s=>s.action.trim()||s.expected_result.trim()).map((s,i)=>({
          step_no:i+1, action:s.action.trim(), expected_result:s.expected_result.trim(),
          test_data:s.test_data.trim()?{value:s.test_data.trim()}:{}, is_required:s.is_required,
        })),
      });
      onDone(tc);
    } catch { setErr("Kaydedilemedi."); }
  };

  const inp = "w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 focus:border-blue-500/40 focus:outline-none transition-colors";
  const sel = "rounded-xl border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-300 focus:border-blue-500/40 focus:outline-none";

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-8 bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl rounded-2xl border border-white/[0.08] bg-[#0d1221] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/[0.06] px-6 py-4">
          <h2 className="text-[15px] font-semibold text-slate-100">Yeni Test Senaryosu</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-slate-600 hover:bg-white/[0.06] hover:text-slate-300 transition-colors"><IcClose/></button>
        </div>

        <div className="space-y-4 px-6 py-5">
          {/* Title */}
          <input autoFocus type="text" value={title} onChange={e=>setTitle(e.target.value)} placeholder="Senaryo başlığı *" className={inp}/>

          {/* Metadata */}
          <div className="grid grid-cols-4 gap-2">
            <select value={priority} onChange={e=>setPriority(e.target.value)} className={sel}>
              {["P0","P1","P2","P3"].map(v=><option key={v} value={v}>{v}</option>)}
            </select>
            <select value={severity} onChange={e=>setSeverity(e.target.value)} className={sel}>
              {["critical","major","minor","trivial"].map(v=><option key={v} value={v}>{v}</option>)}
            </select>
            <select value={type} onChange={e=>setType(e.target.value)} className={sel}>
              {TYPE_OPTIONS.map(v=><option key={v} value={v}>{v}</option>)}
            </select>
            <select value={status} onChange={e=>setStatus(e.target.value)} className={sel}>
              <option value="draft">Taslak</option>
              <option value="active">Aktif</option>
              <option value="review">Review</option>
            </select>
          </div>

          {/* Suite / Folder */}
          <div className="grid grid-cols-2 gap-2">
            <select value={suiteId} onChange={e=>{setSuiteId(e.target.value);setFolderId("");}} className={sel}>
              <option value="">Suite seç</option>
              {suites.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={folderId} onChange={e=>setFolderId(e.target.value)} className={sel}>
              <option value="">Folder seç</option>
              {avFolders.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </div>

          {/* Obj + Pre */}
          <div className="grid grid-cols-2 gap-3">
            <div><label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Amaç</label>
              <textarea value={obj} onChange={e=>setObj(e.target.value)} rows={2} placeholder="Bu senaryonun amacı…" className={cn(inp,"resize-none")}/></div>
            <div><label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Ön Koşullar</label>
              <textarea value={pre} onChange={e=>setPre(e.target.value)} rows={2} placeholder="Başlamak için…" className={cn(inp,"resize-none")}/></div>
          </div>

          {/* Tags */}
          <input type="text" value={tagsText} onChange={e=>setTagsText(e.target.value)} placeholder="smoke, regression, login…" className={inp}/>

          {/* Steps */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-[10px] uppercase tracking-widest text-slate-600">Test Adımları</label>
              <button type="button" onClick={()=>setSteps(s=>[...s,step()])}
                className="flex items-center gap-1 rounded-lg border border-white/[0.08] px-2 py-1 text-[11px] text-slate-500 hover:text-slate-300 transition-colors">
                <IcPlus/> Adım
              </button>
            </div>
            <DndContext sensors={sensors} collisionDetection={closestCenter}
              onDragEnd={e => {
                const {active,over}=e; if(!over||active.id===over.id) return;
                setSteps(c=>{const oi=c.findIndex(s=>s.id===active.id),ni=c.findIndex(s=>s.id===over.id);return arrayMove(c,oi,ni);});
              }}>
              <SortableContext items={steps.map(s=>s.id)} strategy={verticalListSortingStrategy}>
                <div className="space-y-2">
                  {steps.map((s,i) => (
                    <SortableStepItem key={s.id} s={s} index={i}
                      onUpdate={patch=>setSteps(c=>c.map(x=>x.id===s.id?{...x,...patch}:x))}
                      onRemove={()=>setSteps(c=>c.length>1?c.filter(x=>x.id!==s.id):c)}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          </div>

          {err && <p className="text-[12px] text-red-400">{err}</p>}
        </div>

        <div className="flex items-center justify-between border-t border-white/[0.06] px-6 py-4">
          <button type="button" onClick={onClose}
            className="rounded-xl border border-white/[0.08] px-4 py-2 text-[13px] text-slate-500 hover:text-slate-300 transition-colors">
            İptal
          </button>
          <button type="button" onClick={save} disabled={!title.trim()||createCase.isPending}
            className="rounded-xl bg-blue-600 px-5 py-2 text-[13px] font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors">
            {createCase.isPending ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Case Detail Drawer ───────────────────────────────────────────────────────

const P_BADGE: Record<string, string> = {
  P0: "border-red-500/30 bg-red-500/10 text-red-400",
  P1: "border-orange-400/30 bg-orange-400/10 text-orange-400",
  P2: "border-slate-600 bg-slate-800/60 text-slate-400",
  P3: "border-slate-700 bg-slate-800/30 text-slate-500",
};
const SB_BADGE: Record<string, string> = {
  active:   "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  draft:    "border-slate-600 bg-slate-800/60 text-slate-400",
  review:   "border-blue-500/30 bg-blue-500/10 text-blue-400",
  ready:    "border-teal-500/30 bg-teal-500/10 text-teal-400",
  archived: "border-slate-700 bg-slate-900 text-slate-500",
};

function CaseDetailDrawer({ caseId, pid, projectId, onClose }: {
  caseId: string; pid: string; projectId: string; onClose: () => void;
}) {
  const { data: tc, isLoading } = useManagementCase(pid || undefined, caseId || undefined);
  const update  = useUpdateManagementCase(pid);
  const archive = useArchiveManagementCase(pid);

  const [editing,   setEditing]   = useState(false);
  const [title,     setTitle]     = useState("");
  const [priority,  setPriority]  = useState("P2");
  const [status,    setStatus]    = useState("draft");
  const [tagsText,  setTagsText]  = useState("");

  useEffect(() => {
    if (!tc) return;
    setTitle(tc.title ?? "");
    setPriority(tc.priority ?? "P2");
    setStatus(tc.status ?? "draft");
    setTagsText((tc.tags ?? []).join(", "));
    setEditing(false);
  }, [tc?.id]);

  const save = async () => {
    if (!tc) return;
    await update.mutateAsync({
      caseId: tc.id,
      title:    title.trim() || tc.title,
      priority,
      status,
      tags: tagsText.split(",").map(t => t.trim()).filter(Boolean),
    });
    setEditing(false);
  };

  const inp = "w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/40 transition-colors";
  const sel = "w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-2.5 py-2 text-[13px] text-slate-300 outline-none focus:border-blue-500/40 transition-colors";

  return (
    <aside className="flex w-[360px] flex-none flex-col border-l border-white/[0.06] bg-[#0d1221] overflow-hidden">

      {/* Header */}
      <div className="flex shrink-0 items-center gap-2 border-b border-white/[0.06] px-4 py-2.5">
        {tc && <span className="font-mono text-[10px] text-slate-600">{tc.case_key}</span>}
        <span className="flex-1 truncate text-[12px] font-medium text-slate-400">
          {isLoading ? "Yükleniyor…" : tc ? "Detay" : "—"}
        </span>
        <div className="flex items-center gap-0.5">
          {tc && (
            <>
              <button type="button" onClick={() => setEditing(v => !v)}
                title={editing ? "Görüntüle" : "Düzenle"}
                className={cn("rounded-md p-1.5 transition-colors",
                  editing ? "bg-blue-500/10 text-blue-400" : "text-slate-600 hover:bg-white/[0.05] hover:text-slate-300")}>
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                </svg>
              </button>
              <Link href={`/p/${projectId}/management/cases/${caseId}`}
                title="Tam Sayfada Aç"
                className="rounded-md p-1.5 text-slate-600 hover:bg-white/[0.05] hover:text-slate-300 transition-colors">
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
              </Link>
            </>
          )}
          <button type="button" onClick={onClose}
            className="rounded-md p-1.5 text-slate-600 hover:bg-white/[0.05] hover:text-slate-300 transition-colors">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[1,2,3,4,5].map(i => (
              <div key={i} className="h-8 rounded-lg bg-slate-800/40 animate-pulse"
                style={{ opacity: Math.max(0.15, 1 - i * 0.18) }}/>
            ))}
          </div>
        ) : !tc ? (
          <div className="flex items-center justify-center p-8">
            <p className="text-[13px] text-slate-600">Senaryo yüklenemedi</p>
          </div>
        ) : editing ? (

          /* ── Edit mode ──────────────────────────────────────────────── */
          <div className="p-4 space-y-3">
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Başlık</label>
              <input value={title} onChange={e => setTitle(e.target.value)} className={inp}/>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Priority</label>
                <select value={priority} onChange={e => setPriority(e.target.value)} className={sel}>
                  {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Durum</label>
                <select value={status} onChange={e => setStatus(e.target.value)} className={sel}>
                  {["draft","review","active","archived"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Etiketler</label>
              <input value={tagsText} onChange={e => setTagsText(e.target.value)}
                placeholder="smoke, regression, auth…" className={inp}/>
            </div>
            <div className="flex gap-2 pt-1">
              <button type="button" onClick={save} disabled={update.isPending}
                className="flex-1 rounded-xl bg-blue-600 py-2 text-[13px] font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors">
                {update.isPending ? "Kaydediliyor…" : "Kaydet"}
              </button>
              <button type="button" onClick={() => setEditing(false)}
                className="rounded-xl border border-white/[0.08] px-4 py-2 text-[13px] text-slate-500 hover:text-slate-300 transition-colors">
                İptal
              </button>
            </div>
          </div>

        ) : (

          /* ── View mode ──────────────────────────────────────────────── */
          <div className="p-4 space-y-4">

            {/* Title */}
            <h3 className="text-[14px] font-semibold leading-snug text-slate-100">{tc.title}</h3>

            {/* Badges row */}
            <div className="flex flex-wrap gap-1.5">
              <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-medium", P_BADGE[tc.priority] ?? P_BADGE.P2)}>
                {tc.priority}
              </span>
              <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-medium", SB_BADGE[tc.status] ?? SB_BADGE.draft)}>
                {({ active:"Aktif", draft:"Taslak", review:"Review", ready:"Hazır", archived:"Arşiv" } as Record<string,string>)[tc.status] ?? tc.status}
              </span>
              <span className="rounded-full border border-white/[0.06] px-2 py-0.5 text-[11px] text-slate-500">{tc.type}</span>
              {tc.severity && (
                <span className="rounded-full border border-white/[0.06] px-2 py-0.5 text-[11px] text-slate-600">{tc.severity}</span>
              )}
              {tc.automation_status && tc.automation_status !== "manual" && (
                <span className="rounded-full border border-purple-500/20 bg-purple-500/5 px-2 py-0.5 text-[11px] text-purple-400/80">
                  {tc.automation_status}
                </span>
              )}
            </div>

            {/* Tags */}
            {tc.tags && tc.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tc.tags.map(tag => (
                  <span key={tag} className="rounded-md bg-white/[0.04] px-2 py-0.5 text-[11px] text-slate-500">{tag}</span>
                ))}
              </div>
            )}

            {/* Meta grid */}
            <div className="grid grid-cols-2 gap-y-3 rounded-xl border border-white/[0.06] bg-white/[0.01] px-4 py-3 text-[12px]">
              {([
                ["Son Koşum", tc.last_run_status ?? "—"],
                ["Adım Sayısı", String(tc.steps?.length ?? 0)],
                ["Versiyon", `v${tc.current_version}`],
                ["Otomasyon", tc.automation_status],
              ] as [string, string][]).map(([k, v]) => (
                <div key={k}>
                  <p className="text-slate-600">{k}</p>
                  <p className="mt-0.5 text-slate-300">{v}</p>
                </div>
              ))}
            </div>

            {/* Objective */}
            {tc.objective && (
              <div>
                <p className="mb-1.5 text-[10px] uppercase tracking-widest text-slate-600">Amaç</p>
                <p className="text-[12px] leading-relaxed text-slate-400">{tc.objective}</p>
              </div>
            )}

            {/* Preconditions */}
            {tc.preconditions && (
              <div>
                <p className="mb-1.5 text-[10px] uppercase tracking-widest text-slate-600">Ön Koşullar</p>
                <p className="text-[12px] leading-relaxed text-slate-400">{tc.preconditions}</p>
              </div>
            )}

            {/* Steps */}
            {tc.steps && tc.steps.length > 0 && (
              <div>
                <p className="mb-2 text-[10px] uppercase tracking-widest text-slate-600">
                  Test Adımları
                  <span className="ml-1 text-slate-700 normal-case">({tc.steps.length})</span>
                </p>
                <div className="space-y-1.5">
                  {tc.steps.map((s, i) => (
                    <div key={s.id ?? i} className="rounded-xl border border-white/[0.05] bg-white/[0.02] p-3">
                      <div className="flex items-start gap-2.5">
                        <span className="mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full bg-white/[0.07] font-mono text-[10px] font-bold text-slate-600">
                          {s.step_no}
                        </span>
                        <div className="flex-1 min-w-0 space-y-1">
                          <p className="text-[12px] leading-relaxed text-slate-200">{s.action}</p>
                          {s.expected_result && (
                            <p className="text-[11px] leading-relaxed text-slate-500">
                              <span className="text-slate-700">→ </span>{s.expected_result}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Archive */}
            <div className="border-t border-white/[0.06] pt-3">
              <button type="button" disabled={archive.isPending}
                onClick={async () => { await archive.mutateAsync(tc.id); onClose(); }}
                className="w-full rounded-xl border border-red-500/[0.15] py-2 text-[12px] text-red-500/60 hover:bg-red-500/[0.05] hover:text-red-400 disabled:opacity-40 transition-colors">
                {archive.isPending ? "Arşivleniyor…" : "Arşivle"}
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RepositoryPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid = useManagementProjectId(projectId || undefined);
  const repoQ = useManagementRepository(mpid||undefined);
  const moveCase = useMoveManagementCase(mpid || "");

  const suites  = repoQ.data?.suites  ?? [];
  const folders = repoQ.data?.folders ?? [];
  const all     = repoQ.data?.cases   ?? [];

  const [node,        setNode]        = useState<Node>({ type: "all" });
  const [selId,       setSelId]       = useState<string|null>(null);
  const [checked,     setChecked]     = useState<Set<string>>(new Set());
  const [showModal,   setShowModal]   = useState(false);
  const [search,      setSearch]      = useState("");
  const [statusF,     setStatusF]     = useState("");
  const [priorityF,   setPriorityF]   = useState("");
  const [typeF,       setTypeF]       = useState("");
  const [draggingId,  setDraggingId]  = useState<string|null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor,{activationConstraint:{distance:8}}),
    useSensor(KeyboardSensor,{coordinateGetter:sortableKeyboardCoordinates}),
  );

  const active = all.filter(c => !c.archived);

  const nodeCases = useMemo(() => {
    switch (node.type) {
      case "suite":  return active.filter(c => c.suite_id === node.id);
      case "folder": return active.filter(c => c.folder_id === node.id);
      default:       return active;
    }
  }, [active, node]);

  const filtered = useMemo(() => {
    let r = nodeCases;
    const q = search.trim().toLowerCase();
    if (q) r = r.filter(c => c.title.toLowerCase().includes(q) || c.case_key.toLowerCase().includes(q));
    if (statusF)   r = r.filter(c => c.status === statusF);
    if (priorityF) r = r.filter(c => c.priority === priorityF);
    if (typeF)     r = r.filter(c => c.type === typeF);
    return r;
  }, [nodeCases, search, statusF, priorityF, typeF]);

  const allChecked = filtered.length > 0 && filtered.every(c => checked.has(c.id));
  const hasFilter  = !!(search || statusF || priorityF || typeF);
  const loading    = repoQ.isLoading;

  const nodeName = node.type==="all" ? "Tüm Senaryolar"
                 : node.type==="suite"  ? (suites.find(s=>s.id===node.id)?.name ?? "Suite")
                 : (folders.find(f=>f.id===node.id)?.name ?? "Folder");

  const SEL = "rounded-xl border border-white/[0.08] bg-white/[0.04] px-2.5 py-1.5 text-[11px] text-slate-400 outline-none focus:border-blue-500/30 transition-colors";

  return (
    <div className="flex h-full">

      {/* Left tree */}
      <aside className="hidden w-[200px] flex-none md:block overflow-hidden">
        <LeftTree suites={suites} folders={folders} cases={active}
          node={node} onNode={setNode} projectId={projectId} pid={mpid || "" || ""}/>
      </aside>

      {/* Center */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.06] bg-[#0d1221] px-4 py-2.5">
          <span className="text-[13px] font-medium text-slate-400 mr-1">{nodeName}</span>
          {filtered.length > 0 && <span className="rounded-full bg-white/[0.06] px-2 py-0.5 text-[10px] text-slate-500 tabular-nums">{filtered.length}</span>}
          <div className="flex-1"/>
          {/* Search */}
          <div className="flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.04] px-2.5 py-1.5 w-44">
            <IcSearch/><input type="text" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Ara…"
              className="flex-1 bg-transparent text-[11px] text-slate-300 placeholder-slate-600 outline-none min-w-0"/>
          </div>
          <select value={statusF} onChange={e=>setStatusF(e.target.value)} className={SEL}>
            <option value="">Durum</option><option value="active">Aktif</option>
            <option value="draft">Taslak</option><option value="review">Review</option>
          </select>
          <select value={priorityF} onChange={e=>setPriorityF(e.target.value)} className={SEL}>
            <option value="">Priority</option>
            {["P0","P1","P2","P3"].map(v=><option key={v} value={v}>{v}</option>)}
          </select>
          <select value={typeF} onChange={e=>setTypeF(e.target.value)} className={cn(SEL,"hidden lg:block")}>
            <option value="">Tür</option>
            {TYPE_OPTIONS.map(v=><option key={v} value={v}>{v}</option>)}
          </select>
          {hasFilter && <button type="button" onClick={()=>{setSearch("");setStatusF("");setPriorityF("");setTypeF("");}}
            className="text-[11px] text-red-500/70 hover:text-red-400 transition-colors">✕ Temizle</button>}
          <button type="button" onClick={()=>setShowModal(true)}
            className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-1.5 text-[13px] font-medium text-white hover:bg-blue-500 transition-colors">
            <IcPlus/> Yeni Senaryo
          </button>
        </div>

        {/* Bulk bar */}
        {checked.size > 0 && (
          <div className="flex items-center gap-2 border-b border-white/[0.06] bg-blue-500/[0.06] px-4 py-1.5">
            <span className="text-[12px] font-medium text-blue-400">{checked.size} seçili</span>
            {["Aktife Al","Arşivle","Regresyon Seti","Taşı","Sil"].map(l=>(
              <button key={l} type="button"
                className={cn("rounded-lg border px-2.5 py-1 text-[11px] transition-colors",
                  l==="Sil"?"border-red-500/20 text-red-400 hover:bg-red-500/10":"border-white/[0.08] text-slate-400 hover:text-slate-200")}>
                {l}
              </button>
            ))}
            <button type="button" onClick={()=>setChecked(new Set())} className="ml-auto text-[11px] text-slate-600 hover:text-slate-400">Temizle</button>
          </div>
        )}

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div>{Array.from({length:8}).map((_,i)=>(
              <div key={i} className="flex items-center gap-3 border-b border-white/[0.04] px-4 py-3">
                <div className="h-4 w-4 shrink-0 rounded bg-slate-800 animate-pulse"/>
                <div className="h-3 w-16 rounded bg-slate-800 animate-pulse"/>
                <div className="h-3 flex-1 max-w-sm rounded bg-slate-800 animate-pulse"/>
                <div className="h-4 w-8 rounded bg-slate-800 animate-pulse"/>
              </div>
            ))}</div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24">
              {hasFilter ? (
                <><p className="text-[14px] text-slate-500">Sonuç bulunamadı</p>
                <button type="button" onClick={()=>{setSearch("");setStatusF("");setPriorityF("");setTypeF("");}}
                  className="mt-3 text-[12px] text-slate-600 hover:text-slate-400 transition-colors">Filtreleri temizle</button></>
              ) : (
                <><p className="text-[14px] text-slate-500">Henüz senaryo yok</p>
                <button type="button" onClick={()=>setShowModal(true)}
                  className="mt-3 flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-[13px] font-medium text-white hover:bg-blue-500 transition-colors">
                  <IcPlus/> İlk senaryoyu oluştur
                </button></>
              )}
            </div>
          ) : (
            <DndContext sensors={sensors} collisionDetection={closestCenter}
              onDragStart={e=>setDraggingId(String(e.active.id))}
              onDragEnd={()=>setDraggingId(null)}>
              <table className="w-full">
                <thead className="sticky top-0 z-10 bg-[#0a0f1e]/95 backdrop-blur-sm">
                  <tr className="border-b border-white/[0.06]">
                    <th className="hidden w-5 sm:table-cell"/>
                    <th className="w-8 px-2 py-2.5">
                      <button type="button" onClick={()=>allChecked?setChecked(new Set()):setChecked(new Set(filtered.map(c=>c.id)))}
                        className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
                          allChecked?"bg-blue-600 border-blue-600":"border-slate-700 hover:border-slate-500")}>
                        {allChecked&&<svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5"/></svg>}
                      </button>
                    </th>
                    {["ID","Başlık","P","Tür","Durum","Son Koşum","Adım","Tarih",""].map(h=>(
                      <th key={h} className={cn("px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-widest text-slate-700",
                        h==="Tür"&&"hidden lg:table-cell", h==="Durum"&&"hidden md:table-cell",
                        h==="Son Koşum"&&"hidden lg:table-cell", h==="Adım"&&"hidden xl:table-cell",
                        h==="Tarih"&&"hidden xl:table-cell")}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <SortableContext items={filtered.map(c=>c.id)} strategy={verticalListSortingStrategy}>
                  <tbody>
                    {filtered.map(tc=>(
                      <CaseRow key={tc.id} tc={tc}
                        selected={selId===tc.id}
                        onSelect={()=>setSelId(selId===tc.id?null:tc.id)}
                        checked={checked.has(tc.id)}
                        onCheck={e=>{e.stopPropagation();setChecked(p=>{const n=new Set(p);n.has(tc.id)?n.delete(tc.id):n.add(tc.id);return n;})}}
                        projectId={projectId}/>
                    ))}
                  </tbody>
                </SortableContext>
              </table>
              <DragOverlay>
                {draggingId && (()=>{const tc=filtered.find(c=>c.id===draggingId);return tc?(
                  <div className="flex items-center gap-3 rounded-xl border border-blue-500/30 bg-[#0d1221] px-4 py-2.5 shadow-2xl shadow-black/50">
                    <span className="font-mono text-[10px] text-slate-500">{tc.case_key}</span>
                    <span className="text-[13px] text-slate-300 truncate max-w-xs">{tc.title}</span>
                  </div>
                ):null;})()}
              </DragOverlay>
            </DndContext>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-white/[0.06] bg-[#0d1221] px-4 py-1.5">
          <span className="text-[10px] text-slate-700">
            {hasFilter?`${filtered.length} / ${nodeCases.length}`:`${filtered.length} senaryo`}
          </span>
          <span className="text-[10px] text-slate-700">{suites.length} suite · {folders.length} folder</span>
        </div>
      </div>

      {/* Case Detail Drawer */}
      {selId && (
        <CaseDetailDrawer
          caseId={selId}
          pid={mpid || ""}
          projectId={projectId}
          onClose={() => setSelId(null)}
        />
      )}

      {/* New Case Modal */}
      {showModal && (
        <NewCaseModal pid={mpid || ""} suites={suites} folders={folders}
          defSuiteId={node.type==="suite"?node.id:node.type==="folder"?node.suiteId:undefined}
          defFolderId={node.type==="folder"?node.id:undefined}
          onClose={()=>setShowModal(false)}
          onDone={tc=>{setShowModal(false);setSelId(tc.id);}}/>
      )}
    </div>
  );
}
