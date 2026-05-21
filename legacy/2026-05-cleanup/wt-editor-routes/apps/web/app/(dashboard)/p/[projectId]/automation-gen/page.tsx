"use client";

import { useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";

type AiBatch = { id: string; source_name: string | null; total_generated: number; approved_count: number };

type GherkinResult = { gherkin: string; feature_name: string; scenario_count: number; filename: string };
type JavaResult = { java_code: string; class_name: string; filename: string; method_count: number };
type PlaywrightResult = { ts_code: string; filename: string; test_count: number };

type GenerateResponse = {
  feature_name: string;
  test_case_count: number;
  gherkin: GherkinResult | null;
  java: JavaResult | null;
  playwright: PlaywrightResult | null;
  errors: string[];
  message: string;
};

function CodeBlock({ code, language, filename }: { code: string; language: string; filename: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-slate-700 overflow-hidden">
      <div className="flex items-center justify-between bg-slate-800/60 px-4 py-2.5 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400">{filename}</span>
          <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400 uppercase">{language}</span>
        </div>
        <button
          onClick={handleCopy}
          className="rounded bg-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-600 transition"
        >
          {copied ? "✓ Kopyalandı" : "Kopyala"}
        </button>
      </div>
      <div className="overflow-auto max-h-96 bg-slate-950/80">
        <pre className="p-4 text-xs font-mono text-slate-300 whitespace-pre">{code}</pre>
      </div>
    </div>
  );
}

export default function AutomationGenPage() {
  const projectId = useRouteParam("projectId");

  const [batches, setBatches] = useState<AiBatch[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState("");
  const [featureName, setFeatureName] = useState("");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"gherkin" | "java" | "playwright">("gherkin");

  useEffect(() => {
    apiFetch<AiBatch[]>(`/api/v1/tspm/projects/${projectId}/test-cases/batches`)
      .then(data => {
        const approved = (data || []).filter(b => b.approved_count > 0);
        setBatches(approved);
        if (approved.length > 0) setSelectedBatchId(approved[0].id);
      })
      .catch(() => {});
  }, [projectId]);

  const handleGenerate = async () => {
    if (!featureName.trim()) {
      setError("Feature adı gerekli");
      return;
    }
    setGenerating(true);
    setError(null);
    setResult(null);

    try {
      const payload: Record<string, unknown> = {
        feature_name: featureName,
        include_java: true,
        include_playwright: true,
      };
      if (selectedBatchId) payload.batch_id = selectedBatchId;

      const res = await apiFetch<GenerateResponse>(
        `/api/v1/tspm/projects/${projectId}/automation/generate`,
        { method: "POST", json: payload },
      );
      setResult(res);
      if (res.gherkin) setActiveTab("gherkin");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Üretim başarısız");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6 space-y-6" data-testid="automation-gen-page">
      <PageHeader
        icon={<span className="text-xl">⚙️</span>}
        title="Otomasyon Üretimi"
        description="Onaylı test case'lerden Gherkin, Java ve Playwright kodları üretin"
      />

      {/* Form */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-4 max-w-2xl" data-testid="automation-gen-form">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-400">
            Feature Adı <span className="text-red-400">*</span>
          </label>
          <input
            value={featureName}
            onChange={e => setFeatureName(e.target.value)}
            placeholder="ör. Kullanıcı Giriş Sistemi"
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            data-testid="feature-name-input"
          />
        </div>

        <div>
          <label htmlFor="automation-gen-batch-select" className="mb-1.5 block text-xs font-medium text-slate-400">
            Test Case Kaynağı
          </label>
          {batches.length === 0 ? (
            <p className="text-xs text-slate-500">Onaylı test case bulunamadı.</p>
          ) : (
            <select
              id="automation-gen-batch-select"
              value={selectedBatchId}
              onChange={e => setSelectedBatchId(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none"
              data-testid="batch-select"
            >
              <option value="">Tüm onaylı test case&apos;ler</option>
              {batches.map(b => (
                <option key={b.id} value={b.id}>
                  {b.source_name || "Test Üretimi"} ({b.approved_count} onaylı)
                </option>
              ))}
            </select>
          )}
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating || !featureName.trim() || batches.length === 0}
          className={`w-full rounded-xl py-3 text-sm font-semibold transition ${
            generating || !featureName.trim() || batches.length === 0
              ? "bg-slate-700 text-slate-500 cursor-not-allowed"
              : "bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-500 hover:to-purple-500"
          }`}
          data-testid="generate-button"
        >
          {generating ? "Kod Üretiliyor..." : "⚙️ Kod Üret"}
        </button>

        {error && (
          <div className="rounded-lg border border-red-700/40 bg-red-950/30 px-3 py-2.5 text-xs text-red-300" data-testid="error-message">
            ⚠ {error}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4" data-testid="generation-result">
          <div className="rounded-lg border border-emerald-700/30 bg-emerald-950/30 px-4 py-3 text-sm text-emerald-400">
            ✓ {result.message} — {result.test_case_count} test case işlendi
          </div>

          {result.errors.length > 0 && (
            <div className="rounded-lg border border-yellow-700/40 bg-yellow-950/20 px-4 py-3">
              <p className="text-xs font-semibold text-yellow-400 mb-1">⚠ Bazı üretimler başarısız:</p>
              {result.errors.map((err, i) => (
                <p key={i} className="text-xs text-yellow-300">{err}</p>
              ))}
            </div>
          )}

          <div className="flex gap-1 border-b border-slate-800 pb-2">
            {([
              { key: "gherkin" as const, label: "Gherkin", available: !!result.gherkin },
              { key: "java" as const, label: "Java", available: !!result.java },
              { key: "playwright" as const, label: "Playwright", available: !!result.playwright },
            ]).map(tab => (
              <button
                key={tab.key}
                onClick={() => tab.available && setActiveTab(tab.key)}
                disabled={!tab.available}
                className={`rounded-lg px-4 py-1.5 text-sm font-medium transition ${
                  activeTab === tab.key
                    ? "bg-blue-600 text-white"
                    : tab.available
                    ? "text-slate-400 hover:text-white"
                    : "text-slate-600 cursor-not-allowed"
                }`}
                data-testid={`tab-${tab.key}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === "gherkin" && result.gherkin && (
            <CodeBlock code={result.gherkin.gherkin} language="gherkin" filename={result.gherkin.filename} />
          )}
          {activeTab === "java" && result.java && (
            <CodeBlock code={result.java.java_code} language="java" filename={result.java.filename} />
          )}
          {activeTab === "playwright" && result.playwright && (
            <CodeBlock code={result.playwright.ts_code} language="typescript" filename={result.playwright.filename} />
          )}
        </div>
      )}
    </div>
  );
}
