"use client";

import React, { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  DndContext, PointerSensor, KeyboardSensor,
  useSensor, useSensors, closestCenter,
} from "@dnd-kit/core";
import {
  SortableContext, sortableKeyboardCoordinates,
  verticalListSortingStrategy, useSortable, arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  useCreateManagementCase,
  useGenerateTestCases,
  type GeneratedCase,
  type TestCase, type TestFolder, type TestSuite,
} from "@/lib/hooks/use-management";
import { IcClose, IcPlus, TYPE_OPTIONS } from "./shared";

type DraftStep = { id: string; action: string; expected_result: string; test_data: string; is_required: boolean };

function step(o?: Partial<DraftStep>): DraftStep {
  return { id: `s${Math.random().toString(36).slice(2, 7)}`, action: "", expected_result: "", test_data: "", is_required: true, ...o };
}

function IcSparkle() {
  return (
    <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
    </svg>
  );
}

function IcChevronRight() {
  return (
    <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

function SortableStepItem({ s, index, onUpdate, onRemove }: {
  s: DraftStep; index: number;
  onUpdate: (patch: Partial<DraftStep>) => void;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: s.id });
  return (
    <div ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.35 : 1 }}
      className="rounded-xl border border-border bg-surface-raised p-3 shadow-xs">
      <div className="mb-2 flex items-center gap-2">
        <button type="button" {...attributes} {...listeners}
          className="flex h-5 w-5 shrink-0 cursor-grab touch-none items-center justify-center rounded-full border border-border bg-surface-overlay font-mono text-[10px] font-bold text-fg-muted active:cursor-grabbing">
          {index + 1}
        </button>
        <label className="ml-auto flex items-center gap-1.5 text-[10px] text-fg-subtle">
          <input type="checkbox" checked={s.is_required} onChange={e => onUpdate({ is_required: e.target.checked })} className="h-3 w-3 accent-blue-600" />
          Zorunlu
        </label>
        <button type="button" onClick={onRemove} className="text-fg-subtle transition-colors hover:text-danger"><IcClose /></button>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <textarea value={s.action} onChange={e => onUpdate({ action: e.target.value })}
          placeholder="Aksiyon…" rows={2} className="resize-none rounded-lg border border-border bg-surface-raised px-3 py-2 text-[12px] text-fg placeholder:text-fg-subtle outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15" />
        <textarea value={s.expected_result} onChange={e => onUpdate({ expected_result: e.target.value })}
          placeholder="Beklenen sonuç…" rows={2} className="resize-none rounded-lg border border-border bg-surface-raised px-3 py-2 text-[12px] text-fg placeholder:text-fg-subtle outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15" />
      </div>
    </div>
  );
}

// ─── AI Panel ─────────────────────────────────────────────────────────────────

function AIGeneratePanel({
  pid, suiteId, folderId,
  onApply, onClose,
}: {
  pid: string; suiteId: string; folderId: string;
  onApply: (gc: GeneratedCase) => void;
  onClose: () => void;
}) {
  const [prompt,  setPrompt]  = useState("");
  const [count,   setCount]   = useState(3);
  const [results, setResults] = useState<GeneratedCase[]>([]);
  const [saving,  setSaving]  = useState<string | null>(null);
  const generate  = useGenerateTestCases(pid);
  const createCase = useCreateManagementCase(pid);

  const run = async () => {
    if (!prompt.trim()) return;
    const res = await generate.mutateAsync({
      prompt: prompt.trim(),
      count,
      suite_id: suiteId || null,
      folder_id: folderId || null,
      save: false,
    });
    setResults(res.cases);
  };

  const saveOne = async (gc: GeneratedCase) => {
    setSaving(gc.title);
    try {
      const tc = await createCase.mutateAsync({
        title: gc.title,
        objective: gc.objective,
        suite_id: suiteId || null,
        folder_id: folderId || null,
        priority: gc.priority,
        type: "manual",
        status: "draft",
        source_type: "ai_generated",
        tags: gc.tags,
        steps: gc.steps.map(s => ({
          step_no: s.step_no,
          action: s.action,
          expected_result: s.expected_result,
          test_data: {},
          is_required: s.is_required,
        })),
      });
      onApply({ ...gc, saved_id: tc.id });
    } finally {
      setSaving(null);
    }
  };

  const applyToForm = (gc: GeneratedCase) => onApply(gc);

  return (
    <div className="flex h-full flex-col gap-3 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <IcSparkle />
          <span className="text-[13px] font-semibold text-fg">AI ile Test Üret</span>
        </div>
        <button type="button" onClick={onClose} className="rounded-lg p-1 text-fg-subtle hover:bg-surface-overlay hover:text-fg">
          <IcClose />
        </button>
      </div>

      <textarea
        autoFocus
        value={prompt}
        onChange={e => setPrompt(e.target.value)}
        rows={3}
        placeholder="Ne test etmek istiyorsunuz? (ör: Kullanıcı giriş formu, şifre sıfırlama akışı, kredi kartı ödeme sayfası…)"
        className="resize-none rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15"
      />

      <div className="flex items-center gap-3">
        <label className="text-[11px] text-fg-subtle">Senaryo sayısı:</label>
        {[1, 3, 5, 10].map(n => (
          <button key={n} type="button" onClick={() => setCount(n)}
            className={cn("rounded-lg border px-2 py-1 text-[11px] font-medium transition-colors",
              count === n
                ? "border-brand bg-brand-soft text-brand"
                : "border-border text-fg-muted hover:border-border-strong")}>
            {n}
          </button>
        ))}
        <button type="button" onClick={run} disabled={!prompt.trim() || generate.isPending}
          className="ml-auto flex items-center gap-1.5 rounded-xl bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105 disabled:opacity-40">
          {generate.isPending ? (
            <>
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-brand-fg border-t-transparent" />
              Üretiliyor…
            </>
          ) : (
            <><IcSparkle /> Üret</>
          )}
        </button>
      </div>

      {results.length > 0 && (
        <div className="flex-1 overflow-y-auto space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">{results.length} senaryo üretildi</p>
          {results.map((gc, i) => (
            <div key={i} className="rounded-xl border border-border bg-surface-overlay p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium text-fg leading-snug">{gc.title}</p>
                  {gc.objective && <p className="mt-0.5 text-[11px] text-fg-muted line-clamp-2">{gc.objective}</p>}
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    <span className="rounded bg-surface-accent px-1.5 py-0.5 text-[10px] text-fg-subtle">{gc.priority}</span>
                    {gc.tags.slice(0, 3).map(t => (
                      <span key={t} className="rounded bg-surface-accent px-1.5 py-0.5 text-[10px] text-fg-subtle">{t}</span>
                    ))}
                    <span className="text-[10px] text-fg-subtle">{gc.steps.length} adım</span>
                  </div>
                </div>
                <div className="flex shrink-0 flex-col gap-1">
                  <button type="button" onClick={() => applyToForm(gc)}
                    className="flex items-center gap-1 rounded-lg border border-brand/30 bg-brand-soft px-2 py-1 text-[11px] text-brand transition-colors hover:bg-brand/15">
                    <IcChevronRight /> Forma uygula
                  </button>
                  <button type="button" onClick={() => saveOne(gc)} disabled={saving === gc.title}
                    className="flex items-center gap-1 rounded-lg bg-brand px-2 py-1 text-[11px] font-semibold text-brand-fg transition-colors hover:brightness-105 disabled:opacity-40">
                    {saving === gc.title ? "Kaydediliyor…" : "Kaydet"}
                  </button>
                </div>
              </div>
              {gc.steps.length > 0 && (
                <div className="mt-2 space-y-1 border-t border-border pt-2">
                  {gc.steps.slice(0, 3).map(s => (
                    <div key={s.step_no} className="flex items-start gap-2 text-[11px]">
                      <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-surface-accent font-mono text-[9px] text-fg-subtle">{s.step_no}</span>
                      <span className="text-fg-muted line-clamp-1">{s.action}</span>
                    </div>
                  ))}
                  {gc.steps.length > 3 && <p className="text-[10px] text-fg-subtle">+{gc.steps.length - 3} adım daha</p>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {generate.isError && (
        <p className="rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-[12px] text-red-400">
          Üretim başarısız. LLM sunucusunun çalıştığını kontrol edin.
        </p>
      )}
    </div>
  );
}

// ─── Main Modal ───────────────────────────────────────────────────────────────

export function NewCaseModal({ pid, suites, folders, defSuiteId, defFolderId, onClose, onDone }: {
  pid: string; suites: TestSuite[]; folders: TestFolder[];
  defSuiteId?: string; defFolderId?: string;
  onClose: () => void; onDone: (tc: TestCase) => void;
}) {
  const createCase = useCreateManagementCase(pid);
  const [title,    setTitle]    = useState("");
  const [obj,      setObj]      = useState("");
  const [pre,      setPre]      = useState("");
  const [suiteId,  setSuiteId]  = useState(defSuiteId ?? "");
  const [folderId, setFolderId] = useState(defFolderId ?? "");
  const [priority, setPriority] = useState("P1");
  const [severity, setSeverity] = useState("major");
  const [type,     setType]     = useState("manual");
  const [status,   setStatus]   = useState("draft");
  const [tagsText, setTagsText] = useState("");
  const [steps,    setSteps]    = useState<DraftStep[]>([step(), step()]);
  const [err,      setErr]      = useState("");
  const [showAI,   setShowAI]   = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

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
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last?.focus(); }
      } else {
        if (document.activeElement === last)  { e.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const avFolders = folders.filter(f => !suiteId || f.suite_id === suiteId);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const applyGenerated = (gc: GeneratedCase) => {
    if (!title) setTitle(gc.title);
    if (!obj)   setObj(gc.objective);
    setPriority(gc.priority);
    if (gc.tags.length) setTagsText(gc.tags.join(", "));
    if (gc.steps.length) {
      setSteps(gc.steps.map(s => step({
        action: s.action, expected_result: s.expected_result, is_required: s.is_required,
      })));
    }
    setShowAI(false);
  };

  const save = async () => {
    if (!title.trim()) { setErr("Başlık zorunlu."); return; }
    setErr("");
    try {
      const tc = await createCase.mutateAsync({
        title: title.trim(), objective: obj.trim() || null, preconditions: pre.trim() || null,
        suite_id: suiteId || null, folder_id: folderId || null,
        priority, severity, type, status, source_type: "manual",
        tags: tagsText.split(",").map(t => t.trim()).filter(Boolean),
        steps: steps.filter(s => s.action.trim() || s.expected_result.trim()).map((s, i) => ({
          step_no: i + 1, action: s.action.trim(), expected_result: s.expected_result.trim(),
          test_data: s.test_data.trim() ? { value: s.test_data.trim() } : {}, is_required: s.is_required,
        })),
      });
      onDone(tc);
    } catch { setErr("Kaydedilemedi."); }
  };

  const inp = "w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";
  const sel = "rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg-muted outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";

  return (
    <div className="fixed inset-0 z-modal flex items-start justify-center overflow-y-auto p-8 bg-black/60 backdrop-blur-sm">
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-case-modal-title"
        className={cn("relative w-full rounded-xl border border-border bg-surface-raised shadow-2xl transition-all",
          showAI ? "flex max-w-4xl gap-0" : "max-w-2xl")}>

        {/* ── AI Panel (sol) ─────────────────────────────────────────────── */}
        {showAI && (
          <div className="flex w-96 shrink-0 flex-col border-r border-border bg-surface-overlay">
            <AIGeneratePanel
              pid={pid} suiteId={suiteId} folderId={folderId}
              onApply={applyGenerated}
              onClose={() => setShowAI(false)}
            />
          </div>
        )}

        {/* ── Form (sağ) ─────────────────────────────────────────────────── */}
        <div className="flex flex-1 min-w-0 flex-col">
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h2 id="new-case-modal-title" className="text-[15px] font-semibold text-fg">Yeni Test Senaryosu</h2>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => setShowAI(v => !v)}
                className={cn(
                  "flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-[12px] font-medium transition-colors",
                  showAI
                    ? "border-brand bg-brand-soft text-brand"
                    : "border-border text-fg-muted hover:border-brand/50 hover:text-brand",
                )}>
                <IcSparkle /> AI ile Üret
              </button>
              <button type="button" onClick={onClose}
                className="rounded-lg p-1.5 text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg">
                <IcClose />
              </button>
            </div>
          </div>

          <div className="space-y-4 overflow-y-auto px-6 py-5" style={{ maxHeight: "calc(85vh - 130px)" }}>
            <div className="space-y-1">
              <label htmlFor="new-case-title" className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">
                Başlık<span className="text-red-400 ml-0.5">*</span>
              </label>
              <input id="new-case-title" autoFocus type="text" value={title} onChange={e => setTitle(e.target.value)} placeholder="Senaryo başlığı" className={inp} />
            </div>

            <div className="grid grid-cols-4 gap-2">
              <div>
                <label htmlFor="new-case-priority" className="sr-only">Öncelik</label>
                <select id="new-case-priority" value={priority} onChange={e => setPriority(e.target.value)} className={sel}>
                  {["P0", "P1", "P2", "P3"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="new-case-severity" className="sr-only">Önem Derecesi</label>
                <select id="new-case-severity" value={severity} onChange={e => setSeverity(e.target.value)} className={sel}>
                  {["critical", "major", "minor", "trivial"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="new-case-type" className="sr-only">Tür</label>
                <select id="new-case-type" value={type} onChange={e => setType(e.target.value)} className={sel}>
                  {TYPE_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="new-case-status" className="sr-only">Durum</label>
                <select id="new-case-status" value={status} onChange={e => setStatus(e.target.value)} className={sel}>
                  <option value="draft">Taslak</option>
                  <option value="active">Aktif</option>
                  <option value="review">Review</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label htmlFor="new-case-suite" className="sr-only">Suite</label>
                <select id="new-case-suite" value={suiteId} onChange={e => { setSuiteId(e.target.value); setFolderId(""); }} className={sel}>
                  <option value="">Suite seç</option>
                  {suites.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="new-case-folder" className="sr-only">Folder</label>
                <select id="new-case-folder" value={folderId} onChange={e => setFolderId(e.target.value)} className={sel}>
                  <option value="">Folder seç</option>
                  {avFolders.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="new-case-obj" className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Amaç</label>
                <textarea id="new-case-obj" value={obj} onChange={e => setObj(e.target.value)} rows={2} placeholder="Bu senaryonun amacı…" className={cn(inp, "resize-none")} />
              </div>
              <div>
                <label htmlFor="new-case-pre" className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Ön Koşullar</label>
                <textarea id="new-case-pre" value={pre} onChange={e => setPre(e.target.value)} rows={2} placeholder="Başlamak için…" className={cn(inp, "resize-none")} />
              </div>
            </div>

            <div>
              <label htmlFor="new-case-tags" className="sr-only">Etiketler</label>
              <input id="new-case-tags" type="text" value={tagsText} onChange={e => setTagsText(e.target.value)} placeholder="smoke, regression, login…" className={inp} />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Test Adımları</label>
                <button type="button" onClick={() => setSteps(s => [...s, step()])}
                  className="flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-[11px] text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg">
                  <IcPlus /> Adım
                </button>
              </div>
              <DndContext sensors={sensors} collisionDetection={closestCenter}
                onDragEnd={e => {
                  const { active, over } = e; if (!over || active.id === over.id) return;
                  setSteps(c => { const oi = c.findIndex(s => s.id === active.id), ni = c.findIndex(s => s.id === over.id); return arrayMove(c, oi, ni); });
                }}>
                <SortableContext items={steps.map(s => s.id)} strategy={verticalListSortingStrategy}>
                  <div className="space-y-2">
                    {steps.map((s, i) => (
                      <SortableStepItem key={s.id} s={s} index={i}
                        onUpdate={patch => setSteps(c => c.map(x => x.id === s.id ? { ...x, ...patch } : x))}
                        onRemove={() => setSteps(c => c.length > 1 ? c.filter(x => x.id !== s.id) : c)}
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>
            </div>

            {err && <p className="text-[12px] text-red-400">{err}</p>}
          </div>

          <div className="flex items-center justify-between border-t border-border px-6 py-4">
            <button type="button" onClick={onClose}
              className="rounded-xl border border-border px-4 py-2 text-[13px] font-medium text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg">
              İptal
            </button>
            <button type="button" onClick={save} disabled={!title.trim() || createCase.isPending}
              className="rounded-xl bg-brand px-5 py-2 text-[13px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105 disabled:opacity-40">
              {createCase.isPending ? "Kaydediliyor…" : "Kaydet"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
