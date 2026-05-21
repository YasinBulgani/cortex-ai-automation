"use client";

import { useCallback, useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
} from "@/components/nexus";
import {
  useCoverageAnalysis,
  useCoverageGaps,
  useCoverageGapSuggestions,
  type CoverageGap,
  type CoverageGapSuggestion,
} from "@/lib/hooks/use-api-testing";
import {
  useUploadCoverage,
  useAnalyzeCoverage,
  useGenerateTests,
  useCoverageReports,
  useCoverageTrends,
  useBankingTargets,
  type CoverageReport as CUReport,
  type CoverageGapTarget,
  type GeneratedTest,
} from "@/lib/hooks/use-coverup";

type MatrixRow = {
  requirement_id: string;
  external_id: string;
  title: string;
  is_covered: boolean;
  scenario_ids: string[];
};

type CoverageMatrix = {
  coverage_percentage: number;
  total_requirements: number;
  covered_count: number;
  matrix: MatrixRow[];
  gaps: MatrixRow[];
};

export default function CoveragePage() {
  const projectId = useRouteParam("projectId");
  const [data, setData] = useState<CoverageMatrix | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    apiFetch<CoverageMatrix>(`/api/v1/tspm/projects/${projectId}/coverage-matrix`)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const pct = data ? Math.round(data.coverage_percentage) : 0;

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="coverage-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        }
        title="Kapsam Analizi"
        description="Gereksinim kapsam durumu"
      />

      {loading ? (
        <div className="flex-1 flex items-center justify-center py-16">
          <div className="flex items-center gap-3 text-slate-500">
            <div className="w-5 h-5 border-2 border-slate-700 border-t-blue-400 rounded-full animate-spin" />
            Yükleniyor…
          </div>
        </div>
      ) : !data ? (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16">
          <EmptyState icon="📊" title="Veri yok" description="Kapsam matrisi oluşturulamadı" />
        </div>
      ) : (
        <>
          {/* Coverage gauge */}
          <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5" data-testid="coverage-gauge">
            <div className="flex items-end justify-between mb-3">
              <div>
                <p className="text-sm font-medium text-slate-400">Kapsam Oranı</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {data.covered_count} / {data.total_requirements} gereksinim
                </p>
              </div>
              <span
                className={`text-4xl font-bold tabular-nums ${
                  pct >= 80 ? "text-emerald-400" : pct >= 50 ? "text-amber-400" : "text-red-400"
                }`}
              >
                {data.matrix.length === 0 ? (
                  <div className="p-8">
                    <EmptyState icon="📋" title="Matris verisi yok" description="Gereksinim ve senaryo oluşturarak matrisi doldurun" />
                  </div>
                ) : (
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-800">
                        <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">External ID</th>
                        <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Başlık</th>
                        <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
                        <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-right">Senaryo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.matrix.map(row => (
                        <tr key={row.requirement_id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                          <td className="px-4 py-3 font-mono text-xs text-slate-400">{row.external_id}</td>
                          <td className="px-4 py-3 text-sm text-white">{row.title}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${
                              row.is_covered
                                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                                : "bg-red-500/10 border-red-500/20 text-red-400"
                            }`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${row.is_covered ? "bg-emerald-400" : "bg-red-400"}`} />
                              {row.is_covered ? "Kapsanıyor" : "Kapsanmıyor"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm tabular-nums text-slate-400 text-right">
                            {row.scenario_ids?.length ?? 0}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </SectionCard>

              {/* BDD Gaps */}
              {data.gaps.length > 0 && (
                <SectionCard
                  title="BDD Kapsam Boşlukları"
                  icon={<svg className="w-3.5 h-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
                  right={<span className="text-red-400 text-xs font-medium">{data.gaps.length} boşluk</span>}
                  noPad
                >
                  {data.gaps.map(g => (
                    <div key={g.requirement_id} className="flex items-center gap-3 px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                      <span className="font-mono text-xs text-red-400">{g.external_id}</span>
                      <span className="text-sm text-slate-300">{g.title}</span>
                      <span className="ml-auto text-xs text-slate-500">senaryo yok</span>
                    </div>
                  ))}
                </SectionCard>
              )}
            </>
          )}
        </>
      )}

      {/* ─── API Endpoint Coverage Tab ────────────────────────────── */}
      {activeTab === "api" && (
        <>
          {apiLoading ? (
            <div className="flex justify-center py-16">
              <div className="w-6 h-6 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className={`h-full rounded-full transition-all ${
                  pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500"
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          {/* Gaps list */}
          {data.gaps.length > 0 && (
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden" data-testid="coverage-gaps">
              <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
                <h3 className="text-sm font-semibold text-red-400">Kapsam Boşlukları</h3>
                <span className="text-xs text-slate-500">{data.gaps.length} boşluk</span>
              </div>
              <div className="divide-y divide-slate-800">
                {data.gaps.map((g) => (
                  <div
                    key={g.requirement_id}
                    className="flex items-center gap-3 px-4 py-3 hover:bg-slate-800/30"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                    <span className="font-mono text-xs text-red-400 shrink-0">{g.external_id}</span>
                    <span className="text-sm text-slate-300 truncate">{g.title}</span>
                    <span className="ml-auto text-xs text-slate-500 shrink-0">senaryo yok</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Covered requirements summary */}
          <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden" data-testid="coverage-matrix">
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
              <h3 className="text-sm font-semibold">Gereksinim Listesi</h3>
              <span className="text-xs text-slate-500">{data.matrix.length} gereksinim</span>
            </div>
            {data.matrix.length === 0 ? (
              <div className="p-8">
                <EmptyState icon="📋" title="Matris verisi yok" description="Gereksinim ve senaryo oluşturun" />
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Endpoint</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Risk</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Şiddet</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Mevcut</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Eksik Tipler</th>
                  </tr>
                </thead>
                <tbody>
                  {data.matrix.map((row) => (
                    <tr key={row.requirement_id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                      <td className="px-4 py-3 font-mono text-xs text-slate-400">{row.external_id}</td>
                      <td className="px-4 py-3 text-sm text-white">{row.title}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${
                            row.is_covered
                              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                              : "bg-red-500/10 border-red-500/20 text-red-400"
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${row.is_covered ? "bg-emerald-400" : "bg-red-400"}`} />
                          {row.is_covered ? "Kapsanıyor" : "Kapsanmıyor"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm tabular-nums text-slate-400 text-right">
                        {row.scenario_ids?.length ?? 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </SectionCard>

          {/* AI Suggestions */}
          {suggestions.length > 0 && (
            <SectionCard
              title="AI Önerileri"
              icon={<svg className="w-3.5 h-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
              noPad
            >
              {suggestions.map((s, i) => (
                <div key={i} className="px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-sm font-mono text-slate-300">{s.endpoint}</span>
                    <span className={`px-2 py-0.5 rounded-full border text-xs font-medium ${SEVERITY_COLORS[s.gap_severity] ?? SEVERITY_COLORS.low}`}>
                      {s.gap_severity}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">{s.suggestion}</p>
                  <div className="flex gap-1 mt-1.5">
                    {s.missing_types.map(t => (
                      <span key={t} className="px-1.5 py-0.5 rounded bg-violet-500/10 border border-violet-500/20 text-violet-300 text-[10px]">{t}</span>
                    ))}
                  </div>
                </div>
              ))}
            </SectionCard>
          )}
        </div>
      )}

      {/* ─── Code Coverage (CoverUp) Tab ─────────────────────────── */}
      {activeTab === "code" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* Upload section */}
            <div className="lg:col-span-3 space-y-4">
              <SectionCard
                title="Kapsam Raporu Yükle"
                icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>}
              >
                {/* Drag & drop area */}
                <div
                  className={`relative rounded-xl border-2 border-dashed p-6 text-center transition-all cursor-pointer ${
                    cuDragOver
                      ? "border-violet-400 bg-violet-500/10"
                      : cuFile
                        ? "border-emerald-500/40 bg-emerald-500/5"
                        : "border-slate-700 bg-slate-900/40 hover:border-slate-500"
                  }`}
                  onDragOver={e => { e.preventDefault(); setCuDragOver(true); }}
                  onDragLeave={() => setCuDragOver(false)}
                  onDrop={e => {
                    e.preventDefault();
                    setCuDragOver(false);
                    const f = e.dataTransfer.files[0];
                    if (f) setCuFile(f);
                  }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".lcov,.json,.xml,.coverage"
                    onChange={e => {
                      const f = e.target.files?.[0];
                      if (f) setCuFile(f);
                    }}
                  />
                  {cuFile ? (
                    <div className="flex items-center justify-center gap-2">
                      <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                      <span className="text-sm text-emerald-300">{cuFile.name}</span>
                      <button
                        onClick={e => { e.stopPropagation(); setCuFile(null); }}
                        className="ml-2 text-xs text-slate-500 hover:text-red-400"
                      >
                        Kaldır
                      </button>
                    </div>
                  ) : (
                    <div>
                      <svg className="w-8 h-8 mx-auto text-slate-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                      <p className="text-sm text-slate-400">Dosyayı sürükleyip bırakın veya tıklayın</p>
                      <p className="text-xs text-slate-600 mt-1">LCOV, Istanbul JSON, Cobertura XML, coverage.py</p>
                    </div>
                  )}
                </div>

                {/* Inputs */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Format</label>
                    <select
                      value={cuFormat}
                      onChange={e => setCuFormat(e.target.value)}
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none"
                    >
                      {FORMAT_OPTIONS.map(o => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Proje Adı</label>
                    <input
                      value={cuProject}
                      onChange={e => setCuProject(e.target.value)}
                      placeholder="ornek-proje"
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-violet-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Commit SHA</label>
                    <input
                      value={cuCommit}
                      onChange={e => setCuCommit(e.target.value)}
                      placeholder="abc1234"
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white font-mono placeholder:text-slate-600 focus:border-violet-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Branch</label>
                    <input
                      value={cuBranch}
                      onChange={e => setCuBranch(e.target.value)}
                      placeholder="main"
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white font-mono placeholder:text-slate-600 focus:border-violet-500 focus:outline-none"
                    />
                  </div>
                </div>

                <button
                  onClick={handleCuUpload}
                  disabled={!cuFile || !cuProject || uploadMut.isPending}
                  className="mt-4 flex items-center gap-2 px-5 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {uploadMut.isPending ? (
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                  )}
                  Yükle & Analiz Et
                </button>
              </SectionCard>

              {/* Coverage Summary */}
              {cuActiveReport && (
                <>
                  <div className="grid grid-cols-4 gap-3">
                    {/* Line Rate Gauge */}
                    <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-4 col-span-1">
                      <p className="text-xs text-slate-500 mb-2">Satır Kapsam</p>
                      <div className="relative w-20 h-20 mx-auto">
                        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                          <circle cx="40" cy="40" r="34" fill="none" strokeWidth="8" className="stroke-slate-800" />
                          <circle
                            cx="40" cy="40" r="34" fill="none" strokeWidth="8"
                            strokeLinecap="round"
                            className={rateBg(cuActiveReport.summary.line_rate * 100).replace("bg-", "stroke-")}
                            strokeDasharray={`${cuActiveReport.summary.line_rate * 213.6} 213.6`}
                          />
                        </svg>
                        <span className={`absolute inset-0 flex items-center justify-center text-lg font-bold ${rateColor(cuActiveReport.summary.line_rate * 100)}`}>
                          {Math.round(cuActiveReport.summary.line_rate * 100)}%
                        </span>
                      </div>
                    </div>
                    <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
                      <p className="text-xs text-slate-500 mb-1">Branch Kapsam</p>
                      <p className={`text-2xl font-bold ${rateColor(cuActiveReport.summary.branch_rate * 100)}`}>
                        {Math.round(cuActiveReport.summary.branch_rate * 100)}%
                      </p>
                      <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                        <div className={`h-full rounded-full ${rateBg(cuActiveReport.summary.branch_rate * 100)}`} style={{ width: `${cuActiveReport.summary.branch_rate * 100}%` }} />
                      </div>
                    </div>
                    <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
                      <p className="text-xs text-slate-500 mb-1">Fonksiyon Kapsam</p>
                      <p className={`text-2xl font-bold ${rateColor(cuActiveReport.summary.function_rate * 100)}`}>
                        {Math.round(cuActiveReport.summary.function_rate * 100)}%
                      </p>
                      <p className="text-xs text-slate-600 mt-1">
                        {cuActiveReport.summary.covered_functions}/{cuActiveReport.summary.total_functions} fonksiyon
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
                      <p className="text-xs text-slate-500 mb-1">Toplam Dosya</p>
                      <p className="text-2xl font-bold text-white">{cuActiveReport.summary.total_files}</p>
                      <p className="text-xs text-slate-600 mt-1">
                        {cuActiveReport.summary.covered_lines}/{cuActiveReport.summary.total_lines} satır
                      </p>
                    </div>
                  </div>

                  {/* File Table */}
                  <SectionCard
                    title="Dosya Kapsam Detayları"
                    icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
                    right={<span className="text-xs text-slate-500">{cuActiveReport.files.length} dosya</span>}
                    noPad
                  >
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-slate-800">
                          <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Dosya</th>
                          <th className="px-3 py-2.5 text-xs font-medium text-slate-400 text-right">Satır</th>
                          <th className="px-3 py-2.5 text-xs font-medium text-slate-400 text-right">Kapsanan</th>
                          <th className="px-3 py-2.5 text-xs font-medium text-slate-400 text-right">Eksik</th>
                          <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Satır Kapsam</th>
                          <th className="px-3 py-2.5 text-xs font-medium text-slate-400 text-right">Branch</th>
                          <th className="px-3 py-2.5 text-xs font-medium text-slate-400 text-right">Fonksiyon</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cuActiveReport.files.map(f => {
                          const lr = Math.round(f.line_rate * 100);
                          const expanded = cuExpandedFile === f.file_path;
                          return (
                            <tr key={f.file_path} className="group">
                              <td colSpan={7} className="p-0">
                                <div
                                  className="flex items-center border-b border-slate-800 hover:bg-slate-800/30 cursor-pointer"
                                  onClick={() => setCuExpandedFile(expanded ? null : f.file_path)}
                                >
                                  <td className="px-4 py-3 text-sm font-mono text-slate-300 truncate max-w-[260px]">
                                    <span className="flex items-center gap-1.5">
                                      <svg className={`w-3 h-3 text-slate-600 transition-transform ${expanded ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                                      {f.file_path}
                                    </span>
                                  </td>
                                  <td className="px-3 py-3 text-xs text-slate-400 text-right tabular-nums">{f.total_lines}</td>
                                  <td className="px-3 py-3 text-xs text-emerald-400 text-right tabular-nums">{f.covered_lines}</td>
                                  <td className="px-3 py-3 text-xs text-red-400 text-right tabular-nums">{f.missed_lines}</td>
                                  <td className="px-4 py-3">
                                    <div className="flex items-center gap-2">
                                      <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                                        <div className={`h-full rounded-full ${rateBg(lr)}`} style={{ width: `${lr}%` }} />
                                      </div>
                                      <span className={`text-xs tabular-nums ${rateColor(lr)}`}>{lr}%</span>
                                    </div>
                                  </td>
                                  <td className="px-3 py-3 text-xs text-slate-400 text-right tabular-nums">{Math.round(f.branch_rate * 100)}%</td>
                                  <td className="px-3 py-3 text-xs text-slate-400 text-right tabular-nums">{f.covered_functions}/{f.total_functions}</td>
                                </div>
                                {/* Expanded detail */}
                                {expanded && (
                                  <div className="px-6 py-3 bg-slate-900/60 border-b border-slate-800 space-y-3">
                                    {f.missed_line_numbers.length > 0 && (
                                      <div>
                                        <p className="text-xs font-medium text-slate-500 mb-1.5">Kapsanmayan Satırlar</p>
                                        <div className="flex flex-wrap gap-1">
                                          {f.missed_line_numbers.map(ln => (
                                            <span key={ln} className="px-1.5 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 font-mono text-[11px]">
                                              {ln}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                    {f.uncovered_functions.length > 0 && (
                                      <div>
                                        <p className="text-xs font-medium text-slate-500 mb-1.5">Kapsanmayan Fonksiyonlar</p>
                                        <div className="flex flex-wrap gap-1.5">
                                          {f.uncovered_functions.map(fn => (
                                            <span key={fn} className="px-2 py-0.5 rounded bg-orange-500/10 border border-orange-500/20 text-orange-300 font-mono text-xs">
                                              {fn}()
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                    {f.complexity !== undefined && (
                                      <p className="text-xs text-slate-600">Karmasıklık: <span className="text-slate-400">{f.complexity}</span></p>
                                    )}
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </SectionCard>
                </>
              )}
            </div>

            {/* Report list sidebar */}
            <div className="lg:col-span-1">
              <SectionCard
                title="Raporlar"
                icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
                noPad
              >
                {cuReports.length === 0 ? (
                  <div className="p-4">
                    <EmptyState icon="📂" title="Rapor yok" description="Bir kapsam dosyası yükleyin" />
                  </div>
                ) : (
                  <div className="max-h-[480px] overflow-y-auto">
                    {cuReports.map(r => {
                      const lr = Math.round(r.summary.line_rate * 100);
                      const isActive = cuActiveReport?.report_id === r.report_id;
                      return (
                        <button
                          key={r.report_id}
                          type="button"
                          onClick={() => setCuActiveReport(r)}
                          className={`w-full text-left px-4 py-3 border-b border-slate-800 last:border-0 transition-colors ${
                            isActive ? "bg-violet-500/10" : "hover:bg-slate-800/30"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className={`text-sm font-bold tabular-nums ${rateColor(lr)}`}>{lr}%</span>
                            <span className="text-[10px] text-slate-600">{r.format}</span>
                          </div>
                          <p className="text-xs text-slate-400 truncate">{r.project_name}</p>
                          {r.commit_sha && (
                            <p className="text-[10px] font-mono text-slate-600 mt-0.5">{r.commit_sha.slice(0, 8)}</p>
                          )}
                          <p className="text-[10px] text-slate-600 mt-0.5">
                            {new Date(r.created_at).toLocaleDateString("tr-TR")}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                )}
              </SectionCard>
            </div>
          </div>
        </div>
      )}

      {/* ─── Test Generator Tab ──────────────────────────────────── */}
      {activeTab === "generate" && (
        <div className="space-y-4">
          {cuReports.length === 0 ? (
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16">
              <EmptyState
                icon="📊"
                title="Kapsam raporu bulunamadı"
                description="Test üretmek için önce Kod Kapsam sekmesinden bir rapor yükleyin"
              />
            </div>
          ) : (
            <>
              {/* Config section */}
              <SectionCard
                title="Hedef Yapılandırma"
                icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>}
              >
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Rapor</label>
                    <select
                      value={genReportId}
                      onChange={e => setGenReportId(e.target.value)}
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none"
                    >
                      <option value="">Rapor seçin...</option>
                      {cuReports.map(r => (
                        <option key={r.report_id} value={r.report_id}>
                          {r.project_name} — {Math.round(r.summary.line_rate * 100)}% ({new Date(r.created_at).toLocaleDateString("tr-TR")})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Framework</label>
                    <select
                      value={genFramework}
                      onChange={e => setGenFramework(e.target.value)}
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none"
                    >
                      {FRAMEWORK_OPTIONS.map(o => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">Dil</label>
                    <select
                      value={genLanguage}
                      onChange={e => setGenLanguage(e.target.value)}
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-violet-500 focus:outline-none"
                    >
                      {LANGUAGE_OPTIONS.map(o => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <div
                        onClick={() => setGenBanking(v => !v)}
                        className={`relative w-10 h-5 rounded-full transition-colors ${genBanking ? "bg-violet-600" : "bg-slate-700"}`}
                      >
                        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${genBanking ? "left-5" : "left-0.5"}`} />
                      </div>
                      <span className="text-xs text-slate-400">Bankacılık Bağlamı</span>
                    </label>
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={handleAnalyzeTargets}
                      disabled={!genReportId || analyzeMut.isPending}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {analyzeMut.isPending ? (
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      ) : (
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                      )}
                      Hedefleri Bul
                    </button>
                  </div>
                </div>
              </SectionCard>

              {/* Gap Targets Table */}
              {genTargets.length > 0 && (
                <SectionCard
                  title="Kapsam Boşluk Hedefleri"
                  icon={<svg className="w-3.5 h-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
                  right={
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-500">{genSelected.size}/{genTargets.length} seçili</span>
                      <button
                        onClick={() => {
                          if (genSelected.size === genTargets.length) setGenSelected(new Set());
                          else setGenSelected(new Set(genTargets.map((_, i) => i)));
                        }}
                        className="text-xs text-violet-400 hover:text-violet-300"
                      >
                        {genSelected.size === genTargets.length ? "Hiçbirini Seçme" : "Tümünü Seç"}
                      </button>
                    </div>
                  }
                  noPad
                >
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-800">
                        <th className="px-4 py-2.5 w-10"></th>
                        <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Dosya</th>
                        <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Fonksiyon</th>
                        <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Satırlar</th>
                        <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tip</th>
                        <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Risk</th>
                        <th className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Faktörler</th>
                        <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Öneri</th>
                      </tr>
                    </thead>
                    <tbody>
                      {genTargets.map((t, i) => (
                        <tr key={i} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                          <td className="px-4 py-3">
                            <input
                              type="checkbox"
                              checked={genSelected.has(i)}
                              onChange={() => toggleGenTarget(i)}
                              className="w-3.5 h-3.5 rounded border-slate-600 bg-slate-900 text-violet-500 focus:ring-violet-500 focus:ring-offset-0"
                            />
                          </td>
                          <td className="px-3 py-3 text-xs font-mono text-slate-300 truncate max-w-[160px]">{t.file_path}</td>
                          <td className="px-3 py-3 text-xs font-mono text-slate-400">{t.function_name ?? "—"}</td>
                          <td className="px-3 py-3 text-xs text-slate-500 tabular-nums">{t.start_line}-{t.end_line}</td>
                          <td className="px-3 py-3">
                            <span className={`px-2 py-0.5 rounded-full border text-[10px] font-medium ${GAP_TYPE_COLORS[t.gap_type] ?? "bg-slate-800 border-slate-700 text-slate-400"}`}>
                              {t.gap_type.replace(/_/g, " ")}
                            </span>
                          </td>
                          <td className="px-3 py-3">
                            <div className="flex items-center gap-1.5">
                              <div className="w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                                <div className={`h-full rounded-full ${riskColor(t.risk_score)}`} style={{ width: `${t.risk_score * 10}%` }} />
                              </div>
                              <span className="text-xs text-slate-400 tabular-nums">{t.risk_score}</span>
                            </div>
                          </td>
                          <td className="px-3 py-3">
                            <div className="flex flex-wrap gap-1">
                              {t.risk_factors.slice(0, 3).map(rf => (
                                <span key={rf} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">{rf}</span>
                              ))}
                              {t.risk_factors.length > 3 && (
                                <span className="text-[10px] text-slate-600">+{t.risk_factors.length - 3}</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-xs text-slate-500 max-w-[200px] truncate" title={t.suggestion}>{t.suggestion}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </SectionCard>
              )}

              {/* Generate button */}
              {genTargets.length > 0 && genSelected.size > 0 && (
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleGenerateTests}
                    disabled={generateMut.isPending}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {generateMut.isPending ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
                    )}
                    Test Üret ({genSelected.size} hedef)
                  </button>
                  {generateMut.isPending && (
                    <span className="text-xs text-slate-500">AI ile test üretiliyor...</span>
                  )}
                </div>
              )}

              {/* Generated Tests Results */}
              {genResults.length > 0 && (
                <div className="space-y-3">
                  {/* Summary bar */}
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-5 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div>
                        <p className="text-xs text-slate-500">Üretilen Test</p>
                        <p className="text-lg font-bold text-emerald-400">{genResults.length}</p>
                      </div>
                      <div className="w-px h-8 bg-slate-800" />
                      <div>
                        <p className="text-xs text-slate-500">Tahmini Toplam Kazanım</p>
                        <p className="text-lg font-bold text-emerald-400">
                          +{genResults.reduce((s, r) => s + r.estimated_coverage_gain, 0).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-medium">
                      {genFramework} / {genLanguage}
                    </span>
                  </div>

                  {/* Test cards */}
                  {genResults.map((r, i) => {
                    const isExpanded = genExpandedIdx === i;
                    return (
                      <div key={i} className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setGenExpandedIdx(isExpanded ? null : i)}
                          className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-800/30 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <svg className={`w-3.5 h-3.5 text-slate-600 transition-transform ${isExpanded ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                            <div className="text-left">
                              <p className="text-sm font-mono text-slate-300">{r.target_file}</p>
                              {r.target_function && (
                                <p className="text-xs text-slate-500 mt-0.5">{r.target_function}()</p>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 text-[10px] font-medium">
                              {r.test_framework}
                            </span>
                            <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[10px] font-medium">
                              +{r.estimated_coverage_gain.toFixed(1)}%
                            </span>
                          </div>
                        </button>
                        {isExpanded && (
                          <div className="border-t border-slate-800">
                            <div className="flex items-center justify-between px-4 py-2 bg-slate-900/80">
                              <span className="text-xs font-mono text-slate-500">{r.test_file_path}</span>
                              <button
                                onClick={() => handleCopyCode(r.test_code, i)}
                                className="flex items-center gap-1 text-xs text-slate-500 hover:text-white transition-colors"
                              >
                                {genCopied === i ? (
                                  <>
                                    <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                                    <span className="text-emerald-400">Kopyalandı</span>
                                  </>
                                ) : (
                                  <>
                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                                    Kopyala
                                  </>
                                )}
                              </button>
                            </div>
                            <pre className="px-4 py-3 text-xs font-mono text-slate-300 bg-slate-950 overflow-x-auto max-h-[400px] overflow-y-auto leading-relaxed">
                              {r.test_code}
                            </pre>
                            {r.lines_targeted.length > 0 && (
                              <div className="px-4 py-2 border-t border-slate-800 bg-slate-900/60">
                                <span className="text-xs text-slate-500">Hedeflenen satırlar: </span>
                                <span className="text-xs font-mono text-slate-400">
                                  {r.lines_targeted.length <= 10
                                    ? r.lines_targeted.join(", ")
                                    : `${r.lines_targeted.slice(0, 10).join(", ")} ... (+${r.lines_targeted.length - 10})`
                                  }
                                </span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
