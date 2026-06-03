"use client";

import type { ModuleConfig } from "./module-service-map";
import { getServicesToStart, getServicesToStop } from "./module-service-map";

const SERVICE_LABELS: Record<string, { icon: string; label: string }> = {
  engine: { icon: "⚙", label: "Engine" },
  worker: { icon: "⬡", label: "Worker" },
  "ai-gateway": { icon: "◈", label: "AI Gateway" },
  postgres: { icon: "▦", label: "Postgres" },
  redis: { icon: "◉", label: "Redis" },
  backend: { icon: "▣", label: "Backend" },
};

interface Props {
  fromModule: ModuleConfig;
  toModule: ModuleConfig;
  onConfirm: () => void;
  onSkip: () => void;
}

export function ModuleTransitionDialog({ fromModule, toModule, onConfirm, onSkip }: Props) {
  const toStop = getServicesToStop(fromModule, toModule);
  const toStart = getServicesToStart(fromModule, toModule);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div
        className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="mod-transition-title"
      >
        {/* Header */}
        <div className="border-b border-slate-700/60 px-5 py-4">
          <div className="mb-1 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span className="font-mono text-[10px] font-semibold uppercase tracking-widest text-amber-400">
              Modül Geçişi
            </span>
          </div>
          <div id="mod-transition-title" className="flex items-center gap-2 text-sm">
            <span className="font-semibold text-white">{fromModule.label}</span>
            <span className="text-slate-500">→</span>
            <span className="font-semibold text-white">{toModule.label}</span>
          </div>
        </div>

        {/* Body */}
        <div className="space-y-4 px-5 py-4">
          <p className="text-sm text-slate-300">
            <span className="font-medium text-white">{fromModule.label}</span> modülüyle
            işiniz bitti mi?
          </p>

          {toStop.length > 0 && (
            <div>
              <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Durdurulacak
              </p>
              <div className="space-y-1">
                {toStop.map((s) => {
                  const meta = SERVICE_LABELS[s] ?? { icon: "○", label: s };
                  return (
                    <div key={s} className="flex items-center gap-2.5 text-sm">
                      <span className="w-4 text-center text-red-400">{meta.icon}</span>
                      <span className="font-mono text-slate-300">{meta.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {toStart.length > 0 && (
            <div>
              <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Başlatılacak
              </p>
              <div className="space-y-1">
                {toStart.map((s) => {
                  const meta = SERVICE_LABELS[s] ?? { icon: "○", label: s };
                  return (
                    <div key={s} className="flex items-center gap-2.5 text-sm">
                      <span className="w-4 text-center text-emerald-400">{meta.icon}</span>
                      <span className="font-mono text-slate-300">{meta.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 border-t border-slate-700/60 px-5 py-4">
          <button
            type="button"
            onClick={onConfirm}
            className="flex-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            Evet, geç
          </button>
          <button
            type="button"
            onClick={onSkip}
            className="flex-1 rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-500"
          >
            Servisleri canlı tut
          </button>
        </div>
      </div>
    </div>
  );
}
