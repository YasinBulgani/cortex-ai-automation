"use client";

import { useCallback, useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { FileDropZone } from "@/components/dnd/FileDropZone";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

type ManualTest = {
  title: string;
  steps: { action: string; expected: string }[];
};

type BddScenario = {
  title: string;
  description?: string;
  gherkin?: string;
  tags?: string[];
  steps?: { keyword: string; text: string }[];
};

type Scenario = {
  id: string;
  title: string;
  status: string;
  current_version: number;
};

type Tab = "analyze" | "manual" | "bdd" | "saved";

export default function AnalysisPage() {
  const projectId = useRouteParam("projectId");

  const [tab, setTab] = useState<Tab>("analyze");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Analysis input
  const [text, setText] = useState("");
  const [extraInstructions, setExtraInstructions] = useState("");

  // Results
  const [manualTests, setManualTests] = useState<ManualTest[]>([]);
  const [bddScenarios, setBddScenarios] = useState<BddScenario[]>([]);

  // Saved scenarios
  const [savedScenarios, setSavedScenarios] = useState<Scenario[]>([]);

  const loadSaved = useCallback(() => {
    if (!projectId) return;
    apiFetch<Scenario[]>(`/api/v1/tspm/projects/${projectId}/scenarios`).then(setSavedScenarios).catch(() => {});
  }, [projectId]);

  useEffect(() => {
    loadSaved();
  }, [loadSaved]);

  function handleFileDrop(files: File[]) {
    for (const file of files) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const content = ev.target?.result;
        if (typeof content === "string") {
          setText((prev) => (prev ? prev + "\n\n---\n\n" : "") + content);
        }
      };
      reader.readAsText(file);
    }
  }

  async function runAnalysis() {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await apiFetch<{
        manual_tests: ManualTest[];
        bdd_scenarios: BddScenario[];
        manual_error?: string;
        bdd_error?: string;
      }>(`/api/v1/tspm/projects/${projectId}/wizard/analyze`, {
        method: "POST",
        json: { text, extra_instructions: extraInstructions },
      });
      setManualTests(res.manual_tests || []);
      setBddScenarios(res.bdd_scenarios || []);

      const total = (res.manual_tests?.length || 0) + (res.bdd_scenarios?.length || 0);
      if (total > 0) {
        setSuccess(`${total} senaryo basariyla uretildi`);
        setTab("manual");
      } else {
        setError("Senaryo uretilemedi. Daha detayli bir analiz dokumani deneyin.");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analiz hatasi");
    } finally {
      setLoading(false);
    }
  }

  async function saveScenarioToProject(title: string, steps: { keyword: string; text: string }[] | { action: string; expected: string }[], isBdd: boolean) {
    setError(null);
    try {
      const formattedSteps = isBdd
        ? (steps as { keyword: string; text: string }[]).map((s) => ({ keyword: s.keyword, text: s.text }))
        : (steps as { action: string; expected: string }[]).map((s, i) => ({ keyword: i === 0 ? "Olduğu gibi" : i === steps.length - 1 ? "O zaman" : "Eğer", text: `${s.action} → ${s.expected}` }));

      await apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios`, {
        method: "POST",
        json: { title, description: `AI tarafindan uretildi`, status: "draft", steps: formattedSteps },
      });
      setSuccess(`"${title}" projeye kaydedildi`);
      loadSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Kaydetme hatasi");
    }
  }

  async function saveAllBddToProject() {
    setLoading(true);
    let count = 0;
    for (const s of bddScenarios) {
      try {
        await apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios`, {
          method: "POST",
          json: {
            title: s.title,
            description: s.description || s.gherkin?.slice(0, 200) || "",
            status: "draft",
            steps: s.steps || [],
          },
        });
        count++;
      } catch {
        // continue
      }
    }
    setSuccess(`${count} BDD senaryo projeye kaydedildi`);
    setLoading(false);
    loadSaved();
  }

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "analyze", label: "Analiz" },
    { id: "manual", label: "Manuel Testler", count: manualTests.length },
    { id: "bdd", label: "BDD Senaryolar", count: bddScenarios.length },
    { id: "saved", label: "Kayitli Senaryolar", count: savedScenarios.length },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-6" data-testid="analysis-page">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Analiz Merkezi</h1>
        <p className="text-sm text-slate-400">Dokuman analizi, AI ile senaryo uretimi ve yonetimi</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-900/40 p-1 bg-slate-800/30">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all ${
              tab === t.id ? "bg-slate-900 text-white shadow-sm" : "text-slate-400 hover:text-white"
            }`}
          >
            {t.label}
            {t.count !== undefined && t.count > 0 && (
              <span className="rounded-full bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-bold text-blue-400">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Notifications */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-400">
          {error}
          <button type="button" className="ml-2 underline" onClick={() => setError(null)}>Kapat</button>
        </div>
      )}
      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-950/30 dark:text-green-400">
          {success}
          <button type="button" className="ml-2 underline" onClick={() => setSuccess(null)}>Kapat</button>
        </div>
      )}

      {/* Tab: Analyze */}
      {tab === "analyze" && (
        <div className="space-y-6">
          <FileDropZone onFiles={handleFileDrop} accept=".txt,.md,.pdf,.doc,.docx,.csv,.json,.xml" maxSizeMB={20} />

          <div>
            <label className="mb-1 block text-sm font-medium">Analiz Dokumani</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={"Gereksinim veya analiz dokumani yapistiriniz...\n\nOrnek:\n- Kullanici giris yapabilmeli\n- Izin talebi olusturabilmeli\n- Avans basvurusu yapabilmeli"}
              rows={12}
              className="w-full rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-white placeholder:text-slate-400/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Ek Talimatlar (Opsiyonel)</label>
            <Input
              value={extraInstructions}
              onChange={(e) => setExtraInstructions(e.target.value)}
              placeholder="Orn: Login akislarina odaklan, negatif senaryolari dahil et"
            />
          </div>

          <div className="flex items-center gap-3">
            <Button type="button" onClick={runAnalysis} disabled={loading || !text.trim()}>
              {loading ? "AI Analiz Ediyor..." : "Analiz Et"}
            </Button>
            <span className="text-xs text-slate-400">{text.length} karakter</span>
            {text.length > 0 && (
              <button type="button" className="text-xs text-red-500 hover:underline" onClick={() => setText("")}>Temizle</button>
            )}
          </div>
        </div>
      )}

      {/* Tab: Manual Tests */}
      {tab === "manual" && (
        <div className="space-y-4">
          {manualTests.length === 0 ? (
            <div className="rounded-lg border border-slate-800 p-8 text-center">
              <p className="text-slate-400">Henuz manuel test uretilmedi. Analiz sekmesinden baslayin.</p>
            </div>
          ) : (
            manualTests.map((t, i) => (
              <div key={i} className="rounded-lg border border-slate-800 p-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">{t.title}</h3>
                  <Button
                    type="button"
                    variant="secondary"
                    className="h-7 px-2 text-xs"
                    onClick={() => saveScenarioToProject(t.title, t.steps, false)}
                  >
                    Projeye Kaydet
                  </Button>
                </div>
                <table className="mt-3 w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs text-slate-400">
                      <th className="w-8 pb-2 text-center">#</th>
                      <th className="pb-2">Aksiyon</th>
                      <th className="pb-2">Beklenen Sonuc</th>
                    </tr>
                  </thead>
                  <tbody>
                    {t.steps.map((s, j) => (
                      <tr key={j} className="border-b border-slate-800/50 last:border-0">
                        <td className="py-2 text-center text-xs text-slate-400">{j + 1}</td>
                        <td className="py-2">{s.action}</td>
                        <td className="py-2 text-green-700 dark:text-green-400">{s.expected}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab: BDD Scenarios */}
      {tab === "bdd" && (
        <div className="space-y-4">
          {bddScenarios.length > 0 && (
            <div className="flex justify-end">
              <Button type="button" onClick={saveAllBddToProject} disabled={loading}>
                {loading ? "Kaydediliyor..." : `Tumunu Kaydet (${bddScenarios.length})`}
              </Button>
            </div>
          )}
          {bddScenarios.length === 0 ? (
            <div className="rounded-lg border border-slate-800 p-8 text-center">
              <p className="text-slate-400">Henuz BDD senaryo uretilmedi. Analiz sekmesinden baslayin.</p>
            </div>
          ) : (
            bddScenarios.map((s, i) => (
              <div key={i} className="rounded-lg border border-slate-800 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h3 className="font-medium">{s.title}</h3>
                    {s.tags?.map((tag) => (
                      <Badge key={tag} className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">
                        @{tag}
                      </Badge>
                    ))}
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    className="h-7 px-2 text-xs"
                    onClick={() => saveScenarioToProject(s.title, s.steps || [], true)}
                  >
                    Projeye Kaydet
                  </Button>
                </div>
                {s.description && <p className="mt-1 text-xs text-slate-400">{s.description}</p>}
                {s.gherkin && (
                  <pre className="mt-3 overflow-auto rounded-lg bg-black/[0.03] p-4 text-xs dark:bg-white/[0.04]">{s.gherkin}</pre>
                )}
                {!s.gherkin && s.steps && (
                  <div className="mt-3 space-y-1 text-sm">
                    {s.steps.map((st, j) => (
                      <p key={j}><span className="font-semibold text-blue-400">{st.keyword}</span> {st.text}</p>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab: Saved Scenarios */}
      {tab === "saved" && (
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead className="border-b border-slate-800 bg-slate-900/40 dark:bg-white/[0.04]">
              <tr>
                <th className="p-3">Baslik</th>
                <th className="p-3">Durum</th>
                <th className="p-3">Surum</th>
              </tr>
            </thead>
            <tbody>
              {savedScenarios.map((s) => (
                <tr key={s.id} className="border-b border-slate-800 last:border-0">
                  <td className="p-3 font-medium">{s.title}</td>
                  <td className="p-3">
                    <Badge className={s.status === "draft" ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-800"}>
                      {s.status}
                    </Badge>
                  </td>
                  <td className="p-3 tabular-nums text-slate-400">v{s.current_version}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {savedScenarios.length === 0 && (
            <p className="p-8 text-center text-sm text-slate-400">Henuz kayitli senaryo yok.</p>
          )}
        </div>
      )}
    </div>
  );
}
