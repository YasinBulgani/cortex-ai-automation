"use client";

import { useState, useCallback } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { apiFetch } from "@/lib/api";

interface Step {
  id: number;
  action: string;
  expected: string;
}

interface PipelineResult {
  ok: boolean;
  gherkin?: string;
  playwright_code?: string;
  error?: string;
}

let stepCounter = 0;
const newStep = (): Step => ({ id: ++stepCounter, action: "", expected: "" });

export default function ManualToAutomationPage() {
  const projectId = useRouteParam("projectId");

  const [title, setTitle] = useState("");
  const [steps, setSteps] = useState<Step[]>([newStep()]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [activeTab, setActiveTab] = useState<"gherkin" | "code">("gherkin");

  const updateStep = useCallback(
    (id: number, field: "action" | "expected", value: string) => {
      setSteps((prev) => prev.map((s) => (s.id === id ? { ...s, [field]: value } : s)));
    },
    [],
  );

  const addStep = () => setSteps((prev) => [...prev, newStep()]);
  const removeStep = (id: number) => setSteps((prev) => prev.filter((s) => s.id !== id));

  const handleConvert = async () => {
    const valid = steps.filter((s) => s.action.trim() && s.expected.trim());
    if (!title.trim() || valid.length === 0) return;

    setLoading(true);
    setResult(null);
    try {
      const res = await apiFetch<PipelineResult>(
        "/api/v1/automation/proxy/api/pipeline/manual-to-automation",
        {
          method: "POST",
          json: {
            title: title.trim(),
            steps: valid.map((s) => ({ action: s.action.trim(), expected: s.expected.trim() })),
            framework: "playwright",
            project_id: projectId,
          },
        },
      );
      setResult(res);
      setActiveTab("gherkin");
    } catch (err: unknown) {
      setResult({ ok: false, error: err instanceof Error ? err.message : String(err) });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setTitle("");
    setSteps([newStep()]);
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6" data-testid="manual-to-automation-page">
      <PageHeader
        title="Manuel → Otomasyon"
        description="Manuel test adımlarından Gherkin BDD ve Playwright kodu üretin"
      />

      {/* Input form */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Test Başlığı <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Örn: Login başarılı senaryo"
            data-testid="test-title"
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Test Adımları <span className="text-red-500">*</span>
          </label>
          <div className="space-y-3">
            {steps.map((step, idx) => (
              <div key={step.id} className="grid grid-cols-[auto_1fr_1fr_auto] gap-2 items-start">
                <span className="mt-2 text-xs font-mono text-slate-500 w-6 text-right">{idx + 1}.</span>
                <input
                  type="text"
                  value={step.action}
                  onChange={(e) => updateStep(step.id, "action", e.target.value)}
                  placeholder="Aksiyon"
                  data-testid={`step-action-${idx}`}
                  className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <input
                  type="text"
                  value={step.expected}
                  onChange={(e) => updateStep(step.id, "expected", e.target.value)}
                  placeholder="Beklenen sonuç"
                  data-testid={`step-expected-${idx}`}
                  className="rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={() => removeStep(step.id)}
                  disabled={steps.length === 1}
                  className="mt-1.5 text-slate-500 hover:text-red-400 disabled:opacity-30 text-lg"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <button onClick={addStep} className="mt-3 text-sm text-blue-400 hover:text-blue-300 font-medium">
            + Adım Ekle
          </button>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            onClick={handleConvert}
            disabled={loading}
            data-testid="convert-btn"
            className="px-5 py-2 text-sm font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Üretiliyor…
              </>
            ) : (
              "Otomasyona Çevir"
            )}
          </button>
          {result && (
            <button onClick={handleReset} className="px-4 py-2 text-sm text-slate-500 hover:text-white">
              Sıfırla
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden" data-testid="result-panel">
          {!result.ok ? (
            <div className="p-6">
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-200">
                ⚠️ {result.error}
              </div>
            </div>
          ) : (
            <>
              {/* Tab bar */}
              <div className="flex border-b border-slate-800 bg-slate-950/30">
                {(["gherkin", "code"] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    data-testid={`tab-${tab}`}
                    className={`px-5 py-3 text-sm font-medium transition-colors ${
                      activeTab === tab
                        ? "border-b-2 border-blue-500 text-blue-300"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {tab === "gherkin" ? "Gherkin BDD" : "Playwright Kodu"}
                  </button>
                ))}
              </div>

              <pre className="max-h-96 overflow-auto whitespace-pre-wrap bg-slate-950/60 p-5 font-mono text-sm text-slate-200">
                {activeTab === "gherkin"
                  ? result.gherkin || "(içerik boş)"
                  : result.playwright_code || "(içerik boş)"}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}
