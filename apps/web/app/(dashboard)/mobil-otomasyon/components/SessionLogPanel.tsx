"use client";

// ─── Types ────────────────────────────────────────────────────────────────────

export type Device = {
  id: string;
  name: string;
};

export type Session = {
  id: string;
  deviceId: string;
  scenarioName: string;
  status: "queued" | "running" | "passed" | "failed";
  startedAt: number;
  finishedAt?: number;
  healed: number;
};

export type LogEntry = {
  id: number;
  ts: number;
  level: "info" | "warn" | "error" | "llm" | "heal";
  deviceId?: string;
  sessionId?: string;
  message: string;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmtMs = (ms: number) =>
  ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;

// ─── Props ────────────────────────────────────────────────────────────────────

export interface SessionLogPanelProps {
  /** List of sessions to display. */
  sessions: Session[];
  /** List of live log entries to display. */
  logs: LogEntry[];
  /** All devices — used to resolve device names in the session rows. */
  devices: Device[];
  /** Clear all log entries. */
  onClearLogs: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * SessionLogPanel
 *
 * Two-column panel showing the session history ("Koşular") on the left and
 * the live log stream ("Canlı Loglar") on the right.
 *
 * All state is owned by the parent (MobilOtomasyonPage). This component is
 * purely presentational and only invokes `onClearLogs` to clear the log list.
 */
export function SessionLogPanel({
  sessions,
  logs,
  devices,
  onClearLogs,
}: SessionLogPanelProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* ── Sessions ── */}
      <section className="rounded-lg border border-slate-800 overflow-hidden">
        <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3">
          <h2 className="text-sm font-semibold">📊 Koşular</h2>
          <p className="text-xs text-slate-400 mt-0.5">Son {sessions.length} session</p>
        </div>

        <div className="max-h-[380px] overflow-y-auto divide-y divide-slate-800/60">
          {sessions.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">Henüz koşu yok</div>
          ) : (
            sessions.map((s) => {
              const d = devices.find((x) => x.id === s.deviceId);
              const dur = s.finishedAt
                ? s.finishedAt - s.startedAt
                : Date.now() - s.startedAt;
              const color =
                s.status === "passed"
                  ? "text-emerald-400"
                  : s.status === "failed"
                  ? "text-red-400"
                  : "text-blue-400";
              return (
                <div key={s.id} className="flex items-center gap-3 px-4 py-2 text-xs">
                  <span className={`w-14 font-semibold uppercase ${color}`}>
                    {s.status}
                  </span>
                  <span className="flex-1 truncate">
                    <span className="font-medium">{s.scenarioName}</span>
                    {" · "}
                    <span className="text-slate-400">{d?.name ?? s.deviceId}</span>
                  </span>
                  {s.healed > 0 && (
                    <span className="text-amber-400">🔧{s.healed}</span>
                  )}
                  <span className="text-slate-500 font-mono">{fmtMs(dur)}</span>
                </div>
              );
            })
          )}
        </div>
      </section>

      {/* ── Live Logs ── */}
      <section className="rounded-lg border border-slate-800 overflow-hidden">
        <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold">📜 Canlı Loglar</h2>
            <p className="text-xs text-slate-400 mt-0.5">Son {logs.length} olay</p>
          </div>
          <button
            type="button"
            onClick={onClearLogs}
            className="text-[11px] text-slate-400 hover:text-white"
          >
            Temizle
          </button>
        </div>

        <div className="max-h-[380px] overflow-y-auto bg-slate-950/60">
          {logs.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">Henüz log yok</div>
          ) : (
            <ul className="divide-y divide-slate-800/40">
              {logs.map((l) => {
                const color =
                  l.level === "error" ? "text-red-400"
                  : l.level === "warn"  ? "text-amber-400"
                  : l.level === "llm"   ? "text-violet-300"
                  : l.level === "heal"  ? "text-amber-300"
                  : "text-slate-300";
                const icon =
                  l.level === "error" ? "✕"
                  : l.level === "warn"  ? "⚠"
                  : l.level === "llm"   ? "🧠"
                  : l.level === "heal"  ? "🔧"
                  : "›";
                return (
                  <li key={l.id} className="flex gap-2 px-3 py-1.5 text-[11px] font-mono">
                    <span className="text-slate-600 shrink-0">
                      {new Date(l.ts).toLocaleTimeString("tr-TR")}
                    </span>
                    <span className={`${color} shrink-0 w-3`}>{icon}</span>
                    <span className={`${color} truncate`}>{l.message}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
