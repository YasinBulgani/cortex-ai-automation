"use client";

import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
  StatCard,
  MetricRow,
} from "@/components/nexus";

type A11yIssue = { id: string; rule: string; impact: string; element: string; description: string };

const IMPACT_STYLES: Record<string, { color: string; dot: string; label: string }> = {
  critical: { color: "bg-red-500/10 border-red-500/20 text-red-400",     dot: "bg-red-400",     label: "Kritik" },
  serious:  { color: "bg-amber-500/10 border-amber-500/20 text-amber-400", dot: "bg-amber-400",   label: "Ciddi" },
  moderate: { color: "bg-blue-500/10 border-blue-500/20 text-blue-400",   dot: "bg-blue-400",    label: "Orta" },
  minor:    { color: "bg-slate-800 border-slate-700 text-slate-400",       dot: "bg-slate-500",   label: "Düşük" },
};

const IMPACT_ORDER = ["critical", "serious", "moderate", "minor"];

export default function AccessibilityPage() {
  const [url, setUrl] = useState("");
  const [scanning, setScanning] = useState(false);
  const [issues, setIssues] = useState<A11yIssue[]>([]);
  const [scanAttempted, setScanAttempted] = useState(false);
  const [scanError, setScanError] = useState(false);

  async function runScan() {
    if (!url.trim()) return;
    setScanning(true);
    setScanAttempted(true);
    setScanError(false);
    try {
      const res = await apiFetch<{ violations: A11yIssue[] }>("/api/v1/automation/proxy/api/accessibility/test", {
        method: "POST",
        json: { url },
      });
      setIssues(res.violations ?? []);
    } catch {
      setScanError(true);
    } finally {
      setScanning(false);
    }
  }

  const counts = IMPACT_ORDER.reduce((acc, imp) => {
    acc[imp] = issues.filter(i => i.impact === imp).length;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="a11y-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        }
        title="Erişilebilirlik Testi"
        description="WCAG standartlarına uygunluk kontrolü"
      />

      {/* URL input */}
      <SectionCard
        title="URL Tara"
        icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>}
      >
        <div className="flex gap-3">
          <input
            value={url}
            onChange={e => setUrl(e.target.value)}
            onKeyDown={e => e.key === "Enter" && runScan()}
            placeholder="https://test-edilecek-site.com"
            data-testid="a11y-input-url"
            className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
          />
          <button
            onClick={runScan}
            disabled={scanning || !url.trim()}
            data-testid="a11y-btn-scan"
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50"
          >
            {scanning ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Taranıyor…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Tarama Başlat
              </>
            )}
          </button>
        </div>
      </SectionCard>

      {/* Error */}
      {scanError && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          Tarama başlatılamadı. Backend ve otomasyon motorunun (Flask) çalıştığından emin olun.
        </div>
      )}

      {/* Stats row after scan */}
      {scanAttempted && !scanning && !scanError && issues.length > 0 && (
        <MetricRow cols={4}>
          <StatCard label="Kritik" value={counts.critical} color={counts.critical > 0 ? "red" : "slate"} />
          <StatCard label="Ciddi" value={counts.serious} color={counts.serious > 0 ? "amber" : "slate"} />
          <StatCard label="Orta" value={counts.moderate} color={counts.moderate > 0 ? "blue" : "slate"} />
          <StatCard label="Düşük" value={counts.minor} color="slate" />
        </MetricRow>
      )}

      {/* Issues list */}
      {scanAttempted && !scanning && !scanError && (
        issues.length > 0 ? (
          <SectionCard
            title={`Bulunan Sorunlar`}
            icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
            right={<span className="text-xs text-slate-500">{issues.length} sorun</span>}
            noPad
          >
            {IMPACT_ORDER.flatMap(imp =>
              issues.filter(i => i.impact === imp).map(issue => {
                const s = IMPACT_STYLES[issue.impact] ?? IMPACT_STYLES.minor;
                return (
                  <div key={issue.id} className="px-4 py-4 border-b border-slate-800 last:border-0 hover:bg-slate-800/30" data-testid={`a11y-issue-${issue.id}`}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${s.color}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                        {s.label}
                      </span>
                      <code className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded font-mono">{issue.rule}</code>
                    </div>
                    <p className="text-sm text-white mb-1">{issue.description}</p>
                    <code className="text-xs text-slate-500 font-mono break-all">{issue.element}</code>
                  </div>
                );
              })
            )}
          </SectionCard>
        ) : (
          <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16" data-testid="a11y-empty">
            <EmptyState
              icon="✅"
              title="İhlal bulunamadı"
              description="Tarama tamamlandı; raporlanan erişilebilirlik ihlali yok."
            />
          </div>
        )
      )}
      <PageFeedbackWidget />

    </div>
  );
}
