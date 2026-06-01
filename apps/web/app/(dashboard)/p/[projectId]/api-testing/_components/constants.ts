// ── Color maps for API testing UI ────────────────────────────────────────────

export function statusCodeColor(code: number): string {
  if (code >= 500) return "text-red-400";
  if (code >= 400) return "text-amber-400";
  if (code >= 200) return "text-emerald-400";
  return "text-slate-400";
}

export const TEST_TYPE_COLORS: Record<string, string> = {
  positive:    "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  negative:    "bg-red-500/15 text-red-400 border-red-500/30",
  boundary:    "bg-amber-500/15 text-amber-400 border-amber-500/30",
  security:    "bg-violet-500/15 text-violet-400 border-violet-500/30",
  performance: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  edge_case:   "bg-orange-500/15 text-orange-400 border-orange-500/30",
  contract:    "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  compliance:  "bg-rose-500/15 text-rose-400 border-rose-500/30",
  regression:  "bg-slate-700 text-slate-300 border-slate-600",
};

export const STATUS_COLORS: Record<string, string> = {
  passed:  "text-emerald-400",
  failed:  "text-red-400",
  pending: "text-slate-400",
  running: "text-blue-400",
};

export const RISK_COLORS: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
  high:     "bg-orange-500/15 text-orange-400 border-orange-500/30",
  medium:   "bg-amber-500/15 text-amber-400 border-amber-500/30",
  low:      "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};

export const METHOD_COLORS: Record<string, string> = {
  GET:    "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  POST:   "bg-blue-500/15 text-blue-400 border-blue-500/30",
  PUT:    "bg-amber-500/15 text-amber-400 border-amber-500/30",
  PATCH:  "bg-orange-500/15 text-orange-400 border-orange-500/30",
  DELETE: "bg-red-500/15 text-red-400 border-red-500/30",
};
