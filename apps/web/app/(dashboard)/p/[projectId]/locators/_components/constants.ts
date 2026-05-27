// ── Types ────────────────────────────────────────────────────────────────────

export type Locator = {
  id: string;
  name: string;
  selector: string;
  type: string;
  page: string;
  status: string;
};

export type TabId = "management" | "stability" | "fallback" | "pom" | "breakage";

// ── Color / style maps ───────────────────────────────────────────────────────

export const STATUS_STYLES: Record<string, { color: string; dot: string; label: string }> = {
  healthy: { color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", dot: "bg-emerald-400", label: "Saglikli" },
  broken:  { color: "bg-red-500/10 border-red-500/20 text-red-400",            dot: "bg-red-400",     label: "Kırık" },
  warning: { color: "bg-amber-500/10 border-amber-500/20 text-amber-400",      dot: "bg-amber-400",   label: "Uyari" },
};

export const TYPE_COLORS: Record<string, string> = {
  css:    "bg-blue-500/10 border-blue-500/20 text-blue-400",
  xpath:  "bg-amber-500/10 border-amber-500/20 text-amber-400",
  testid: "bg-violet-500/10 border-violet-500/20 text-violet-400",
  text:   "bg-slate-800 border-slate-700 text-slate-300",
};

export const TABS: { id: TabId; label: string }[] = [
  { id: "management", label: "Yönetim" },
  { id: "stability",  label: "Stabilite" },
  { id: "fallback",   label: "Fallback" },
  { id: "pom",        label: "POM" },
  { id: "breakage",   label: "Kırılma" },
];

// ── CSS class strings ────────────────────────────────────────────────────────

export const BTN_PRIMARY =
  "inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all";

export const INPUT_CLS =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";

export const TEXTAREA_CLS =
  "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 resize-none font-mono";

// ── Pure functions ───────────────────────────────────────────────────────────

export function getScoreColor(score: number): string {
  if (score >= 4) return "bg-emerald-500/10 border-emerald-500/20 text-emerald-400";
  if (score >= 3) return "bg-blue-500/10 border-blue-500/20 text-blue-400";
  if (score >= 2) return "bg-amber-500/10 border-amber-500/20 text-amber-400";
  return "bg-red-500/10 border-red-500/20 text-red-400";
}
