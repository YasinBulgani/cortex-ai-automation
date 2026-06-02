"use client";

// ─── Types ────────────────────────────────────────────────────────────────────

export type Platform = "android" | "ios";
export type DeviceKind = "emulator" | "simulator" | "physical";
export type DeviceStatus = "idle" | "running" | "booting" | "offline" | "error";

export type Device = {
  id: string;
  name: string;
  platform: Platform;
  osVersion: string;
  profile: string;
  kind: DeviceKind;
  status: DeviceStatus;
  battery: number;
  cpuPct: number;
  ramPct: number;
  appiumPort: number;
  currentStep?: string;
  stepsDone: number;
  stepsTotal: number;
  healStreak: number;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function statusPill(s: DeviceStatus) {
  const map: Record<DeviceStatus, string> = {
    idle:    "bg-slate-500/15 text-slate-300 border-slate-500/30",
    running: "bg-blue-500/15 text-blue-300 border-blue-500/30 animate-pulse",
    booting: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    offline: "bg-slate-700/40 text-slate-500 border-slate-600/40",
    error:   "bg-red-500/15 text-red-300 border-red-500/30",
  };
  const label: Record<DeviceStatus, string> = {
    idle: "hazır", running: "çalışıyor", booting: "açılıyor", offline: "kapalı", error: "hata",
  };
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${map[s]}`}>
      {label[s]}
    </span>
  );
}

function platformBadge(p: Platform, os: string, kind: DeviceKind) {
  const color = p === "ios" ? "text-slate-200" : "text-emerald-300";
  const icon  = p === "ios" ? "" : "🤖";
  const kindLabel = kind === "emulator" ? "emu" : kind === "simulator" ? "sim" : "fiz";
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] ${color}`}>
      <span className="text-sm leading-none">{icon}</span>
      <span className="font-medium">{p === "ios" ? "iOS" : "Android"} {os}</span>
      <span className="rounded bg-slate-800 px-1 text-[9px] uppercase tracking-wide text-slate-400">{kindLabel}</span>
    </span>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

export interface DeviceFarmGridProps {
  /** Full list of devices in the farm. */
  devices: Device[];
  /** The currently selected device id (for detail panel), or null. */
  activeDeviceId: string | null;
  /** Toggle active device selection. Passes null when deselecting same device. */
  onSelectDevice: (id: string | null) => void;
  /** Reboot a device by id. */
  onReboot: (id: string) => void;
  /** Open the mock device screen modal for the active device. */
  onOpenScreen: () => void;
  /** Take a mock screenshot of the active device. */
  onScreenshot: () => void;
  /** Run a session on the active device. */
  onRunDevice: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * DeviceFarmGrid
 *
 * Renders the "Cihaz Farm'ı" section of the Mobil Otomasyon page. Shows the
 * 10-device grid with live CPU/RAM/battery metrics and — when a device is
 * selected — an expanded detail panel with action buttons.
 *
 * All state is owned by the parent (MobilOtomasyonPage). This component is
 * purely presentational and only calls the provided callbacks on user
 * interaction.
 */
export function DeviceFarmGrid({
  devices,
  activeDeviceId,
  onSelectDevice,
  onReboot,
  onOpenScreen,
  onScreenshot,
  onRunDevice,
}: DeviceFarmGridProps) {
  const activeDevice = devices.find((d) => d.id === activeDeviceId) ?? null;

  return (
    <section className="rounded-lg border border-slate-800 overflow-hidden">
      <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3">
        <h2 className="text-sm font-semibold">🖥️ Cihaz Farm&apos;ı (10 sanal)</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Appium port eşlemesi 4723–4728 (Android), 4730–4733 (iOS). Canlı CPU/RAM metriği her 1.5 sn güncellenir.
        </p>
      </div>

      {/* Device grid */}
      <div className="p-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {devices.map((d) => {
          const progress = d.stepsTotal
            ? Math.round((d.stepsDone / d.stepsTotal) * 100)
            : 0;
          return (
            <div
              key={d.id}
              onClick={() => onSelectDevice(d.id === activeDeviceId ? null : d.id)}
              className={`cursor-pointer rounded-lg border p-3 space-y-2 transition-colors
                ${activeDeviceId === d.id
                  ? "border-blue-500/60 bg-blue-500/5"
                  : "border-slate-800 bg-slate-900/20 hover:border-slate-700"}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs font-semibold truncate">{d.name}</p>
                  {platformBadge(d.platform, d.osVersion, d.kind)}
                </div>
                {statusPill(d.status)}
              </div>

              {/* Mini "phone frame" */}
              <div
                className={`relative mx-auto aspect-[9/19] w-[70px] rounded-[10px] border border-slate-700
                  ${d.status === "offline"
                    ? "bg-slate-900"
                    : "bg-gradient-to-b from-slate-800 to-slate-950"}
                  flex items-center justify-center overflow-hidden`}
              >
                <div className="absolute left-1/2 top-0.5 h-1 w-5 -translate-x-1/2 rounded-full bg-slate-700" />
                {d.status === "running" && (
                  <div className="absolute inset-0 flex items-end justify-center pb-2">
                    <div className="h-0.5 w-[80%] bg-slate-800 rounded overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                )}
                {d.status === "booting"  && <div className="text-[8px] text-amber-400 animate-pulse">boot…</div>}
                {d.status === "error"    && <div className="text-[8px] text-red-400">err</div>}
                {d.status === "offline"  && <div className="text-[8px] text-slate-600">off</div>}
                {d.status === "idle"     && <div className="text-[8px] text-slate-500">idle</div>}
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-1 text-[10px]">
                <div className="rounded bg-slate-950/60 px-1.5 py-1 text-center">
                  <p className="text-slate-500">CPU</p>
                  <p className="font-mono text-slate-300">{d.cpuPct}%</p>
                </div>
                <div className="rounded bg-slate-950/60 px-1.5 py-1 text-center">
                  <p className="text-slate-500">RAM</p>
                  <p className="font-mono text-slate-300">{d.ramPct}%</p>
                </div>
                <div className="rounded bg-slate-950/60 px-1.5 py-1 text-center">
                  <p className="text-slate-500">🔋</p>
                  <p className="font-mono text-slate-300">{d.battery}%</p>
                </div>
              </div>

              {/* Status row */}
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-slate-500">:{d.appiumPort}</span>
                {d.status === "running" ? (
                  <span className="text-blue-300 truncate">
                    {d.stepsDone}/{d.stepsTotal} · {d.currentStep}
                  </span>
                ) : d.healStreak > 0 ? (
                  <span className="text-amber-300">🔧 {d.healStreak} heal</span>
                ) : (
                  <span className="text-slate-600">—</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected device detail panel */}
      {activeDevice && (
        <div className="border-t border-slate-800 bg-slate-950/40 p-4 grid gap-4 md:grid-cols-[1fr_auto]">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <p className="text-sm font-semibold">{activeDevice.name}</p>
              {statusPill(activeDevice.status)}
              {platformBadge(activeDevice.platform, activeDevice.osVersion, activeDevice.kind)}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
              <div>
                <span className="text-slate-500">Profile:</span>{" "}
                <span className="font-mono text-slate-300">{activeDevice.profile}</span>
              </div>
              <div>
                <span className="text-slate-500">Kind:</span>{" "}
                <span className="font-mono text-slate-300">{activeDevice.kind}</span>
              </div>
              <div>
                <span className="text-slate-500">Appium URL:</span>{" "}
                <span className="font-mono text-slate-300">
                  http://127.0.0.1:{activeDevice.appiumPort}
                </span>
              </div>
              <div>
                <span className="text-slate-500">ID:</span>{" "}
                <span className="font-mono text-slate-300">{activeDevice.id}</span>
              </div>
            </div>
          </div>

          <div className="flex gap-2 flex-wrap">
            <button
              type="button"
              onClick={onOpenScreen}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 transition-colors"
            >
              📱 Ekranı Aç
            </button>
            <button
              type="button"
              onClick={() => onReboot(activeDevice.id)}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 transition-colors"
            >
              🔄 Reboot
            </button>
            <button
              type="button"
              onClick={onScreenshot}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-700 transition-colors"
            >
              📸 Screenshot
            </button>
            <button
              type="button"
              onClick={onRunDevice}
              className="inline-flex items-center gap-1.5 rounded-md bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-500 transition-colors"
            >
              ▶️ Bu cihazda koş
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
