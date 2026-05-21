"use client";

import { useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { FileDropZone } from "@/components/dnd/FileDropZone";
import {
  PageHeader,
  SectionCard,
} from "@/components/nexus";

type ManualTest = { title: string; steps: { action: string; expected: string }[] };
type BddScenario = { title: string; gherkin?: string; tags?: string[]; steps?: { keyword: string; text: string }[] };
type AutomationResult = { feature_files: { name: string; content: string; scenario_title: string }[]; test_files: { name: string; content: string }[] };

const STEPS = [
  { id: 1, title: "Proje Bilgileri", icon: "🎯" },
  { id: 2, title: "Analiz Dokümanı", icon: "📄" },
  { id: 3, title: "Senaryolar", icon: "📋" },
  { id: 4, title: "Otomasyon Üretimi", icon: "⚙️" },
  { id: 5, title: "Sonuçlar", icon: "✅" },
];

const inputCls = "w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";

export default function WizardPage() {
  const projectId = useRouteParam("projectId");

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [targetUrl, setTargetUrl] = useState("");
  const [analysisText, setAnalysisText] = useState("");
  const [manualTests, setManualTests] = useState<ManualTest[]>([]);
  const [bddScenarios, setBddScenarios] = useState<BddScenario[]>([]);
  const [automation, setAutomation] = useState<AutomationResult | null>(null);
  const [projectName, setProjectName] = useState("proje");

  useEffect(() => {
    apiFetch<{ id: string; name: string }[]>("/api/v1/tspm/projects").then(
      (list) => {
        const match = list.find((p) => p.id === projectId);
        if (match) setProjectName(match.name.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "") || "proje");
      },
      () => {},
    );
  }, [projectId]);

  async function runAnalysis() {
    if (!analysisText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<{ manual_tests: ManualTest[]; bdd_scenarios: BddScenario[] }>(
        `/api/v1/tspm/projects/${projectId}/wizard/analyze`,
        { method: "POST", json: { text: analysisText } },
      );
      setManualTests(res.manual_tests || []);
      setBddScenarios(res.bdd_scenarios || []);
      setStep(3);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analiz hatası");
    } finally {
      setLoading(false);
    }
  }

  async function runAutomation() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<AutomationResult>(
        `/api/v1/tspm/projects/${projectId}/wizard/generate-automation`,
        { method: "POST", json: { scenarios: manualTests, url: targetUrl, project_name: projectName } },
      );
      setAutomation(res);
      setStep(5);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Otomasyon üretim hatası");
    } finally {
      setLoading(false);
    }
  }

  function renderStep() {
    switch (step) {
      case 1:
        return (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-slate-400">Test edilecek uygulamanın URL bilgisini girin</p>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-slate-300">Hedef URL *</label>
              <input value={targetUrl} onChange={(e) => setTargetUrl(e.target.value)} placeholder="https://example.com" data-testid="wizard-input-url" className={inputCls} />
            </div>
          </div>
        );

      case 2:
        return (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-slate-400">Analiz dokümanını yapıştırın. AI bunu analiz edip otomatik senaryo üretecek.</p>
            <textarea value={analysisText} onChange={(e) => setAnalysisText(e.target.value)} placeholder="Test gereksinimlerini buraya yazın veya yapıştırın..." rows={10} data-testid="wizard-textarea-analysis" className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 font-mono resize-y" />
            <button type="button" onClick={runAnalysis} disabled={loading || !analysisText.trim()} data-testid="wizard-btn-analyze" className="flex items-center gap-2 w-fit px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50">
              {loading ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />AI Analiz Ediyor…</> : "Analiz Et ve Senaryo Üret"}
            </button>
          </div>
        );

      case 3:
        return (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-slate-400">
              AI tarafından <span className="text-white font-semibold">{manualTests.length}</span> manuel test + <span className="text-white font-semibold">{bddScenarios.length}</span> BDD senaryo üretildi
            </p>
            {manualTests.map((t, i) => (
              <div key={i} className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
                <h4 className="font-semibold text-white mb-2">{t.title}</h4>
                <ol className="flex flex-col gap-1.5">
                  {t.steps.map((s, j) => (
                    <li key={j} className="flex gap-2 text-sm">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-500/10 border border-blue-500/20 text-xs font-bold text-blue-400">{j + 1}</span>
                      <span className="text-slate-200">{s.action}</span>
                      <span className="text-xs text-emerald-400">→ {s.expected}</span>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
            {bddScenarios.map((s, i) => (
              <div key={i} className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
                <h4 className="font-semibold text-white mb-2">{s.title}</h4>
                {s.gherkin && <pre className="rounded-lg bg-slate-900 border border-slate-700 p-3 text-xs text-slate-300 font-mono overflow-auto">{s.gherkin}</pre>}
              </div>
            ))}
          </div>
        );

      case 4:
        return (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-slate-400">Senaryolardan Playwright otomasyon kodu ve Gherkin feature dosyaları üretilecek</p>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-sm">
              <div className="flex gap-4">
                <span className="text-slate-300"><span className="text-blue-400 font-bold">{manualTests.length}</span> manuel senaryo</span>
                <span className="text-slate-300"><span className="text-violet-400 font-bold">{bddScenarios.length}</span> BDD senaryo</span>
              </div>
            </div>
            <button type="button" onClick={runAutomation} disabled={loading} data-testid="wizard-btn-generate" className="flex items-center gap-2 w-fit px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50">
              {loading ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Kod Üretiliyor…</> : "⚙️ Otomasyon Kodunu Üret"}
            </button>
          </div>
        );

      case 5:
        return (
          <div className="flex flex-col gap-6 items-center text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-3xl">✅</div>
            <div>
              <h2 className="text-xl font-bold text-white">Sihirbaz Tamamlandı!</h2>
              <p className="text-sm text-slate-400 mt-1">Tüm adımlar başarıyla tamamlandı</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 w-full max-w-xl">
              {[
                { title: "Manuel Senaryolar", value: manualTests.length, color: "text-blue-400" },
                { title: "BDD Senaryolar", value: bddScenarios.length, color: "text-violet-400" },
                { title: "Üretilen Dosya", value: (automation?.feature_files?.length || 0) + (automation?.test_files?.length || 0), color: "text-emerald-400" },
              ].map(({ title, value, color }) => (
                <div key={title} className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-center">
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{title}</p>
                </div>
              ))}
            </div>
            {automation && (
              <div className="flex flex-col gap-3 w-full text-left">
                {automation.feature_files?.map((f, i) => (
                  <details key={`f${i}`} className="rounded-xl border border-slate-700 bg-slate-900/40">
                    <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-emerald-400 hover:text-emerald-300">{f.name}</summary>
                    <pre className="p-4 max-h-[300px] overflow-auto text-xs text-slate-300 font-mono border-t border-slate-700">{f.content}</pre>
                  </details>
                ))}
                {automation.test_files?.map((f, i) => (
                  <details key={`t${i}`} className="rounded-xl border border-slate-700 bg-slate-900/40">
                    <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-blue-400 hover:text-blue-300">{f.name}</summary>
                    <pre className="p-4 max-h-[300px] overflow-auto text-xs text-slate-300 font-mono border-t border-slate-700">{f.content}</pre>
                  </details>
                ))}
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="wizard-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
        }
        title="URL Test Üreticisi"
        description="URL üzerinden otomatik test senaryosu + otomasyon kodu üret"
      />

      <div className="flex gap-1 p-1 rounded-xl bg-slate-900/60 border border-slate-800">
        {STEPS.map((s) => (
          <button key={s.id} type="button" onClick={() => s.id <= step && setStep(s.id)} disabled={s.id > step} data-testid={`wizard-step-${s.id}`} className={`flex flex-1 flex-col items-center gap-1 rounded-lg px-2 py-2.5 text-center transition-all ${s.id === step ? "bg-blue-600/20 border border-blue-500/30 text-blue-300" : s.id < step ? "cursor-pointer bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/15" : "text-slate-600 cursor-not-allowed"}`}>
            <span className="text-base">{s.id < step ? "✓" : s.icon}</span>
            <span className="text-[10px] font-medium leading-tight">{s.title}</span>
          </button>
        ))}
      </div>

      {error && (
        <div className="flex items-center justify-between rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300" data-testid="wizard-error">
          {error}
          <button type="button" onClick={() => setError(null)} className="text-red-400 hover:text-red-200 ml-3">✕</button>
        </div>
      )}

      <SectionCard title={STEPS[step - 1]?.title ?? ""} icon={<span className="text-base">{STEPS[step - 1]?.icon}</span>}>
        <div className="min-h-[280px]">{renderStep()}</div>
      </SectionCard>

      <div className="flex items-center justify-between">
        <button type="button" onClick={() => setStep(Math.max(1, step - 1))} disabled={step === 1} className="flex items-center gap-2 px-4 py-2 text-sm text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 rounded-xl transition-colors disabled:opacity-30">
          ← Geri
        </button>
        <span className="text-sm text-slate-500">Adım {step} / {STEPS.length}</span>
        {step < 5 && (
          <button type="button" onClick={() => {
            if (step === 2 && analysisText.trim()) { runAnalysis(); return; }
            if (step === 4 && !automation) { runAutomation(); return; }
            setStep(step + 1);
          }} disabled={loading || (step === 1 && !targetUrl.trim()) || (step === 2 && !analysisText.trim())} className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50">
            {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : null}
            {loading ? "İşleniyor…" : step === 2 ? "Analiz Et" : step === 4 ? "Kod Üret" : "İleri →"}
          </button>
        )}
      </div>
    </div>
  );
}
