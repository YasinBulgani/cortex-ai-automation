"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import {
  useManagementCase,
  useManagementCaseVersions,
  useUpdateManagementCase,
  type TestCaseStep,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

const PRIORITY_OPTIONS = ["P0", "P1", "P2", "P3"];
const SEVERITY_OPTIONS = ["blocker", "critical", "major", "minor", "trivial"];
const TYPE_OPTIONS = ["manual", "exploratory", "regression", "smoke", "uat"];
const STATUS_OPTIONS = ["draft", "ready", "active", "archived"];

type DraftStep = { id?: string; step_no: number; action: string; expected_result: string; test_data: string };

function makeStep(no: number): DraftStep {
  return { step_no: no, action: "", expected_result: "", test_data: "" };
}

export default function ManagementCaseDetailPage() {
  const projectId = useRouteParam("projectId");
  const caseId    = useRouteParam("caseId");

  const mpid = useManagementProjectId(projectId || undefined);

  const { data: tc, isLoading } = useManagementCase(mpid || undefined, caseId || undefined);
  const { data: versions }      = useManagementCaseVersions(mpid || undefined, caseId || undefined);
  const update                  = useUpdateManagementCase(mpid || "");

  const [title, setTitle]             = useState("");
  const [objective, setObjective]     = useState("");
  const [preconditions, setPreconditions] = useState("");
  const [priority, setPriority]       = useState("P1");
  const [severity, setSeverity]       = useState("major");
  const [type, setType]               = useState("manual");
  const [status, setStatus]           = useState("draft");
  const [tags, setTags]               = useState("");
  const [steps, setSteps]             = useState<DraftStep[]>([makeStep(1)]);
  const [dirty, setDirty]             = useState(false);
  const [saving, setSaving]           = useState(false);

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
    setSteps(
      tc.steps && tc.steps.length > 0
        ? tc.steps.map((s: TestCaseStep) => ({
            id: s.id,
            step_no: s.step_no,
            action: s.action,
            expected_result: s.expected_result,
            test_data: typeof s.test_data === "string" ? s.test_data : JSON.stringify(s.test_data ?? {}),
          }))
        : [makeStep(1)]
    );
  }, [tc]);

  const markDirty = () => setDirty(true);

  const handleSave = async () => {
    if (!caseId || !mpid) return;
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
        steps: steps.map((s, idx) => ({
          step_no: idx + 1,
          action: s.action,
          expected_result: s.expected_result,
          test_data: {},
          notes: null,
          is_required: true,
        })),
      });
      setDirty(false);
    } finally {
      setSaving(false);
    }
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

  if (isLoading) {
    return (
      <div className="min-h-[calc(100vh-88px)] bg-[#0a0f1e] flex items-center justify-center">
        <div className="animate-pulse h-6 w-32 rounded bg-white/[0.04]" />
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-88px)] bg-[#0a0f1e] text-slate-200">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-white/[0.06] bg-[#0d1221] px-6 py-3">
        <Link
          href={`/p/${projectId}/management/repository`}
          className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
        >
          ← Repository
        </Link>
        <div className="flex items-center gap-2">
          {dirty && <span className="text-[10px] text-slate-600">Kaydedilmemiş değişiklik</span>}
          <button
            onClick={handleSave}
            disabled={saving || !dirty}
            className="rounded-md bg-blue-600 px-4 py-1.5 text-[11px] font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors"
          >
            {saving ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="flex h-[calc(100vh-88px-48px)] overflow-hidden">
        {/* LEFT — editor */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Title */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-slate-600">Başlık</label>
            <input
              value={title}
              onChange={e => { setTitle(e.target.value); markDirty(); }}
              onBlur={handleSave}
              className="w-full rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-base font-medium text-slate-100 placeholder-slate-600 outline-none focus:border-blue-500/50"
              placeholder="Test case başlığı"
            />
          </div>

          {/* Objective */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-slate-600">Amaç</label>
            <textarea
              rows={2}
              value={objective}
              onChange={e => { setObjective(e.target.value); markDirty(); }}
              onBlur={handleSave}
              className="w-full resize-none rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/50"
              placeholder="Test'in amacı…"
            />
          </div>

          {/* Preconditions */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-slate-600">Ön Koşullar</label>
            <textarea
              rows={2}
              value={preconditions}
              onChange={e => { setPreconditions(e.target.value); markDirty(); }}
              onBlur={handleSave}
              className="w-full resize-none rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/50"
              placeholder="Gerekli ön koşullar…"
            />
          </div>

          {/* Steps */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-[10px] font-medium uppercase tracking-wider text-slate-600">Adımlar</label>
              <button
                onClick={addStep}
                className="text-[11px] text-blue-500 hover:text-blue-400 transition-colors"
              >
                + Adım Ekle
              </button>
            </div>
            <div className="space-y-2">
              {steps.map((step, idx) => (
                <div key={idx} className="rounded-md border border-white/[0.06] bg-white/[0.02] p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-[10px] text-slate-600">Adım {idx + 1}</span>
                    {steps.length > 1 && (
                      <button
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
                      className="w-full resize-none rounded border border-white/[0.06] bg-white/[0.02] px-2 py-1.5 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/50"
                    />
                    <textarea
                      rows={2}
                      placeholder="Beklenen sonuç"
                      value={step.expected_result}
                      onChange={e => updateStep(idx, "expected_result", e.target.value)}
                      className="w-full resize-none rounded border border-white/[0.06] bg-white/[0.02] px-2 py-1.5 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/50"
                    />
                    <input
                      placeholder="Test verisi (opsiyonel)"
                      value={step.test_data}
                      onChange={e => updateStep(idx, "test_data", e.target.value)}
                      className="w-full rounded border border-white/[0.06] bg-white/[0.02] px-2 py-1.5 text-[11px] text-slate-400 placeholder-slate-600 outline-none focus:border-blue-500/50"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT — metadata */}
        <div className="w-72 shrink-0 border-l border-white/[0.06] bg-[#0d1221] overflow-y-auto px-5 py-5 space-y-5">
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
                  className="w-full rounded-md border border-white/[0.06] bg-[#0a0f1e] px-2 py-1.5 text-[13px] text-slate-200 outline-none focus:border-blue-500/50"
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
                className="w-full rounded-md border border-white/[0.06] bg-[#0a0f1e] px-2 py-1.5 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/50"
              />
            </div>
          </div>

          {/* Version info */}
          {tc && (
            <div className="space-y-1.5">
              <h3 className="text-[10px] font-medium uppercase tracking-wider text-slate-600">Versiyon</h3>
              <div className="rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2">
                <p className="text-[11px] text-slate-500">v{tc.current_version}</p>
                <p className="text-[10px] text-slate-600 mt-0.5">
                  {new Date(tc.updated_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })}
                </p>
              </div>
            </div>
          )}

          {/* Version history */}
          {(versions ?? []).length > 0 && (
            <div className="space-y-2">
              <h3 className="text-[10px] font-medium uppercase tracking-wider text-slate-600">Versiyon Geçmişi</h3>
              {(versions ?? []).slice(0, 6).map(v => (
                <div key={v.id} className="rounded-md border border-white/[0.04] bg-white/[0.02] px-3 py-2">
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
      </div>
    </div>
  );
}
