"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  useManagementCase,
  useManagementCaseVersions,
  useUpdateManagementCase,
  useSubCases,
  useCreateSubCase,
  useCaseDependencies,
  useAddCaseDependency,
  useRemoveCaseDependency,
  useManagementCases,
  type TestCaseStep,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { CommentThread } from "../../_components/CommentThread";
import { SharedStepPicker } from "../../_components/SharedStepPicker";

function SortableStepCard({ id, children }: { id: string; children: React.ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <div className="flex items-start gap-2">
        <button {...listeners} className="mt-1 cursor-grab text-slate-600 hover:text-slate-400 p-1" title="Sürükle" type="button">
          ⠿
        </button>
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}

const PRIORITY_OPTIONS = ["P0", "P1", "P2", "P3"];
const SEVERITY_OPTIONS = ["blocker", "critical", "major", "minor", "trivial"];
const TYPE_OPTIONS = ["manual", "exploratory", "regression", "smoke", "uat"];
const STATUS_OPTIONS = ["draft", "ready", "active", "archived"];

type DraftStep = { id: string; step_no: number; action: string; expected_result: string; test_data: string; is_required: boolean; notes: string };

function makeStep(no: number): DraftStep {
  return { id: crypto.randomUUID(), step_no: no, action: "", expected_result: "", test_data: "", is_required: true, notes: "" };
}

export default function ManagementCaseDetailPage() {
  const projectId = useRouteParam("projectId");
  const caseId    = useRouteParam("caseId");

  const mpid = useManagementProjectId(projectId || undefined);

  const { data: tc, isLoading } = useManagementCase(mpid || undefined, caseId || undefined);
  const { data: versions }      = useManagementCaseVersions(mpid || undefined, caseId || undefined);
  const { data: subCases = [] } = useSubCases(mpid || undefined, caseId || undefined);
  const { data: dependencies = [] } = useCaseDependencies(mpid || undefined, caseId || undefined);
  const { data: allCases = [] } = useManagementCases(mpid || undefined);
  const update                  = useUpdateManagementCase(mpid || "");
  const createSubCase           = useCreateSubCase(mpid || "");
  const addDependency           = useAddCaseDependency(mpid || "");
  const removeDependency        = useRemoveCaseDependency(mpid || "");

  const [title, setTitle]             = useState("");
  const [objective, setObjective]     = useState("");
  const [preconditions, setPreconditions] = useState("");
  const [priority, setPriority]       = useState("P1");
  const [severity, setSeverity]       = useState("major");
  const [type, setType]               = useState("manual");
  const [status, setStatus]           = useState("draft");
  const [tags, setTags]               = useState("");
  const [steps, setSteps]             = useState<DraftStep[]>([makeStep(1)]);
  const [customComponent, setCustomComponent] = useState("");
  const [customPlatform,  setCustomPlatform]  = useState("");
  const [customRiskArea,  setCustomRiskArea]  = useState("");
  const [dirty, setDirty]             = useState(false);
  const [saving, setSaving]           = useState(false);
  const [saveError, setSaveError]     = useState("");
  const [titleError, setTitleError]   = useState<string|null>(null);
  const [activeTab, setActiveTab]     = useState<"edit" | "comments" | "history">("edit");
  const [revertMsg, setRevertMsg]     = useState("");
  const [showStepPicker, setShowStepPicker] = useState(false);
  const [depKeyInput, setDepKeyInput] = useState("");
  const [depTypeInput, setDepTypeInput] = useState<"blocks" | "related">("blocks");
  const [depAddError, setDepAddError] = useState("");

  useEffect(() => {
    if (!tc) return;
    setTitle(tc.title ?? "");
    setObjective(tc.objective ?? "");
    setPreconditions(tc.preconditions ?? "");
    setPriority(tc.priority ?? "P1");
    setSeverity(tc.severity ?? "major");
    setType(tc.type ?? "manual");
    setStatus(tc.status ?? "draft");
    setTags((tc.tags ?? []).join(", "));
    const cf = tc.custom_fields ?? {};
    setCustomComponent((cf.component as string) ?? "");
    setCustomPlatform((cf.platform as string) ?? "");
    setCustomRiskArea((cf.risk_area as string) ?? "");
    setSteps(
      tc.steps && tc.steps.length > 0
        ? tc.steps.map((s: TestCaseStep) => ({
            id: s.id ?? crypto.randomUUID(),
            step_no: s.step_no,
            action: s.action,
            expected_result: s.expected_result,
            test_data: typeof s.test_data === "string" ? s.test_data : JSON.stringify(s.test_data ?? {}),
            is_required: (s as unknown as { is_required?: boolean }).is_required ?? true,
            notes: (s as unknown as { notes?: string }).notes ?? "",
          }))
        : [makeStep(1)]
    );
  }, [tc]);

  const markDirty = () => setDirty(true);

  const handleSave = async () => {
    if (!dirty) return;
    if (!caseId || !mpid) return;
    if (!title || title.trim().length === 0) {
      setTitleError("Başlık boş bırakılamaz")
      return
    }
    if (title.trim().length > 500) {
      setTitleError("Başlık en fazla 500 karakter olabilir")
      return
    }
    setTitleError(null)
    setSaveError("");
    setSaving(true);
    try {
      await update.mutateAsync({
        caseId,
        title,
        objective: objective || null,
        preconditions: preconditions || null,
        priority,
        severity,
        type,
        status,
        tags: tags.split(",").map(t => t.trim()).filter(Boolean),
        custom_fields: {
          ...(customComponent.trim() ? { component: customComponent.trim() } : {}),
          ...(customPlatform.trim()  ? { platform: customPlatform.trim() }   : {}),
          ...(customRiskArea.trim()  ? { risk_area: customRiskArea.trim() }  : {}),
        },
        steps: steps.map((s, idx) => ({
          step_no: idx + 1,
          action: s.action,
          expected_result: s.expected_result,
          test_data: {},
          notes: s.notes ?? "",
          is_required: s.is_required ?? true,
        })),
      });
      setDirty(false);
    } catch {
      setSaveError("Kayıt başarısız. Lütfen tekrar deneyin.");
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const handleRevert = (snapshot: Record<string, unknown>) => {
    setTitle((snapshot.title as string) ?? "");
    setObjective((snapshot.objective as string) ?? "");
    setPreconditions((snapshot.preconditions as string) ?? "");
    setPriority((snapshot.priority as string) ?? "P1");
    setSeverity((snapshot.severity as string) ?? "major");
    setType((snapshot.type as string) ?? "manual");
    setStatus((snapshot.status as string) ?? "draft");
    setTags(Array.isArray(snapshot.tags) ? (snapshot.tags as string[]).join(", ") : "");
    const rawSteps = snapshot.steps as TestCaseStep[] | undefined;
    setSteps(
      rawSteps && rawSteps.length > 0
        ? rawSteps.map((s: TestCaseStep) => ({
            id: s.id ?? crypto.randomUUID(),
            step_no: s.step_no,
            action: s.action,
            expected_result: s.expected_result,
            test_data: typeof s.test_data === "string" ? s.test_data : JSON.stringify(s.test_data ?? {}),
            is_required: (s as unknown as { is_required?: boolean }).is_required ?? true,
            notes: (s as unknown as { notes?: string }).notes ?? "",
          }))
        : [makeStep(1)]
    );
    setDirty(true);
    setActiveTab("edit");
    setRevertMsg("Geri alındı, kaydetmeyi unutma!");
    setTimeout(() => setRevertMsg(""), 3500);
  };

  const addStep = () => {
    setSteps(prev => [...prev, makeStep(prev.length + 1)]);
    markDirty();
  };

  const updateStep = (idx: number, field: keyof DraftStep, value: string) => {
    setSteps(prev => prev.map((s, i) => i === idx ? { ...s, [field]: value } : s));
    markDirty();
  };

  const removeStep = (idx: number) => {
    setSteps(prev => prev.filter((_, i) => i !== idx).map((s, i) => ({ ...s, step_no: i + 1 })));
    markDirty();
  };

  const insertSharedSteps = (sharedItems: import("@/lib/hooks/use-management").SharedStepItem[]) => {
    const newSteps: DraftStep[] = sharedItems.map((s, i) => ({
      id: crypto.randomUUID(),
      step_no: steps.length + i + 1,
      action: s.action,
      expected_result: s.expected_result ?? "",
      test_data: "",
      notes: s.notes ?? "",
      is_required: s.is_required ?? true,
    }));
    setSteps(prev => [...prev, ...newSteps]);
    markDirty();
  };

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      setSteps(prev => {
        const oldIdx = prev.findIndex(s => s.id === active.id);
        const newIdx = prev.findIndex(s => s.id === over!.id);
        return arrayMove(prev, oldIdx, newIdx).map((s, i) => ({ ...s, step_no: i + 1 }));
      });
      markDirty();
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-[calc(100vh-88px)] bg-bg flex items-center justify-center">
        <div className="animate-pulse h-6 w-32 rounded bg-white/[0.04]" />
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-88px)] bg-bg text-slate-200">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-border bg-surface-raised px-6 py-3">
        <div className="flex items-center gap-4">
          <Link
            href={`/p/${projectId}/management/repository`}
            className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
          >
            ← Repository
          </Link>
          {tc && <span className="font-mono text-[11px] text-slate-600">{tc.case_key}</span>}
        </div>
        <div className="flex items-center gap-2">
          {/* Tab switcher */}
          <div className="flex rounded-lg border border-border overflow-hidden">
            {([ ["edit", "Düzenle"], ["comments", "Yorumlar"], ["history", "Geçmiş"] ] as const).map(([tab, label]) => (
              <button key={tab} type="button" onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 text-[11px] font-medium transition-colors ${
                  activeTab === tab ? "bg-brand text-white" : "bg-transparent text-slate-500 hover:text-slate-300"
                }`}>
                {label}
              </button>
            ))}
          </div>
          {activeTab === "edit" && (
            <>
              {revertMsg && (
                <span className="text-[10px] text-amber-400 bg-amber-400/10 rounded px-2 py-1">{revertMsg}</span>
              )}
              {dirty && !revertMsg && <span className="text-[10px] text-slate-600">Kaydedilmemiş</span>}
              <div className="flex flex-col items-end gap-0.5">
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving || !dirty}
                  className="rounded-md bg-brand px-4 py-1.5 text-[11px] font-medium text-white hover:brightness-105 disabled:opacity-40 transition-colors"
                >
                  {saving ? "Kaydediliyor…" : "Kaydet"}
                </button>
                {saveError && <p className="text-[12px] text-red-400 mt-1">{saveError}</p>}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Comments tab */}
      {activeTab === "comments" && caseId && (
        <div className="flex-1 overflow-y-auto p-6 max-w-2xl mx-auto">
          <CommentThread
            entityType="case"
            entityId={caseId}
            projectId={mpid ?? null}
            title="Case Yorumları"
          />
        </div>
      )}

      {/* History tab */}
      {activeTab === "history" && (
        <div className="p-6 max-w-2xl mx-auto">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-600">Versiyon Geçmişi</h2>
          {(versions ?? []).length === 0 ? (
            <p className="text-[13px] text-slate-600">Henüz versiyon geçmişi yok.</p>
          ) : (
            <div className="space-y-2">
              {(versions ?? []).map((v, idx) => {
                const isLatest = idx === 0;
                return (
                  <div key={v.id} className="flex items-start gap-3 rounded-xl border border-border bg-surface-raised px-4 py-3">
                    <span className="flex h-6 w-8 items-center justify-center rounded bg-surface-overlay font-mono text-[10px] font-bold text-slate-400 shrink-0">v{v.version_no}</span>
                    <div className="flex-1 min-w-0">
                      {v.change_summary && <p className="text-[13px] text-slate-300">{v.change_summary}</p>}
                      {v.changed_fields.length > 0 && (
                        <p className="mt-0.5 text-[11px] text-slate-500">{v.changed_fields.join(", ")} güncellendi</p>
                      )}
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-[10px] text-slate-600">
                        {new Date(v.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })}
                      </span>
                      {!isLatest && v.snapshot && (
                        <button
                          type="button"
                          onClick={() => handleRevert(v.snapshot as Record<string, unknown>)}
                          className="rounded-md border border-border bg-white/[0.04] px-2 py-1 text-[10px] text-slate-400 hover:border-teal-500/40 hover:text-teal-400 transition-colors"
                        >
                          ← Geri Al
                        </button>
                      )}
                      {isLatest && (
                        <span className="rounded-md bg-teal-500/10 px-2 py-1 text-[10px] text-teal-500">Mevcut</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Two-column layout (Edit tab) */}
      {activeTab === "edit" && <div className="flex h-[calc(100vh-88px-48px)] overflow-hidden">
        {/* LEFT — editor */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Title */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-slate-600">Başlık</label>
            <input
              value={title}
              onChange={e => { setTitle(e.target.value); markDirty(); if (titleError) setTitleError(null); }}
              onBlur={handleSave}
              maxLength={500}
              className="w-full rounded-md border border-border bg-white/[0.02] px-3 py-2 text-base font-medium text-slate-100 placeholder-slate-600 outline-none focus:border-teal-500/50"
              placeholder="Test case başlığı"
            />
            <div className="flex items-center justify-between mt-1">
              {titleError ? <p className="text-red-400 text-xs">{titleError}</p> : <span />}
              <span className={`text-xs ${title.length >= 480 ? "text-amber-400" : "text-fg-subtle"}`}>{title.length}/500</span>
            </div>
          </div>

          {/* Objective */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-slate-600">Amaç</label>
            <textarea
              rows={2}
              value={objective}
              onChange={e => { setObjective(e.target.value); markDirty(); }}
              onBlur={handleSave}
              maxLength={2000}
              className="w-full resize-none rounded-md border border-border bg-white/[0.02] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
              placeholder="Test'in amacı…"
            />
            <span className={`text-xs ${objective.length >= 1900 ? "text-amber-400" : "text-fg-subtle"}`}>{objective.length}/2000</span>
          </div>

          {/* Preconditions */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-slate-600">Ön Koşullar</label>
            <textarea
              rows={2}
              value={preconditions}
              onChange={e => { setPreconditions(e.target.value); markDirty(); }}
              onBlur={handleSave}
              maxLength={2000}
              className="w-full resize-none rounded-md border border-border bg-white/[0.02] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
              placeholder="Gerekli ön koşullar…"
            />
            <span className={`text-xs ${preconditions.length >= 1900 ? "text-amber-400" : "text-fg-subtle"}`}>{preconditions.length}/2000</span>
          </div>

          {/* Steps */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-[10px] font-medium uppercase tracking-wider text-slate-600">Adımlar</label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowStepPicker(true)}
                  className="flex items-center gap-1 text-[11px] text-brand hover:text-brand-secondary transition-colors"
                >
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                  </svg>
                  Şablondan
                </button>
                <button type="button" onClick={addStep} className="text-[11px] text-teal-500 hover:text-teal-400 transition-colors">
                  + Adım Ekle
                </button>
              </div>
            </div>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={steps.map(s => s.id)} strategy={verticalListSortingStrategy}>
                <div className="space-y-2">
                  {steps.map((step, idx) => (
                    <SortableStepCard key={step.id} id={step.id}>
                      <div className="rounded-md border border-border bg-white/[0.02] p-3">
                        <div className="mb-2 flex items-center justify-between">
                          <span className="text-[10px] text-slate-600">Adım {idx + 1}</span>
                          {steps.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeStep(idx)}
                              className="text-[10px] text-slate-600 hover:text-red-400 transition-colors"
                            >
                              Kaldır
                            </button>
                          )}
                        </div>
                        <div className="space-y-2">
                          <textarea
                            rows={2}
                            placeholder="Aksiyon"
                            value={step.action}
                            onChange={e => updateStep(idx, "action", e.target.value)}
                            className="w-full resize-none rounded border border-border bg-white/[0.02] px-2 py-1.5 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
                          />
                          <textarea
                            rows={2}
                            placeholder="Beklenen sonuç"
                            value={step.expected_result}
                            onChange={e => updateStep(idx, "expected_result", e.target.value)}
                            className="w-full resize-none rounded border border-border bg-white/[0.02] px-2 py-1.5 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
                          />
                          <input
                            placeholder="Test verisi (opsiyonel)"
                            value={step.test_data}
                            onChange={e => updateStep(idx, "test_data", e.target.value)}
                            className="w-full rounded border border-border bg-white/[0.02] px-2 py-1.5 text-[11px] text-slate-400 placeholder-slate-600 outline-none focus:border-teal-500/50"
                          />
                          <input
                            placeholder="Notlar (opsiyonel)"
                            value={step.notes}
                            onChange={e => updateStep(idx, "notes", e.target.value)}
                            className="w-full rounded border border-border bg-white/[0.02] px-2 py-1.5 text-[11px] text-slate-400 placeholder-slate-600 outline-none focus:border-teal-500/50"
                          />
                          <label className="flex items-center gap-2 text-[11px] text-slate-500 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={step.is_required}
                              onChange={e => {
                                setSteps(prev => prev.map((s, i) => i === idx ? { ...s, is_required: e.target.checked } : s));
                                markDirty();
                              }}
                              className="rounded"
                            />
                            Zorunlu adım
                          </label>
                        </div>
                      </div>
                    </SortableStepCard>
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          </div>
        </div>

        {/* RIGHT — metadata */}
        <div className="w-72 shrink-0 border-l border-border bg-surface-raised overflow-y-auto px-5 py-5 space-y-5">
          {/* Metadata fields */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-medium uppercase tracking-wider text-slate-600">Metadata</h3>
            {[
              { label: "Öncelik", value: priority, onChange: setPriority, opts: PRIORITY_OPTIONS },
              { label: "Severity", value: severity, onChange: setSeverity, opts: SEVERITY_OPTIONS },
              { label: "Tip", value: type, onChange: setType, opts: TYPE_OPTIONS },
              { label: "Durum", value: status, onChange: setStatus, opts: STATUS_OPTIONS },
            ].map(({ label, value, onChange, opts }) => (
              <div key={label}>
                <label className="mb-1 block text-[11px] text-slate-500">{label}</label>
                <select
                  value={value}
                  onChange={e => { onChange(e.target.value); markDirty(); }}
                  className="w-full rounded-md border border-border bg-bg px-2 py-1.5 text-[13px] text-slate-200 outline-none focus:border-teal-500/50"
                >
                  {opts.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            ))}

            {/* Tags */}
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">Etiketler</label>
              <input
                value={tags}
                onChange={e => { setTags(e.target.value); markDirty(); }}
                onBlur={handleSave}
                placeholder="login, payment, …"
                className="w-full rounded-md border border-border bg-bg px-2 py-1.5 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
              />
            </div>
          </div>

          {/* Custom Fields — editable */}
          <div className="space-y-2">
            <h3 className="text-[10px] font-medium uppercase tracking-wider text-slate-600">Özel Alanlar</h3>
            <div className="rounded-md border border-border bg-white/[0.02] p-3 space-y-2">
              {[
                { label: "Bileşen", val: customComponent, set: setCustomComponent },
                { label: "Platform", val: customPlatform, set: setCustomPlatform },
                { label: "Risk Alanı", val: customRiskArea, set: setCustomRiskArea },
              ].map(({ label, val, set }) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="w-20 shrink-0 text-[10px] font-medium text-fg-subtle">{label}</span>
                  <input
                    value={val}
                    onChange={e => { set(e.target.value); setDirty(true); }}
                    placeholder="—"
                    className="flex-1 rounded border border-border bg-surface-overlay px-2 py-1 text-[12px] text-fg placeholder:text-fg-disabled outline-none focus:border-brand focus:ring-1 focus:ring-brand/20"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Version info */}
          {tc && (
            <div className="space-y-1.5">
              <h3 className="text-[10px] font-medium uppercase tracking-wider text-slate-600">Versiyon</h3>
              <div className="rounded-md border border-border bg-white/[0.02] px-3 py-2">
                <p className="text-[11px] text-slate-500">v{tc.current_version}</p>
                <p className="text-[10px] text-slate-600 mt-0.5">
                  {new Date(tc.updated_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })}
                </p>
              </div>
            </div>
          )}

          {/* Dependencies */}
          <div className="space-y-2">
            <h3 className="text-[10px] font-medium uppercase tracking-wider text-slate-600">
              Bağımlılıklar {dependencies.length > 0 && <span className="ml-1 text-fg-muted">({dependencies.length})</span>}
            </h3>
            {dependencies.length > 0 ? (
              <div className="space-y-1">
                {dependencies.map(dep => (
                  <div
                    key={dep.id}
                    className={`flex items-center gap-2 rounded-md border px-3 py-1.5 ${
                      dep.dep_type === "blocks" ? "border-red-500/30 bg-red-500/[0.04]" : "border-border bg-white/[0.02]"
                    }`}
                  >
                    <span className="font-mono text-[9px] text-fg-disabled shrink-0">{dep.depends_on_key}</span>
                    <span className="flex-1 truncate text-[11px] text-slate-400">{dep.depends_on_title}</span>
                    <span className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] ${
                      dep.dep_type === "blocks" ? "bg-red-500/10 text-red-400" : "bg-surface-overlay text-fg-subtle"
                    }`}>
                      {dep.dep_type}
                    </span>
                    <button
                      type="button"
                      onClick={async () => {
                        if (!caseId) return;
                        await removeDependency.mutateAsync({ caseId, depId: dep.id });
                      }}
                      disabled={removeDependency.isPending}
                      className="shrink-0 text-[10px] text-slate-600 hover:text-red-400 transition-colors disabled:opacity-40"
                      title="Bağımlılığı kaldır"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[10px] text-slate-600">Bağımlılık yok</p>
            )}
            {/* Add dependency form */}
            <div className="space-y-1.5">
              <div className="flex gap-1.5">
                <input
                  value={depKeyInput}
                  onChange={e => { setDepKeyInput(e.target.value); setDepAddError(""); }}
                  placeholder="TC-XXX (case key)"
                  className="flex-1 rounded border border-border bg-bg px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
                />
                <select
                  value={depTypeInput}
                  onChange={e => setDepTypeInput(e.target.value as "blocks" | "related")}
                  className="rounded border border-border bg-bg px-1 py-1 text-[11px] text-slate-200 outline-none focus:border-teal-500/50"
                >
                  <option value="blocks">blocks</option>
                  <option value="related">related</option>
                </select>
              </div>
              <button
                type="button"
                disabled={!depKeyInput.trim() || addDependency.isPending}
                onClick={async () => {
                  if (!caseId || !depKeyInput.trim()) return;
                  const target = allCases.find(c => c.case_key === depKeyInput.trim());
                  if (!target) {
                    setDepAddError(`"${depKeyInput.trim()}" bulunamadı`);
                    return;
                  }
                  try {
                    await addDependency.mutateAsync({ caseId, depends_on_id: target.id, dep_type: depTypeInput });
                    setDepKeyInput("");
                    setDepAddError("");
                  } catch {
                    setDepAddError("Eklenemedi");
                  }
                }}
                className="w-full rounded-md border border-border bg-white/[0.04] py-1 text-[11px] text-slate-400 hover:border-teal-500/40 hover:text-teal-400 transition-colors disabled:opacity-40"
              >
                {addDependency.isPending ? "Ekleniyor…" : "+ Bağımlılık Ekle"}
              </button>
              {depAddError && <p className="text-[10px] text-red-400">{depAddError}</p>}
            </div>
          </div>

          {/* Sub-cases */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-[10px] font-medium uppercase tracking-wider text-slate-600">
                Alt Senaryolar {subCases.length > 0 && <span className="ml-1 text-fg-muted">({subCases.length})</span>}
              </h3>
              <button
                type="button"
                onClick={async () => {
                  if (!caseId) return;
                  await createSubCase.mutateAsync({ parentId: caseId, title: "Yeni Alt Senaryo" });
                }}
                disabled={createSubCase.isPending}
                className="text-[10px] text-brand hover:text-brand-secondary transition-colors disabled:opacity-40"
              >
                + Ekle
              </button>
            </div>
            {subCases.length > 0 ? (
              <div className="space-y-1">
                {subCases.map(sc => (
                  <Link
                    key={sc.id}
                    href={`/p/${projectId}/management/cases/${sc.id}`}
                    className="flex items-center gap-2 rounded-md border border-border bg-white/[0.02] px-3 py-1.5 hover:bg-surface-overlay transition-colors"
                  >
                    <span className="font-mono text-[9px] text-fg-disabled">{sc.case_key}</span>
                    <span className="flex-1 truncate text-[11px] text-slate-400">{sc.title}</span>
                    <span className="shrink-0 rounded px-1.5 py-0.5 text-[9px] bg-surface-overlay text-fg-subtle">{sc.status}</span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-[10px] text-slate-600">Alt senaryo yok</p>
            )}
          </div>

          {/* Version history */}
          {(versions ?? []).length > 0 && (
            <div className="space-y-2">
              <h3 className="text-[10px] font-medium uppercase tracking-wider text-slate-600">Versiyon Geçmişi</h3>
              {(versions ?? []).slice(0, 6).map(v => (
                <div key={v.id} className="rounded-md border border-border bg-white/[0.02] px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">v{v.version_no}</span>
                    <span className="text-[10px] text-slate-600">
                      {new Date(v.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
                    </span>
                  </div>
                  {v.change_summary && (
                    <p className="mt-0.5 text-[10px] text-slate-600 truncate">{v.change_summary}</p>
                  )}
                  {v.changed_fields.length > 0 && (
                    <p className="mt-0.5 text-[10px] text-slate-600">{v.changed_fields.join(", ")}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>}

      {showStepPicker && mpid && (
        <SharedStepPicker
          projectId={mpid}
          onInsert={insertSharedSteps}
          onClose={() => setShowStepPicker(false)}
        />
      )}
    </div>
  );
}
