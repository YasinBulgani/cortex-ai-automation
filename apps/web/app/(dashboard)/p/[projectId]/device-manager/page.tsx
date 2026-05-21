"use client";

import { useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { engineFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/nexus/PageHeader";
import { EmptyState } from "@/components/nexus/EmptyState";

interface ManagedDevice {
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

interface DeviceSummary {
  total: number;
  online: number;
  android: number;
  ios: number;
  physical: number;
}

const TYPE_LABEL: Record<string, { label: string; cls: string }> = {
  emulator: { label: "Emülatör", cls: "bg-green-500/15 text-green-300 border-green-500/25" },
  simulator: { label: "Simülatör", cls: "bg-blue-500/15 text-blue-300 border-blue-500/25" },
  physical: { label: "Fiziksel", cls: "bg-purple-500/15 text-purple-300 border-purple-500/25" },
};

function healthColor(s: number) {
  return s >= 80 ? "text-emerald-400" : s >= 50 ? "text-yellow-400" : "text-red-400";
}

function DeviceCard({ device, selected, onSelect }: { device: ManagedDevice; selected: boolean; onSelect: () => void }) {
  const ts = TYPE_LABEL[device.device_type] ?? TYPE_LABEL.physical;
  return (
    <div
      onClick={onSelect}
      data-testid={`device-card-${device.serial}`}
      className={cn(
        "rounded-xl border p-4 cursor-pointer transition-all",
        selected
          ? "border-indigo-500 bg-indigo-950/30 ring-1 ring-indigo-500/30"
          : device.online
            ? "border-slate-700 bg-slate-800/40 hover:border-slate-500"
            : "border-slate-800 bg-slate-900/30 opacity-60",
      )}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className="relative shrink-0">
          <span className="text-2xl">{device.platform === "ios" ? "🍎" : "🤖"}</span>
          <span className={cn("absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-slate-800", device.online ? "bg-emerald-500" : "bg-slate-600")} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-white truncate">{device.name}</p>
          <p className="text-xs text-slate-500">{device.brand}</p>
        </div>
        <span className={cn("text-lg font-bold", healthColor(device.health_score))}>{device.health_score}</span>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-slate-500">Platform</span>
          <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-semibold", device.platform === "ios" ? "bg-slate-700 text-slate-300" : "bg-green-900/40 text-green-400")}>
            {device.platform === "ios" ? "iOS" : "Android"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Sürüm</span>
          <span className="text-slate-300">{device.android_version || device.ios_version || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Tip</span>
          <span className={cn("px-1.5 py-0.5 rounded border text-[10px] font-semibold", ts.cls)}>{ts.label}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Ekran</span>
          <span className="text-slate-300">{device.screen_size || "—"}</span>
        </div>
      </div>

      {device.online && device.battery.level != null && (
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
          <span>🔋 %{device.battery.level}</span>
          <span>·</span>
          <span>📱 {device.installed_apps_count} uygulama</span>
        </div>
      )}

      <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-800/50">
        <span className="text-[10px] text-slate-600 font-mono truncate max-w-[120px]">{device.serial.substring(0, 16)}</span>
        {device.uptime && <span className="text-[10px] text-slate-600">{device.uptime}</span>}
      </div>
    </div>
  );
}

export default function DeviceManagerPage() {
  const projectId = useRouteParam("projectId");

  const [devices, setDevices] = useState<ManagedDevice[]>([]);
  const [summary, setSummary] = useState<DeviceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSerial, setSelectedSerial] = useState<string | null>(null);
  const [platformFilter, setPlatformFilter] = useState<"all" | "android" | "ios">("all");

  useEffect(() => {
    setLoading(true);
    engineFetch<{ devices: ManagedDevice[]; summary: DeviceSummary }>("/api/device-manager/devices")
      .then((data) => {
        setDevices(data.devices ?? []);
        setSummary(data.summary ?? null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = devices.filter((d) => platformFilter === "all" || d.platform === platformFilter);
  const online = filtered.filter((d) => d.online);
  const offline = filtered.filter((d) => !d.online);
  const selected = devices.find((d) => d.serial === selectedSerial) ?? null;

  const stats = [
    { label: "Toplam", value: summary?.total ?? 0, icon: "📱", color: "text-slate-200" },
    { label: "Çevrimiçi", value: summary?.online ?? 0, icon: "🟢", color: "text-emerald-400" },
    { label: "Android", value: summary?.android ?? 0, icon: "🤖", color: "text-green-400" },
    { label: "iOS", value: summary?.ios ?? 0, icon: "🍎", color: "text-sky-400" },
    { label: "Fiziksel", value: summary?.physical ?? 0, icon: "📲", color: "text-purple-400" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="device-manager-page">
      <PageHeader
        icon={<span className="text-xl">📱</span>}
        title="Cihaz Yönetim Merkezi"
        description="Android + iOS cihazlarınızı merkezi olarak yönetin ve izleyin"
      />

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="rounded-xl border border-slate-700 bg-slate-800/40 p-3">
            <div className="flex items-center gap-1.5 mb-0.5">
              <span>{s.icon}</span>
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">{s.label}</span>
            </div>
            <p className={cn("text-2xl font-bold", s.color)}>{loading ? "—" : s.value}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2">
        {(["all", "android", "ios"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setPlatformFilter(f)}
            className={cn("rounded-full px-3 py-1.5 text-xs font-medium", platformFilter === f ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700")}
          >
            {f === "all" ? "Tümü" : f === "ios" ? "🍎 iOS" : "🤖 Android"}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6">
        <div className="space-y-4">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-slate-800 bg-slate-800/20 h-48 animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState icon="📱" title="Bağlı cihaz bulunamadı" description="Emülatör veya Simulator başlatın." />
          ) : (
            <>
              {online.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-slate-400 mb-2 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" /> Çevrimiçi ({online.length})
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {online.map((d) => (
                      <DeviceCard key={d.serial} device={d} selected={selectedSerial === d.serial} onSelect={() => setSelectedSerial(d.serial)} />
                    ))}
                  </div>
                </div>
              )}
              {offline.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-slate-400 mb-2 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-slate-600" /> Çevrimdışı ({offline.length})
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {offline.map((d) => (
                      <DeviceCard key={d.serial} device={d} selected={selectedSerial === d.serial} onSelect={() => setSelectedSerial(d.serial)} />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {selected && selected.online && (
          <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-4" data-testid="device-detail">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl">{selected.platform === "ios" ? "🍎" : "🤖"}</span>
              <div>
                <h2 className="text-base font-bold text-white">{selected.name}</h2>
                <p className="text-xs text-slate-500">{selected.brand} · {selected.serial.substring(0, 20)}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              {[
                ["Sürüm", selected.android_version || selected.ios_version || "—"],
                ["Ekran", selected.screen_size || "—"],
                ["Uygulamalar", `${selected.installed_apps_count}`],
                ["Batarya", selected.battery.level != null ? `%${selected.battery.level}` : "—"],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between py-1 border-b border-slate-800/40">
                  <span className="text-slate-500">{label}</span>
                  <span className="text-slate-300 font-mono text-[11px]">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
