"use client";

// ── Types (mirrored from page.tsx) ────────────────────────────────────────────

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
  analysis: {
    scenarios: unknown[];
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
  started_at: string;
  video_url?: string | null;
};

type LiveFrame = { step: number | "final"; screenshot: string; url: string };

// ── Props ─────────────────────────────────────────────────────────────────────

export interface MonkeyReportViewerProps {
  liveResult: EngineResult | null;
  liveRunning: boolean;
  liveFrame: LiveFrame | null;
  liveActions: EngineAction[];
  drawerAction: EngineAction | null;
  onSetDrawerAction: (action: EngineAction | null) => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "emerald" | "yellow" | "red" | "slate";
}) {
  const color =
    accent === "emerald"
      ? "text-emerald-400"
      : accent === "yellow"
      ? "text-yellow-400"
      : accent === "red"
      ? "text-red-400"
      : "text-slate-200";
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950/40 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-sm font-bold ${color}`}>{value}</div>
    </div>
  );
}

function ColHeader({ label }: { label: string }) {
  return (
    <div className="px-3 py-2 text-slate-300 bg-slate-900/60 text-center border-r last:border-r-0 border-slate-700">
      {label}
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export function MonkeyReportViewer({
  liveResult,
  liveRunning,
  liveFrame,
  liveActions,
  drawerAction,
  onSetDrawerAction,
}: MonkeyReportViewerProps) {
  const actionErrors = liveActions.filter(
    (a) => (a.result ?? "").includes("error") || a.triggered_error,
  );

  return (
    <>
      {/* Live preview + stats */}
      {(liveRunning || liveResult) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Sol: canlı önizleme */}
          <div className="lg:col-span-2 rounded-xl border border-slate-700 bg-slate-900/60 p-2 flex flex-col gap-2">
            <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
              <span>
                📺 Canlı Önizleme{" "}
                {liveFrame?.step ? `(adım ${liveFrame.step})` : ""}
              </span>
              {liveFrame?.url && (
                <span
                  className="font-mono truncate max-w-[60%]"
                  title={liveFrame.url}
                >
                  {liveFrame.url}
                </span>
              )}
            </div>
            <div className="aspect-video w-full overflow-hidden rounded-md bg-slate-950 border border-slate-800 flex items-center justify-center">
              {liveFrame ? (
                <img
                  src={`data:image/jpeg;base64,${liveFrame.screenshot}`}
                  alt={`step-${liveFrame.step}`}
                  className="max-h-full max-w-full object-contain"
                />
              ) : (
                <div className="text-xs text-slate-600">
                  {liveRunning ? "İlk frame bekleniyor…" : "Henüz çalıştırılmadı"}
                </div>
              )}
            </div>

            {liveResult?.video_url && (
              <div className="mt-2">
                <div className="text-[11px] text-slate-400 mb-1 px-1">📹 Kayıt</div>
                <video
                  controls
                  className="w-full rounded-md bg-slate-950 border border-slate-800"
                  src={liveResult.video_url}
                />
              </div>
            )}
          </div>

          {/* Sağ: istatistikler */}
          <div className="flex flex-col gap-2">
            {liveResult && (
              <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3 flex flex-col gap-2">
                <div className="text-[11px] uppercase tracking-widest text-slate-400">
                  Özet
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <StatCard
                    label="Stabilite"
                    value={`%${liveResult.stability_score}`}
                    accent={
                      liveResult.stability_score >= 80
                        ? "emerald"
                        : liveResult.stability_score >= 50
                        ? "yellow"
                        : "red"
                    }
                  />
                  <StatCard
                    label="Risk"
                    value={liveResult.analysis.risk_level}
                    accent={
                      liveResult.analysis.risk_level === "low"
                        ? "emerald"
                        : liveResult.analysis.risk_level === "medium"
                        ? "yellow"
                        : "red"
                    }
                  />
                  <StatCard
                    label="Eylem"
                    value={`${liveResult.actions_performed}`}
                    accent="slate"
                  />
                  <StatCard
                    label="Hata"
                    value={`${liveResult.error_count}`}
                    accent={liveResult.error_count === 0 ? "emerald" : "red"}
                  />
                  <StatCard
                    label="Sayfa"
                    value={`${liveResult.pages_visited_count}`}
                    accent="slate"
                  />
                  <StatCard
                    label="Süre"
                    value={`${liveResult.total_time_seconds}s`}
                    accent="slate"
                  />
                </div>
              </div>
            )}

            {liveResult?.action_stats && (
              <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3">
                <div className="text-[11px] uppercase tracking-widest text-slate-400 mb-1.5">
                  Eylem İstatistikleri
                </div>
                <div className="flex flex-col gap-0.5 text-[10px]">
                  {Object.entries(liveResult.action_stats).map(([t, s]) => (
                    <div key={t} className="flex justify-between text-slate-400">
                      <span>{t}</span>
                      <span>
                        <span className="text-emerald-400">{s.success}</span>
                        {" / "}
                        <span className="text-red-400">{s.error}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action log (canlı) */}
      {liveActions.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-700">
          <div className="border-b border-slate-800 bg-slate-900/60 px-3 py-1.5 text-[11px] font-semibold text-slate-300 flex items-center justify-between">
            <span>📋 Eylemler ({liveActions.length})</span>
            <span className="text-slate-500">
              <span className="text-red-400">{actionErrors.length}</span> hata
              tetiklendi
            </span>
          </div>
          <div className="max-h-64 overflow-y-auto">
            {liveActions.slice(-200).map((a) => {
              const hasError =
                (a.result ?? "").includes("error") || a.triggered_error;
              return (
                <button
                  key={`${a.step}-${a.timestamp}`}
                  type="button"
                  onClick={() => onSetDrawerAction(a)}
                  className={cn(
                    "w-full text-left flex items-start gap-3 border-b border-slate-800/60 px-3 py-1.5 text-xs hover:bg-slate-800/40 transition-colors",
                    hasError && "bg-red-500/5",
                  )}
                >
                  <span className="w-8 shrink-0 text-right font-mono text-[10px] text-slate-600">
                    {a.step}
                  </span>
                  <span
                    className={cn(
                      "mt-0.5 h-2 w-2 shrink-0 rounded-full",
                      hasError ? "bg-red-400" : "bg-emerald-400",
                    )}
                  />
                  <span className="w-24 shrink-0 font-medium text-orange-300">
                    {a.type}
                  </span>
                  <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-slate-400">
                    {a.target ??
                      a.value ??
                      a.key ??
                      a.direction ??
                      a.viewport ??
                      "—"}
                  </span>
                  <span
                    className={cn(
                      "max-w-[260px] truncate text-[10px]",
                      hasError ? "text-red-400" : "text-slate-500",
                    )}
                  >
                    {a.result}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Bug & error tabs */}
      {liveResult && (
        <div className="rounded-xl border border-slate-700">
          <div className="grid grid-cols-3 border-b border-slate-700 text-[11px] font-semibold">
            <ColHeader label={`🐛 Bug'lar (${liveResult.analysis.bugs.length})`} />
            <ColHeader
              label={`⚠️ Console (${liveResult.console_errors.length})`}
            />
            <ColHeader
              label={`🌐 Network (${liveResult.network_errors.length})`}
            />
          </div>
          <div className="grid grid-cols-3 gap-px bg-slate-700">
            <div className="bg-slate-900/40 p-2 max-h-72 overflow-y-auto">
              {liveResult.analysis.bugs.length === 0 ? (
                <div className="text-[11px] text-slate-500 p-2">Bug yok 🎉</div>
              ) : (
                liveResult.analysis.bugs.map((b, i) => (
                  <div
                    key={i}
                    className="border-b border-slate-800 px-2 py-1.5 text-[11px]"
                  >
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
                      <span className="text-slate-300 truncate">
                        {b.category}
                      </span>
                      <span className="text-slate-500">×{b.count}</span>
                    </div>
                    <div className="mt-1 text-[10px] text-slate-500 truncate">
                      {b.sample}
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="bg-slate-900/40 p-2 max-h-72 overflow-y-auto">
              {liveResult.console_errors.length === 0 ? (
                <div className="text-[11px] text-slate-500 p-2">
                  Console temiz
                </div>
              ) : (
                liveResult.console_errors.map((c, i) => (
                  <div
                    key={i}
                    className="border-b border-slate-800 px-2 py-1.5 text-[10px]"
                  >
                    <div className="text-slate-400">{c.category}</div>
                    <div className="text-red-300 line-clamp-2">{c.text}</div>
                    <div className="text-slate-600 truncate">{c.url}</div>
                  </div>
                ))
              )}
            </div>
            <div className="bg-slate-900/40 p-2 max-h-72 overflow-y-auto">
              {liveResult.network_errors.length === 0 ? (
                <div className="text-[11px] text-slate-500 p-2">
                  Network temiz
                </div>
              ) : (
                liveResult.network_errors.map((n, i) => (
                  <div
                    key={i}
                    className="border-b border-slate-800 px-2 py-1.5 text-[10px]"
                  >
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
                      <span className="text-slate-400 truncate">
                        {n.category}
                      </span>
                    </div>
                    <div className="text-slate-500 truncate mt-0.5">{n.url}</div>
                  </div>
                ))
              )}
            </div>
          </div>

          {liveResult.analysis.recommendations.length > 0 && (
            <div className="border-t border-slate-700 bg-slate-900/40 p-3">
              <div className="text-[11px] font-semibold text-violet-300 mb-1">
                💡 Öneriler
              </div>
              <ul className="text-[11px] text-slate-300 space-y-1">
                {liveResult.analysis.recommendations.map((r, i) => (
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
      )}

      {/* Error drawer */}
      {drawerAction && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-end sm:items-center justify-center p-3"
          onClick={() => onSetDrawerAction(null)}
        >
          <div
            className="w-full max-w-2xl rounded-xl border border-slate-700 bg-slate-900 p-4 flex flex-col gap-2"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-100">
                Eylem #{drawerAction.step} — {drawerAction.type}
              </h3>
              <button
                type="button"
                onClick={() => onSetDrawerAction(null)}
                className="text-slate-500 hover:text-slate-200 text-lg leading-none"
              >
                ×
              </button>
            </div>
            <dl className="grid grid-cols-3 gap-y-1.5 gap-x-3 text-[11px]">
              {Object.entries(drawerAction).map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-slate-500">{k}</dt>
                  <dd className="col-span-2 font-mono text-slate-300 break-all">
                    {String(v ?? "—")}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}
    </>
  );
}
