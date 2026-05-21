"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

/* ── Types ─────────────────────────────────────────────────────────── */

interface LogEntry {
  timestamp: string;
  phase: string;
  agent: string;
  message: string;
  level: "info" | "success" | "error" | "warning";
}

interface PipelineStatus {
  run_id: string | null;
  phase: string;
  running: boolean;
  progress: number;
  started_at: string | null;
  completed_at: string | null;
  logs: LogEntry[];
  total?: number;
}

const PHASE_LABELS: Record<string, string> = {
  idle: "Hazır",
  analysis: "Analiz Ajanı",
  frontend_backend: "Frontend & Backend",
  test: "Test Ajanı",
  completed: "Tamamlandı",
  failed: "Başarısız",
};

const PHASE_ORDER = ["analysis", "frontend_backend", "test"];

const LEVEL_COLORS: Record<string, string> = {
  info: "text-blue-400",
  success: "text-emerald-400",
  warning: "text-amber-400",
  error: "text-red-400",
};

const LEVEL_ICONS: Record<string, string> = {
  info: "◦",
  success: "✓",
  warning: "⚠",
  error: "✗",
};

/* ── Component ─────────────────────────────────────────────────────── */

export function AgentRunner() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [starting, setStarting] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isRunning = status?.running ?? false;
  const phase = status?.phase ?? "idle";
  const progress = status?.progress ?? 0;

  const scrollToBottom = useCallback(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [logs.length, scrollToBottom]);

  /* ── Polling ── */
  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    let logIndex = 0;
    pollRef.current = setInterval(async () => {
      try {
        const data = await apiFetch<PipelineStatus & { total: number }>(
          `/api/v1/agents/logs?since=${logIndex}`
        );
        if (data.logs.length > 0) {
          setLogs((prev) => [...prev, ...data.logs]);
          logIndex = data.total;
        }
        setStatus({
          run_id: data.run_id,
          phase: data.phase,
          running: data.running,
          progress: data.progress,
          started_at: null,
          completed_at: null,
          logs: [],
        });
        if (!data.running) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
        }
      } catch {
        /* ignore transient failures */
      }
    }, 800);
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  /* ── Actions ── */
  const handleRunAll = async () => {
    setStarting(true);
    setLogs([]);
    try {
      await apiFetch<{ run_id: string }>("/api/v1/agents/run-all", {
        method: "POST",
        json: {},
      });
      setOpen(true);
      startPolling();
    } catch (err: any) {
      setLogs([
        {
          timestamp: new Date().toISOString(),
          phase: "error",
          agent: "İstemci",
          message: `Başlatma hatası: ${err.message}`,
          level: "error",
        },
      ]);
      setOpen(true);
    } finally {
      setStarting(false);
    }
  };

  const handleCancel = async () => {
    try {
      await apiFetch("/api/v1/agents/cancel", { method: "POST" });
    } catch {
      /* noop */
    }
  };

  /* ── Render helpers ── */
  const phaseIndex = PHASE_ORDER.indexOf(phase);

  return (
    <>
      {/* ── Trigger Button ── */}
      <button
        type="button"
        onClick={() => {
          if (isRunning) {
            setOpen(true);
          } else {
            handleRunAll();
          }
        }}
        disabled={starting}
        className={cn(
          "relative flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all",
          isRunning
            ? "bg-emerald-500/15 text-emerald-500 hover:bg-emerald-500/25 animate-pulse"
            : "bg-blue-600 text-blue-400-fg hover:opacity-90",
          starting && "opacity-50 cursor-wait"
        )}
        title="Tüm Ajanları Çalıştır"
        data-testid="btn-run-all-agents"
      >
        {isRunning ? (
          <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
            <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
          </svg>
        ) : (
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
        {isRunning ? `%${progress}` : "Ajanları Çalıştır"}
      </button>

      {/* ── Backdrop ── */}
      {open && (
        <div
          className="fixed left-0 right-0 top-14 bottom-0 z-40 bg-black/30 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}

      {/* ── Slide-out Drawer ── */}
      <div
        className={cn(
          "fixed right-0 top-14 bottom-0 z-50 flex w-[420px] max-w-[min(90vw,420px)] flex-col border-l border-slate-800 bg-slate-900 shadow-2xl transition-transform duration-300",
          open ? "translate-x-0" : "translate-x-full"
        )}
        role="dialog"
        aria-label="Ajan Orkestratörü"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <div className="flex items-center gap-2">
            <svg className="h-5 w-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <h2 className="text-sm font-bold text-white">Ajan Orkestratörü</h2>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded p-1 text-slate-400 hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
            aria-label="Kapat"
            title="Kapat"
            data-testid="btn-close-agent-drawer"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Phase Progress */}
        <div className="border-b border-slate-800 px-4 py-3">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Ilerleme ({Math.min(Math.floor(progress / 10) + 1, 10)}/10 döngü)</span>
            <span className="font-mono">%{progress}</span>
          </div>
          <div className="h-2 w-full rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                phase === "failed" ? "bg-red-500" : phase === "completed" ? "bg-emerald-500" : "bg-blue-600"
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-3 grid grid-cols-3 gap-1">
            {PHASE_ORDER.map((p, i) => {
              const isCurrent = phase === p;
              const isDone = phaseIndex > i || phase === "completed";
              return (
                <div
                  key={p}
                  className={cn(
                    "min-w-0 truncate rounded px-1.5 py-1.5 text-center text-[10px] font-medium transition-colors",
                    isCurrent && "bg-blue-500/20 text-blue-400 ring-1 ring-blue-500/40",
                    isDone && !isCurrent && "bg-emerald-500/15 text-emerald-500",
                    !isCurrent && !isDone && "bg-black/5 dark:bg-white/5 text-slate-400"
                  )}
                  title={PHASE_LABELS[p]}
                >
                  {isDone && !isCurrent ? "✓ " : ""}
                  {PHASE_LABELS[p]}
                </div>
              );
            })}
          </div>
        </div>

        {/* Logs */}
        <div className="flex-1 overflow-y-auto px-4 py-3 font-mono text-xs">
          {logs.length === 0 && !isRunning && (
            <div className="flex h-full items-center justify-center text-slate-400">
              <div className="text-center">
                <svg className="mx-auto mb-2 h-10 w-10 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p>Henüz log kaydı yok</p>
                <p className="mt-1 text-[10px]">Ajanları çalıştırmak için butona tıklayın</p>
              </div>
            </div>
          )}
          {logs.map((log, i) => (
            <div
              key={i}
              className={cn(
                "mb-1 flex flex-wrap items-baseline gap-x-2 gap-y-0.5 rounded px-2 py-1 transition-colors",
                log.level === "error" && "bg-red-500/5",
                log.level === "success" && "bg-emerald-500/5"
              )}
            >
              <span className={cn("shrink-0 w-3 text-center", LEVEL_COLORS[log.level])}>
                {LEVEL_ICONS[log.level]}
              </span>
              <span className="shrink-0 text-slate-400 tabular-nums">
                {new Date(log.timestamp).toLocaleTimeString("tr-TR", {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
              <span className="shrink-0 max-w-[140px] truncate text-slate-400" title={log.agent}>
                [{log.agent}]
              </span>
              <span className={cn("min-w-0 basis-full break-words sm:basis-0 sm:flex-1", LEVEL_COLORS[log.level] || "text-white")}>
                {log.message}
              </span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>

        {/* Footer actions */}
        <div className="border-t border-slate-800 px-4 py-3 flex items-center gap-2">
          {isRunning ? (
            <button
              type="button"
              onClick={handleCancel}
              className="flex-1 rounded-lg bg-red-500/15 px-3 py-2 text-xs font-semibold text-red-500 hover:bg-red-500/25 transition-colors"
              data-testid="btn-cancel-pipeline"
            >
              İptal Et
            </button>
          ) : (
            <button
              type="button"
              onClick={handleRunAll}
              disabled={starting}
              className="flex-1 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-blue-400-fg hover:opacity-90 transition-colors disabled:opacity-50"
              data-testid="btn-restart-pipeline"
            >
              {phase === "completed" || phase === "failed" ? "Tekrar Çalıştır" : "Tüm Ajanları Başlat"}
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              setLogs([]);
              setStatus(null);
            }}
            className="rounded-lg border border-slate-800 px-3 py-2 text-xs text-slate-400 hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
          >
            Temizle
          </button>
        </div>
      </div>
    </>
  );
}
