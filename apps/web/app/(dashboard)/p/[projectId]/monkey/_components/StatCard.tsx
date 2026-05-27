"use client";

// ── StatCard ──────────────────────────────────────────────────────────────────

export function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "emerald" | "yellow" | "red" | "slate";
}) {
  const color =
    accent === "emerald"
      ? "text-emerald-400"
      : accent === "yellow"
        ? "text-yellow-400"
        : accent === "red"
          ? "text-red-400"
          : "text-slate-200";
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950/40 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-sm font-bold ${color}`}>{value}</div>
    </div>
  );
}

// ── ColHeader ─────────────────────────────────────────────────────────────────

export function ColHeader({ label }: { label: string }) {
  return (
    <div className="px-3 py-2 text-slate-300 bg-slate-900/60 text-center border-r last:border-r-0 border-slate-700">
      {label}
    </div>
  );
}
