"use client";

/**
 * Nexus QA — Faz 6: AI Debug Report & Allure Export
 * Başarısız test sonuçlarını AI ile analiz eder,
 * kök neden sınıflandırır, fix önerileri sunar ve Allure export sağlar.
 */

import { useCallback, useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { FlowGuideCard } from "@/components/FlowGuideCard";
import { PageHeader } from "@/components/nexus/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/tspm";

// ── Types ─────────────────────────────────────────────────────────────────────

type Execution = {
  id: string;
  name: string;
  status: string;
  created_at: string;
};

type DebugAnalysisItem = {
  test_id: string;
  root_cause_category: string;
  root_cause_subcategory: string;
  confidence: number;
  fix_steps: string[];
  estimated_fix_time: string;
  risk_level: string;
  similar_tests_at_risk: string[];
  explanation: string;
};

type DebugResponse = {
  execution_id: string;
  analyses: DebugAnalysisItem[];
  overall_health: string;
  key_patterns: string[];
  recommended_actions: string[];
  ai_provider: string;
  fallback_used: boolean;
  summary: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
    pass_rate: number;
    health: string;
  };
  generated_at: string;
  allure_results: Record<string, unknown>[];
};

// ── Sub-components ────────────────────────────────────────────────────────────

function HealthBadge({ health }: { health: string }) {
  const config: Record<string, { bg: string; text: string; icon: string }> = {
    healthy:  { bg: "bg-emerald-500/10 border border-emerald-500/20",  text: "text-emerald-200",  icon: "✅" },
    at_risk:  { bg: "bg-amber-500/10 border border-amber-500/20",  text: "text-amber-200",  icon: "⚠️" },
    critical: { bg: "bg-red-500/10 border border-red-500/20",      text: "text-red-200",      icon: "🚨" },
    unknown:  { bg: "bg-slate-800 border border-slate-700",       text: "text-slate-300",    icon: "❓" },
  };
  const c = config[health] ?? config.unknown;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-semibold ${c.bg} ${c.text}`}>
      {c.icon} {health.replace("_", " ").toUpperCase()}
    </span>
  );
}

function CategoryBadge({ category }: { category: string }) {
  const config: Record<string, string> = {
    PRODUCT_BUG:     "bg-red-500/10 text-red-200 border border-red-500/20",
    TEST_ISSUE:      "bg-amber-500/10 text-amber-200 border border-amber-500/20",
    ENVIRONMENT:     "bg-blue-500/10 text-blue-200 border border-blue-500/20",
    AUTOMATION_DEBT: "bg-violet-500/10 text-violet-200 border border-violet-500/20",
    UNKNOWN:         "bg-slate-800 text-slate-300 border border-slate-700",
  };
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${config[category] ?? config.UNKNOWN}`}>
      {category.replace("_", " ")}
    </span>
  );
}

function ConfidenceMeter({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-400">{pct}%</span>
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: string; label: string; value: string | number; color: string }) {
  return (
    <div className={`rounded-xl border p-4 ${color}`}>
      <div className="text-2xl">{icon}</div>
      <div className="mt-1 text-2xl font-bold text-white">{value}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}

function AnalysisCard({ item, index }: { item: DebugAnalysisItem; index: number }) {
  const [open, setOpen] = useState(false);
  const riskColor: Record<string, string> = {
    critical: "border-red-400",
    high:     "border-orange-400",
    medium:   "border-amber-300",
    low:      "border-gray-300",
  };

  return (
    <div className={`rounded-xl border-l-4 border border-slate-800 bg-slate-900/60 p-4 shadow-sm ${riskColor[item.risk_level] ?? "border-gray-300"}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-mono text-slate-500">#{index + 1}</span>
            <CategoryBadge category={item.root_cause_category} />
            {item.root_cause_subcategory && (
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-300">
                {item.root_cause_subcategory}
              </span>
            )}
            <ConfidenceMeter confidence={item.confidence} />
          </div>
          <p className="mt-2 text-sm text-slate-300">{item.explanation}</p>
        </div>
        <button
          onClick={() => setOpen(!open)}
          className="ml-2 shrink-0 text-xs text-blue-300 hover:underline"
        >
          {open ? "Daralt ▲" : "Fix Adımları ▼"}
        </button>
      </div>

      {open && (
        <div className="mt-3 space-y-3">
          {item.fix_steps.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Fix Adımları</p>
              <ol className="space-y-1">
                {item.fix_steps.map((step, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <span className="shrink-0 font-medium text-blue-400">{i + 1}.</span>
                    <span className="text-slate-300">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
          {item.estimated_fix_time && (
            <p className="text-xs text-slate-400">
              ⏱ Tahmini fix süresi: <strong>{item.estimated_fix_time}</strong>
            </p>
          )}
          {item.similar_tests_at_risk.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold text-amber-300">Risk Altındaki Benzer Testler</p>
              <ul className="space-y-0.5">
                {item.similar_tests_at_risk.map((t, i) => (
                  <li key={i} className="text-xs text-slate-400">• {t}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function DebugReportPage() {
  const projectId = useRouteParam("projectId");

  const [executions, setExecutions] = useState<Execution[]>([]);
  const [selectedExecId, setSelectedExecId] = useState("");
  const [loading, setLoading] = useState(false);
  const [debugResult, setDebugResult] = useState<DebugResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"analysis" | "patterns" | "allure">("analysis");
  const [exporting, setExporting] = useState(false);

  // Load executions for selector
  useEffect(() => {
    if (!projectId) return;
    fetch(`${API}/projects/${projectId}/executions`, {
      credentials: "include",
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then((data: Execution[] | { runs?: Execution[] }) => {
        const list = Array.isArray(data) ? data : (data.runs ?? []);
        setExecutions(list);
        if (list.length > 0) setSelectedExecId(list[0].id);
      })
      .catch(() => {
        // Use mock data if endpoint returns error
        const mockExecs: Execution[] = [
          { id: "exec-001", name: "Smoke Test Run", status: "completed", created_at: new Date().toISOString() },
          { id: "exec-002", name: "Regression Suite", status: "completed", created_at: new Date().toISOString() },
        ];
        setExecutions(mockExecs);
        setSelectedExecId(mockExecs[0].id);
      });
  }, [projectId]);

  const handleRunDebug = useCallback(async () => {
    if (!selectedExecId) return;
    setLoading(true);
    setError(null);
    setDebugResult(null);

    try {
      const res = await fetch(
        `${API}/projects/${projectId}/executions/${selectedExecId}/debug`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            execution_id: selectedExecId,
            generate_allure: true,
            results: [], // will be read from DB by backend
          }),
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Analiz başarısız");
      }

      const data: DebugResponse = await res.json();
      setDebugResult(data);
      setActiveTab("analysis");
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedExecId]);

  const handleAllureExport = useCallback(async () => {
    if (!debugResult) return;
    setExporting(true);
    try {
      // Build zip-like download from allure_results JSON
      const data = {
        allure_results: debugResult.allure_results,
        environment_properties: "",
      };
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `allure-results-${debugResult.execution_id.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }, [debugResult]);

  const health = debugResult?.overall_health ?? "unknown";
  const summary = debugResult?.summary;
  const analyses = debugResult?.analyses ?? [];
  const failedAnalyses = analyses.filter(a => a.root_cause_category !== "UNKNOWN" || a.explanation);

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4 overflow-auto">
      <PageHeader
        icon={<span className="text-base">🔍</span>}
        title="AI Debug Report"
        description="Başarısız koşuları kök neden, risk paterni ve önerilen düzeltme adımlarıyla inceleyin."
        right={debugResult ? <HealthBadge health={health} /> : undefined}
      />

      <FlowGuideCard
        projectId={projectId}
        stage="observe"
        title="Debug ve gözlem akışı"
        description="Önce koşuyu seçin, ardından AI analiziyle hata desenlerini ve sonraki aksiyonu netleştirin."
        nextLabel="Raporlara dön"
        nextHref={`/p/${projectId}/reports`}
        supportLinks={[
          { label: "Kosular", href: `/p/${projectId}/executions` },
          { label: "Execution detayi", href: `/p/${projectId}/executions` },
          { label: "AI Asistan", href: `/p/${projectId}/ai-chat` },
        ]}
      />

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="flex-1 min-w-48">
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Execution Seç
          </label>
          <select
            value={selectedExecId}
            onChange={(e) => setSelectedExecId(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
          >
            {executions.length === 0 && (
              <option value="">— Execution bulunamadı —</option>
            )}
            {executions.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name || `Execution ${e.id.slice(0, 8)}`} ({e.status})
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleRunDebug}
          disabled={loading || !selectedExecId}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Analiz ediliyor...
            </>
          ) : (
            <>🤖 AI Analizi Başlat</>
          )}
        </button>

        {debugResult && debugResult.allure_results.length > 0 && (
          <button
            onClick={handleAllureExport}
            disabled={exporting}
            className="flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800"
          >
            📦 Allure Export
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          ⚠ {error}
        </div>
      )}

      {/* Results */}
      {debugResult && (
        <>
          {/* Summary Stats */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <StatCard icon="🧪" label="Toplam Test"   value={summary?.total ?? 0}     color="border-slate-800 bg-slate-900/50" />
            <StatCard icon="✅" label="Başarılı"       value={summary?.passed ?? 0}    color="border-emerald-500/20 bg-emerald-500/10" />
            <StatCard icon="❌" label="Başarısız"      value={summary?.failed ?? 0}    color="border-red-500/20 bg-red-500/10" />
            <StatCard icon="⏭" label="Atlanan"        value={summary?.skipped ?? 0}   color="border-slate-800 bg-slate-900/50" />
            <StatCard icon="📊" label="Başarı Oranı"  value={`${summary?.pass_rate ?? 0}%`} color="border-blue-500/20 bg-blue-500/10" />
          </div>

          {/* AI Provider Badge */}
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>AI Sağlayıcı:</span>
            <span className={`rounded px-2 py-0.5 font-medium ${
              debugResult.fallback_used
                ? "bg-amber-500/10 text-amber-200 border border-amber-500/20"
                : "bg-emerald-500/10 text-emerald-200 border border-emerald-500/20"
            }`}>
              {debugResult.ai_provider} {debugResult.fallback_used ? "(fallback)" : ""}
            </span>
            <span className="text-slate-600">•</span>
            <span>{new Date(debugResult.generated_at).toLocaleString("tr-TR")}</span>
          </div>

          {/* Tabs */}
          <div className="border-b border-slate-800">
            <div className="flex gap-6">
              {(["analysis", "patterns", "allure"] as const).map((tab) => {
                const labels: Record<string, string> = {
                  analysis: `🔬 Analiz (${failedAnalyses.length})`,
                  patterns: `💡 Öneriler (${debugResult.recommended_actions.length})`,
                  allure:   `📦 Allure (${debugResult.allure_results.length})`,
                };
                return (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`border-b-2 pb-2 text-sm font-medium transition-colors ${
                      activeTab === tab
                        ? "border-blue-500 text-blue-300"
                        : "border-transparent text-slate-400 hover:text-white"
                    }`}
                  >
                    {labels[tab]}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Tab Content */}
          {activeTab === "analysis" && (
            <div className="space-y-3">
              {failedAnalyses.length === 0 ? (
                <div className="rounded-xl border border-dashed border-emerald-500/30 bg-emerald-500/10 p-8 text-center">
                  <div className="text-4xl mb-2">🎉</div>
                  <p className="font-medium text-emerald-200">Başarısız test bulunamadı!</p>
                  <p className="mt-1 text-sm text-slate-400">Tüm testler başarıyla geçti.</p>
                </div>
              ) : (
                failedAnalyses.map((item, i) => (
                  <AnalysisCard key={item.test_id} item={item} index={i} />
                ))
              )}
            </div>
          )}

          {activeTab === "patterns" && (
            <div className="space-y-4">
              {/* Key Patterns */}
              {debugResult.key_patterns.length > 0 && (
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
                  <h3 className="mb-3 font-semibold text-white">🔑 Tespit Edilen Örüntüler</h3>
                  <ul className="space-y-2">
                    {debugResult.key_patterns.map((p, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                        <span className="mt-0.5 text-blue-400">▸</span>
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {/* Recommended Actions */}
              {debugResult.recommended_actions.length > 0 && (
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
                  <h3 className="mb-3 font-semibold text-white">✅ Önerilen Aksiyonlar</h3>
                  <ol className="space-y-2">
                    {debugResult.recommended_actions.map((action, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-500/10 text-xs font-bold text-blue-300">
                          {i + 1}
                        </span>
                        <span className="text-slate-300">{action}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}

          {activeTab === "allure" && (
            <div className="space-y-3">
              <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-white">
                    📦 Allure Export — {debugResult.allure_results.length} sonuç
                  </h3>
                  <button
                    onClick={handleAllureExport}
                    className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
                  >
                    JSON İndir
                  </button>
                </div>
                <p className="mb-4 text-sm text-slate-400">
                  Bu JSON dosyasını <code className="rounded bg-slate-800 px-1">allure-results/</code> klasörüne koyarak
                  <code className="ml-1 rounded bg-slate-800 px-1">allure serve</code> komutuyla görüntüleyebilirsiniz.
                </p>
                <div className="max-h-80 overflow-auto rounded-lg bg-gray-900 p-4">
                  <pre className="text-xs text-green-400 whitespace-pre-wrap">
                    {JSON.stringify(debugResult.allure_results.slice(0, 3), null, 2)}
                    {debugResult.allure_results.length > 3 && `\n\n... (${debugResult.allure_results.length - 3} daha)`}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!debugResult && !loading && !error && (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 py-20">
          <div className="text-5xl mb-4">🤖</div>
          <h3 className="text-lg font-semibold text-white">AI Debug Analizi</h3>
          <p className="mt-2 max-w-sm text-center text-sm text-slate-400">
            Bir execution seçin ve "AI Analizi Başlat" butonuna tıklayın.
            Başarısız testler otomatik olarak analiz edilecek.
          </p>
          <div className="mt-6 flex gap-8 text-center">
            {[
              { icon: "🔬", label: "Kök Neden Analizi" },
              { icon: "🔧", label: "Fix Önerileri" },
              { icon: "📦", label: "Allure Export" },
            ].map((f) => (
              <div key={f.label} className="flex flex-col items-center gap-1">
                <div className="text-2xl">{f.icon}</div>
                <div className="text-xs text-slate-500">{f.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
