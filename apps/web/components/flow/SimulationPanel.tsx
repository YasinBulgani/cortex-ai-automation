"use client";

import { Button } from "@/components/ui/button";

import type { SimulationState } from "./useFlowSimulation";

interface SimulationLog {
  nodeId: string;
  nodeLabel: string;
  status: "running" | "success" | "error" | "skipped";
  message: string;
  timestamp: number;
  duration?: number;
}

interface Props {
  simState: SimulationState;
  logs: SimulationLog[];
  progress: number;
  onRun: () => void;
  onStop: () => void;
  onPause: () => void;
  onResume: () => void;
  onReset: () => void;
  onClose: () => void;
}

export function SimulationPanel({
  simState,
  logs,
  progress,
  onRun,
  onStop,
  onPause,
  onResume,
  onReset,
  onClose,
}: Props) {
  return (
    <div className="absolute bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800 shadow-lg z-20 transition-all">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <h4 className="text-sm font-semibold text-white">Simülasyon</h4>

          {simState === "running" && (
            <span className="flex items-center gap-1.5 text-xs text-blue-600">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
              </span>
              Çalışıyor
            </span>
          )}
          {simState === "paused" && (
            <span className="text-xs text-amber-600 font-medium">Duraklatıldı</span>
          )}
          {simState === "completed" && (
            <span className="text-xs text-emerald-600 font-medium">Tamamlandı</span>
          )}
          {simState === "error" && (
            <span className="text-xs text-red-600 font-medium">Hata</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {simState === "idle" && (
            <Button
              variant="primary"
              size="sm"
              onClick={onRun}
              className="gap-1.5 bg-emerald-500 text-white hover:bg-emerald-600"
            >
              <span>▶</span> Çalıştır
            </Button>
          )}
          {simState === "running" && (
            <>
              <Button
                variant="primary"
                size="sm"
                onClick={onPause}
                className="gap-1.5 bg-amber-500 text-white hover:bg-amber-600"
              >
                <span>⏸</span> Duraklat
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={onStop}
                className="gap-1.5 bg-red-500 text-white hover:bg-red-600"
              >
                <span>⏹</span> Durdur
              </Button>
            </>
          )}
          {simState === "paused" && (
            <>
              <Button
                variant="primary"
                size="sm"
                onClick={onResume}
                className="gap-1.5 bg-emerald-500 text-white hover:bg-emerald-600"
              >
                <span>▶</span> Devam Et
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={onStop}
                className="gap-1.5 bg-red-500 text-white hover:bg-red-600"
              >
                <span>⏹</span> Durdur
              </Button>
            </>
          )}
          {(simState === "completed" || simState === "error") && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onReset}
              className="gap-1.5 bg-gray-500 text-white hover:bg-gray-600"
            >
              <span>↻</span> Sıfırla
            </Button>
          )}
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-lg leading-none ml-2"
          >
            ×
          </button>
        </div>
      </div>

      {simState !== "idle" && (
        <div className="h-1 bg-gray-200 dark:bg-gray-800">
          <div
            className="h-full transition-all duration-300 rounded-r-full"
            style={{
              width: `${progress}%`,
              background:
                simState === "error"
                  ? "#ef4444"
                  : simState === "completed"
                    ? "#10b981"
                    : "#3b82f6",
            }}
          />
        </div>
      )}

      <div className="max-h-48 overflow-y-auto p-3 space-y-1">
        {logs.length === 0 && simState === "idle" && (
          <p className="text-xs text-slate-400 text-center py-4">
            Simülasyonu başlatmak için &quot;Çalıştır&quot; butonuna tıklayın.
            <br />
            <span className="text-[10px]">Akış tetikleyici düğümden başlayarak sırayla çalışır.</span>
          </p>
        )}
        {logs.map((log, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className="text-[10px] text-slate-400 font-mono whitespace-nowrap mt-0.5">
              {new Date(log.timestamp).toLocaleTimeString("tr-TR")}
            </span>
            <span>
              {log.status === "running" && <span className="text-blue-500">●</span>}
              {log.status === "success" && <span className="text-emerald-500">✓</span>}
              {log.status === "error" && <span className="text-red-500">✗</span>}
              {log.status === "skipped" && <span className="text-gray-400">○</span>}
            </span>
            <span className="text-white">{log.message}</span>
            {log.duration != null && (
              <span className="text-slate-400 ml-auto whitespace-nowrap">{log.duration}ms</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
