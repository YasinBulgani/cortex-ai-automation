"use client";

// ── Types (shared with page) ─────────────────────────────────────────────────

type EngineBug = {
  category: string;
  severity: "critical" | "warning" | string;
  count: number;
  sample: string;
  affected_pages: string[];
};

type EngineConsoleError = {
  type: string;
  text: string;
  url: string;
  timestamp: string;
  category: string;
};

type EngineNetworkError = {
  url: string;
  status: number;
  page_url: string;
  timestamp: string;
  category: string;
};

type EngineRecommendation = { priority: string; text: string };

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

// ── Props ────────────────────────────────────────────────────────────────────

export interface BugReportPanelProps {
  bugs: EngineBug[];
  consoleErrors: EngineConsoleError[];
  networkErrors: EngineNetworkError[];
  recommendations: EngineRecommendation[];
}

// ── Component ────────────────────────────────────────────────────────────────

export function BugReportPanel({
  bugs,
  consoleErrors,
  networkErrors,
  recommendations,
}: BugReportPanelProps) {
  return (
    <div className="rounded-xl border border-slate-700">
      <div className="grid grid-cols-3 border-b border-slate-700 text-[11px] font-semibold">
        <ColHeader label={`🐛 Bug'lar (${bugs.length})`} />
        <ColHeader label={`⚠️ Console (${consoleErrors.length})`} />
        <ColHeader label={`🌐 Network (${networkErrors.length})`} />
      </div>
      <div className="grid grid-cols-3 gap-px bg-slate-700">
        {/* Bugs column */}
        <div className="bg-slate-900/40 p-2 max-h-72 overflow-y-auto">
          {bugs.length === 0 ? (
            <div className="text-[11px] text-slate-500 p-2">Bug yok 🎉</div>
          ) : (
            bugs.map((b, i) => (
              <div key={i} className="border-b border-slate-800 px-2 py-1.5 text-[11px]">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "rounded px-1 text-[9px] font-bold uppercase",
                      b.severity === "critical"
                        ? "bg-red-500/30 text-red-200"
                        : "bg-yellow-500/30 text-yellow-200",
                    )}
                  >
                    {b.severity}
                  </span>
                  <span className="text-slate-300 truncate">{b.category}</span>
                  <span className="text-slate-500">×{b.count}</span>
                </div>
                <div className="mt-1 text-[10px] text-slate-500 truncate">{b.sample}</div>
              </div>
            ))
          )}
        </div>

        {/* Console errors column */}
        <div className="bg-slate-900/40 p-2 max-h-72 overflow-y-auto">
          {consoleErrors.length === 0 ? (
            <div className="text-[11px] text-slate-500 p-2">Console temiz</div>
          ) : (
            consoleErrors.map((c, i) => (
              <div key={i} className="border-b border-slate-800 px-2 py-1.5 text-[10px]">
                <div className="text-slate-400">{c.category}</div>
                <div className="text-red-300 line-clamp-2">{c.text}</div>
                <div className="text-slate-600 truncate">{c.url}</div>
              </div>
            ))
          )}
        </div>

        {/* Network errors column */}
        <div className="bg-slate-900/40 p-2 max-h-72 overflow-y-auto">
          {networkErrors.length === 0 ? (
            <div className="text-[11px] text-slate-500 p-2">Network temiz</div>
          ) : (
            networkErrors.map((n, i) => (
              <div key={i} className="border-b border-slate-800 px-2 py-1.5 text-[10px]">
                <div className="flex gap-2">
                  <span
                    className={cn(
                      "rounded px-1 font-bold",
                      n.status >= 500
                        ? "bg-red-500/30 text-red-200"
                        : "bg-yellow-500/30 text-yellow-200",
                    )}
                  >
                    {n.status}
                  </span>
                  <span className="text-slate-400 truncate">{n.category}</span>
                </div>
                <div className="text-slate-500 truncate mt-0.5">{n.url}</div>
              </div>
            ))
          )}
        </div>
      </div>

      {recommendations.length > 0 && (
        <div className="border-t border-slate-700 bg-slate-900/40 p-3">
          <div className="text-[11px] font-semibold text-violet-300 mb-1">💡 Öneriler</div>
          <ul className="text-[11px] text-slate-300 space-y-1">
            {recommendations.map((r, i) => (
              <li key={i} className="flex gap-2">
                <span
                  className={cn(
                    "shrink-0 rounded px-1 text-[9px] uppercase font-bold",
                    r.priority === "critical"
                      ? "bg-red-500/30 text-red-200"
                      : r.priority === "high"
                        ? "bg-orange-500/30 text-orange-200"
                        : r.priority === "info"
                          ? "bg-blue-500/30 text-blue-200"
                          : "bg-slate-700 text-slate-300",
                  )}
                >
                  {r.priority}
                </span>
                <span>{r.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Local helper ─────────────────────────────────────────────────────────────

function ColHeader({ label }: { label: string }) {
  return (
    <div className="px-3 py-2 text-slate-300 bg-slate-900/60 text-center border-r last:border-r-0 border-slate-700">
      {label}
    </div>
  );
}
