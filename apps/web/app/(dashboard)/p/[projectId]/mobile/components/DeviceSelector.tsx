"use client";

import Image from "next/image";
import { useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

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

// ─── Internal sub-components ─────────────────────────────────────────────────

function StatusBadge({ status }: { status: RunStatus }) {
  const map: Record<RunStatus, { label: string; cls: string }> = {
    idle:    { label: "Bekliyor",    cls: "bg-slate-700 text-slate-400" },
    running: { label: "Çalışıyor",  cls: "bg-blue-900/60 text-blue-300 animate-pulse" },
    done:    { label: "Tamamlandı", cls: "bg-emerald-900/60 text-emerald-300" },
    error:   { label: "Hata",       cls: "bg-red-900/60 text-red-300" },
  };
  const { label, cls } = map[status];
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold", cls)}>
      {label}
    </span>
  );
}

function DeviceCard({
  device,
  selected,
  state,
  onToggle,
}: {
  device: DeviceProfile;
  selected: boolean;
  state: DeviceRunState;
  onToggle: () => void;
}) {
  const isIos = device.platform === "ios";
  return (
    <div
      data-testid={`device-card-${device.slug}`}
      className={cn(
        "relative rounded-xl border p-3 cursor-pointer transition-all select-none",
        selected
          ? "border-indigo-500 bg-indigo-950/40 shadow-indigo-900/30 shadow-md"
          : "border-slate-700 bg-slate-800/40 hover:border-slate-600"
      )}
      onClick={onToggle}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{device.icon}</span>
          <div>
            <p className="text-[13px] font-semibold text-slate-100 leading-tight">{device.name}</p>
            <p className="text-[11px] text-slate-500">{device.os}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge status={state.status} />
          {selected && (
            <span className="text-[10px] font-bold text-indigo-400">✓ SEÇİLİ</span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 text-[11px] text-slate-500 mb-2">
        <span>{device.viewport_width}×{device.viewport_height}</span>
        <span className={cn(
          "px-1.5 py-0.5 rounded font-medium",
          isIos ? "bg-slate-700 text-slate-300" : "bg-green-900/40 text-green-400"
        )}>
          {isIos ? "iOS" : "Android"}
        </span>
        {device.has_touch && <span className="text-slate-600">👆</span>}
      </div>

      {(state.passed > 0 || state.failed > 0) && (
        <div className="flex gap-2 text-[11px]">
          <span className="text-emerald-400">✓ {state.passed}</span>
          <span className="text-red-400">✗ {state.failed}</span>
        </div>
      )}

      {state.screenshot_b64 && (
        <div className="mt-2 overflow-hidden rounded border border-slate-700">
          <Image
            src={`data:image/jpeg;base64,${state.screenshot_b64}`}
            alt="Canlı ekran"
            width={320}
            height={160}
            unoptimized
            className="w-full h-20 object-cover object-top"
          />
        </div>
      )}
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

export interface DeviceSelectorProps {
  /** Full list of available virtual devices. */
  devices: DeviceProfile[];
  /** Set of currently selected device names. */
  selected: Set<string>;
  /** Per-device run states. */
  deviceRunStates: Record<string, DeviceRunState>;
  /** Whether a run is currently in progress. */
  running: boolean;
  /** Loading flag while devices are being fetched. */
  loading: boolean;
  /** Active device name for the live monitoring panel. */
  activeDevice: string | null;
  /** Toggle a device's selection state. */
  onToggle: (deviceName: string) => void;
  /** Called when the user changes the active monitoring device. */
  onSetActiveDevice: (deviceName: string) => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * DeviceSelector
 *
 * Renders the virtual device grid in the Mobile test page. Allows the user
 * to select one or multiple devices for a test run.
 *
 * All state lives in the parent (MobilePage); this component only calls the
 * provided callbacks on user interaction.
 */
export function DeviceSelector({
  devices,
  selected,
  deviceRunStates,
  loading,
  activeDevice,
  onToggle,
  onSetActiveDevice,
}: DeviceSelectorProps) {
  if (loading) {
    return (
      <div className="text-center py-8 text-slate-500 text-sm">
        Cihazlar yükleniyor...
      </div>
    );
  }

  if (devices.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500 text-sm">
        <p className="text-2xl mb-2">📱</p>
        <p>Cihaz bulunamadı.</p>
        <p className="text-xs mt-1">Engine bağlantısını kontrol edin.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {devices.map((d) => (
        <DeviceCard
          key={d.slug}
          device={d}
          selected={selected.has(d.name)}
          state={
            deviceRunStates[d.name] ?? {
              status: "idle",
              passed: 0,
              failed: 0,
              screenshot_b64: null,
              logs: [],
            }
          }
          onToggle={() => {
            onToggle(d.name);
            onSetActiveDevice(d.name);
          }}
        />
      ))}
    </div>
  );
}
