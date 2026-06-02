"use client";

type AgentPhase =
  | "idle"
  | "starting"
  | "planning"
  | "running"
  | "summarizing"
  | "done"
  | "error";

interface AgentBrowserViewProps {
  screenshot: string;
  currentUrl: string;
  targetUrl: string;
  phase: AgentPhase;
  duration: number;
  maxSteps: number;
  currentStep: number;
}

function cn(...cls: (string | false | null | undefined)[]) {
  return cls.filter(Boolean).join(" ");
}

export function AgentBrowserView({
  screenshot,
  currentUrl,
  targetUrl,
  phase,
  duration,
  maxSteps,
  currentStep,
}: AgentBrowserViewProps) {
  const isRunning =
    phase === "starting" ||
    phase === "planning" ||
    phase === "running" ||
    phase === "summarizing";

  return (
    <div className="flex flex-col h-full">
      {/* URL bar */}
      <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900/80 px-3 py-2">
        <div className="flex gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/60" />
        </div>
        <div className="flex-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-0.5 text-[11px] font-mono text-slate-400 truncate">
          {currentUrl || targetUrl}
        </div>
        {isRunning && (
          <div
            className="h-2 w-2 rounded-full bg-violet-400 animate-pulse shrink-0"
            title="Tarayıcı aktif"
          />
        )}
      </div>

      {/* Step progress bar */}
      <div className="h-0.5 w-full bg-slate-800">
        <div
          className="h-full bg-gradient-to-r from-violet-600 to-sky-500 transition-all duration-500"
          style={{ width: `${Math.min(100, (currentStep / maxSteps) * 100)}%` }}
        />
      </div>

      {/* Screenshot area */}
      <div className="flex-1 overflow-hidden bg-slate-950 flex items-center justify-center">
        {screenshot ? (
          <img
            src={`data:image/jpeg;base64,${screenshot}`}
            alt="agent-view"
            className="h-full w-full object-contain"
          />
        ) : (
          <div className="flex flex-col items-center gap-3 text-slate-600">
            {isRunning ? (
              <>
                <div className="h-8 w-8 rounded-full border-2 border-violet-500/40 border-t-violet-400 animate-spin" />
                <span className="text-xs">
                  {phase === "starting" && "Tarayıcı başlatılıyor…"}
                  {phase === "planning" && "Hipotezler üretiliyor…"}
                  {phase === "running" && "Test yürütülüyor…"}
                  {phase === "summarizing" && "Özet hazırlanıyor…"}
                  {!["starting", "planning", "running", "summarizing"].includes(
                    phase
                  ) && "İşleniyor…"}
                </span>
                {duration > 0 && (
                  <span className="text-[10px] text-slate-700 font-mono">
                    {Math.floor(duration / 60)}:
                    {String(duration % 60).padStart(2, "0")}
                  </span>
                )}
              </>
            ) : (
              <span className="text-sm">Ekran görüntüsü yok</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
