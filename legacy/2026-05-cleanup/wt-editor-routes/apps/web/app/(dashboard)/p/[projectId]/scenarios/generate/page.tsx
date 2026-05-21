"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";

type GeneratedScenario = {
  title: string;
  description: string;
  feature: string;
  gherkin: string;
  tags: string[];
  steps: { keyword: string; text: string }[];
  selected: boolean;
};

export default function GenerateBddPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");

  const [analysisText, setAnalysisText] = useState("");
  const [scenarios, setScenarios] = useState<GeneratedScenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function generate() {
    if (analysisText.trim().length < 10) {
      setError("Analiz dokümanı en az 10 karakter olmalı.");
      return;
    }
    setLoading(true);
    setError(null);
    setSuccess(null);
    setScenarios([]);

    try {
      const res = await apiFetch<{ scenarios: Omit<GeneratedScenario, "selected">[] }>(
        `/api/v1/tspm/projects/${projectId}/scenarios/generate-bdd`,
        { method: "POST", json: { analysis_text: analysisText } },
      );
      setScenarios(res.scenarios.map((s) => ({ ...s, selected: true })));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Senaryo üretilirken hata oluştu.");
    } finally {
      setLoading(false);
    }
  }

  function toggleScenario(idx: number) {
    setScenarios((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, selected: !s.selected } : s)),
    );
  }

  async function saveSelected() {
    const toSave = scenarios.filter((s) => s.selected);
    if (toSave.length === 0) {
      setError("En az bir senaryo seçmelisiniz.");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const payload = toSave.map(({ selected: _, ...rest }) => rest);
      await apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios/save-bdd`, {
        method: "POST",
        json: { scenarios: payload },
      });
      setSuccess(`${toSave.length} senaryo başarıyla kaydedildi!`);
      setTimeout(() => router.push(`/p/${projectId}/scenarios`), 1500);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Kaydetme sırasında hata oluştu.");
    } finally {
      setSaving(false);
    }
  }

  const selectedCount = scenarios.filter((s) => s.selected).length;

  return (
    <div className="mx-auto max-w-4xl space-y-6" data-testid="scenario-generate-page">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">BDD Senaryosu Üret</h1>
          <p className="text-sm text-slate-400">
            Analiz dokümanını yapıştırın, AI otomatik olarak BDD senaryoları üretsin.
          </p>
        </div>
        <Link href={`/p/${projectId}/scenarios`}>
          <Button type="button" variant="secondary" data-testid="generate-btn-back">
            Geri dön
          </Button>
        </Link>
      </div>

      {/* Input */}
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Analiz Dokümanı *
          </label>
          <textarea
            className="min-h-[200px] w-full rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm leading-relaxed placeholder:text-slate-400/60 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
            placeholder="Analiz dokümanınızı buraya yapıştırın..."
            value={analysisText}
            onChange={(e) => setAnalysisText(e.target.value)}
            disabled={loading}
            data-testid="generate-input-analysis"
          />
        </div>
        <Button type="button" onClick={generate} disabled={loading} data-testid="generate-btn-submit">
          {loading ? "Üretiliyor…" : "Senaryoları Üret"}
        </Button>
      </div>

      {/* Messages */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-lg border border-green-800 bg-green-950/30 px-4 py-3 text-sm text-green-400">
          {success}
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900 p-6">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <p className="text-sm font-medium">AI senaryoları üretiyor...</p>
        </div>
      )}

      {/* Generated Scenarios */}
      {scenarios.length > 0 && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Üretilen Senaryolar ({scenarios.length})</h2>
            <Button type="button" onClick={saveSelected} disabled={saving || selectedCount === 0}>
              {saving ? "Kaydediliyor…" : `Seçilenleri kaydet (${selectedCount})`}
            </Button>
          </div>

          <div className="space-y-3">
            {scenarios.map((sc, idx) => (
              <div
                key={idx}
                className={`rounded-lg border p-4 transition-colors ${
                  sc.selected ? "border-blue-500/40 bg-blue-600/[0.03]" : "border-slate-800 bg-slate-900"
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={sc.selected}
                    onChange={() => toggleScenario(idx)}
                    className="mt-1 h-4 w-4 shrink-0"
                    aria-label={`Senaryo seç: ${sc.title}`}
                  />
                  <div className="min-w-0 flex-1">
                    <h3 className="font-medium">{sc.title}</h3>
                    {sc.feature && (
                      <p className="mt-0.5 text-xs text-slate-400">Özellik: {sc.feature}</p>
                    )}
                    {sc.description && (
                      <p className="mt-1 text-sm text-slate-400">{sc.description}</p>
                    )}
                    {sc.tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {sc.tags.map((tag) => (
                          <span key={tag} className="inline-flex rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-medium">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
