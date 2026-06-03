"use client";

import { useEffect, useState } from "react";
import { useManagementStandup } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

interface StandupData {
  health_score: number;
  summary_health: "healthy" | "at_risk" | "critical";
  eta_hours: number | null;
  remaining_cases: number;
  total_cases: number;
  completed_cases: number;
  pass_rate: number;
  blocked: number;
  failed: number;
  velocity_per_hour: number;
  anomalies: { severity: string; title: string }[];
  run_name: string;
  predicted_completion: string | null;
  will_meet_gate: boolean;
  blocking_factors: string[];
}

const HEALTH_CONFIG = {
  healthy:  { bg: "from-emerald-950 to-slate-950", ring: "border-emerald-500", label: "SAĞLIKLI", color: "text-emerald-400", dot: "bg-emerald-500" },
  at_risk:  { bg: "from-amber-950 to-slate-950",   ring: "border-amber-500",   label: "RİSKLİ",   color: "text-amber-400",   dot: "bg-amber-500" },
  critical: { bg: "from-red-950 to-slate-950",    ring: "border-red-500",    label: "KRİTİK",   color: "text-red-400",    dot: "bg-red-500" },
};

function HealthGaugeMobile({ score, health }: { score: number; health: "healthy" | "at_risk" | "critical" }) {
  const cfg = HEALTH_CONFIG[health];
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;
  const strokeColor = health === "healthy" ? "#10b981" : health === "at_risk" ? "#f59e0b" : "#f43f5e";

  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r="54" fill="none" stroke="#1e293b" strokeWidth="12" />
        <circle
          cx="70" cy="70" r="54"
          fill="none"
          stroke={strokeColor}
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
        <text x="70" y="65" textAnchor="middle" fill="white" fontSize="28" fontWeight="bold">{score.toFixed(0)}</text>
        <text x="70" y="85" textAnchor="middle" fill={strokeColor} fontSize="11" fontWeight="600">{cfg.label}</text>
      </svg>
    </div>
  );
}

function StatCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised p-4 text-center">
      <p className={`text-3xl font-bold ${accent ?? "text-white"}`}>{value}</p>
      <p className="text-xs text-slate-400 mt-1 font-medium uppercase tracking-wide">{label}</p>
      {sub && <p className="text-xs text-slate-600 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function StandupPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid      = useManagementProjectId(projectId || undefined);
  const standupQ  = useManagementStandup(mpid || undefined);

  const [countdown, setCountdown] = useState(60);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    if (!standupQ.isLoading && standupQ.data) setLastUpdate(new Date());
  }, [standupQ.data, standupQ.isLoading]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCountdown(c => {
        if (c <= 1) { void standupQ.refetch(); return 60; }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [standupQ]);

  const data    = standupQ.data as StandupData | undefined;
  const loading = standupQ.isLoading;
  const health  = data?.summary_health ?? "at_risk";
  const cfg = HEALTH_CONFIG[health];
  const pct = data && data.total_cases > 0 ? Math.round((data.completed_cases / data.total_cases) * 100) : 0;

  return (
    <div className={`min-h-screen bg-bg px-4 py-6 flex flex-col gap-4 max-w-sm mx-auto`}>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-widest font-semibold">Stand-up</p>
          <p className="text-white font-bold text-lg">Release Durumu</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className={`flex items-center gap-1.5 rounded-full border ${cfg.ring} px-2.5 py-1`}>
            <span className={`w-2 h-2 rounded-full animate-pulse ${cfg.dot}`} />
            <span className={`text-xs font-bold ${cfg.color}`}>{cfg.label}</span>
          </div>
          <p className="text-[10px] text-slate-600">{countdown}sn sonra güncellenir</p>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Ana gauge */}
          <div className="flex justify-center py-2">
            <HealthGaugeMobile score={data?.health_score ?? 0} health={health} />
          </div>

          {/* Execution progress */}
          <div className="rounded-xl border border-border bg-surface-raised p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Execution</span>
              <span className="text-white font-bold">{pct}%</span>
            </div>
            <div className="h-3 rounded-full bg-surface-overlay overflow-hidden">
              <div
                className="h-full rounded-full bg-teal-500 transition-all duration-700"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 text-center">
              {data?.completed_cases ?? 0} / {data?.total_cases ?? 0} case
            </p>
          </div>

          {/* KPI grid */}
          <div className="grid grid-cols-2 gap-3">
            <StatCard
              label="Pass Rate"
              value={`${data?.pass_rate.toFixed(0) ?? 0}%`}
              accent={(data?.pass_rate ?? 0) >= 90 ? "text-emerald-400" : (data?.pass_rate ?? 0) >= 70 ? "text-amber-400" : "text-red-400"}
            />
            <StatCard
              label="Blocked"
              value={String(data?.blocked ?? 0)}
              accent={(data?.blocked ?? 0) === 0 ? "text-emerald-400" : "text-amber-400"}
            />
            <StatCard
              label="Failed"
              value={String(data?.failed ?? 0)}
              accent={(data?.failed ?? 0) === 0 ? "text-emerald-400" : "text-red-400"}
            />
            <StatCard
              label="Bekleyen"
              value={String(data?.remaining_cases ?? 0)}
              accent="text-slate-300"
            />
          </div>

          {/* Release gate */}
          {data && (
            <div className={`rounded-xl border p-4 space-y-2 ${
              data.will_meet_gate
                ? "border-emerald-500/30 bg-emerald-500/10"
                : "border-red-500/30 bg-red-500/10"
            }`}>
              <div className="flex items-center gap-2">
                <span className="text-lg">{data.will_meet_gate ? "✅" : "🚫"}</span>
                <p className={`text-sm font-bold ${data.will_meet_gate ? "text-emerald-400" : "text-red-400"}`}>
                  {data.will_meet_gate ? "Release Gate Karşılanıyor" : "Release Gate Karşılanmıyor"}
                </p>
              </div>
              {data.blocking_factors.length > 0 && (
                <ul className="space-y-1">
                  {data.blocking_factors.map((f, i) => (
                    <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-red-400 mt-0.5 shrink-0">•</span>
                      {f}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Son güncelleme */}
          {lastUpdate && (
            <p className="text-center text-xs text-slate-600">
              Son güncelleme: {lastUpdate.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </p>
          )}

          {/* Aksiyonlar */}
          <div className="flex gap-2">
            <button
              onClick={() => { void standupQ.refetch(); setCountdown(60); }}
              className="flex-1 rounded-xl border border-border bg-surface-overlay py-3 text-sm font-medium text-slate-400 hover:text-white hover:border-border-strong transition-colors"
            >
              ↺ Şimdi Yenile
            </button>
            <button
              onClick={() => window.print()}
              className="rounded-xl border border-border bg-surface-overlay px-4 py-3 text-sm font-medium text-slate-400 hover:text-white hover:border-border-strong transition-colors"
              title="Yazdır / PDF olarak kaydet"
            >
              🖨️ Yazdır
            </button>
          </div>
        </>
      )}
    </div>
  );
}
