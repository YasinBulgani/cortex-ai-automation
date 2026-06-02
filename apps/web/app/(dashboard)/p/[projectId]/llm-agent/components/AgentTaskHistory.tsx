"use client";

type Finding = {
  id: string;
  step: number;
  text: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  url: string;
  timestamp: string;
  wave?: number;
  title?: string;
  category?: string;
  hypothesis_id?: string;
  impact?: string;
  steps_to_reproduce?: string[];
};

type ActionRecord = {
  step: number;
  type: string;
  selector?: string;
  value?: string;
  description: string;
  success: boolean;
  url: string;
  timestamp: string;
  wave?: number;
};

type CoverageData = {
  coverage_pct: number;
  tested_areas: string[];
  wave1_count: number;
  wave2_count: number;
  findings_by_severity: Record<string, number>;
};

interface AgentTaskHistoryProps {
  findings: Finding[];
  actions: ActionRecord[];
  coverage: CoverageData | null;
  duration: number;
  wave: number;
  summaryText: string;
  planText: string;
  targetUrl: string;
  techStack: Array<{ name: string; category: string; version?: string }>;
  sensitiveKeys: string[];
  apiCallsSlice: Array<{
    url: string;
    method: string;
    status: number;
    duration_ms: number;
    is_error: boolean;
    timestamp: string;
  }>;
  consoleErrorsSlice: Array<{
    type: "error" | "warning" | "info";
    text: string;
    url?: string;
    timestamp: string;
  }>;
  hypotheses: Array<{
    id: string;
    claim: string;
    area: string;
    priority: string;
    status: string;
    confidence?: number;
    wave?: number;
  }>;
  learnedFacts: string[];
}

function cn(...cls: (string | false | null | undefined)[]) {
  return cls.filter(Boolean).join(" ");
}

function severityColor(s: string) {
  if (s === "critical")
    return {
      bg: "bg-red-500/15 border-red-500/30",
      text: "text-red-300",
      badge: "bg-red-500/25 text-red-200",
    };
  if (s === "high")
    return {
      bg: "bg-orange-500/10 border-orange-500/25",
      text: "text-orange-300",
      badge: "bg-orange-500/20 text-orange-200",
    };
  if (s === "medium")
    return {
      bg: "bg-yellow-500/10 border-yellow-500/25",
      text: "text-yellow-300",
      badge: "bg-yellow-500/20 text-yellow-200",
    };
  if (s === "low")
    return {
      bg: "bg-blue-500/10 border-blue-500/25",
      text: "text-blue-300",
      badge: "bg-blue-500/20 text-blue-200",
    };
  return {
    bg: "bg-slate-800/60 border-slate-700",
    text: "text-slate-300",
    badge: "bg-slate-700 text-slate-300",
  };
}

export function AgentTaskHistory({
  findings,
  actions,
  coverage,
  duration,
  wave,
  summaryText,
  planText,
  targetUrl,
  techStack,
  sensitiveKeys,
  apiCallsSlice,
  consoleErrorsSlice,
  hypotheses,
  learnedFacts,
}: AgentTaskHistoryProps) {
  function handleDownloadMd() {
    const techLine =
      techStack.length > 0
        ? `Teknoloji: ${techStack.map((t) => t.name).join(", ")}\n`
        : "";
    const covLine = coverage
      ? `Kapsam: %${coverage.coverage_pct} (${coverage.tested_areas.join(", ")})\n`
      : "";
    const findingsMd = findings.map((f) => {
      const impactLine = f.impact ? `\nEtki: ${f.impact}` : "";
      const stepsLine = f.steps_to_reproduce?.length
        ? `\nAdımlar: ${f.steps_to_reproduce.join(" → ")}`
        : "";
      return `### [${f.severity.toUpperCase()}${f.wave === 2 ? " W2" : ""}] ${f.title || f.text.slice(0, 60)}\n${f.text}${impactLine}${stepsLine}\nURL: ${f.url}`;
    });
    const md = [
      "# LLM Ajan Test Raporu",
      `URL: ${targetUrl} | Tarih: ${new Date().toLocaleString("tr-TR")}`,
      techLine +
        covLine +
        `Eylem: ${actions.length} | Bulgu: ${findings.length} | Süre: ${duration}s | Dalga: ${wave}`,
      "",
      "## Test Planı",
      planText,
      "",
      "## Bulgular",
      ...findingsMd,
      "",
      "## Özet",
      summaryText,
    ].join("\n");
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `llm_agent_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleDownloadJson() {
    const payload = {
      meta: {
        url: targetUrl,
        date_iso: new Date().toISOString(),
        duration_sec: duration,
        wave,
      },
      summary: summaryText,
      plan: planText,
      coverage,
      tech_stack: techStack,
      hypotheses,
      findings,
      actions,
      api_calls: apiCallsSlice,
      console_errors: consoleErrorsSlice,
      sensitive_keys: sensitiveKeys,
      learned_facts: learnedFacts,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `llm_agent_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="border-t border-slate-800 bg-slate-900/60 px-3 py-2 space-y-1 flex-shrink-0">
      <div className="grid grid-cols-3 gap-1 text-center mb-1">
        <div>
          <p className="text-[9px] text-slate-600">Eylem</p>
          <p className="text-xs font-bold text-slate-300">{actions.length}</p>
        </div>
        <div>
          <p className="text-[9px] text-slate-600">Bulgu</p>
          <p className="text-xs font-bold text-slate-300">{findings.length}</p>
        </div>
        <div>
          <p className="text-[9px] text-slate-600">Süre</p>
          <p className="text-xs font-bold font-mono text-slate-300">
            {Math.floor(duration / 60)}:
            {String(duration % 60).padStart(2, "0")}
          </p>
        </div>
      </div>

      {findings.length > 0 && (
        <div className="border-t border-slate-800/60 pt-1 space-y-1">
          <p className="text-[9px] uppercase tracking-wide text-slate-500 mb-1">
            Tüm Bulgular
          </p>
          {findings.slice(0, 5).map((f) => {
            const col = severityColor(f.severity);
            return (
              <div
                key={f.id}
                className={cn("rounded px-2 py-1 border", col.bg.split(" ")[0], "border-slate-700/60")}
              >
                <div className="flex items-center gap-1 mb-0.5">
                  <span
                    className={cn(
                      "rounded px-1 py-0.5 text-[8px] font-bold uppercase",
                      col.badge
                    )}
                  >
                    {f.severity}
                  </span>
                  {f.wave === 2 && (
                    <span className="text-[8px] text-amber-300 font-bold">W2</span>
                  )}
                  <span className="text-[9px] text-slate-600 ml-auto">#{f.step}</span>
                </div>
                <p className="text-[10px] text-slate-400 leading-relaxed truncate">
                  {f.title || f.text.slice(0, 80)}
                </p>
              </div>
            );
          })}
          {findings.length > 5 && (
            <p className="text-[10px] text-slate-600 text-center">
              +{findings.length - 5} daha
            </p>
          )}
        </div>
      )}

      <button
        onClick={handleDownloadMd}
        className="w-full rounded-lg border border-emerald-500/25 bg-emerald-500/10 py-1.5 text-[11px] font-semibold text-emerald-300 hover:bg-emerald-500/20"
      >
        ↓ Rapor İndir (.md)
      </button>
      <button
        type="button"
        onClick={handleDownloadJson}
        className="mt-1.5 w-full rounded-lg border border-sky-500/25 bg-sky-500/10 py-1.5 text-[11px] font-semibold text-sky-300 hover:bg-sky-500/20"
      >
        ↓ Tam Veri (.json)
      </button>
    </div>
  );
}
