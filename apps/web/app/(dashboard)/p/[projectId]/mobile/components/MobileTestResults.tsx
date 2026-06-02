"use client";

import Image from "next/image";
import { useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

// ─── Types (re-exported so the parent can import from one place) ──────────────

export interface DeviceProfile {
  name: string;
  slug: string;
  platform: "ios" | "android";
  os: string;
  viewport_width: number;
  viewport_height: number;
  icon: string;
  has_touch: boolean;
  device_scale_factor: number;
  playwright_key?: string;
}

export type RunStatus = "idle" | "running" | "done" | "error";

export interface DeviceRunState {
  status: RunStatus;
  passed: number;
  failed: number;
  screenshot_b64: string | null;
  logs: string[];
}

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Canlı screenshot büyük görünüm */
function LiveScreenshot({
  b64,
  deviceName,
}: {
  b64: string | null;
  deviceName: string;
}) {
  if (!b64) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border border-slate-700 bg-slate-800/40 text-slate-600 text-sm">
        <div className="text-center">
          <p className="text-2xl mb-1">📱</p>
          <p>Ekran bekleniyor...</p>
          <p className="text-xs mt-1">{deviceName}</p>
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-lg overflow-hidden border border-slate-700">
      <p className="bg-slate-800 px-3 py-1 text-[11px] text-slate-400 font-mono">
        {deviceName}
      </p>
      <Image
        src={`data:image/jpeg;base64,${b64}`}
        alt={`${deviceName} canlı ekran`}
        width={720}
        height={1280}
        unoptimized
        className="w-full max-h-80 object-contain bg-black"
      />
    </div>
  );
}

/** Mini log terminali */
function MiniLogTerminal({
  logs,
  deviceName,
}: {
  logs: string[];
  deviceName: string;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950 overflow-hidden">
      <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5">
        <span className="h-2 w-2 rounded-full bg-red-500" />
        <span className="h-2 w-2 rounded-full bg-yellow-500" />
        <span className="h-2 w-2 rounded-full bg-green-500" />
        <span className="ml-2 text-[11px] text-slate-400 font-mono">{deviceName}</span>
      </div>
      <div className="h-40 overflow-y-auto p-3 font-mono text-[11px] leading-relaxed text-slate-300">
        {logs.length === 0 ? (
          <span className="text-slate-600">Test çıktısı bekleniyor...</span>
        ) : (
          logs.map((line, i) => (
            <div
              key={i}
              className={cn(
                "whitespace-pre-wrap break-all",
                line.includes("PASSED")
                  ? "text-emerald-400"
                  : line.includes("FAILED")
                  ? "text-red-400"
                  : line.includes("ERROR")
                  ? "text-orange-400"
                  : "text-slate-300"
              )}
            >
              {line}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

/** Sonuç karşılaştırma tablosu — görünür hale gelir when at least one device is done */
function ResultsComparisonTable({
  devices,
  states,
}: {
  devices: DeviceProfile[];
  states: Record<string, DeviceRunState>;
}) {
  const done = devices.filter((d) => states[d.name]?.status === "done");
  if (done.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800/40 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/60">
        <h3 className="text-sm font-semibold text-slate-200">Sonuç Karşılaştırması</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/40">
            <tr>
              <th className="px-4 py-2 text-left text-[12px] text-slate-400 font-medium">Cihaz</th>
              <th className="px-4 py-2 text-center text-[12px] text-slate-400 font-medium">Geçti</th>
              <th className="px-4 py-2 text-center text-[12px] text-slate-400 font-medium">Kaldı</th>
              <th className="px-4 py-2 text-center text-[12px] text-slate-400 font-medium">Başarı %</th>
              <th className="px-4 py-2 text-left text-[12px] text-slate-400 font-medium">Platform</th>
            </tr>
          </thead>
          <tbody>
            {done.map((d) => {
              const st = states[d.name];
              const total = st.passed + st.failed;
              const rate = total > 0 ? Math.round((st.passed / total) * 100) : 0;
              return (
                <tr key={d.slug} className="border-t border-slate-700/50">
                  <td className="px-4 py-2 text-slate-200 text-[13px]">
                    <span className="mr-1">{d.icon}</span> {d.name}
                  </td>
                  <td className="px-4 py-2 text-center text-emerald-400 font-medium">
                    {st.passed}
                  </td>
                  <td className="px-4 py-2 text-center text-red-400 font-medium">
                    {st.failed}
                  </td>
                  <td className="px-4 py-2 text-center">
                    <span
                      className={cn(
                        "font-bold",
                        rate >= 80
                          ? "text-emerald-400"
                          : rate >= 50
                          ? "text-yellow-400"
                          : "text-red-400"
                      )}
                    >
                      {rate}%
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={cn(
                        "text-[11px] px-2 py-0.5 rounded font-medium",
                        d.platform === "ios"
                          ? "bg-slate-700 text-slate-300"
                          : "bg-green-900/40 text-green-400"
                      )}
                    >
                      {d.platform === "ios" ? "🍎 iOS" : "🤖 Android"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

export interface MobileTestResultsProps {
  /** Full list of virtual device profiles. */
  devices: DeviceProfile[];
  /** Per-device run states (screenshot, logs, pass/fail counts). */
  deviceRunStates: Record<string, DeviceRunState>;
  /** Currently selected device names. */
  selected: Set<string>;
  /** The device name whose live monitoring is currently shown. */
  activeDevice: string | null;
  /** Change the active monitoring device. */
  onSetActiveDevice: (deviceName: string) => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * MobileTestResults
 *
 * Right-side live monitoring panel for the Mobile test page (virtual tab).
 * Shows device selector tabs, the live screenshot, the log terminal, device
 * detail info, and the results comparison table.
 *
 * All state is owned by the parent (MobilePage).
 */
export function MobileTestResults({
  devices,
  deviceRunStates,
  selected,
  activeDevice,
  onSetActiveDevice,
}: MobileTestResultsProps) {
  const activeSt = deviceRunStates[activeDevice ?? ""] ?? null;
  const activeDeviceObj = devices.find((d) => d.name === activeDevice) ?? null;

  return (
    <div className="space-y-4">
      {/* ── Live monitoring panel ── */}
      <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Canlı İzleme</h2>

        {/* Device tab buttons */}
        {selected.size > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {Array.from(selected).map((dn) => {
              const st = deviceRunStates[dn];
              return (
                <button
                  key={dn}
                  type="button"
                  onClick={() => onSetActiveDevice(dn)}
                  className={cn(
                    "rounded-lg px-2.5 py-1 text-[12px] font-medium transition-colors",
                    activeDevice === dn
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-700 text-slate-400 hover:bg-slate-600"
                  )}
                >
                  {dn.split(" ")[0]}
                  {st?.status === "running" && (
                    <span className="ml-1 animate-pulse">●</span>
                  )}
                  {st?.status === "done" && (
                    <span className="ml-1 text-emerald-400">✓</span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Live screenshot */}
        <LiveScreenshot
          b64={activeSt?.screenshot_b64 ?? null}
          deviceName={activeDevice ?? "Cihaz seçilmedi"}
        />
      </div>

      {/* ── Log terminal ── */}
      {activeDevice && (
        <MiniLogTerminal
          logs={activeSt?.logs ?? []}
          deviceName={activeDevice}
        />
      )}

      {/* ── Device detail info ── */}
      {activeDeviceObj && (
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-xs text-slate-500 space-y-1.5">
          <h3 className="text-sm font-medium text-slate-300 mb-2">
            {activeDeviceObj.name}
          </h3>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            <span className="text-slate-600">Platform</span>
            <span className="text-slate-300">
              {activeDeviceObj.platform.toUpperCase()}
            </span>
            <span className="text-slate-600">OS</span>
            <span className="text-slate-300">{activeDeviceObj.os}</span>
            <span className="text-slate-600">Viewport</span>
            <span className="text-slate-300">
              {activeDeviceObj.viewport_width}×{activeDeviceObj.viewport_height}
            </span>
            <span className="text-slate-600">DPR</span>
            <span className="text-slate-300">
              ×{activeDeviceObj.device_scale_factor}
            </span>
            <span className="text-slate-600">Dokunmatik</span>
            <span className="text-slate-300">
              {activeDeviceObj.has_touch ? "Evet" : "Hayır"}
            </span>
            {activeDeviceObj.playwright_key && (
              <>
                <span className="text-slate-600">PW Key</span>
                <span className="text-slate-400 font-mono truncate">
                  {activeDeviceObj.playwright_key}
                </span>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Results comparison table ── */}
      <ResultsComparisonTable devices={devices} states={deviceRunStates} />
    </div>
  );
}
