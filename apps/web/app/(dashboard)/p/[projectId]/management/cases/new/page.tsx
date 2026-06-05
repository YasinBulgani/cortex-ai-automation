"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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

type FormErrors = { title?: boolean };

import { useCreateManagementCase, useManagementRepository } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
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
        <button {...listeners} className="mt-2 cursor-grab text-slate-500 hover:text-slate-300 p-1" title="Sürükle" type="button">
          ⠿
        </button>
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}


type DraftStep = {
  id: string;
  action: string;
  expected_result: string;
  test_data: string;
  notes: string;
  is_required: boolean;
};

export default function NewManagementCasePage({ params }: { params: { projectId: string } }) {
  const router = useRouter();
  const createCase = useCreateManagementCase(params.projectId);
  const mpid = useManagementProjectId(params.projectId || undefined);
  const repository = useManagementRepository(mpid || undefined);
  const [showStepPicker, setShowStepPicker] = useState(false);
  const [title, setTitle] = useState("");
  const [suiteId, setSuiteId] = useState("");
  const [folderId, setFolderId] = useState("");
  const [priority, setPriority] = useState("P2");
  const [severity, setSeverity] = useState("major");
  const [type, setType] = useState("functional");
  const [automationStatus, setAutomationStatus] = useState("manual");
  const [status, setStatus] = useState("draft");
  const [objective, setObjective] = useState("");
  const [preconditions, setPreconditions] = useState("");
  const [testData, setTestData] = useState("");
  const [component, setComponent] = useState("");
  const [platform, setPlatform] = useState("");
  const [riskArea, setRiskArea] = useState("");
  const [tags, setTags] = useState("");
  const [steps, setSteps] = useState<DraftStep[]>([
    { id: crypto.randomUUID(), action: "", expected_result: "", test_data: "", notes: "", is_required: true },
  ]);

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
    }
  };
  const [formError, setFormError] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});

  const addStep = () => {
    setSteps((current) => [...current, { id: crypto.randomUUID(), action: "", expected_result: "", test_data: "", notes: "", is_required: true }]);
  };

  const insertSharedSteps = (sharedItems: import("@/lib/hooks/use-management").SharedStepItem[]) => {
    const newSteps: DraftStep[] = sharedItems.map(s => ({
      id: crypto.randomUUID(),
      action: s.action,
      expected_result: s.expected_result ?? "",
      test_data: "",
      notes: s.notes ?? "",
      is_required: s.is_required,
    }));
    setSteps(curr => [...curr.filter(s => s.action || s.expected_result), ...newSteps]);
  };

  const updateStep = (index: number, patch: Partial<DraftStep>) => {
    setSteps((current) =>
      current.map((step, stepIndex) => stepIndex === index ? { ...step, ...patch } : step),
    );
  };

  const removeStep = (index: number) => {
    setSteps((current) => current.filter((_, stepIndex) => stepIndex !== index));
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError("");
    setErrors({});
    const cleanSteps = steps
      .map((step, index) => ({
        step_no: index + 1,
        action: step.action.trim(),
        expected_result: step.expected_result.trim(),
        test_data: step.test_data.trim() ? { value: step.test_data.trim() } : {},
        notes: step.notes.trim() || null,
        is_required: step.is_required,
      }))
      .filter((step) => step.action && step.expected_result);

    if (!title || title.trim().length === 0) {
      setErrors({ title: true });
      setFormError("Başlık boş bırakılamaz");
      return;
    }
    if (title.trim().length > 500) {
      setErrors({ title: true });
      setFormError("Başlık en fazla 500 karakter olabilir");
      return;
    }
    if (cleanSteps.length === 0) {
      setFormError("En az bir action + expected result adımı girilmeli.");
      return;
    }

    try {
      const created = await createCase.mutateAsync({
        title: title.trim(),
        suite_id: suiteId || null,
        folder_id: folderId || null,
        priority,
        severity,
        type,
        automation_status: automationStatus,
        objective: objective.trim(),
        preconditions: preconditions.trim(),
        test_data: testData.trim() ? { value: testData.trim() } : {},
        status,
        tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
        custom_fields: {
          component: component.trim(),
          platform: platform.trim(),
          risk_area: riskArea.trim(),
        },
        steps: cleanSteps,
      });
      router.push(`/p/${params.projectId}/management/cases/${created.id}`);
    } catch {
      setFormError("Kaydetme başarısız. Lütfen tekrar deneyin.");
    }
  };

  return (
    <div className="min-h-full bg-bg px-5 py-5 space-y-5">
      <section className="rounded-xl border border-border bg-surface-raised p-5">
        <form onSubmit={submit} className="space-y-5">
          {formError ? (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {formError}
            </div>
          ) : null}
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Title<span className="text-red-400 ml-0.5">*</span>
              </span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={500}
                className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                placeholder="Login valid credentials"
              />
              <div className="flex items-center justify-between mt-1">
                {errors.title ? <p className="text-[12px] text-red-400">Başlık zorunludur.</p> : <span />}
                <span className={`text-xs ${title.length >= 480 ? "text-amber-400" : "text-fg-subtle"}`}>{title.length}/500</span>
              </div>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Suite</span>
                <select
                  value={suiteId}
                  onChange={(event) => {
                    setSuiteId(event.target.value);
                    setFolderId("");
                  }}
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  <option value="">Suite seç</option>
                  {(repository.data?.suites ?? []).map((suite) => <option key={suite.id} value={suite.id}>{suite.name}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Folder</span>
                <select
                  value={folderId}
                  onChange={(event) => setFolderId(event.target.value)}
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  <option value="">Folder seç</option>
                  {(repository.data?.folders ?? []).filter((folder) => !suiteId || folder.suite_id === suiteId).map((folder) => <option key={folder.id} value={folder.id}>{folder.path}</option>)}
                </select>
              </label>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Priority</span>
                <select
                  value={priority}
                  onChange={(event) => setPriority(event.target.value)}
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  {["P0", "P1", "P2", "P3"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Severity</span>
                <select
                  value={severity}
                  onChange={(event) => setSeverity(event.target.value)}
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  {["blocker", "critical", "major", "minor"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Type</span>
                <select
                  value={type}
                  onChange={(event) => setType(event.target.value)}
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  {["functional", "smoke", "regression", "uat", "exploratory"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</span>
                <select
                  value={status}
                  onChange={(event) => setStatus(event.target.value)}
                  className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
                >
                  {["draft", "review", "active"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Automation</span>
              <select value={automationStatus} onChange={(event) => setAutomationStatus(event.target.value)} className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none">
                {["manual", "candidate", "automated", "deprecated"].map((item) => <option key={item}>{item}</option>)}
              </select>
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Component</span>
              <input value={component} onChange={(event) => setComponent(event.target.value)} className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Auth" />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Platform</span>
              <input value={platform} onChange={(event) => setPlatform(event.target.value)} className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Web / iOS / Android" />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Risk Area</span>
              <input value={riskArea} onChange={(event) => setRiskArea(event.target.value)} className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Payment, Session" />
            </label>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Objective</span>
              <textarea
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
                maxLength={2000}
                rows={3}
                className="w-full resize-none rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
              />
              <span className={`text-xs ${objective.length >= 1900 ? "text-amber-400" : "text-fg-subtle"}`}>{objective.length}/2000</span>
            </label>
            <label className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Preconditions</span>
              <textarea
                value={preconditions}
                onChange={(event) => setPreconditions(event.target.value)}
                maxLength={2000}
                rows={3}
                className="w-full resize-none rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
              />
              <span className={`text-xs ${preconditions.length >= 1900 ? "text-amber-400" : "text-fg-subtle"}`}>{preconditions.length}/2000</span>
            </label>
          </div>
          <label className="block space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Test Data</span>
            <textarea
              value={testData}
              onChange={(event) => setTestData(event.target.value)}
              maxLength={2000}
              rows={3}
              className="w-full resize-none rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
              placeholder="Kullanıcı, rol, veri seti, fixture veya özel inputlar"
            />
            <span className={`text-xs ${testData.length >= 1900 ? "text-amber-400" : "text-fg-subtle"}`}>{testData.length}/2000</span>
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Tags</span>
            <input
              value={tags}
              onChange={(event) => setTags(event.target.value)}
              className="w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none"
              placeholder="login, smoke, auth"
            />
          </label>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Steps</h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowStepPicker(true)}
                  className="flex items-center gap-1.5 rounded-lg border border-brand/30 px-3 py-1.5 text-xs text-brand hover:bg-brand-soft transition-colors"
                >
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                  </svg>
                  Şablondan Ekle
                </button>
                <button
                  type="button"
                  onClick={addStep}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs text-slate-300 hover:bg-surface-overlay"
                >
                  Adım Ekle
                </button>
              </div>
            </div>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={steps.map(s => s.id)} strategy={verticalListSortingStrategy}>
                {steps.map((step, index) => (
                  <SortableStepCard key={step.id} id={step.id}>
                    <div className="grid gap-3 rounded-lg border border-border bg-bg p-3 md:grid-cols-[2rem_1fr_1fr_auto]">
                      <div className="pt-2 text-center font-mono text-xs text-slate-500">{index + 1}</div>
                      <div className="space-y-2">
                        <textarea value={step.action} onChange={(event) => updateStep(index, { action: event.target.value })} rows={2} className="w-full resize-none rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Action" />
                        <input value={step.test_data} onChange={(event) => updateStep(index, { test_data: event.target.value })} className="w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-xs text-white focus:border-teal-500/50 focus:outline-none" placeholder="Step test data" />
                      </div>
                      <div className="space-y-2">
                        <textarea value={step.expected_result} onChange={(event) => updateStep(index, { expected_result: event.target.value })} rows={2} className="w-full resize-none rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-white focus:border-teal-500/50 focus:outline-none" placeholder="Expected result / validation" />
                        <input value={step.notes} onChange={(event) => updateStep(index, { notes: event.target.value })} className="w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-xs text-white focus:border-teal-500/50 focus:outline-none" placeholder="Notes" />
                      </div>
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-xs text-slate-400">
                          <input type="checkbox" checked={step.is_required} onChange={(event) => updateStep(index, { is_required: event.target.checked })} />
                          Required
                        </label>
                        <button
                          type="button"
                          onClick={() => removeStep(index)}
                          className="rounded-lg border border-border px-3 py-2 text-xs text-slate-500 hover:bg-surface-overlay hover:text-slate-200"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </SortableStepCard>
                ))}
              </SortableContext>
            </DndContext>
          </div>
          <div className="sticky bottom-0 z-10 border-t border-border bg-surface-base px-6 py-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => router.back()}
              className="rounded-lg border border-border px-4 py-2 text-sm text-slate-300 hover:bg-surface-overlay"
            >
              İptal
            </button>
            <button
              type="submit"
              disabled={!title.trim() || createCase.isPending}
              className="rounded-lg bg-teal-500 px-5 py-2 text-sm font-semibold text-slate-950 hover:bg-teal-400 disabled:opacity-40"
            >
              {createCase.isPending ? "Kaydediliyor..." : "Kaydet"}
            </button>
          </div>
        </form>
      </section>

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
