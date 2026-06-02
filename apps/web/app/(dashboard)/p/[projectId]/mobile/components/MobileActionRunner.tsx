"use client";

import { cn } from "@/lib/utils";

type RunStatus = "idle" | "running" | "done" | "error";

interface MobileActionRunnerProps {
  running: boolean;
  selectedCount: number;
  selectedLiveCount?: number;
  browser: string;
  baseUrl: string;
  tags: string;
  error: string | null;
  liveRunError?: string | null;
  mode: "virtual" | "live";
  onRun: () => void;
  onStop: () => void;
  onBrowserChange: (v: string) => void;
  onBaseUrlChange: (v: string) => void;
  onTagsChange: (v: string) => void;
  uploadZone?: React.ReactNode;
}

export function MobileActionRunner({
  running,
  selectedCount,
  selectedLiveCount,
  browser,
  baseUrl,
  tags,
  error,
  liveRunError,
  mode,
  onRun,
  onStop,
  onBrowserChange,
  onBaseUrlChange,
  onTagsChange,
  uploadZone,
}: MobileActionRunnerProps) {
  const isLive = mode === "live";
  const count = isLive ? (selectedLiveCount ?? 0) : selectedCount;
  const accentRun = isLive ? "bg-purple-600 hover:bg-purple-500" : "bg-indigo-600 hover:bg-indigo-500";
  const accentBorder = isLive ? "focus:border-purple-500" : "focus:border-indigo-500";

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 space-y-4">
      <h2 className="text-sm font-semibold text-slate-300">
        {isLive ? "Canlı Cihaz Koşumu" : "Koşum Ayarları"}
      </h2>

      {!isLive && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label
              htmlFor="mobile-browser-select"
              className="block text-[11px] text-slate-500 mb-1"
            >
              Tarayıcı
            </label>
            <select
              id="mobile-browser-select"
              value={browser}
              onChange={(e) => onBrowserChange(e.target.value)}
              disabled={running}
              aria-label="Koşumda kullanılacak tarayıcı motoru"
              className={cn(
                "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:outline-none disabled:opacity-50",
                accentBorder
              )}
            >
              <option value="chromium">Chromium</option>
              <option value="firefox">Firefox</option>
              <option value="webkit">WebKit</option>
            </select>
          </div>
          <div>
            <label className="block text-[11px] text-slate-500 mb-1">
              Base URL (opsiyonel)
            </label>
            <input
              type="url"
              value={baseUrl}
              onChange={(e) => onBaseUrlChange(e.target.value)}
              disabled={running}
              placeholder="https://örnek.com"
              className={cn(
                "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:outline-none disabled:opacity-50",
                accentBorder
              )}
            />
          </div>
          <div>
            <label className="block text-[11px] text-slate-500 mb-1">
              Test etiketleri
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => onTagsChange(e.target.value)}
              disabled={running}
              placeholder="smoke, regression..."
              className={cn(
                "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:outline-none disabled:opacity-50",
                accentBorder
              )}
            />
          </div>
        </div>
      )}

      {isLive && (
        <div>
          <label className="block text-[11px] text-slate-500 mb-1">
            Test etiketleri
          </label>
          <input
            type="text"
            value={tags}
            onChange={(e) => onTagsChange(e.target.value)}
            disabled={running}
            placeholder="smoke, mobile, regression..."
            className={cn(
              "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:outline-none disabled:opacity-50",
              accentBorder
            )}
          />
        </div>
      )}

      {uploadZone && (
        <div>
          <label className="block text-[11px] text-slate-500 mb-2">
            Uygulama (APK/IPA) — Opsiyonel
          </label>
          {uploadZone}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={running ? onStop : onRun}
          disabled={!running && count === 0}
          data-testid="mobile-run-btn"
          className={cn(
            "flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors",
            running
              ? "bg-red-700 hover:bg-red-600 text-white"
              : count > 0
                ? `${accentRun} text-white`
                : "bg-slate-700 text-slate-500 cursor-not-allowed"
          )}
        >
          {running ? (
            <>
              <span className="animate-spin">⏹</span>
              Durdur
            </>
          ) : (
            <>
              ▶{" "}
              {count > 1
                ? `${count} Cihazda ${isLive ? "Koştur" : "Paralel Koştur"}`
                : "Koştur"}
            </>
          )}
        </button>
        {count > 0 && !running && (
          <span className="text-slate-500 text-sm">{count} cihaz seçili</span>
        )}
      </div>

      {error && <p className="text-red-400 text-sm">⚠ {error}</p>}
      {liveRunError && <p className="text-red-400 text-sm">⚠ {liveRunError}</p>}
    </div>
  );
}
