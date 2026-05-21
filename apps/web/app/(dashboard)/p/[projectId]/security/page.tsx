"use client";

import { useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import { useApiSpecs } from "@/lib/hooks/use-api-testing";

// ── Types ──────────────────────────────────────────────────────────

interface SecurityFinding {
  owasp_category: string;
  owasp_name: string;
  severity: string;
  title: string;
  description: string;
  recommendation: string;
  confidence: number;
  banking_impact: string;
}

interface ComplianceStatus {
  passed: number;
  failed: number;
  checks: string[];
}

interface VulnerableEndpoint {
  endpoint_id: string;
  method: string;
  path: string;
  finding_count: number;
  security_score: number;
}

interface SecurityDashboard {
  total_endpoints: number;
  scanned_endpoints: number;
  findings_by_severity: Record<string, number>;
  findings_by_owasp: Record<string, number>;
  avg_security_score: number;
  top_vulnerable_endpoints: VulnerableEndpoint[];
  compliance_status: Record<string, ComplianceStatus>;
  recommendations: string[];
}

interface EndpointScanResult {
  endpoint_id: string;
  method: string;
  path: string;
  risk_level: string;
  findings: SecurityFinding[];
  security_score: number;
  test_suggestions: Array<{ title: string; test_type: string; owasp_category: string }>;
}

interface SpecScanResult {
  spec_id: string;
  spec_name: string;
  total_endpoints: number;
  endpoints_scanned: number;
  total_findings: number;
  findings_by_severity: Record<string, number>;
  avg_security_score: number;
  endpoint_results: EndpointScanResult[];
}

// ── Constants ──────────────────────────────────────────────────────

const BASE = (pid: string) => `/api/v1/api-testing/projects/${pid}`;

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 border-red-500/20 text-red-400",
  high: "bg-orange-500/10 border-orange-500/20 text-orange-400",
  medium: "bg-amber-500/10 border-amber-500/20 text-amber-400",
  low: "bg-slate-500/10 border-slate-500/20 text-slate-400",
  info: "bg-blue-500/10 border-blue-500/20 text-blue-400",
};

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-amber-500",
  low: "bg-slate-500",
  info: "bg-blue-500",
};

const COMPLIANCE_LABELS: Record<string, string> = {
  kvkk: "KVKK",
  bddk: "BDDK",
  pci_dss: "PCI-DSS",
};

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-emerald-500/20 text-emerald-400",
  POST: "bg-blue-500/20 text-blue-400",
  PUT: "bg-amber-500/20 text-amber-400",
  DELETE: "bg-red-500/20 text-red-400",
  PATCH: "bg-purple-500/20 text-purple-400",
};

// ── Hooks ──────────────────────────────────────────────────────────

function useSecurityDashboard(projectId: string | undefined) {
  return useQuery({
    queryKey: ["api-testing", projectId, "security-dashboard"],
    queryFn: () => apiFetch<SecurityDashboard>(`${BASE(projectId!)}/security/dashboard`),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

function useScanSpec(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (specId: string) =>
      apiFetch<SpecScanResult>(`${BASE(projectId)}/security/scan/spec/${specId}`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["api-testing", projectId, "security-dashboard"] });
    },
  });
}

function useGenerateSecurityTests(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { endpoint_ids?: string[]; owasp_categories?: string[] }) =>
      apiFetch<{ generated_count: number; test_cases: Array<{ id: string; title: string }> }>(
        `${BASE(projectId)}/security/generate-tests`,
        { method: "POST", json: args },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["api-testing", projectId] });
    },
  });
}

// ── Page ───────────────────────────────────────────────────────────

type TabId = "dashboard" | "scan";

export default function SecurityPage() {
  const projectId = useRouteParam("projectId");
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [scanResult, setScanResult] = useState<SpecScanResult | null>(null);

  const { data: dashboard, isLoading } = useSecurityDashboard(projectId);
  const { data: specs = [] } = useApiSpecs(projectId);
  const scanMut = useScanSpec(projectId);
  const genMut = useGenerateSecurityTests(projectId);

  const secScore = dashboard ? Math.round(dashboard.avg_security_score) : 0;

  async function handleScanSpec(specId: string) {
    try {
      const result = await scanMut.mutateAsync(specId);
      setScanResult(result);
      setActiveTab("scan");
    } catch { /* */ }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="security-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        }
        title="Güvenlik Tarama"
        description="OWASP API Top-10 güvenlik analizi ve bankacılık uyumluluk kontrolü"
        right={
          specs.length > 0 ? (
            <div className="flex items-center gap-2">
              <select
                id="scan-spec"
                className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-white"
                defaultValue=""
              >
                <option value="" disabled>Spec seç...</option>
                {specs.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <button
                onClick={() => {
                  const sel = (document.getElementById("scan-spec") as HTMLSelectElement)?.value;
                  if (sel) handleScanSpec(sel);
                }}
                disabled={scanMut.isPending}
                className="flex items-center gap-2 px-4 py-1.5 text-sm font-semibold text-red-300 border border-red-500/30 rounded-xl hover:bg-red-500/10 transition-all disabled:opacity-50"
              >
                {scanMut.isPending ? (
                  <div className="w-3.5 h-3.5 border-2 border-red-300/30 border-t-red-300 rounded-full animate-spin" />
                ) : (
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                )}
                Tara
              </button>
            </div>
          ) : undefined
        }
      />

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900/40 border border-slate-700 rounded-xl p-1 w-fit">
        <button
          onClick={() => setActiveTab("dashboard")}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${activeTab === "dashboard" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"}`}
        >
          Dashboard
        </button>
        <button
          onClick={() => setActiveTab("scan")}
          disabled={!scanResult}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed ${activeTab === "scan" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"}`}
        >
          Tarama Sonuçları
        </button>
      </div>

      {/* ─── Dashboard Tab ──────────────────────────────────────── */}
      {activeTab === "dashboard" && (
        <>
          {isLoading ? (
            <div className="flex justify-center py-16">
              <div className="w-6 h-6 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
            </div>
          ) : !dashboard ? (
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16">
              <EmptyState icon="🛡️" title="Güvenlik verisi yok" description="Bir API spec tarayarak başlayın" />
            </div>
          ) : (
            <>
              {/* Security Score + Stats */}
              <div className="grid grid-cols-5 gap-3">
                <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
                  <p className="text-xs text-slate-400 mb-1">Güvenlik Skoru</p>
                  <p className={`text-2xl font-bold ${secScore >= 80 ? "text-emerald-400" : secScore >= 50 ? "text-amber-400" : "text-red-400"}`}>
                    {secScore}/100
                  </p>
                </div>
                {["critical", "high", "medium", "low"].map((sev) => (
                  <div key={sev} className={`rounded-xl border px-4 py-3 ${
                    sev === "critical" ? "border-red-500/20 bg-red-500/5" :
                    sev === "high" ? "border-orange-500/20 bg-orange-500/5" :
                    sev === "medium" ? "border-amber-500/20 bg-amber-500/5" :
                    "border-slate-700 bg-slate-900/40"
                  }`}>
                    <p className="text-xs text-slate-400 mb-1 capitalize">{sev}</p>
                    <p className={`text-2xl font-bold ${
                      sev === "critical" ? "text-red-400" :
                      sev === "high" ? "text-orange-400" :
                      sev === "medium" ? "text-amber-400" :
                      "text-slate-300"
                    }`}>{dashboard.findings_by_severity[sev] ?? 0}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* OWASP Distribution */}
                <SectionCard
                  title="OWASP API Top-10 Dağılımı"
                  icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" /></svg>}
                  noPad
                >
                  {Object.entries(dashboard.findings_by_owasp).length === 0 ? (
                    <div className="p-6"><EmptyState icon="✅" title="Bulgu yok" description="OWASP bulgusu tespit edilmedi" /></div>
                  ) : (
                    Object.entries(dashboard.findings_by_owasp)
                      .sort(([, a], [, b]) => b - a)
                      .map(([cat, count]) => (
                        <div key={cat} className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800 last:border-0">
                          <span className="text-sm font-mono text-slate-300">{cat}</span>
                          <span className="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium">
                            {count}
                          </span>
                        </div>
                      ))
                  )}
                </SectionCard>

                {/* Compliance Status */}
                <SectionCard
                  title="Bankacılık Uyumluluk"
                  icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>}
                  noPad
                >
                  {Object.entries(dashboard.compliance_status).map(([key, status]) => {
                    const total = status.passed + status.failed;
                    const rate = total > 0 ? Math.round((status.passed / total) * 100) : 0;
                    return (
                      <div key={key} className="px-4 py-3 border-b border-slate-800 last:border-0">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-medium text-white">{COMPLIANCE_LABELS[key] ?? key}</span>
                          <span className={`text-xs font-bold ${rate >= 80 ? "text-emerald-400" : rate >= 50 ? "text-amber-400" : "text-red-400"}`}>
                            {rate}%
                          </span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${rate >= 80 ? "bg-emerald-500" : rate >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                            style={{ width: `${rate}%` }}
                          />
                        </div>
                        <div className="flex gap-2 mt-1">
                          <span className="text-[10px] text-emerald-400">{status.passed} geçti</span>
                          <span className="text-[10px] text-red-400">{status.failed} kaldı</span>
                        </div>
                      </div>
                    );
                  })}
                </SectionCard>
              </div>

              {/* Top vulnerable endpoints */}
              {dashboard.top_vulnerable_endpoints.length > 0 && (
                <SectionCard
                  title="En Kırılgan Endpoint'ler"
                  icon={<svg className="w-3.5 h-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
                  right={
                    <button
                      onClick={() => genMut.mutate({})}
                      disabled={genMut.isPending}
                      className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-violet-300 border border-violet-500/30 rounded-lg hover:bg-violet-500/10 transition-all disabled:opacity-50"
                    >
                      {genMut.isPending ? (
                        <div className="w-3 h-3 border-2 border-violet-300/30 border-t-violet-300 rounded-full animate-spin" />
                      ) : (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                      )}
                      Test Üret
                    </button>
                  }
                  noPad
                >
                  {genMut.data && (
                    <div className="px-4 py-2 bg-emerald-500/5 border-b border-emerald-500/20 text-xs text-emerald-400">
                      {genMut.data.generated_count} güvenlik testi üretildi
                    </div>
                  )}
                  {dashboard.top_vulnerable_endpoints.map((ep) => (
                    <div key={ep.endpoint_id} className="flex items-center justify-between px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${METHOD_COLORS[ep.method] ?? "bg-slate-800 text-slate-300"}`}>{ep.method}</span>
                        <span className="text-sm font-mono text-slate-300 truncate max-w-[240px]">{ep.path}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-xs">{ep.finding_count} bulgu</span>
                        <span className={`text-xs font-bold ${ep.security_score >= 70 ? "text-emerald-400" : ep.security_score >= 40 ? "text-amber-400" : "text-red-400"}`}>
                          {Math.round(ep.security_score)}
                        </span>
                      </div>
                    </div>
                  ))}
                </SectionCard>
              )}

              {/* Recommendations */}
              {dashboard.recommendations.length > 0 && (
                <SectionCard
                  title="Öneriler"
                  icon={<svg className="w-3.5 h-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
                >
                  <ul className="space-y-1.5">
                    {dashboard.recommendations.map((r, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-300">
                        <span className="text-violet-400 shrink-0">•</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </SectionCard>
              )}
            </>
          )}
        </>
      )}

      {/* ─── Scan Results Tab ───────────────────────────────────── */}
      {activeTab === "scan" && scanResult && (
        <div className="space-y-4">
          {/* Scan summary */}
          <div className="grid grid-cols-4 gap-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Taranan Endpoint</p>
              <p className="text-2xl font-bold text-white">{scanResult.endpoints_scanned}</p>
            </div>
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Toplam Bulgu</p>
              <p className="text-2xl font-bold text-red-400">{scanResult.total_findings}</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Ort. Güvenlik Skoru</p>
              <p className={`text-2xl font-bold ${scanResult.avg_security_score >= 70 ? "text-emerald-400" : scanResult.avg_security_score >= 40 ? "text-amber-400" : "text-red-400"}`}>
                {Math.round(scanResult.avg_security_score)}
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Spec</p>
              <p className="text-lg font-bold text-white truncate">{scanResult.spec_name}</p>
            </div>
          </div>

          {/* Per-endpoint findings */}
          {scanResult.endpoint_results.map((ep) => (
            <SectionCard
              key={ep.endpoint_id}
              title={`${ep.method} ${ep.path}`}
              right={
                <span className={`text-xs font-bold ${ep.security_score >= 70 ? "text-emerald-400" : ep.security_score >= 40 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(ep.security_score)}/100
                </span>
              }
              noPad
            >
              {ep.findings.length === 0 ? (
                <div className="px-4 py-3 text-xs text-emerald-400">Güvenlik açığı bulunamadı</div>
              ) : (
                ep.findings.map((f, i) => (
                  <div key={i} className="px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`w-2 h-2 rounded-full ${SEVERITY_DOT[f.severity] ?? "bg-slate-500"}`} />
                      <span className={`px-2 py-0.5 rounded-full border text-[10px] font-medium ${SEVERITY_COLORS[f.severity] ?? SEVERITY_COLORS.low}`}>
                        {f.severity}
                      </span>
                      <span className="text-xs font-mono text-slate-400">{f.owasp_category}</span>
                      <span className="text-sm font-medium text-white">{f.title}</span>
                    </div>
                    <p className="text-xs text-slate-400 ml-4">{f.description}</p>
                    {f.banking_impact && (
                      <p className="text-xs text-amber-400 ml-4 mt-0.5">Bankacılık etkisi: {f.banking_impact}</p>
                    )}
                  </div>
                ))
              )}
            </SectionCard>
          ))}
        </div>
      )}
    </div>
  );
}
