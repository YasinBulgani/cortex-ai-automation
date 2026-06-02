"use client";

import { cn } from "@/lib/utils";
import type { SelectorValidationItem } from "@/lib/hooks/use-playwright-mcp";

// ── Color helpers ────────────────────────────────────────────────────

function stabilityColor(score: number) {
  if (score >= 5) return "bg-emerald-500/15 border-emerald-500/30 text-emerald-400";
  if (score >= 4) return "bg-blue-500/15 border-blue-500/30 text-blue-400";
  if (score >= 3) return "bg-amber-500/15 border-amber-500/30 text-amber-400";
  if (score >= 2) return "bg-orange-500/15 border-orange-500/30 text-orange-400";
  return "bg-red-500/15 border-red-500/30 text-red-400";
}

// ── Props ────────────────────────────────────────────────────────────

export interface SelectorValidationTableProps {
  results: SelectorValidationItem[];
}

// ── Component ────────────────────────────────────────────────────────

export function SelectorValidationTable({ results }: SelectorValidationTableProps) {
  if (results.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800 text-left">
            <th className="px-4 py-2 text-xs font-semibold text-slate-400">Selector</th>
            <th className="px-4 py-2 text-xs font-semibold text-slate-400 text-center">Bulundu</th>
            <th className="px-4 py-2 text-xs font-semibold text-slate-400 text-center">Adet</th>
            <th className="px-4 py-2 text-xs font-semibold text-slate-400 text-center">Gorunur</th>
            <th className="px-4 py-2 text-xs font-semibold text-slate-400">Tag</th>
            <th className="px-4 py-2 text-xs font-semibold text-slate-400 text-center">Stabilite</th>
            <th className="px-4 py-2 text-xs font-semibold text-slate-400">Alternatifler</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r: SelectorValidationItem) => (
            <tr key={r.selector} className="border-b border-slate-800/60 hover:bg-slate-800/30">
              <td
                className="px-4 py-2 font-mono text-xs text-slate-300 max-w-[200px] truncate"
                title={r.selector}
              >
                {r.selector}
              </td>
              <td className="px-4 py-2 text-center">
                {r.found ? (
                  <span className="text-emerald-400 text-base">&#10003;</span>
                ) : (
                  <span className="text-red-400 text-base">&#10007;</span>
                )}
              </td>
              <td className="px-4 py-2 text-center text-slate-300">{r.count}</td>
              <td className="px-4 py-2 text-center">
                {r.visible ? (
                  <span className="text-emerald-400 text-base">&#10003;</span>
                ) : (
                  <span className="text-slate-600 text-base">&#10007;</span>
                )}
              </td>
              <td className="px-4 py-2 text-xs text-slate-400">{r.tag ?? "—"}</td>
              <td className="px-4 py-2 text-center">
                <span
                  className={cn(
                    "inline-block rounded-full border px-2 py-0.5 text-xs font-semibold",
                    stabilityColor(r.stability_score),
                  )}
                >
                  {r.stability_score}/5
                </span>
              </td>
              <td className="px-4 py-2">
                {r.alternatives && r.alternatives.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {r.alternatives.slice(0, 3).map((alt) => (
                      <span
                        key={alt}
                        className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-400"
                      >
                        {alt}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-xs text-slate-600">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
