"use client";

import { useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import {
  usePrivacyAudit,
  usePrivacyReport,
} from "@/lib/hooks/use-synthetic-advanced";

const COMPLIANCE_LABELS: Record<string, { label: string; icon: string }> = {
  kvkk: { label: "KVKK", icon: "🇹🇷" },
  gdpr: { label: "GDPR", icon: "🇪🇺" },
  pci_dss: { label: "PCI-DSS", icon: "💳" },
};

export default function PrivacyPage() {
  const projectId = useRouteParam("projectId");
  const [actionError, setActionError] = useState<string | null>(null);

  const {
    data: report,
    isLoading: reportLoading,
    isError: reportFailed,
    error: reportError,
  } = usePrivacyReport(projectId);
  const auditMut = usePrivacyAudit(projectId);

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

  const auditData = auditMut.data || report;

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
          {actionError || (reportError instanceof Error && reportError.message) || "Gizlilik verileri yüklenemedi."}
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
          {/* Risk Summary */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">Yeniden Tanımlama Riski</p>
              <p className={`text-3xl font-bold ${
                auditData.re_identification_risk > 0.7 ? "text-red-400" :
                auditData.re_identification_risk > 0.4 ? "text-amber-400" : "text-emerald-400"
              }`}>
                {(auditData.re_identification_risk * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">Toplam Kayıt</p>
              <p className="text-3xl font-bold text-blue-400">{auditData.total_records}</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">PII Sütun Sayısı</p>
              <p className="text-3xl font-bold text-amber-400">{auditData.pii_columns_detected.length}</p>
            </div>
          </div>

          {/* PII Columns */}
          {auditData.pii_columns_detected.length > 0 && (
            <SectionCard title="Tespit Edilen PII Sütunları">
              <div className="flex flex-wrap gap-2">
                {auditData.pii_columns_detected.map(col => (
                  <span key={col} className="px-3 py-1.5 text-xs font-medium text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg">
                    {col}
                  </span>
                ))}
              </div>
            </SectionCard>
          )}

          {/* Compliance */}
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

      {!auditData && !auditMut.isPending && !reportLoading && (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-12">
          <EmptyState icon="🔒" title="Gizlilik Denetimi"
            description="Yukarıdaki alana JSON veri yapıştırıp denetim başlatın" />
        </div>
      )}
    </div>
  );
}
