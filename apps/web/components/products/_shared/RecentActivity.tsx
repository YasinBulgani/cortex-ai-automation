"use client";

import type { ActivityEvent } from "@/lib/products/telemetry-types";

interface RecentActivityProps {
  events: ActivityEvent[];
  brandText: string;
  loading?: boolean;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "şu an";
  if (mins < 60) return `${mins} dk önce`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} sa önce`;
  return `${Math.floor(hrs / 24)} gün önce`;
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

const AVATAR_COLORS = [
  "bg-indigo-500", "bg-violet-500", "bg-sky-500", "bg-emerald-500",
  "bg-rose-500", "bg-amber-500", "bg-fuchsia-500", "bg-cyan-500",
];

function avatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export function RecentActivity({ events, brandText, loading }: RecentActivityProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-12 rounded-lg bg-slate-900/60 animate-pulse" />
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-slate-400">
        <p className="text-sm">Henüz aktivite yok</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {events.map((event, idx) => (
        <div key={event.id} className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-900/60 transition-colors group">
          <div className="relative flex-shrink-0">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${avatarColor(event.actor)}`}>
              {initials(event.actor)}
            </div>
            {idx < events.length - 1 && (
              <div className="absolute left-1/2 top-full -translate-x-px w-px h-2 bg-white/10" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white leading-tight">
              <span className="font-medium">{event.actor}</span>
              {" "}
              <span className="text-slate-400">{event.verb}</span>
              {" "}
              <span className={`font-medium ${brandText}`}>{event.objectName}</span>
            </p>
            {event.meta && <p className="text-xs text-slate-400">{event.meta}</p>}
          </div>
          <span className="text-xs text-white-subtle flex-shrink-0">{timeAgo(event.ts)}</span>
        </div>
      ))}
    </div>
  );
}
