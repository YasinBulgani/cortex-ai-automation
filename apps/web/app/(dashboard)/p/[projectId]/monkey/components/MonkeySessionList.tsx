"use client";

// ── Types (local copies — avoids circular imports) ────────────────────────────

type EngineAction = {
  step: number;
  type: string;
  url: string;
  timestamp: string;
  target?: string;
  value?: string;
  result?: string;
  triggered_error?: boolean;
  load_time_ms?: number;
  direction?: string;
  key?: string;
  viewport?: string;
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

type EngineBug = {
  category: string;
  severity: "critical" | "warning" | string;
  count: number;
  sample: string;
  affected_pages: string[];
};

type EngineScenario = {
  title: string;
  type: string;
  description: string;
  steps: { action: string; expected: string }[];
  priority: string;
};

type EngineRecommendation = { priority: string; text: string };

type EngineAnalysis = {
  scenarios: EngineScenario[];
  bugs: EngineBug[];
  recommendations: EngineRecommendation[];
  risk_level: string;
  summary: {
    total_bugs: number;
    critical_bugs: number;
    warning_bugs: number;
    scenarios_generated: number;
    pages_with_errors: number;
    error_categories: string[];
    network_categories: string[];
  };
};

type EngineResult = {
  run_id?: string;
  status: string;
  test_url: string;
  actions_performed: number;
  actions_log: EngineAction[];
  action_stats: Record<string, { total: number; success: number; error: number }>;
  console_errors: EngineConsoleError[];
  network_errors: EngineNetworkError[];
  error_count: number;
  stability_score: number;
  pages_visited: string[];
  pages_visited_count: number;
  performance_metrics: { url: string; load_time_ms: number; timestamp: string }[];
  screenshots: { final?: string };
  total_time_seconds: number;
  analysis: EngineAnalysis;
  started_at: string;
  video_url?: string | null;
};

export type HistoryEntry = {
  id: string;
  timestamp: string;
  url: string;
  actions: number;
  errors: number;
  stability: number;
  scenarios: number;
  videoUrl?: string | null;
  data: EngineResult;
};

// ── Helper ────────────────────────────────────────────────────────────────────

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface MonkeySessionListProps {
  history: HistoryEntry[];
  onLoadEntry: (entry: HistoryEntry) => void;
  onClearHistory: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MonkeySessionList({
  history,
  onLoadEntry,
  onClearHistory,
}: MonkeySessionListProps) {
  if (history.length === 0) {
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-3">
        <div className="text-center text-xs text-slate-500 py-4">
          Henüz çalıştırma kaydı yok.
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-3">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs font-semibold text-slate-300">Son Çalıştırmalar</span>
        <button
          type="button"
          onClick={onClearHistory}
          className="text-[10px] text-red-400 hover:text-red-300"
        >
          Tümünü temizle
        </button>
      </div>
      <div className="max-h-60 overflow-y-auto flex flex-col gap-1">
        {history.map((h) => (
          <button
            key={h.id}
            type="button"
            onClick={() => onLoadEntry(h)}
            className="text-left flex items-center gap-3 rounded-md border border-slate-700 bg-slate-800/40 px-2 py-1.5 text-[11px] hover:border-slate-500"
          >
            <span className="font-mono text-slate-500 w-32 truncate">
              {new Date(h.timestamp).toLocaleString("tr-TR")}
            </span>
            <span className="flex-1 truncate text-slate-300">{h.url}</span>
            <span className="text-orange-300">{h.actions} eylem</span>
            <span
              className={cn(
                "font-semibold",
                h.stability >= 80
                  ? "text-emerald-400"
                  : h.stability >= 50
                  ? "text-yellow-400"
                  : "text-red-400"
              )}
            >
              %{h.stability}
            </span>
            <span className="text-red-400">{h.errors} hata</span>
          </button>
        ))}
      </div>
    </div>
  );
}
