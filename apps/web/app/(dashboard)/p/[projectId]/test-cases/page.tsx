"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { apiFetch } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

type TestCaseStep = { order: number; action: string; expected: string };

type TestCase = {
  id: string;
  title: string;
  description: string | null;
  module_name: string | null;
  test_type: string;
  priority: string;
  risk_level: string;
  steps: TestCaseStep[];
  expected_result: string | null;
  tags: string[];
  review_status: string;
};

type GenerateResponse = {
  batch_id: string;
  total_generated: number;
  test_cases: TestCase[];
  message: string;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-300 border-red-700/40",
  high: "bg-orange-500/20 text-orange-300 border-orange-700/40",
  medium: "bg-yellow-500/20 text-yellow-300 border-yellow-700/40",
  low: "bg-slate-500/20 text-slate-300 border-slate-700/40",
};

const TYPE_LABELS: Record<string, string> = {
  functional: "Fonksiyonel",
  regression: "Regresyon",
  smoke: "Duman",
  edge_case: "Kenar Durum",
  negative: "Negatif",
};

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  pending: { label: "Bekliyor", cls: "bg-yellow-900/30 text-yellow-400" },
  approved: { label: "Onaylı", cls: "bg-emerald-900/30 text-emerald-400" },
  rejected: { label: "Reddedildi", cls: "bg-red-900/30 text-red-400" },
  edited: { label: "Düzenlendi", cls: "bg-blue-900/30 text-blue-400" },
};

function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span
      className={`rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${PRIORITY_COLORS[priority] || PRIORITY_COLORS.medium}`}
    >
      {priority}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_BADGE[status] || STATUS_BADGE.pending;
  return (
    <span className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function TestCasesPage() {
  const projectId = useRouteParam("projectId");

  const [analysisText, setAnalysisText] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadTestCases = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<TestCase[]>(
        `/api/v1/tspm/projects/${projectId}/test-cases`,
      );
      setTestCases(data || []);
    } catch {
      setTestCases([]);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadTestCases();
  }, [loadTestCases]);

  const handleGenerate = async () => {
    if (!analysisText.trim()) return;
    setGenerating(true);
    setError(null);
    setMessage(null);
    try {
      const res = await apiFetch<GenerateResponse>(
        `/api/v1/tspm/projects/${projectId}/test-cases/generate`,
        {
          method: "POST",
          json: {
            source_type: "text",
            source_name: "Manuel giriş",
            analysis_text: analysisText,
          },
        },
      );
      setMessage(res.message);
      setTestCases(res.test_cases);
      setAnalysisText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Üretim başarısız");
    } finally {
      setGenerating(false);
    }
  };

  const totalCount = testCases.length;
  const approvedCount = testCases.filter(
    (tc) => tc.review_status === "approved",
  ).length;

  return (
    <div
      className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4"
      data-testid="test-cases-page"
    >
      <PageHeader
        icon={<span className="text-base">🧪</span>}
        title="AI Test Case Tasarimi"
        description="Analiz metninden AI ile test case üretin ve inceleyin."
        right={
          totalCount > 0 ? (
            <div className="flex items-center gap-3 text-xs">
              <span className="text-slate-400">{totalCount} test case</span>
              <span className="text-emerald-400">{approvedCount} onaylı</span>
            </div>
          ) : undefined
        }
      />

      {/* ── Generate Section ─────────────────────────────────────────────── */}
      <div
        className="rounded-xl border border-slate-800 bg-slate-900/50 p-5"
        data-testid="generate-section"
      >
        <h2 className="text-sm font-semibold text-white mb-3">
          Yeni Test Case Üretimi
        </h2>

        <textarea
          value={analysisText}
          onChange={(e) => setAnalysisText(e.target.value)}
          rows={6}
          placeholder="Sistem analizi veya gereksinim belgesini buraya yapıştırın..."
          className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none font-mono text-xs mb-3"
          data-testid="analysis-input"
        />

        {error && (
          <div className="mb-3 rounded-lg border border-red-700/40 bg-red-950/30 px-4 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        {message && (
          <div className="mb-3 rounded-lg border border-emerald-700/40 bg-emerald-950/30 px-4 py-2 text-sm text-emerald-300">
            {message}
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={generating || !analysisText.trim()}
          className={`rounded-lg px-5 py-2.5 text-sm font-semibold transition flex items-center gap-2 ${
            generating || !analysisText.trim()
              ? "bg-slate-700 text-slate-500 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-500"
          }`}
          data-testid="generate-button"
        >
          {generating ? (
            <>
              <svg
                className="h-4 w-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeDasharray="31.4"
                  strokeDashoffset="10"
                />
              </svg>
              AI Üretiyor...
            </>
          ) : (
            "AI ile Üret"
          )}
        </button>
      </div>

      {/* ── Test Cases List ──────────────────────────────────────────────── */}
      <div
        className="flex-1 rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden"
        data-testid="test-cases-list"
      >
        {loading ? (
          <div className="flex items-center justify-center py-16 text-slate-500 text-sm">
            Yükleniyor...
          </div>
        ) : testCases.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-3 text-3xl">🧪</div>
            <p className="text-slate-400 text-sm">Henüz test case yok</p>
            <p className="text-slate-500 text-xs mt-1">
              Yukarıdaki alana analiz metni girin ve AI ile üretin.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {testCases.map((tc) => (
              <div
                key={tc.id}
                className="px-5 py-4 hover:bg-slate-800/30 transition cursor-pointer"
                onClick={() =>
                  setExpandedId(expandedId === tc.id ? null : tc.id)
                }
                data-testid={`test-case-${tc.id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <PriorityBadge priority={tc.priority} />
                      <span className="rounded-md bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                        {TYPE_LABELS[tc.test_type] || tc.test_type}
                      </span>
                      {tc.module_name && (
                        <span className="rounded-md bg-indigo-900/30 px-1.5 py-0.5 text-[10px] text-indigo-300">
                          {tc.module_name}
                        </span>
                      )}
                      <StatusBadge status={tc.review_status} />
                    </div>
                    <h3 className="text-sm font-medium text-white">
                      {tc.title}
                    </h3>
                    {tc.description && (
                      <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
                        {tc.description}
                      </p>
                    )}
                  </div>
                  <span className="text-slate-600 text-xs shrink-0">
                    {expandedId === tc.id ? "▾" : "▸"}
                  </span>
                </div>

                {expandedId === tc.id && (
                  <div className="mt-3 rounded-lg bg-slate-950/50 p-3 space-y-2">
                    {tc.steps?.length > 0 &&
                      tc.steps.map((step, i) => (
                        <div key={i} className="flex gap-2 text-xs">
                          <span className="text-slate-600 w-4 shrink-0">
                            {step.order}.
                          </span>
                          <span className="text-slate-300 flex-1">
                            {step.action}
                          </span>
                          {step.expected && (
                            <span className="text-emerald-400 shrink-0">
                              → {step.expected}
                            </span>
                          )}
                        </div>
                      ))}
                    {tc.expected_result && (
                      <p className="text-xs text-emerald-400 border-t border-slate-800 pt-2">
                        Beklenen: {tc.expected_result}
                      </p>
                    )}
                    {tc.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {tc.tags.map((tag, i) => (
                          <span
                            key={i}
                            className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400"
                          >
                            #{tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
