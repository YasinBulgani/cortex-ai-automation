"use client";

import { cn } from "@/lib/utils";

type RunStatus = "idle" | "running" | "done" | "error";

interface DeviceRunState {
  status: RunStatus;
  passed: number;
  failed: number;
  screenshot_b64: string | null;
  logs: string[];
}

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

interface MobileSessionCardProps {
  /** All completed devices for the comparison table */
  devices: DeviceProfile[];
  states: Record<string, DeviceRunState>;
}

function statusLabel(status: RunStatus): string {
  const map: Record<RunStatus, string> = {
    idle: "Bekliyor",
    running: "Çalışıyor",
    done: "Tamamlandı",
    error: "Hata",
  };
  return map[status];
}

function statusCls(status: RunStatus): string {
  const map: Record<RunStatus, string> = {
    idle: "bg-slate-700 text-slate-400",
    running: "bg-blue-900/60 text-blue-300 animate-pulse",
    done: "bg-emerald-900/60 text-emerald-300",
    error: "bg-red-900/60 text-red-300",
  };
  return map[status];
}

/** Shows a results comparison table across all devices that have finished */
export function MobileSessionCard({ devices, states }: MobileSessionCardProps) {
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
              <th className="px-4 py-2 text-left text-[12px] text-slate-400 font-medium">
                Cihaz
              </th>
              <th className="px-4 py-2 text-center text-[12px] text-slate-400 font-medium">
                Durum
              </th>
              <th className="px-4 py-2 text-center text-[12px] text-slate-400 font-medium">
                Geçti
              </th>
              <th className="px-4 py-2 text-center text-[12px] text-slate-400 font-medium">
                Kaldı
              </th>
              <th className="px-4 py-2 text-center text-[12px] text-slate-400 font-medium">
                Başarı %
              </th>
              <th className="px-4 py-2 text-left text-[12px] text-slate-400 font-medium">
                Platform
              </th>
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
                  <td className="px-4 py-2 text-center">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                        statusCls(st.status)
                      )}
                    >
                      {statusLabel(st.status)}
                    </span>
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
