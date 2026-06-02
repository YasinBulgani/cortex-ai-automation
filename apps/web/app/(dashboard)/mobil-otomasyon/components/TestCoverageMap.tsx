"use client";

type Session = {
  id: string;
  deviceId: string;
  scenarioName: string;
  status: "queued" | "running" | "passed" | "failed";
  startedAt: number;
  finishedAt?: number;
  healed: number;
};

type Device = {
  id: string;
  name: string;
  platform: "android" | "ios";
  osVersion: string;
  profile: string;
  kind: "emulator" | "simulator" | "physical";
  status: "idle" | "running" | "booting" | "offline" | "error";
  battery: number;
  cpuPct: number;
  ramPct: number;
  appiumPort: number;
  currentStep?: string;
  stepsDone: number;
  stepsTotal: number;
  healStreak: number;
};

interface Stats {
  total: number;
  online: number;
  running: number;
  passed: number;
  failed: number;
  heals: number;
}

interface TestCoverageMapProps {
  stats: Stats;
  sessions: Session[];
  devices: Device[];
}

function fmtDuration(ms: number) {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

export function TestCoverageMap({ stats, sessions, devices }: TestCoverageMapProps) {
  const recentSessions = sessions.slice(0, 40);
  const total = stats.passed + stats.failed;
  const successRate = total > 0 ? Math.round((stats.passed / total) * 100) : null;

  // Group session results by device platform
  const androidSessions = recentSessions.filter((s) => {
    const d = devices.find((x) => x.id === s.deviceId);
    return d?.platform === "android";
  });
  const iosSessions = recentSessions.filter((s) => {
    const d = devices.find((x) => x.id === s.deviceId);
    return d?.platform === "ios";
  });

  const platformStats = (list: Session[]) => {
    const passed = list.filter((s) => s.status === "passed").length;
    const failed = list.filter((s) => s.status === "failed").length;
    const total = passed + failed;
    return { passed, failed, total, rate: total > 0 ? Math.round((passed / total) * 100) : null };
  };

  const android = platformStats(androidSessions);
  const ios = platformStats(iosSessions);

  return (
    <div className="rounded-lg border border-slate-800 overflow-hidden">
      <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3">
        <h2 className="text-sm font-semibold">📊 Test Kapsama Özeti</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Son {recentSessions.length} session sonuçları
        </p>
      </div>

      <div className="p-4 space-y-4">
        {/* Overall stats */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            { label: "Toplam Cihaz", value: stats.total, color: "text-slate-200" },
            { label: "Online", value: stats.online, color: "text-emerald-300" },
            { label: "Çalışan", value: stats.running, color: "text-blue-300" },
            { label: "Son Pass", value: stats.passed, color: "text-emerald-400" },
            { label: "Son Fail", value: stats.failed, color: "text-red-400" },
            { label: "Self-Heal", value: stats.heals, color: "text-amber-300" },
          ].map((s) => (
            <div
              key={s.label}
              className="rounded-lg border border-slate-800 bg-slate-900/30 px-3 py-2.5"
            >
              <p className="text-[10px] uppercase tracking-wide text-slate-500">
                {s.label}
              </p>
              <p className={`mt-0.5 text-xl font-semibold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>

        {/* Platform breakdown */}
        {(android.total > 0 || ios.total > 0) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Android */}
            <div className="rounded-lg border border-slate-800 bg-slate-900/20 p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm">🤖</span>
                <span className="text-xs font-semibold text-slate-300">Android</span>
                {android.rate !== null && (
                  <span
                    className={`ml-auto text-xs font-bold ${
                      android.rate >= 80
                        ? "text-emerald-400"
                        : android.rate >= 50
                          ? "text-yellow-400"
                          : "text-red-400"
                    }`}
                  >
                    %{android.rate}
                  </span>
                )}
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden mb-2">
                {android.total > 0 && (
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all"
                    style={{ width: `${android.rate ?? 0}%` }}
                  />
                )}
              </div>
              <div className="flex gap-3 text-xs text-slate-500">
                <span className="text-emerald-400">✓ {android.passed} pass</span>
                <span className="text-red-400">✗ {android.failed} fail</span>
              </div>
            </div>

            {/* iOS */}
            <div className="rounded-lg border border-slate-800 bg-slate-900/20 p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm">🍎</span>
                <span className="text-xs font-semibold text-slate-300">iOS</span>
                {ios.rate !== null && (
                  <span
                    className={`ml-auto text-xs font-bold ${
                      ios.rate >= 80
                        ? "text-emerald-400"
                        : ios.rate >= 50
                          ? "text-yellow-400"
                          : "text-red-400"
                    }`}
                  >
                    %{ios.rate}
                  </span>
                )}
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden mb-2">
                {ios.total > 0 && (
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all"
                    style={{ width: `${ios.rate ?? 0}%` }}
                  />
                )}
              </div>
              <div className="flex gap-3 text-xs text-slate-500">
                <span className="text-emerald-400">✓ {ios.passed} pass</span>
                <span className="text-red-400">✗ {ios.failed} fail</span>
              </div>
            </div>
          </div>
        )}

        {/* Overall success bar */}
        {successRate !== null && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] text-slate-500">Genel Başarı Oranı</span>
              <span
                className={`text-sm font-bold ${
                  successRate >= 80
                    ? "text-emerald-400"
                    : successRate >= 50
                      ? "text-yellow-400"
                      : "text-red-400"
                }`}
              >
                %{successRate}
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${
                  successRate >= 80
                    ? "bg-emerald-500"
                    : successRate >= 50
                      ? "bg-yellow-500"
                      : "bg-red-500"
                }`}
                style={{ width: `${successRate}%` }}
              />
            </div>
          </div>
        )}

        {/* Recent session list */}
        {recentSessions.length > 0 && (
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">
              Son Sessionlar
            </p>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {recentSessions.slice(0, 10).map((s) => {
                const device = devices.find((d) => d.id === s.deviceId);
                const elapsed =
                  s.finishedAt ? fmtDuration(s.finishedAt - s.startedAt) : "…";
                return (
                  <div
                    key={s.id}
                    className="flex items-center gap-2 rounded-lg border border-slate-800/60 bg-slate-900/20 px-3 py-1.5 text-xs"
                  >
                    <span
                      className={`shrink-0 font-bold text-[10px] ${
                        s.status === "passed"
                          ? "text-emerald-400"
                          : s.status === "failed"
                            ? "text-red-400"
                            : s.status === "running"
                              ? "text-blue-400 animate-pulse"
                              : "text-slate-500"
                      }`}
                    >
                      {s.status === "passed"
                        ? "✅"
                        : s.status === "failed"
                          ? "❌"
                          : s.status === "running"
                            ? "▶"
                            : "⏳"}
                    </span>
                    <span className="flex-1 truncate text-slate-300">
                      {s.scenarioName}
                    </span>
                    {device && (
                      <span className="text-slate-500 shrink-0">
                        {device.platform === "ios" ? "🍎" : "🤖"} {device.name.split(" ")[0]}
                      </span>
                    )}
                    <span className="text-slate-600 shrink-0 font-mono">{elapsed}</span>
                    {s.healed > 0 && (
                      <span className="text-amber-400 shrink-0 text-[10px]">
                        🔧{s.healed}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {recentSessions.length === 0 && (
          <div className="text-center py-6 text-slate-600">
            <p className="text-2xl mb-2">📊</p>
            <p className="text-sm">Henüz session çalışmadı</p>
            <p className="text-xs mt-1">Senaryo üretip çalıştırın</p>
          </div>
        )}
      </div>
    </div>
  );
}
