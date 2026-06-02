"use client";

/**
 * DataExportPanel — KVKK/GDPR Uyumluluk raporu ve DSAR (Data Subject Access
 * Request) dışa aktarma paneli.
 *
 * Sorumluluklar:
 *  - Uyumluluk durumu kartları (KVKK / GDPR / PCI-DSS)
 *  - Quasi-identifier risk analizi çubuğu
 *  - Boş durum ekranı (denetim çalıştırılmamış)
 */

import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";

const COMPLIANCE_LABELS: Record<string, { label: string; icon: string }> = {
  kvkk: { label: "KVKK", icon: "🇹🇷" },
  gdpr: { label: "GDPR", icon: "🇪🇺" },
  pci_dss: { label: "PCI-DSS", icon: "💳" },
};

interface ComplianceValue {
  compliant: boolean;
  issues: string[];
}

interface AuditData {
  compliance: Record<string, ComplianceValue>;
  quasi_identifier_risk?: Record<string, number>;
  recommendations: string[];
}

interface DataExportPanelProps {
  auditData: AuditData | null;
}

export function DataExportPanel({ auditData }: DataExportPanelProps) {
  if (!auditData) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-12">
        <EmptyState
          icon="📋"
          title="Uyumluluk Raporu"
          description="Once 'Genel Bakis' sekmesinden bir denetim çalıştırin"
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Compliance status grid */}
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(auditData.compliance).map(([key, val]) => {
          const label = COMPLIANCE_LABELS[key];
          if (!label) return null;
          return (
            <div
              key={key}
              className={`rounded-xl border p-5 ${
                val.compliant
                  ? "border-emerald-500/20 bg-emerald-500/5"
                  : "border-red-500/20 bg-red-500/5"
              }`}
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="text-3xl">{label.icon}</span>
                <div>
                  <p className="text-sm font-medium text-white">{label.label}</p>
                  <p
                    className={`text-xs font-semibold ${
                      val.compliant ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    {val.compliant ? "Uyumlu" : "Uyumsuz"}
                  </p>
                </div>
              </div>
              {val.issues.length > 0 ? (
                <ul className="space-y-1.5 mt-2">
                  {val.issues.map((issue, i) => (
                    <li key={i} className="flex gap-2 text-xs text-slate-400">
                      <span className="text-red-400 shrink-0">!</span>
                      {issue}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-emerald-400 mt-2">Tum kontroller basarili</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Quasi-identifier risk */}
      {auditData.quasi_identifier_risk &&
        Object.keys(auditData.quasi_identifier_risk).length > 0 && (
          <SectionCard title="Quasi-Identifier Risk Analizi" noPad>
            <div className="divide-y divide-slate-800">
              {Object.entries(auditData.quasi_identifier_risk).map(([col, risk]) => (
                <div key={col} className="flex items-center gap-3 px-4 py-3">
                  <span className="text-sm font-medium text-white w-32">{col}</span>
                  <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        risk > 0.7
                          ? "bg-red-400"
                          : risk > 0.4
                          ? "bg-amber-400"
                          : "bg-emerald-400"
                      }`}
                      style={{ width: `${risk * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-400 w-12 text-right">
                    {(risk * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </SectionCard>
        )}

      {/* Recommendations */}
      {auditData.recommendations.length > 0 && (
        <SectionCard
          title="Öneriler"
          icon={
            <svg
              className="w-3.5 h-3.5 text-cyan-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          }
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
  );
}
