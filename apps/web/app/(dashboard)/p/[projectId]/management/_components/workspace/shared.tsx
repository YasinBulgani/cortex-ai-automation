"use client";

import { cn } from "@/lib/utils";

// ─── Tree node selection ────────────────────────────────────────────────────────

export type WsNode =
  | { type: "all" }
  | { type: "suite"; id: string }
  | { type: "folder"; id: string; suiteId: string };

export function nodeKey(n: WsNode): string {
  return n.type === "all" ? "all" : `${n.type}:${n.id}`;
}

// ─── Color maps ─────────────────────────────────────────────────────────────────

export const P_DOT: Record<string, string> = {
  P0: "bg-red-500/80", P1: "bg-orange-400/60",
  P2: "bg-slate-500",  P3: "bg-slate-600",
};

export const P_LABEL: Record<string, { bg: string; text: string; label: string }> = {
  P0: { bg: "bg-red-500/12",    text: "text-red-400",    label: "Kritik" },
  P1: { bg: "bg-orange-500/12", text: "text-orange-400", label: "Yüksek" },
  P2: { bg: "bg-surface-overlay", text: "text-fg-muted", label: "Orta"   },
  P3: { bg: "bg-surface-overlay", text: "text-fg-subtle", label: "Düşük"  },
};

export const S_DOT: Record<string, { dot: string; label: string }> = {
  active:   { dot: "bg-emerald-500/70", label: "Aktif"  },
  draft:    { dot: "bg-slate-600",      label: "Taslak" },
  review:   { dot: "bg-blue-500/60",    label: "Review" },
  archived: { dot: "bg-surface-accent",      label: "Arşiv"  },
};

export const R_DOT: Record<string, { dot: string; label: string; bg: string; text: string }> = {
  passed:  { dot: "bg-emerald-500",  label: "Passed",  bg: "bg-emerald-500/10", text: "text-emerald-400" },
  failed:  { dot: "bg-red-500",      label: "Failed",  bg: "bg-red-500/10",     text: "text-red-400"     },
  blocked: { dot: "bg-amber-500",    label: "Blocked", bg: "bg-amber-500/10",   text: "text-amber-400"   },
  skipped: { dot: "bg-slate-400",    label: "Skipped", bg: "bg-surface-overlay", text: "text-fg-muted"    },
  not_run: { dot: "bg-slate-500",    label: "—",       bg: "bg-transparent",     text: "text-fg-subtle"   },
};

export const AUTO_DOT: Record<string, { dot: string; label: string; color: string }> = {
  automated:     { dot: "bg-teal-500",   label: "Otomatik",       color: "text-teal-400"   },
  in_progress:   { dot: "bg-blue-400 animate-pulse", label: "Geliştiriliyor", color: "text-blue-400" },
  planned:       { dot: "bg-amber-400",  label: "Planlandı",      color: "text-amber-400"  },
  not_automated: { dot: "bg-slate-500",  label: "Manuel",         color: "text-fg-muted"   },
};

export const P_BADGE: Record<string, string> = {
  P0: "border-red-500/30 bg-red-500/10 text-red-400",
  P1: "border-orange-400/30 bg-orange-400/10 text-orange-400",
  P2: "border-border-strong bg-surface-overlay text-fg-muted",
  P3: "border-border bg-surface-overlay text-fg-subtle",
};

export const SB_BADGE: Record<string, string> = {
  active:   "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  draft:    "border-border-strong bg-surface-overlay text-fg-muted",
  review:   "border-blue-500/30 bg-blue-500/10 text-blue-400",
  ready:    "border-teal-500/30 bg-teal-500/10 text-teal-400",
  archived: "border-border bg-surface-raised text-fg-subtle",
};

export const STATUS_LABEL_TR: Record<string, string> = {
  active: "Aktif", draft: "Taslak", review: "Review", ready: "Hazır", archived: "Arşiv",
};

export const RUN_STATUS_DOT: Record<string, string> = {
  in_progress: "bg-blue-500 animate-pulse",
  not_started: "bg-slate-600",
  completed:   "bg-emerald-500/70",
  passed:      "bg-emerald-500/70",
  failed:      "bg-red-500/70",
  blocked:     "bg-amber-500/60",
};

export const RUN_STATUS_LABEL: Record<string, string> = {
  in_progress: "Devam ediyor",
  not_started: "Bekliyor",
  completed:   "Tamamlandı",
  failed:      "Başarısız",
  passed:      "Passed",
  blocked:     "Bloke",
};

export const TYPE_COLOR: Record<string, string> = {
  manual:        "bg-surface-overlay text-fg-muted",
  smoke:         "bg-teal-500/15 text-teal-400",
  regression:    "bg-purple-500/15 text-purple-400",
  uat:           "bg-indigo-500/15 text-indigo-400",
  exploratory:   "bg-pink-500/15 text-pink-400",
  integration:   "bg-blue-500/15 text-blue-400",
  performance:   "bg-orange-500/15 text-orange-400",
  security:      "bg-red-500/15 text-red-400",
  accessibility: "bg-yellow-500/15 text-yellow-400",
  api:           "bg-cyan-500/15 text-cyan-400",
  e2e:           "bg-violet-500/15 text-violet-400",
};

export const TYPE_OPTIONS = [
  "manual", "smoke", "regression", "uat", "exploratory",
  "integration", "performance", "security", "accessibility", "api", "e2e",
] as const;

// ─── Helpers ────────────────────────────────────────────────────────────────────

export function slugify(s: string) {
  return `/${s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || s}`;
}

export function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "az önce";
  if (mins < 60) return `${mins}dk önce`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}s önce`;
  return `${Math.floor(hrs / 24)}g önce`;
}

// ─── Mini Progress Bar ───────────────────────────────────────────────────────────

export function MiniProgress({ passed, failed, total }: { passed: number; failed: number; total: number }) {
  if (total === 0) return <div className="h-1 w-full rounded-full bg-surface-overlay" />;
  const passW  = Math.round((passed / total) * 100);
  const failW  = Math.round((failed / total) * 100);
  return (
    <div className="flex h-1 w-full overflow-hidden rounded-full bg-surface-overlay">
      <div className="bg-emerald-500/60 transition-all" style={{ width: `${passW}%` }} />
      <div className="bg-red-500/50 transition-all"     style={{ width: `${failW}%` }} />
    </div>
  );
}

// ─── Score Ring (Braintrust-style) ───────────────────────────────────────────────

export function ScoreRing({ score, size = 36 }: { score: number; size?: number }) {
  const r  = (size - 6) / 2;
  const c  = 2 * Math.PI * r;
  const fill = score * c;
  const color = score >= 0.8 ? "#34d399" : score >= 0.5 ? "#fbbf24" : "#f87171";
  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border)" strokeWidth={3} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={3}
        strokeDasharray={`${fill} ${c - fill}`} strokeLinecap="round"
        style={{ transition: "stroke-dasharray 0.6s ease" }} />
    </svg>
  );
}

// ─── Icons ──────────────────────────────────────────────────────────────────────

export function IcChev({ open }: { open: boolean }) {
  return <svg className={cn("h-2.5 w-2.5 shrink-0 transition-transform", open && "rotate-90")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>;
}
export function IcPlus() {
  return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>;
}
export function IcClose() {
  return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>;
}
export function IcGrip() {
  return <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 16 16"><circle cx="5" cy="4" r="1.2" /><circle cx="11" cy="4" r="1.2" /><circle cx="5" cy="8" r="1.2" /><circle cx="11" cy="8" r="1.2" /><circle cx="5" cy="12" r="1.2" /><circle cx="11" cy="12" r="1.2" /></svg>;
}
export function IcSearch() {
  return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>;
}
export function IcFolder({ open }: { open?: boolean }) {
  return open
    ? <svg className="h-3.5 w-3.5 shrink-0 text-brand" fill="currentColor" viewBox="0 0 24 24"><path d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" /></svg>
    : <svg className="h-3 w-3 shrink-0 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" /></svg>;
}
export function IcTrash() {
  return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>;
}
export function IcPencil() {
  return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>;
}
export function IcPlay() {
  return <svg className="h-3.5 w-3.5 shrink-0" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>;
}
export function IcStack() {
  return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 6.878V6a2.25 2.25 0 012.25-2.25h7.5A2.25 2.25 0 0118 6v.878m-12 0c.235-.083.487-.128.75-.128h10.5c.263 0 .515.045.75.128m-12 0A2.25 2.25 0 004.5 9v.878m13.5-3A2.25 2.25 0 0119.5 9v.878m0 0a2.246 2.246 0 00-.75-.128H5.25c-.263 0-.515.045-.75.128m15 0A2.25 2.25 0 0121 12v6a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 18v-6c0-.98.626-1.813 1.5-2.122" /></svg>;
}
export function IcRun() {
  return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /></svg>;
}
export function IcAI() {
  return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" /></svg>;
}
export function IcDot({ className }: { className?: string }) {
  return <span className={cn("inline-block h-1.5 w-1.5 rounded-full", className)} />;
}
