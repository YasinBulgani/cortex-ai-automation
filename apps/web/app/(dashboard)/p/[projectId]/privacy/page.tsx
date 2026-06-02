"use client";

import { useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import {
  usePrivacyAudit,
  usePrivacyReport,
  useAnonymize,
  useAddNoise,
} from "@/lib/hooks/use-synthetic-advanced";
import { ConsentManager } from "./components/ConsentManager";
import { DataExportPanel } from "./components/DataExportPanel";

const COMPLIANCE_LABELS: Record<string, { label: string; icon: string }> = {
  kvkk: { label: "KVKK", icon: "🇹🇷" },
  gdpr: { label: "GDPR", icon: "🇪🇺" },
  pci_dss: { label: "PCI-DSS", icon: "💳" },
};

const MECHANISMS = [
  { value: "laplace" as const, label: "Laplace", desc: "Sürekli veriler için ideal" },
  { value: "gaussian" as const, label: "Gaussian", desc: "Yüksek gizlilik bütçesi" },
  { value: "exponential" as const, label: "Üstel", desc: "Kategorik veriler" },
];
type MechanismType = "laplace" | "gaussian" | "exponential";

export default function PrivacyPage() {
  const projectId = useRouteParam("projectId");
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"audit" | "anonymize" | "noise" | "anonimizasyon" | "gurultu-ekleme" | "uyumluluk">("audit");
  const [kAnon, setKAnon] = useState(3);
  const [lDiv, setLDiv] = useState(2);
  const [anonResult, setAnonResult] = useState<import("@/lib/hooks/use-synthetic-advanced").AnonymizationResult | null>(null);
  const [noiseTrials, setNoiseTrials] = useState<Array<{ original: number; noisy: number; noise: number }>>([]);
  const [testValue, setTestValue] = useState(1000);
  const [epsilon, setEpsilon] = useState(1.0);
  const [mechanism, setMechanism] = useState<MechanismType>("laplace");

  const {
    data: report,
    isLoading: reportLoading,
    isError: reportFailed,
    error: reportError,
  } = usePrivacyReport(projectId);
  const auditMut = usePrivacyAudit(projectId);
  const anonMut = useAnonymize(projectId);
  const noiseMut = useAddNoise(projectId);

  const [sampleDataText, setSampleDataText] = useState(
    JSON.stringify([
      { iban: "TR330006100519786457841326", name: "Ali Yilmaz", tc_no: "12345678901", amount: 5000 },
      { iban: "TR110006100519786457841327", name: "Ayse Kaya", tc_no: "98765432109", amount: 12000 },
    ], null, 2)
  );

  async function runAudit() {
    try {
      setActionError(null);
      const data = JSON.parse(sampleDataText);
      await auditMut.mutateAsync({ data, dataset_name: "Manuel Veri" });
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Gizlilik denetimi başarısız oldu.");
    }
  }

  async function runAnonymize() {
    try {
      setActionError(null);
      const data = JSON.parse(sampleDataText);
      const result = await anonMut.mutateAsync({
        data,
        quasi_identifiers: ["name", "iban"],
        sensitive_columns: ["tc_no", "amount"],
        k_anonymity: kAnon,
        l_diversity: lDiv,
      });
      setAnonResult(result);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Anonimizasyon başarısız oldu.");
    }
  }

  async function runNoise() {
    try {
      setActionError(null);
      const result = await noiseMut.mutateAsync({
        value: testValue,
        config: { epsilon, mechanism },
      });
      setNoiseTrials((prev) => [
        { original: result.original_value, noisy: result.noisy_value, noise: result.noise_added },
        ...prev.slice(0, 19),
      ]);
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "DP gurultu simulasyonu başarısız oldu.");
    }
  }

  const auditData = auditMut.data ?? report ?? null;

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="privacy-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        }
        title="Gizlilik ve Uyumluluk"
        description="PII tarama, risk analizi ve KVKK/GDPR/PCI-DSS uyumluluk kontrolleri"
      />

      {(actionError || reportFailed) && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {actionError ||
            (reportError instanceof Error && reportError.message) ||
            "Gizlilik verileri yüklenemedi."}
        </div>
      )}

      {/* Quick Audit */}
      <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-5">
        <p className="text-sm font-medium text-violet-300 mb-3">Hızlı Gizlilik Denetimi</p>
        <textarea
          value={sampleDataText}
          onChange={e => setSampleDataText(e.target.value)}
          rows={5}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono placeholder:text-slate-500 resize-none mb-3"
          placeholder="JSON dizisi yapıştırın..."
        />
        <button onClick={runAudit} disabled={auditMut.isPending}
          className="px-4 py-2 text-sm font-semibold text-violet-300 border border-violet-500/30 rounded-xl hover:bg-violet-500/10 transition-all disabled:opacity-50">
          {auditMut.isPending ? "Taranıyor..." : "Denetim Başlat"}
        </button>
      </div>

      {/* Audit Results */}
      {auditData && (
        <div className="space-y-4">
          {/* Quick audit */}
          <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-5">
            <p className="text-sm font-medium text-violet-300 mb-3">Hizli Gizlilik Denetimi</p>
            <textarea
              value={sampleDataText}
              onChange={(e) => setSampleDataText(e.target.value)}
              rows={6}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono placeholder:text-slate-500 resize-none mb-3"
              placeholder="JSON dizisi yapistirin..."
            />
            <button
              onClick={runAudit}
              disabled={auditMut.isPending}
              className="px-4 py-2 text-sm font-semibold text-violet-300 border border-violet-500/30 rounded-xl hover:bg-violet-500/10 transition-all disabled:opacity-50"
            >
              {auditMut.isPending ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-violet-300/30 border-t-violet-300 rounded-full animate-spin" />
                  Taranıyor...
                </div>
              ) : "Denetim Başlat"}
            </button>
          </div>

          {/* Audit results */}
          {auditData && (
            <div className="space-y-4">
              {/* Risk gauge */}
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
                  <p className="text-xs text-slate-400 mb-1">Yeniden Tanimlama Riski</p>
                  <p className={`text-3xl font-bold ${
                    auditData.re_identification_risk > 0.7 ? "text-red-400" :
                    auditData.re_identification_risk > 0.4 ? "text-amber-400" : "text-emerald-400"
                  }`}>
                    {(auditData.re_identification_risk * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
                  <p className="text-xs text-slate-400 mb-1">Toplam Kayit</p>
                  <p className="text-3xl font-bold text-blue-400">{auditData.total_records}</p>
                </div>
                <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
                  <p className="text-xs text-slate-400 mb-1">PII Sutun Sayisi</p>
                  <p className="text-3xl font-bold text-amber-400">{auditData.pii_columns_detected.length}</p>
                </div>
              </div>

              {/* PII columns */}
              {auditData.pii_columns_detected.length > 0 && (
                <SectionCard title="Tespit Edilen PII Sutunlari" icon={<svg className="w-3.5 h-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" /></svg>}>
                  <div className="flex flex-wrap gap-2">
                    {auditData.pii_columns_detected.map((col) => (
                      <span key={col} className="px-3 py-1.5 text-xs font-medium text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg">
                        {col}
                      </span>
                    ))}
                  </div>
                </SectionCard>
              )}

              {/* Compliance cards */}
              <div className="grid grid-cols-3 gap-3">
                {Object.entries(auditData.compliance).map(([key, val]) => {
                  const label = COMPLIANCE_LABELS[key];
                  if (!label) return null;
                  return (
                    <div key={key} className={`rounded-xl border p-4 ${
                      val.compliant ? "border-emerald-500/20 bg-emerald-500/5" : "border-red-500/20 bg-red-500/5"
                    }`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-lg">{label.icon}</span>
                        <span className="text-sm font-medium text-white">{label.label}</span>
                        <span className={`ml-auto text-xs font-semibold ${val.compliant ? "text-emerald-400" : "text-red-400"}`}>
                          {val.compliant ? "Uyumlu" : "Uyumsuz"}
                        </span>
                      </div>
                      {val.issues.length > 0 && (
                        <ul className="space-y-1">
                          {val.issues.map((issue, i) => (
                            <li key={i} className="text-[11px] text-slate-400">• {issue}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Recommendations */}
              {auditData.recommendations.length > 0 && (
                <SectionCard
                  title="Öneriler"
                  icon={<svg className="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
                >
                  <ul className="space-y-1.5">
                    {auditData.recommendations.map((r, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-300">
                        <span className="text-cyan-400 shrink-0">{i + 1}.</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </SectionCard>
              )}
            </div>
          )}

          {!auditData && !auditMut.isPending && !reportLoading && (
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-12">
              <EmptyState
                icon="🔒"
                title="Gizlilik Denetimi"
                description="Yukaridaki alana JSON veri yapistirip denetim başlatin veya mevcut raporu görüntüleyin"
              />
            </div>
          )}
        </div>
      )}

      {/* ── Anonimizasyon Tab ──────────────────────────────── */}
      {activeTab === "anonimizasyon" && (
        <ConsentManager
          sampleDataText={sampleDataText}
          onSampleDataChange={setSampleDataText}
          kAnon={kAnon}
          onKAnonChange={setKAnon}
          lDiv={lDiv}
          onLDivChange={setLDiv}
          onAnonymize={runAnonymize}
          isPending={anonMut.isPending}
          result={anonResult}
        />
      )}

      {/* ── DP Gurultu Tab ─────────────────────────────────── */}
      {activeTab === "gurultu-ekleme" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-5">
            <p className="text-sm font-medium text-blue-300 mb-3">Diferansiyel Gizlilik Gurultusu</p>

            {/* Epsilon slider */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-slate-400">Epsilon (gizlilik butcesi)</label>
                <span className="text-sm font-mono text-blue-300">{epsilon.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0.01}
                max={10}
                step={0.01}
                value={epsilon}
                onChange={(e) => setEpsilon(Number(e.target.value))}
                aria-label="Epsilon gizlilik butcesi"
                title="Epsilon gizlilik butcesi"
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                <span>0.01 (Cok gizli)</span>
                <span>1.0 (Dengeli)</span>
                <span>10.0 (Az gizlilik)</span>
              </div>
            </div>

            {/* Mechanism selector */}
            <div className="mb-4">
              <label className="text-xs text-slate-400 block mb-2">Mekanizma</label>
              <div className="flex gap-2">
                {MECHANISMS.map((m) => (
                  <button
                    key={m.value}
                    onClick={() => setMechanism(m.value)}
                    className={`flex-1 px-3 py-2 rounded-xl border text-left transition-all ${
                      mechanism === m.value
                        ? "border-blue-500/40 bg-blue-500/10"
                        : "border-slate-700 hover:border-slate-600"
                    }`}
                  >
                    <p className={`text-xs font-medium ${mechanism === m.value ? "text-blue-300" : "text-white"}`}>{m.label}</p>
                    <p className="text-[10px] text-slate-500">{m.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Compliance */}
          {auditData && <div className="grid grid-cols-3 gap-3">
            {Object.entries(auditData.compliance).map(([key, val]) => {
              const label = COMPLIANCE_LABELS[key];
              if (!label) return null;
              return (
                <div key={key} className={`rounded-xl border p-4 ${
                  val.compliant ? "border-emerald-500/20 bg-emerald-500/5" : "border-red-500/20 bg-red-500/5"
                }`}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-lg">{label.icon}</span>
                    <span className="text-sm font-medium text-white">{label.label}</span>
                    <span className={`ml-auto text-xs font-semibold ${val.compliant ? "text-emerald-400" : "text-red-400"}`}>
                      {val.compliant ? "Uyumlu" : "Uyumsuz"}
                    </span>
                  </div>
                  {val.issues.length > 0 && (
                    <ul className="space-y-1">
                      {val.issues.map((issue, i) => (
                        <li key={i} className="text-[11px] text-slate-400">• {issue}</li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>}

          {/* Recommendations */}
          {auditData && auditData.recommendations.length > 0 && (
            <SectionCard title="Öneriler">
              <ul className="space-y-1.5">
                {auditData.recommendations.map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-300">
                    <span className="text-cyan-400 shrink-0">{i + 1}.</span>
                    {r}
                  </li>
                ))}
              </ul>
            </SectionCard>
          )}
        </div>
      )}

      {/* ── Uyumluluk Tab ──────────────────────────────────── */}
      {activeTab === "uyumluluk" && (
        <DataExportPanel auditData={auditData} />
      )}
    </div>
  );
}
