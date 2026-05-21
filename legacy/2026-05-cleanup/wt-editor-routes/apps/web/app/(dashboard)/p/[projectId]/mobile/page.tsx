"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { FlowGuideCard } from "@/components/FlowGuideCard";
import { MobileAiScenarioCard } from "@/components/dsl/MobileAiScenarioCard";
import { apiFetch, engineFetch, getToken, ENGINE_BASE } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface DeviceProfile {
  name: string;
  slug: string;
  platform: "ios" | "android";
  os: string;
  viewport_width: number;
  viewport_height: number;
  icon: string;
}

type RunStatus = "idle" | "running" | "done" | "error";

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
      // engineFetch (doğrudan engine'e) — FormData ile raw fetch kullanıyoruz
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

/** Karşılaştırma tablosu — tüm cihazlar bitince */
function ResultsComparisonTable({
  devices,
  states,
}: {
  devices: DeviceProfile[];
  states: Record<string, DeviceRunState>;
}) {
  const selected = devices.filter(d => states[d.name]?.status === "done");
  if (selected.length === 0) return null;

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
            {selected.map(d => {
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

// ─── Ana Sayfa ─────────────────────────────────────────────────────────────────

export default function VisiumFarmPage() {
  const projectId = useRouteParam("projectId");

  const [devices, setDevices] = useState<DeviceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [statuses, setStatuses] = useState<Record<string, RunStatus>>({});
  const [running, setRunning] = useState(false);
  const [browser, setBrowser] = useState("chromium");
  const [baseUrl, setBaseUrl] = useState("");
  const [tags, setTags] = useState("");
  const [appUploadId, setAppUploadId] = useState<string | null>(null);
  const [uploadedApp, setUploadedApp] = useState<UploadedApp | null>(null);
  const [activeDevice, setActiveDevice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const list = await engineFetch<DeviceProfile[]>("/api/mobile/devices");
        if (Array.isArray(list)) {
          setDevices(list);
          const init: Record<string, RunStatus> = {};
          for (const d of list) init[d.name] = "idle";
          setStatuses(init);
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
    setStatuses((prev) => {
      const n = { ...prev };
      for (const d of selected) n[d] = "running";
      return n;
    });

    try {
      await engineFetch("/api/mobile/run", {
        method: "POST",
        json: { device_names: Array.from(selected), project_id: projectId },
      });
      setStatuses((prev) => {
        const n = { ...prev };
        for (const d of selected) n[d] = "done";
        return n;
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setStatuses((prev) => {
        const n = { ...prev };
        for (const d of selected) n[d] = "error";
        return n;
      });
    } finally {
      setRunning(false);
    }
  };

  const handleStop = () => {
    setRunning(false);
    setStatuses((prev) => {
      const n = { ...prev };
      for (const k of Object.keys(n)) if (n[k] === "running") n[k] = "idle";
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
            <h1 className="text-xl font-bold">Mobil Test</h1>
          </div>
          <p className="text-sm text-slate-500">Cihaz seçip test koşun.</p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={running ? handleStop : handleRun}
            disabled={!running && selected.size === 0}
            data-testid="run-btn"
            className={cn(
              "rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors",
              running
                ? "bg-red-700 hover:bg-red-600 text-white"
                : selected.size > 0
                  ? "bg-indigo-600 hover:bg-indigo-500 text-white"
                  : "bg-slate-700 text-slate-500 cursor-not-allowed",
            )}
          >
            {running ? "Durdur" : `Koştur (${selected.size})`}
          </button>
          {error && <span className="text-red-400 text-sm">⚠ {error}</span>}
        </div>

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
                    setAppUploadId(app?.upload_id ?? null);
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
                  <span className="text-slate-500 text-sm">
                    {selectedCount} cihaz seçili
                  </span>
                </button>
              );
            })}
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
              {selectedDevices.size > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {Array.from(selectedDevices).map(dn => {
                    const st = deviceStates[dn];
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
      </div>
    </div>
  );
}
