"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Step = {
  id: number;
  keyword: string;
  text: string;
};

type Detail = {
  id: string;
  title: string;
  description: string;
  status: string;
  steps: Record<string, unknown>[];
  data_bindings?: Array<{ data_set_id: string; parameter_mapping: Record<string, string> }>;
};

const STATUS_OPTIONS = ["draft", "active", "deprecated", "review"] as const;

export default function EditScenarioPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");
  const id = useRouteParam("id");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("draft");
  const [steps, setSteps] = useState<Step[]>([]);
  const [dataBindings, setDataBindings] = useState<Array<{ data_set_id: string; parameter_mapping: Record<string, string> }>>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Detail>(`/api/v1/tspm/projects/${projectId}/scenarios/${id}`).then((d) => {
      setTitle(d.title);
      setDescription(d.description);
      setStatus(d.status);
      // Parse steps: if they have id/keyword/text, use as Step[]; otherwise create default steps
      const parsedSteps: Step[] = (d.steps || []).map((s: Record<string, unknown>, idx: number) => ({
        id: (s.id as number) ?? idx,
        keyword: (s.keyword as string) ?? "Given",
        text: (s.text as string) ?? "",
      }));
      setSteps(parsedSteps);
      setDataBindings(d.data_bindings || []);
    });
  }, [projectId, id]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);

    // Validate steps
    if (steps.length === 0) {
      setErr("En az bir adım gerekli");
      return;
    }

    // Convert steps to API format
    const stepsPayload: Record<string, unknown>[] = steps.map((s) => ({
      id: s.id,
      keyword: s.keyword,
      text: s.text,
    }));

    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios/${id}`, {
        method: "PUT",
        json: {
          title,
          description,
          status,
          steps: stepsPayload,
          data_bindings: dataBindings,
        },
      });
      router.push(`/p/${projectId}/scenarios/${id}`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata");
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6" data-testid="scenario-edit-page">
      <h1 className="text-2xl font-semibold tracking-tight" data-testid="scenario-edit-heading">Senaryo düzenle</h1>
      <form onSubmit={submit} className="space-y-4" data-testid="scenario-edit-form">
        <div>
          <label className="mb-1 block text-xs text-slate-400">Başlık</label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} required data-testid="scenario-edit-input-title" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Açıklama</label>
          <textarea
            className="min-h-[80px] w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            data-testid="scenario-edit-input-desc"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Durum</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-100"
            data-testid="scenario-edit-select-status"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt} className="bg-slate-900">
                {opt}
              </option>
            ))}
          </select>
        </div>
        <StepEditor steps={steps} onStepsChange={setSteps} />
        <DataBindingCard dataBindings={dataBindings} onBindingsChange={setDataBindings} />
        {err && <p className="text-sm text-red-600" data-testid="scenario-edit-error">{err}</p>}
        <Button type="submit" data-testid="scenario-edit-btn-save">Kaydet</Button>
      </form>
    </div>
  );
}

const KEYWORDS = ["Given", "When", "Then", "And", "But"] as const;

interface StepEditorProps {
  steps: Step[];
  onStepsChange: (steps: Step[]) => void;
}

function StepEditor({ steps, onStepsChange }: StepEditorProps) {
  function addStep() {
    const newStep: Step = {
      id: Math.max(...steps.map((s) => s.id), -1) + 1,
      keyword: "Given",
      text: "",
    };
    onStepsChange([...steps, newStep]);
  }

  function updateStep(id: number, field: keyof Step, value: string | number) {
    onStepsChange(
      steps.map((s) => (s.id === id ? { ...s, [field]: value } : s))
    );
  }

  function deleteStep(id: number) {
    onStepsChange(steps.filter((s) => s.id !== id));
  }

  return (
    <div>
      <label className="mb-1 block text-xs text-slate-400">Adımlar</label>
      <div className="space-y-2 rounded border border-slate-800 bg-slate-900 p-3">
        {steps.length === 0 ? (
          <p className="text-xs text-slate-500 italic">Adım yok</p>
        ) : (
          steps.map((step) => (
            <div key={step.id} className="flex gap-2">
              <select
                value={step.keyword}
                onChange={(e) => updateStep(step.id, "keyword", e.target.value)}
                className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-100"
              >
                {KEYWORDS.map((kw) => (
                  <option key={kw} value={kw} className="bg-slate-800">
                    {kw}
                  </option>
                ))}
              </select>
              <input
                type="text"
                value={step.text}
                onChange={(e) => updateStep(step.id, "text", e.target.value)}
                placeholder="Adım metni..."
                className="flex-1 rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-100 placeholder-slate-500"
              />
              <button
                type="button"
                onClick={() => deleteStep(step.id)}
                className="rounded bg-red-900 px-2 py-1 text-xs text-red-100 hover:bg-red-800"
              >
                Sil
              </button>
            </div>
          ))
        )}
        <button
          type="button"
          onClick={addStep}
          className="mt-2 rounded bg-blue-900 px-3 py-1 text-xs text-blue-100 hover:bg-blue-800"
        >
          + Adım Ekle
        </button>
      </div>
    </div>
  );
}

interface DataBindingCardProps {
  dataBindings: Array<{ data_set_id: string; parameter_mapping: Record<string, string> }>;
  onBindingsChange: (bindings: Array<{ data_set_id: string; parameter_mapping: Record<string, string> }>) => void;
}

function DataBindingCard({ dataBindings, onBindingsChange }: DataBindingCardProps) {
  const [datasets, setDatasets] = useState<Array<{ id: string; name: string }>>([]);

  useEffect(() => {
    // Fetch available datasets
    apiFetch<Array<{ id: string; name: string }>>(`/api/v1/test-data`).then(setDatasets).catch(() => {
      // If endpoint doesn't exist, proceed with empty list
      setDatasets([]);
    });
  }, []);

  function addBinding() {
    const newBinding = { data_set_id: "", parameter_mapping: {} };
    onBindingsChange([...dataBindings, newBinding]);
  }

  function updateBinding(
    idx: number,
    field: "data_set_id" | "parameter_mapping",
    value: string | Record<string, string>
  ) {
    onBindingsChange(
      dataBindings.map((b, i) => (i === idx ? { ...b, [field]: value } : b))
    );
  }

  function deleteBinding(idx: number) {
    onBindingsChange(dataBindings.filter((_, i) => i !== idx));
  }

  return (
    <div className="rounded border border-slate-700 bg-slate-800 p-4">
      <h3 className="mb-3 font-semibold text-slate-100">📊 Veri Seti Bağlaması</h3>
      <div className="space-y-2">
        {dataBindings.length === 0 ? (
          <p className="text-xs text-slate-500 italic">Veri seti bağlaması yok</p>
        ) : (
          dataBindings.map((binding, idx) => (
            <div key={idx} className="rounded border border-slate-700 bg-slate-900 p-3">
              <div className="mb-2 flex gap-2">
                <select
                  value={binding.data_set_id}
                  onChange={(e) => updateBinding(idx, "data_set_id", e.target.value)}
                  className="flex-1 rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-100"
                >
                  <option value="">Veri Seti Seç</option>
                  {datasets.map((ds) => (
                    <option key={ds.id} value={ds.id} className="bg-slate-800">
                      {ds.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => deleteBinding(idx)}
                  className="rounded bg-red-900 px-2 py-1 text-xs text-red-100 hover:bg-red-800"
                >
                  Sil
                </button>
              </div>
              <div className="text-xs text-slate-400">
                Parametreler: {Object.keys(binding.parameter_mapping).length}
              </div>
            </div>
          ))
        )}
        <button
          type="button"
          onClick={addBinding}
          className="rounded bg-blue-900 px-3 py-1 text-xs text-blue-100 hover:bg-blue-800"
        >
          + Bağlama Ekle
        </button>
      </div>
    </div>
  );
}
