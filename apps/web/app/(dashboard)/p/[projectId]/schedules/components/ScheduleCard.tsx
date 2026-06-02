"use client";

import { useEffect, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

export type Schedule = {
  id: string;
  name: string;
  cron_expression: string;
  is_active: boolean;
  scenario_ids: string[];
  last_run_at: string | null;
  next_run_at: string | null;
  platform?: string | null;
  device_name?: string | null;
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function cronHuman(cron: string) {
  const map: Record<string, string> = {
    "0 2 * * *": "Her gün 02:00",
    "0 9 * * 1": "Her Pazartesi 09:00",
    "0 * * * *": "Her saat başı",
    "0 */6 * * *": "Her 6 saatte bir",
  };
  return map[cron] ?? cron;
}

function PlatformBadge({ platform }: { platform?: string | null }) {
  if (platform === "ios")
    return (
      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 border border-blue-500/20 text-blue-400">
        🍎 iOS
      </span>
    );
  if (platform === "android")
    return (
      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-500/10 border border-green-500/20 text-green-400">
        🤖 Android
      </span>
    );
  return null;
}

function useCountdown(nextRunAt: string | null): string {
  const [label, setLabel] = useState("—");
  useEffect(() => {
    if (!nextRunAt) {
      setLabel("—");
      return;
    }
    const tick = () => {
      const diff = Math.max(
        0,
        Math.floor((new Date(nextRunAt).getTime() - Date.now()) / 1000),
      );
      if (diff === 0) {
        setLabel("Şimdi");
        return;
      }
      const h = Math.floor(diff / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      setLabel(h > 0 ? `${h}s ${m}d` : m > 0 ? `${m}d ${s}sn` : `${s}sn`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [nextRunAt]);
  return label;
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ScheduleCardProps {
  schedule: Schedule;
  onToggle: () => void;
  onTrigger: () => void;
  onDelete: () => void;
  triggering: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ScheduleCard({
  schedule,
  onToggle,
  onTrigger,
  onDelete,
  triggering,
}: ScheduleCardProps) {
  const countdown = useCountdown(schedule.next_run_at);

  return (
    <div
      className="rounded-xl border border-slate-700 bg-slate-800/40 p-4 hover:border-slate-600 transition-all"
      data-testid={`schedule-card-${schedule.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className="text-sm font-semibold text-white truncate">
              {schedule.name}
            </h3>
            {schedule.platform && (
              <PlatformBadge platform={schedule.platform} />
            )}
            <button
              onClick={onToggle}
              className={`shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                schedule.is_active
                  ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  schedule.is_active ? "bg-emerald-400" : "bg-slate-500"
                }`}
              />
              {schedule.is_active ? "Aktif" : "Pasif"}
            </button>
          </div>
          <p className="font-mono text-xs text-blue-400 mb-1">
            {schedule.cron_expression}
          </p>
          <p className="text-xs text-slate-400">
            {cronHuman(schedule.cron_expression)}
          </p>
          {schedule.device_name && (
            <p className="text-xs text-indigo-400 mt-0.5">
              📱 {schedule.device_name}
            </p>
          )}
        </div>
        <div className="flex gap-1 shrink-0">
          <button
            onClick={onTrigger}
            disabled={triggering}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-300 border border-emerald-500/30 rounded-lg hover:bg-emerald-500/10 transition-all disabled:opacity-50"
          >
            {triggering ? (
              <div className="w-3 h-3 border border-emerald-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg
                className="w-3 h-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                />
              </svg>
            )}
            Çalıştır
          </button>
          <button
            onClick={onDelete}
            className="px-2 py-1.5 text-xs text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/10 transition-all"
          >
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-slate-800 grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-slate-500 mb-0.5">Son çalışma</p>
          <p className="text-xs text-slate-300">{fmtDate(schedule.last_run_at)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-0.5">Sonraki çalışma</p>
          <p className="text-xs text-slate-300">
            {fmtDate(schedule.next_run_at)}
          </p>
          {schedule.is_active && schedule.next_run_at && (
            <p className="text-xs text-blue-400 mt-0.5 font-medium">
              {countdown}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
