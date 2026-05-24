"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface FarmDevice {
  id: string;
  name: string;
  platform: "android" | "ios";
  os_version: string;
  provider: string;
  available: boolean;
  extra: Record<string, unknown>;
}

interface FarmSession {
  session_id: string;
  device_id: string;
  provider: string;
  status: "queued" | "running" | "passed" | "failed" | "error";
  appium_endpoint?: string | null;
  video_url?: string | null;
  report_url?: string | null;
  extra: Record<string, unknown>;
}

interface FarmHealth {
  provider: string;
  configured?: boolean;
  total_devices?: number;
  idle_devices?: number;
  region?: string;
  project_arn?: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

const FARM_BASE = "/api/v1/mobile/farm";

function useFarmDevices(platform?: string) {
  return useQuery({
    queryKey: ["farm-devices", platform],
    queryFn: () => {
      const qs = platform ? `?platform=${platform}` : "";
      return apiFetch<FarmDevice[]>(`${FARM_BASE}/devices${qs}`);
    },
    staleTime: 30_000,
  });
}

function useFarmHealth() {
  return useQuery({
    queryKey: ["farm-health"],
    queryFn: () => apiFetch<FarmHealth>(`${FARM_BASE}/health`),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}

function useStartFarmSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      device_id,
      app_path,
      capabilities,
    }: {
      device_id: string;
      app_path: string;
      capabilities?: Record<string, unknown>;
    }) =>
      apiFetch<FarmSession>(
        `${FARM_BASE}/sessions?device_id=${encodeURIComponent(device_id)}&app_path=${encodeURIComponent(app_path)}`,
        { method: "POST", json: capabilities ?? {} },
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["farm-sessions"] }),
  });
}

function useStopFarmSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiFetch<{ status: string }>(`${FARM_BASE}/sessions/${sessionId}`, { method: "DELETE" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["farm-sessions"] }),
  });
}

// ── Status chips ──────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  queued:  "bg-blue-500/15 text-blue-400",
  running: "bg-violet-500/15 text-violet-400",
  passed:  "bg-emerald-500/15 text-emerald-400",
  failed:  "bg-rose-500/15 text-rose-400",
  error:   "bg-amber-500/15 text-amber-400",
};

function StatusChip({ status }: { status: string }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status] ?? "bg-slate-700 text-slate-400"}`}>
      {status}
    </span>
  );
}

// ── Provider badge ────────────────────────────────────────────────────────────

const PROVIDER_COLORS: Record<string, string> = {
  local:        "bg-slate-700 text-slate-300",
  aws:          "bg-orange-500/15 text-orange-400",
  browserstack: "bg-blue-500/15 text-blue-400",
  saucelabs:    "bg-red-500/15 text-red-400",
};

function ProviderBadge({ provider }: { provider: string }) {
  const labels: Record<string, string> = {
    local: "Local", aws: "AWS", browserstack: "BrowserStack", saucelabs: "Sauce Labs",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${PROVIDER_COLORS[provider] ?? "bg-slate-800 text-slate-400"}`}>
      {labels[provider] ?? provider}
    </span>
  );
}

// ── Start session form ────────────────────────────────────────────────────────

function StartSessionForm({ device, onClose }: { device: FarmDevice; onClose: () => void }) {
  const [appPath, setAppPath] = useState("");
  const startMutation = useStartFarmSession();

  const handleStart = () => {
    if (!appPath.trim()) return;
    startMutation.mutate(
      { device_id: device.id, app_path: appPath.trim(), capabilities: { name: `Cortex Run — ${device.name}` } },
      { onSuccess: onClose },
    );
  };

  return (
    <div className="space-y-3 rounded-xl border border-slate-700 bg-slate-900 p-4 mt-3">
      <p className="text-sm font-semibold text-white">Session Başlat — {device.name}</p>
      <div>
        <label className="block text-xs text-slate-400 mb-1">App yolu / URL / Storage ID</label>
        <input
          type="text"
          value={appPath}
          onChange={(e) => setAppPath(e.target.value)}
          placeholder="bs://abc123 veya storage:filename=app.apk"
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-violet-500/50 focus:outline-none"
          autoFocus
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleStart}
          disabled={startMutation.isPending || !appPath.trim()}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40"
        >
          {startMutation.isPending ? "Başlatılıyor…" : "Başlat"}
        </button>
        <button onClick={onClose} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800">
          İptal
        </button>
      </div>
      {startMutation.isSuccess && startMutation.data?.appium_endpoint && (
        <p className="text-xs text-emerald-400">
          Appium Endpoint: <code className="font-mono">{startMutation.data.appium_endpoint}</code>
        </p>
      )}
    </div>
  );
}

// ── Device row ────────────────────────────────────────────────────────────────

function DeviceRow({ device }: { device: FarmDevice }) {
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl" aria-hidden="true">
            {device.platform === "ios" ? "🍎" : "🤖"}
          </span>
          <div>
            <p className="font-semibold text-white">{device.name}</p>
            <p className="text-xs text-slate-400">
              {device.platform === "ios" ? "iOS" : "Android"} {device.os_version}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ProviderBadge provider={device.provider} />
          <span
            className={`h-2 w-2 rounded-full ${device.available ? "bg-emerald-400" : "bg-slate-600"}`}
            title={device.available ? "Available" : "Busy"}
          />
          {device.available && (
            <button
              onClick={() => setShowForm((v) => !v)}
              className="rounded-lg bg-violet-600/20 px-3 py-1.5 text-xs font-medium text-violet-300 hover:bg-violet-600/30"
            >
              Session Başlat
            </button>
          )}
        </div>
      </div>
      {showForm && <StartSessionForm device={device} onClose={() => setShowForm(false)} />}
    </div>
  );
}

// ── Health panel ──────────────────────────────────────────────────────────────

function HealthPanel({ health }: { health: FarmHealth }) {
  const items = [
    { label: "Provider", value: health.provider },
    health.configured !== undefined ? { label: "Configured", value: health.configured ? "✓ Evet" : "✗ Hayır" } : null,
    health.total_devices !== undefined ? { label: "Total Devices", value: String(health.total_devices) } : null,
    health.idle_devices !== undefined ? { label: "Idle", value: String(health.idle_devices) } : null,
    health.region ? { label: "Region", value: health.region } : null,
  ].filter(Boolean) as { label: string; value: string }[];

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">Farm Durumu</p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {items.map((item) => (
          <div key={item.label} className="rounded-lg bg-slate-950 px-3 py-2">
            <p className="text-[10px] text-slate-500 uppercase tracking-wide">{item.label}</p>
            <p className="mt-0.5 text-sm font-semibold text-white">{item.value}</p>
          </div>
        ))}
      </div>
      {health.provider !== "local" && health.configured === false && (
        <div className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
          <p className="text-xs text-amber-400">
            Sağlayıcı yapılandırılmamış. Gerekli ortam değişkenlerini ayarlayın.
          </p>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DeviceFarmPage() {
  const [platformFilter, setPlatformFilter] = useState<"all" | "android" | "ios">("all");
  const devicesQuery = useFarmDevices(platformFilter !== "all" ? platformFilter : undefined);
  const healthQuery = useFarmHealth();

  const devices = devicesQuery.data ?? [];

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100">
      {/* Header */}
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-violet-300">
          Mobil Otomasyon
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-white">Device Farm</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
          Bulut tabanlı cihaz farm sağlayıcılarını yönetin. AWS Device Farm, BrowserStack App
          Automate veya Sauce Labs ile entegre çalışır. Varsayılan: yerel AVD/Simulator farm.
        </p>
      </div>

      {/* Health */}
      {healthQuery.data && (
        <div className="mb-6">
          <HealthPanel health={healthQuery.data} />
        </div>
      )}

      {/* Filter */}
      <div className="mb-4 flex items-center gap-2">
        {(["all", "android", "ios"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setPlatformFilter(f)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              platformFilter === f
                ? "bg-violet-600 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700"
            }`}
          >
            {f === "all" ? "Tümü" : f === "android" ? "🤖 Android" : "🍎 iOS"}
          </button>
        ))}
        <span className="ml-auto text-xs text-slate-500">
          {devicesQuery.isLoading ? "Yükleniyor…" : `${devices.length} cihaz`}
        </span>
      </div>

      {/* Device grid */}
      {devicesQuery.isLoading ? (
        <div className="flex h-24 items-center justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-violet-400" />
        </div>
      ) : devices.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-12 text-center">
          <p className="text-sm text-slate-400">Cihaz bulunamadı.</p>
          <p className="mt-1 text-xs text-slate-500">
            DEVICE_FARM_PROVIDER ortam değişkenini kontrol edin.
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {devices.map((d) => (
            <DeviceRow key={d.id} device={d} />
          ))}
        </div>
      )}

      {/* Environment setup guide */}
      <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="mb-3 text-sm font-semibold text-white">Sağlayıcı Yapılandırması</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {[
            {
              name: "AWS Device Farm",
              value: "aws",
              vars: ["AWS_DEVICE_FARM_PROJECT_ARN", "AWS_DEFAULT_REGION"],
            },
            {
              name: "BrowserStack",
              value: "browserstack",
              vars: ["BROWSERSTACK_USERNAME", "BROWSERSTACK_ACCESS_KEY", "BROWSERSTACK_APP_URL"],
            },
            {
              name: "Sauce Labs",
              value: "saucelabs",
              vars: ["SAUCE_USERNAME", "SAUCE_ACCESS_KEY", "SAUCE_REGION", "SAUCE_APP_ID"],
            },
          ].map((p) => (
            <div key={p.value} className="rounded-lg bg-slate-950 p-3">
              <p className="text-xs font-semibold text-slate-300 mb-2">{p.name}</p>
              <code className="block text-[10px] text-slate-500 mb-2 font-mono">
                DEVICE_FARM_PROVIDER={p.value}
              </code>
              <div className="space-y-1">
                {p.vars.map((v) => (
                  <code key={v} className="block text-[10px] text-violet-400 font-mono">
                    {v}=...
                  </code>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
