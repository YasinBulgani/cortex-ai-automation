"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { MobileAiScenarioCard } from "@/components/dsl/MobileAiScenarioCard";
import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";
import { engineFetch, ENGINE_BASE } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { FlowGuideCard } from "@/components/FlowGuideCard";

interface DeviceProfile {
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

type RunStatus = "idle" | "running" | "done" | "error";

interface DeviceRunState {
  status: RunStatus;
  passed: number;
  failed: number;
  screenshot_b64: string | null;
  logs: string[];
}

interface UploadedApp {
  upload_id: string;
  filename: string;
  size: number;
  platform_hint: string;
}

function StatusBadge({ status }: { status: RunStatus }) {
  const map: Record<RunStatus, { label: string; cls: string }> = {
    idle: { label: "Bekliyor", cls: "bg-slate-700 text-slate-400" },
    running: { label: "Çalışıyor", cls: "bg-blue-900/60 text-blue-300 animate-pulse" },
    done: { label: "Tamamlandı", cls: "bg-emerald-900/60 text-emerald-300" },
    error: { label: "Hata", cls: "bg-red-900/60 text-red-300" },
  };
  const { label, cls } = map[status];
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold", cls)}>
      {label}
    </span>
  );
}

/** Cihaz kartı */
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
        <span className={cn("px-1.5 py-0.5 rounded font-medium", isIos ? "bg-slate-700 text-slate-300" : "bg-green-900/40 text-green-400")}>
          {isIos ? "iOS" : "Android"}
        </span>
        {device.has_touch && <span className="text-slate-600">👆</span>}
      </div>

      {/* Pass/fail sayacı */}
      {(state.passed > 0 || state.failed > 0) && (
        <div className="flex gap-2 text-[11px]">
          <span className="text-emerald-400">✓ {state.passed}</span>
          <span className="text-red-400">✗ {state.failed}</span>
        </div>
      )}

      {/* Canlı screenshot küçük önizleme */}
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

/** Canlı screenshot büyük görünüm */
function LiveScreenshot({ b64, deviceName }: { b64: string | null; deviceName: string }) {
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
      <p className="bg-slate-800 px-3 py-1 text-[11px] text-slate-400 font-mono">{deviceName}</p>
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
function MiniLogTerminal({ logs, deviceName }: { logs: string[]; deviceName: string }) {
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
            <div key={i} className={cn(
              "whitespace-pre-wrap break-all",
              line.includes("PASSED") ? "text-emerald-400" :
              line.includes("FAILED") ? "text-red-400" :
              line.includes("ERROR") ? "text-orange-400" :
              "text-slate-300"
            )}>
              {line}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

/** APK / IPA yükleme alanı */
function AppUploadZone({
  onUploaded,
}: {
  onUploaded: (app: UploadedApp) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState<UploadedApp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${ENGINE_BASE}/api/mobile/upload-app`, {
        method: "POST",
        body: form,
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Yükleme başarısız" }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      const data: UploadedApp = await res.json();
      setUploaded(data);
      onUploaded(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  if (uploaded) {
    return (
      <div className="rounded-lg border border-emerald-700/50 bg-emerald-900/20 p-3 text-sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-emerald-300 font-medium">✓ {uploaded.filename}</p>
            <p className="text-slate-500 text-xs mt-0.5">
              {formatSize(uploaded.size)} · {uploaded.platform_hint.toUpperCase()}
            </p>
          </div>
          <button
            type="button"
            onClick={() => { setUploaded(null); onUploaded(null as unknown as UploadedApp); }}
            className="text-slate-500 hover:text-slate-300 text-xs px-2 py-1 rounded hover:bg-slate-700"
          >
            Değiştir
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-lg border-2 border-dashed p-4 text-center transition-colors cursor-pointer",
        dragging ? "border-indigo-500 bg-indigo-950/30" : "border-slate-700 hover:border-slate-600",
        uploading && "opacity-60 pointer-events-none"
      )}
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => fileRef.current?.click()}
    >
      <input
        ref={fileRef}
        type="file"
        accept=".apk,.ipa,.aab,.xapk"
        aria-label="APK veya IPA dosyası seç"
        title="APK veya IPA dosyası seç"
        className="hidden"
        onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />
      {uploading ? (
        <p className="text-slate-400 text-sm animate-pulse">Yükleniyor...</p>
      ) : (
        <>
          <p className="text-2xl mb-1">📦</p>
          <p className="text-slate-400 text-sm">APK / IPA sürükle veya tıkla</p>
          <p className="text-slate-600 text-xs mt-1">.apk, .ipa, .aab, .xapk</p>
        </>
      )}
      {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
    </div>
  );
}

// ─── Canlı Cihaz Tipleri ──────────────────────────────────────────────────────

interface LiveDevice {
  serial: string;
  state: string;
  online: boolean;
  platform: "android" | "ios";
  device_type: "emulator" | "simulator" | "physical";
  name: string;
  brand: string;
  android_version: string;
  ios_version?: string;
  screen_size: string;
  health_score: number;
  battery: { level?: number };
  installed_apps_count: number;
  uptime: string;
}

type LiveRunStatus = "idle" | "running" | "done" | "error";

const DEVICE_TYPE_META: Record<string, { label: string; cls: string }> = {
  emulator: { label: "Emülatör", cls: "bg-green-500/15 text-green-300 border-green-500/25" },
  simulator: { label: "Simülatör", cls: "bg-blue-500/15 text-blue-300 border-blue-500/25" },
  physical: { label: "Fiziksel", cls: "bg-purple-500/15 text-purple-300 border-purple-500/25" },
};

function healthColor(s: number) {
  return s >= 80 ? "text-emerald-400" : s >= 50 ? "text-yellow-400" : "text-red-400";
}

function LiveDeviceCard({
  device,
  selected,
  liveStatus,
  onSelect,
}: {
  device: LiveDevice;
  selected: boolean;
  liveStatus: LiveRunStatus;
  onSelect: () => void;
}) {
  const ts = DEVICE_TYPE_META[device.device_type] ?? DEVICE_TYPE_META.physical;
  const statusMap: Record<LiveRunStatus, { label: string; cls: string }> = {
    idle: { label: "Bekliyor", cls: "bg-slate-700 text-slate-400" },
    running: { label: "Çalışıyor", cls: "bg-purple-900/60 text-purple-300 animate-pulse" },
    done: { label: "Tamamlandı", cls: "bg-emerald-900/60 text-emerald-300" },
    error: { label: "Hata", cls: "bg-red-900/60 text-red-300" },
  };
  const statusMeta = statusMap[liveStatus];

  return (
    <div
      onClick={onSelect}
      className={cn(
        "relative rounded-xl border p-4 cursor-pointer transition-all select-none",
        selected
          ? "border-purple-500 bg-purple-950/30 ring-1 ring-purple-500/30"
          : device.online
            ? "border-slate-700 bg-slate-800/40 hover:border-slate-500"
            : "border-slate-800 bg-slate-900/30 opacity-55",
      )}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className="relative shrink-0">
          <span className="text-2xl">{device.platform === "ios" ? "🍎" : "🤖"}</span>
          <span className={cn(
            "absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-slate-800",
            device.online ? "bg-emerald-500" : "bg-slate-600"
          )} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-white truncate">{device.name}</p>
          <p className="text-xs text-slate-500">{device.brand}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold", statusMeta.cls)}>
            {statusMeta.label}
          </span>
          <span className={cn("text-sm font-bold", healthColor(device.health_score))}>
            {device.health_score}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <div className="flex justify-between col-span-2">
          <span className="text-slate-500">Tip</span>
          <span className={cn("px-1.5 py-0.5 rounded border text-[10px] font-semibold", ts.cls)}>{ts.label}</span>
        </div>
        <div className="flex justify-between col-span-2">
          <span className="text-slate-500">Platform</span>
          <span className={cn(
            "px-1.5 py-0.5 rounded text-[10px] font-semibold",
            device.platform === "ios" ? "bg-slate-700 text-slate-300" : "bg-green-900/40 text-green-400"
          )}>
            {device.platform === "ios" ? "iOS " + (device.ios_version ?? "") : "Android " + (device.android_version ?? "")}
          </span>
        </div>
        {device.screen_size && (
          <div className="flex justify-between col-span-2">
            <span className="text-slate-500">Ekran</span>
            <span className="text-slate-300">{device.screen_size}</span>
          </div>
        )}
      </div>

      {device.online && device.battery.level != null && (
        <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
          <span>🔋 %{device.battery.level}</span>
          <span>·</span>
          <span>📱 {device.installed_apps_count} uygulama</span>
        </div>
      )}

      <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-800/50">
        <span className="text-[10px] text-slate-600 font-mono truncate max-w-[120px]">{device.serial.substring(0, 16)}</span>
        {selected && <span className="text-[10px] font-bold text-purple-400">✓ SEÇİLİ</span>}
      </div>
    </div>
  );
}

/** Karşılaştırma tablosu — tüm cihazlar bitince */
function ResultsComparisonTable({
  devices,
  states,
}: {
  devices: DeviceProfile[];
  states: Record<string, DeviceRunState>;
}) {
  const done = devices.filter(d => states[d.name]?.status === "done");
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
            {done.map(d => {
              const st = states[d.name];
              const total = st.passed + st.failed;
              const rate = total > 0 ? Math.round((st.passed / total) * 100) : 0;
              return (
                <tr key={d.slug} className="border-t border-slate-700/50">
                  <td className="px-4 py-2 text-slate-200 text-[13px]">
                    <span className="mr-1">{d.icon}</span> {d.name}
                  </td>
                  <td className="px-4 py-2 text-center text-emerald-400 font-medium">{st.passed}</td>
                  <td className="px-4 py-2 text-center text-red-400 font-medium">{st.failed}</td>
                  <td className="px-4 py-2 text-center">
                    <span className={cn(
                      "font-bold",
                      rate >= 80 ? "text-emerald-400" : rate >= 50 ? "text-yellow-400" : "text-red-400"
                    )}>
                      {rate}%
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span className={cn(
                      "text-[11px] px-2 py-0.5 rounded font-medium",
                      d.platform === "ios" ? "bg-slate-700 text-slate-300" : "bg-green-900/40 text-green-400"
                    )}>
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

// ─── Wi-Fi ADB / iOS Bağlantı Paneli ──────────────────────────────────────────

function WifiAdbPanel() {
  const [wifiIp, setWifiIp] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectResult, setConnectResult] = useState<string | null>(null);

  async function handleConnect() {
    if (!wifiIp.trim()) return;
    setConnecting(true);
    setConnectResult(null);
    try {
      const res = await fetch("/api/device-manager/wifi-connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: wifiIp.trim() }),
      });
      const json = await res.json().catch(() => ({}));
      setConnectResult(res.ok ? `✓ Bağlandı: ${wifiIp}` : `✗ ${json?.detail ?? "Bağlantı başarısız"}`);
    } catch {
      setConnectResult("✗ Sunucuya ulaşılamadı");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-700 bg-slate-800/30 p-8 text-center space-y-3">
        <p className="text-4xl">🔌</p>
        <p className="text-slate-300 font-semibold">Bağlı canlı cihaz yok</p>
        <p className="text-sm text-slate-500 max-w-md mx-auto">
          Fiziksel Android veya iOS cihazını USB/Wi-Fi ile bağlayın. Android için ADB,
          iOS için Xcode araçları gereklidir.
        </p>
        <div className="flex flex-col items-center gap-2 mt-2 text-xs text-slate-600">
          <code className="font-mono bg-slate-900 px-3 py-1 rounded">adb devices</code>
          <span>veya</span>
          <code className="font-mono bg-slate-900 px-3 py-1 rounded">xcrun simctl list devices</code>
        </div>
      </div>

      {/* Wi-Fi ADB hızlı bağlantı */}
      <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-5 space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">📡</span>
          <h3 className="text-sm font-semibold text-blue-200">Wi-Fi ADB Bağlantısı</h3>
          <span className="rounded-full border border-amber-400/20 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-300">Android</span>
        </div>
        <p className="text-xs text-slate-400">
          Cihazda Wi-Fi ADB&apos;yi etkinleştirin: <code className="font-mono text-slate-300">adb tcpip 5555</code> ardından IP&apos;yi girin.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="192.168.1.42:5555"
            value={wifiIp}
            onChange={(e) => setWifiIp(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleConnect()}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleConnect}
            disabled={connecting || !wifiIp.trim()}
            className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {connecting ? "Bağlanıyor…" : "Bağlan"}
          </button>
        </div>
        {connectResult && (
          <p className={`text-xs font-medium ${connectResult.startsWith("✓") ? "text-emerald-400" : "text-red-400"}`}>
            {connectResult}
          </p>
        )}
      </div>

      {/* iOS talimatları */}
      <div className="rounded-xl border border-slate-700 bg-slate-800/20 p-5 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">🍎</span>
          <h3 className="text-sm font-semibold text-slate-300">iOS Bağlantısı (Xcode)</h3>
          <span className="rounded-full border border-slate-600 bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-slate-400">Planlı</span>
        </div>
        <ol className="text-xs text-slate-500 space-y-1 list-decimal list-inside">
          <li>Xcode → Window → Devices and Simulators</li>
          <li>Cihazı USB ile bağlayın, &quot;Trust&quot; onaylayın</li>
          <li>WebDriverAgent ile Appium XCUITest driver kullanın</li>
          <li>Kablosuz için: Devices → Connect via network</li>
        </ol>
      </div>
    </div>
  );
}

// ─── Ana Sayfa ─────────────────────────────────────────────────────────────────

export default function NeurexFarmPage() {
  const projectId = useRouteParam("projectId");

  const [devices, setDevices] = useState<DeviceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deviceRunStates, setDeviceRunStates] = useState<Record<string, DeviceRunState>>({});
  const [running, setRunning] = useState(false);
  const currentRunIdRef = useRef<string | null>(null);
  const [browser, setBrowser] = useState("chromium");
  const [baseUrl, setBaseUrl] = useState("");
  const [tags, setTags] = useState("");
  const [uploadedApp, setUploadedApp] = useState<UploadedApp | null>(null);
  const [activeDevice, setActiveDevice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Sekme durumu
  const [tab, setTab] = useState<"virtual" | "live">("virtual");

  // Canlı cihaz state'leri
  const [liveDevices, setLiveDevices] = useState<LiveDevice[]>([]);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [selectedLive, setSelectedLive] = useState<Set<string>>(new Set());
  const [liveRunStates, setLiveRunStates] = useState<Record<string, LiveRunStatus>>({});
  const [liveRunning, setLiveRunning] = useState(false);
  const [liveRunError, setLiveRunError] = useState<string | null>(null);
  const [liveRefreshCount, setLiveRefreshCount] = useState(0);
  const [liveFilter, setLiveFilter] = useState<"tümü" | "android" | "ios" | "fiziksel">("tümü");

  const activeDeviceObj = devices.find(d => d.name === activeDevice) ?? null;
  const activeSt = deviceRunStates[activeDevice ?? ""] ?? null;
  const selectedCount = selected.size;
  const selectedLiveCount = selectedLive.size;

  // Canlı cihazları yükle (sekme değiştiğinde veya yenileme sayacı arttığında)
  useEffect(() => {
    if (tab !== "live") return;
    setLiveLoading(true);
    setLiveError(null);
    engineFetch<{ devices: LiveDevice[] }>("/api/device-manager/devices")
      .then((data) => {
        const list = data.devices ?? [];
        setLiveDevices(list);
        const initStates: Record<string, LiveRunStatus> = {};
        for (const d of list) initStates[d.serial] = "idle";
        setLiveRunStates(initStates);
      })
      .catch(() => setLiveError("Canlı cihaz listesi alınamadı. Engine veya ADB bağlantısını kontrol edin."))
      .finally(() => setLiveLoading(false));
  }, [tab, liveRefreshCount]);

  // Cihaz listesini yükle
  useEffect(() => {
    (async () => {
      try {
        const list = await engineFetch<DeviceProfile[]>("/api/mobile/devices");
        if (Array.isArray(list)) {
          setDevices(list);
          const initStates: Record<string, DeviceRunState> = {};
          for (const d of list) {
            initStates[d.name] = { status: "idle", passed: 0, failed: 0, screenshot_b64: null, logs: [] };
          }
          setDeviceRunStates(initStates);
        }
      } catch {
        /* engine offline */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const toggle = useCallback((name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  }, []);

  const handleRun = async () => {
    if (selected.size === 0) return setError("En az bir cihaz seçin.");
    setError(null);
    setRunning(true);

    // selected Set, device.name tutuyor — name→slug dönüşümü yap
    const selectedDevices = devices.filter(d => selected.has(d.name));
    const slugs = selectedDevices.map(d => d.slug);

    setDeviceRunStates((prev) => {
      const n = { ...prev };
      for (const d of selected) {
        n[d] = { ...n[d], status: "running" };
      }
      return n;
    });

    try {
      const isMulti = slugs.length > 1;
      const endpoint = isMulti ? "/api/mobile/run-parallel" : "/api/mobile/run";
      const body = isMulti
        ? { device_slugs: slugs, project_id: projectId }
        : { device_slug: slugs[0], project_id: projectId };

      const result = await engineFetch<{ run_id: string; device_run_ids?: Record<string, string> }>(endpoint, {
        method: "POST",
        json: body,
      });

      const run_id = result.run_id;
      currentRunIdRef.current = run_id;

      // SSE stream'e bağlan
      const eventSource = new EventSource(`${ENGINE_BASE}/api/mobile/run/${run_id}/stream`);

      eventSource.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as {
            type: string;
            device_name?: string;
            data?: string;
            screenshot_b64?: string;
            passed?: number;
            failed?: number;
            status?: string;
          };

          if (msg.type === "output" && msg.device_name) {
            setDeviceRunStates((prev) => {
              const n = { ...prev };
              const key = msg.device_name!;
              if (n[key]) {
                n[key] = { ...n[key], logs: [...n[key].logs, msg.data ?? ""] };
              }
              return n;
            });
          } else if (msg.type === "image" && msg.device_name) {
            setDeviceRunStates((prev) => {
              const n = { ...prev };
              const key = msg.device_name!;
              if (n[key]) {
                n[key] = { ...n[key], screenshot_b64: msg.screenshot_b64 ?? null };
              }
              return n;
            });
          } else if (msg.type === "test_result" && msg.device_name) {
            setDeviceRunStates((prev) => {
              const n = { ...prev };
              const key = msg.device_name!;
              if (n[key]) {
                n[key] = {
                  ...n[key],
                  passed: (msg.passed ?? 0),
                  failed: (msg.failed ?? 0),
                };
              }
              return n;
            });
          } else if (msg.type === "done" && msg.device_name) {
            setDeviceRunStates((prev) => {
              const n = { ...prev };
              const key = msg.device_name!;
              if (n[key]) {
                n[key] = { ...n[key], status: msg.status === "error" ? "error" : "done" };
              }
              return n;
            });
          } else if (msg.type === "all_done") {
            currentRunIdRef.current = null;
            setRunning(false);
            eventSource.close();
          }
        } catch {
          /* JSON parse hatası — yoksay */
        }
      };

      eventSource.onerror = () => {
        currentRunIdRef.current = null;
        setRunning(false);
        eventSource.close();
      };
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setDeviceRunStates((prev) => {
        const n = { ...prev };
        for (const d of selected) {
          n[d] = { ...n[d], status: "error" };
        }
        return n;
      });
      currentRunIdRef.current = null;
      setRunning(false);
    }
  };

  const handleStop = () => {
    const runId = currentRunIdRef.current;
    if (runId) {
      currentRunIdRef.current = null;
      engineFetch<unknown>(`/api/mobile/run/${runId}/stop`, { method: "POST" }).catch(() => {/* best-effort */});
    }
    setRunning(false);
    setDeviceRunStates((prev) => {
      const n = { ...prev };
      for (const k of Object.keys(n)) {
        if (n[k].status === "running") n[k] = { ...n[k], status: "idle" };
      }
      return n;
    });
  };

  const handleLiveRun = async () => {
    if (selectedLive.size === 0) return setLiveRunError("En az bir canlı cihaz seçin.");
    setLiveRunError(null);
    setLiveRunning(true);
    setLiveRunStates((prev) => {
      const n = { ...prev };
      for (const s of selectedLive) n[s] = "running";
      return n;
    });
    try {
      const result = await engineFetch<{ run_id: string }>("/api/mobile/run-live", {
        method: "POST",
        json: {
          serials: Array.from(selectedLive),
          project_id: projectId,
          tags,
          uploaded_app_id: uploadedApp?.upload_id ?? null,
        },
      });

      const run_id = result.run_id;
      currentRunIdRef.current = run_id;
      const eventSource = new EventSource(`${ENGINE_BASE}/api/mobile/run/${run_id}/stream`);

      eventSource.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as {
            type: string;
            device_name?: string;
            status?: string;
            stopped?: boolean;
          };
          if (msg.type === "done" && msg.device_name) {
            setLiveRunStates((prev) => {
              const n = { ...prev };
              // Map device_name to serial where possible
              const serial = (
                Object.keys(prev).find(
                  (s) => s === msg.device_name || liveDevices.find((d) => d.serial === s)?.name === msg.device_name
                ) ?? msg.device_name
              ) as string;
              if (n[serial] !== undefined) {
                n[serial] = msg.status === "error" ? "error" : "done";
              }
              return n;
            });
          } else if (msg.type === "all_done") {
            currentRunIdRef.current = null;
            setLiveRunning(false);
            eventSource.close();
          }
        } catch { /* JSON parse hatası */ }
      };

      eventSource.onerror = () => {
        currentRunIdRef.current = null;
        setLiveRunning(false);
        eventSource.close();
      };
    } catch (e: unknown) {
      setLiveRunError(e instanceof Error ? e.message : String(e));
      setLiveRunStates((prev) => {
        const n = { ...prev };
        for (const s of selectedLive) n[s] = "error";
        return n;
      });
      currentRunIdRef.current = null;
      setLiveRunning(false);
    }
  };

  const toggleLive = (serial: string) => {
    setSelectedLive((prev) => {
      const n = new Set(prev);
      n.has(serial) ? n.delete(serial) : n.add(serial);
      return n;
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100" data-testid="mobile-page">
      <div className="mx-auto max-w-5xl p-6 space-y-6">
        {/* Header */}
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="text-2xl">📱</span>
            <h1 className="text-xl font-bold text-slate-100">Neurex Farm</h1>
            <span className="rounded-full bg-indigo-900/60 px-2 py-0.5 text-[11px] text-indigo-300 font-medium">
              Mobil Test Orkestrasyonu
            </span>
          </div>
          <p className="text-slate-500 text-sm">
            Sanal emülasyon (Playwright) ve canlı cihaz bağlantısı (Appium/ADB) ile tam spektrum mobil test yüzeyi.
          </p>

          {/* Sekme seçici */}
          <div className="mt-4 flex gap-1 rounded-xl border border-slate-700 bg-slate-900/60 p-1 w-fit">
            <button
              type="button"
              onClick={() => setTab("virtual")}
              className={cn(
                "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors",
                tab === "virtual"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              )}
            >
              🖥 Sanal Cihazlar
              <span className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-bold",
                tab === "virtual" ? "bg-indigo-500/40 text-indigo-100" : "bg-slate-700 text-slate-400"
              )}>
                {devices.length > 0 ? devices.length : "—"}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setTab("live")}
              className={cn(
                "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors",
                tab === "live"
                  ? "bg-purple-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              )}
            >
              📱 Canlı Cihazlar
              {liveDevices.length > 0 && (
                <span className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-bold",
                  tab === "live" ? "bg-purple-500/40 text-purple-100" : "bg-slate-700 text-slate-400"
                )}>
                  {liveDevices.filter(d => d.online).length}/{liveDevices.length}
                </span>
              )}
              {tab !== "live" && (
                <span className="rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-400">Appium</span>
              )}
            </button>
          </div>
        </div>
        <div className="mb-6 space-y-4">
          <FlowGuideCard projectId={projectId} stage="execute" />
          <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 via-slate-900 to-slate-950 p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-200/80">Mobil Kosu Yuzeyi</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Bu alan, Çalıştır asamasinin mobil kolu. Cihaz secimi, canli izleme ve karsilastirmayi burada yapip sonuçlari raporlar ve AI analizine tasiyabilirsiniz.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  href={`/p/${projectId}/executions`}
                  className="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-500 hover:text-white"
                >
                  Koşular
                </Link>
                <Link
                  href={`/p/${projectId}/reports`}
                  className="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-500 hover:text-white"
                >
                  Raporlar
                </Link>
                <Link
                  href={`/p/${projectId}/ai-chat`}
                  className="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-500 hover:text-white"
                >
                  AI Asistan
                </Link>
              </div>
            </div>
          </div>
          <p className="text-sm text-slate-500">Cihaz seçip test koşun.</p>
        </div>

        {/* ── CANLI CİHAZ PANELİ ─────────────────────────────────────────────── */}
        {tab === "live" && (
          <div className="space-y-5">
            {/* Durum satırı */}
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-purple-400 animate-pulse" />
                <span className="text-sm text-slate-400">
                  {liveLoading ? "Cihazlar taranıyor..." : `${liveDevices.filter(d => d.online).length} çevrimiçi · ${liveDevices.length} toplam`}
                </span>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setLiveRefreshCount(c => c + 1)}
                  disabled={liveLoading}
                  className="rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500 hover:text-white transition disabled:opacity-50"
                >
                  ↺ Yenile
                </button>
                <Link
                  href={`/p/${projectId}/device-manager`}
                  className="rounded-lg border border-purple-500/30 bg-purple-500/10 px-3 py-1.5 text-xs text-purple-200 hover:bg-purple-500/20 transition"
                >
                  Tam Yönetim →
                </Link>
              </div>
            </div>

            {/* Hata durumu */}
            {liveError && (
              <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                ⚠ {liveError}
              </div>
            )}

            {/* Yükleme */}
            {liveLoading && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="rounded-xl border border-slate-700 bg-slate-800/30 p-4 h-36 animate-pulse" />
                ))}
              </div>
            )}

            {/* Boş durum */}
            {!liveLoading && !liveError && liveDevices.length === 0 && (
              <WifiAdbPanel />
            )}

            {/* Cihaz ızgarası */}
            {!liveLoading && liveDevices.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* SOL: Cihaz listesi + koşum kontrolü */}
                <div className="space-y-4">
                  {/* Platform filtresi */}
                  <div className="flex gap-1.5">
                    {(
                      [
                        { label: "Tümü", value: "tümü" },
                        { label: "Android", value: "android" },
                        { label: "iOS", value: "ios" },
                        { label: "Fiziksel", value: "fiziksel" },
                      ] as const
                    ).map(({ label, value }) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setLiveFilter(value)}
                        className={cn(
                          "rounded-full border px-3 py-1 text-xs transition-colors",
                          liveFilter === value
                            ? "border-purple-500 bg-purple-600 text-white"
                            : "border-slate-700 bg-slate-800/60 text-slate-400 hover:border-slate-500 hover:text-slate-200"
                        )}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {/* Cihaz kartları */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {liveDevices
                      .filter(d => {
                        if (liveFilter === "android") return d.platform === "android";
                        if (liveFilter === "ios") return d.platform === "ios";
                        if (liveFilter === "fiziksel") return d.device_type === "physical";
                        return true;
                      })
                      .map(d => (
                      <LiveDeviceCard
                        key={d.serial}
                        device={d}
                        selected={selectedLive.has(d.serial)}
                        liveStatus={liveRunStates[d.serial] ?? "idle"}
                        onSelect={() => toggleLive(d.serial)}
                      />
                    ))}
                  </div>

                  {/* Koşum kontrolleri */}
                  <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 space-y-3">
                    <h2 className="text-sm font-semibold text-slate-300">Canlı Cihaz Koşumu</h2>

                    <div>
                      <label className="block text-[11px] text-slate-500 mb-1">Uygulama (APK/IPA) — Opsiyonel</label>
                      <AppUploadZone onUploaded={(app) => setUploadedApp(app ?? null)} />
                    </div>

                    <div>
                      <label className="block text-[11px] text-slate-500 mb-1">Test etiketleri</label>
                      <input
                        type="text"
                        value={tags}
                        onChange={e => setTags(e.target.value)}
                        disabled={liveRunning}
                        placeholder="smoke, mobile, regression..."
                        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-purple-500 disabled:opacity-50"
                      />
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={liveRunning ? undefined : handleLiveRun}
                        disabled={!liveRunning && selectedLiveCount === 0}
                        className={cn(
                          "flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors",
                          liveRunning
                            ? "bg-red-700 hover:bg-red-600 text-white"
                            : selectedLiveCount > 0
                              ? "bg-purple-600 hover:bg-purple-500 text-white"
                              : "bg-slate-700 text-slate-500 cursor-not-allowed"
                        )}
                      >
                        {liveRunning ? (
                          <><span className="animate-spin">⏹</span> Durdur</>
                        ) : (
                          <>▶ {selectedLiveCount > 1 ? `${selectedLiveCount} Cihazda Koştur` : "Koştur"}</>
                        )}
                      </button>
                      {selectedLiveCount > 0 && !liveRunning && (
                        <span className="text-slate-500 text-sm">{selectedLiveCount} cihaz seçili</span>
                      )}
                    </div>

                    {liveRunError && <p className="text-red-400 text-sm">⚠ {liveRunError}</p>}
                  </div>
                </div>

                {/* SAĞ: Canlı izleme + bilgi */}
                <div className="space-y-4">
                  <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-5 space-y-3">
                    <h2 className="text-sm font-semibold text-slate-300">Appium Bağlantı Altyapısı</h2>
                    <div className="space-y-2 text-xs">
                      {[
                        { label: "Driver", value: "Appium 2.x (UiAutomator2 / XCUITest)", status: "planned" },
                        { label: "ADB Köprüsü", value: "/api/device-manager/devices", status: "ready" },
                        { label: "Koşum Uç Noktası", value: "/api/mobile/run-live", status: "ready" },
                        { label: "iOS Desteği", value: "Xcode + WebDriverAgent gerektirir", status: "partial" },
                        { label: "Wi-Fi ADB", value: "adb connect <ip>:5555", status: "partial" },
                      ].map(({ label, value, status }) => (
                        <div key={label} className="flex items-start justify-between gap-2 py-1.5 border-b border-slate-800/60 last:border-0">
                          <span className="text-slate-500 shrink-0">{label}</span>
                          <div className="text-right">
                            <span className="text-slate-300 font-mono text-[11px]">{value}</span>
                            <span className={cn(
                              "block mt-0.5 text-[10px] font-semibold",
                              status === "ready" ? "text-emerald-400" : status === "partial" ? "text-blue-400" : "text-amber-400"
                            )}>
                              {status === "ready" ? "● Hazır" : status === "partial" ? "◑ Kısmi" : "◌ Planlandı"}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-4 space-y-2">
                    <h3 className="text-sm font-semibold text-purple-200">Geliştirme Yol Haritası</h3>
                    <ol className="text-xs text-slate-400 space-y-1.5 list-decimal list-inside">
                      <li>ADB/Instruments cihaz keşfi (engine `/api/device-manager/devices`)</li>
                      <li>Appium session başlatma ve test çalıştırma (`/api/mobile/run-live`)</li>
                      <li>Canlı ekran yansıtma (scrcpy / WebSocket stream)</li>
                      <li>Wi-Fi ADB ve kablosuz iOS bağlantısı</li>
                      <li>Paralel koşum + gerçek zamanlı log akışı</li>
                    </ol>
                  </div>

                  <MobileAiScenarioCard
                    device={null}
                    app={uploadedApp ? { filename: uploadedApp.filename, upload_id: uploadedApp.upload_id } : null}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── SANAL CİHAZ PANELİ ─────────────────────────────────────────────── */}
        {tab === "virtual" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* SOL: Cihaz seçimi + kontrol */}
          <div className="space-y-5">

            {/* Çalıştırma kontrolleri */}
            <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 space-y-4">
              <h2 className="text-sm font-semibold text-slate-300">Koşum Ayarları</h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label
                    htmlFor="visium-farm-browser"
                    className="block text-[11px] text-slate-500 mb-1"
                  >
                    Tarayıcı
                  </label>
                  <select
                    id="visium-farm-browser"
                    value={browser}
                    onChange={e => setBrowser(e.target.value)}
                    disabled={running}
                    aria-label="Koşumda kullanılacak tarayıcı motoru"
                    title="Koşumda kullanılacak tarayıcı motoru"
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                  >
                    <option value="chromium">Chromium</option>
                    <option value="firefox">Firefox</option>
                    <option value="webkit">WebKit</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] text-slate-500 mb-1">Base URL (opsiyonel)</label>
                  <input
                    type="url"
                    value={baseUrl}
                    onChange={e => setBaseUrl(e.target.value)}
                    disabled={running}
                    placeholder="https://örnek.com"
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-slate-500 mb-1">Test etiketleri</label>
                  <input
                    type="text"
                    value={tags}
                    onChange={e => setTags(e.target.value)}
                    disabled={running}
                    placeholder="smoke, regression..."
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                  />
                </div>
              </div>

              {/* APK/IPA Upload */}
              <div>
                <label className="block text-[11px] text-slate-500 mb-2">Uygulama (APK/IPA) — Opsiyonel</label>
                <AppUploadZone
                  onUploaded={(app) => {
                    setUploadedApp(app ?? null);
                  }}
                />
              </div>

              {/* Aksiyon butonları */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={running ? handleStop : handleRun}
                  disabled={!running && selectedCount === 0}
                  data-testid="run-btn"
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors",
                    running
                      ? "bg-red-700 hover:bg-red-600 text-white"
                      : selectedCount > 0
                        ? "bg-indigo-600 hover:bg-indigo-500 text-white"
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
                      ▶ {selectedCount > 1 ? `${selectedCount} Cihazda Paralel Koştur` : "Koştur"}
                    </>
                  )}
                </button>
                {selectedCount > 0 && !running && (
                  <span className="text-slate-500 text-sm">{selectedCount} cihaz seçili</span>
                )}
              </div>

              {error && <p className="text-red-400 text-sm">⚠ {error}</p>}
            </div>

            {/* Cihaz listesi */}
            {loading ? (
              <div className="text-center py-8 text-slate-500 text-sm">Cihazlar yükleniyor...</div>
            ) : devices.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm">
                <p className="text-2xl mb-2">📱</p>
                <p>Cihaz bulunamadı.</p>
                <p className="text-xs mt-1">Engine bağlantısını kontrol edin.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {devices.map(d => (
                  <DeviceCard
                    key={d.slug}
                    device={d}
                    selected={selected.has(d.name)}
                    state={deviceRunStates[d.name] ?? { status: "idle", passed: 0, failed: 0, screenshot_b64: null, logs: [] }}
                    onToggle={() => {
                      toggle(d.name);
                      setActiveDevice(d.name);
                    }}
                  />
                ))}
              </div>
            )}

            {/* Sonuç karşılaştırma tablosu */}
            <ResultsComparisonTable devices={devices} states={deviceRunStates} />
          </div>

          {/* SAĞ: AI Senaryo Üretici + Canlı izleme paneli */}
          <div className="space-y-4">
            <MobileAiScenarioCard
              device={
                activeDeviceObj
                  ? {
                      name: activeDeviceObj.name,
                      platform: activeDeviceObj.platform,
                      os: activeDeviceObj.os,
                      slug: activeDeviceObj.slug,
                    }
                  : null
              }
              app={
                uploadedApp
                  ? {
                      filename: uploadedApp.filename,
                      upload_id: uploadedApp.upload_id,
                    }
                  : null
              }
            />

            <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4">
              <h2 className="text-sm font-semibold text-slate-300 mb-3">Canlı İzleme</h2>

              {/* Cihaz seçici tab'ları */}
              {selected.size > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {Array.from(selected).map(dn => {
                    const st = deviceRunStates[dn];
                    return (
                      <button
                        key={dn}
                        type="button"
                        onClick={() => setActiveDevice(dn)}
                        className={cn(
                          "rounded-lg px-2.5 py-1 text-[12px] font-medium transition-colors",
                          activeDevice === dn
                            ? "bg-indigo-600 text-white"
                            : "bg-slate-700 text-slate-400 hover:bg-slate-600"
                        )}
                      >
                        {dn.split(" ")[0]}
                        {st?.status === "running" && <span className="ml-1 animate-pulse">●</span>}
                        {st?.status === "done" && <span className="ml-1 text-emerald-400">✓</span>}
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Canlı screenshot */}
              <LiveScreenshot
                b64={activeSt?.screenshot_b64 ?? null}
                deviceName={activeDevice ?? "Cihaz seçilmedi"}
              />
            </div>

            {/* Log terminali */}
            {activeDevice && (
              <MiniLogTerminal
                logs={activeSt?.logs ?? []}
                deviceName={activeDevice}
              />
            )}

            {/* Cihaz detay bilgisi */}
            {activeDeviceObj && (
              <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 text-xs text-slate-500 space-y-1.5">
                <h3 className="text-sm font-medium text-slate-300 mb-2">{activeDeviceObj.name}</h3>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  <span className="text-slate-600">Platform</span>
                  <span className="text-slate-300">{activeDeviceObj.platform.toUpperCase()}</span>
                  <span className="text-slate-600">OS</span>
                  <span className="text-slate-300">{activeDeviceObj.os}</span>
                  <span className="text-slate-600">Viewport</span>
                  <span className="text-slate-300">{activeDeviceObj.viewport_width}×{activeDeviceObj.viewport_height}</span>
                  <span className="text-slate-600">DPR</span>
                  <span className="text-slate-300">×{activeDeviceObj.device_scale_factor}</span>
                  <span className="text-slate-600">Dokunmatik</span>
                  <span className="text-slate-300">{activeDeviceObj.has_touch ? "Evet" : "Hayır"}</span>
                  {activeDeviceObj.playwright_key && (
                    <>
                      <span className="text-slate-600">PW Key</span>
                      <span className="text-slate-400 font-mono truncate">{activeDeviceObj.playwright_key}</span>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
        )}
      </div>

      <PageFeedbackWidget />
    </div>
  );
}
