"use client";

/**
 * Coverage heatmap visualization — F8.
 *
 * Module × test-type grid; her hücre coverage % değerine göre renkli.
 * Pure CSS grid, no chart library.
 */

import { coverageColorClass } from "@/lib/useTraceabilityMatrix";

export type HeatmapCell = {
  module: string;
  testType: string;
  coveragePct: number;
  testCount: number;
};

type Props = {
  modules: string[];
  testTypes: string[];
  cells: HeatmapCell[];
};

export function CoverageHeatmap({ modules, testTypes, cells }: Props) {
  // Cell lookup
  const cellMap = new Map<string, HeatmapCell>();
  for (const c of cells) {
    cellMap.set(`${c.module}::${c.testType}`, c);
  }

  if (modules.length === 0 || testTypes.length === 0) {
    return (
      <div
        className="rounded-lg border border-dashed border-slate-700 p-12 text-center text-sm text-slate-500"
        data-testid="coverage-heatmap-empty"
      >
        Modül veya test tipi tanımlanmamış
      </div>
    );
  }

  return (
    <div
      className="overflow-auto rounded-xl border border-slate-800 bg-slate-900/50"
      data-testid="coverage-heatmap"
    >
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="sticky left-0 top-0 z-10 border-b border-r border-slate-800 bg-slate-900 px-3 py-2 text-left font-medium text-slate-400">
              Modül \ Test
            </th>
            {testTypes.map((tt) => (
              <th
                key={tt}
                className="border-b border-slate-800 px-3 py-2 text-left font-medium text-slate-400"
                data-testid={`heatmap-col-${tt}`}
              >
                {tt}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {modules.map((mod) => (
            <tr key={mod}>
              <td
                className="sticky left-0 border-r border-slate-800 bg-slate-900 px-3 py-2 font-medium text-slate-300"
                data-testid={`heatmap-row-${mod}`}
              >
                {mod}
              </td>
              {testTypes.map((tt) => {
                const cell = cellMap.get(`${mod}::${tt}`);
                if (!cell) {
                  return (
                    <td
                      key={tt}
                      className="border-b border-slate-800 px-3 py-2 text-slate-700"
                      data-testid={`heatmap-cell-${mod}-${tt}-empty`}
                    >
                      —
                    </td>
                  );
                }
                return (
                  <td
                    key={tt}
                    className={`border-b border-slate-800 px-3 py-2 ${coverageColorClass(cell.coveragePct)}`}
                    title={`${cell.testCount} test, %${cell.coveragePct.toFixed(0)} kapsama`}
                    data-testid={`heatmap-cell-${mod}-${tt}`}
                  >
                    {cell.coveragePct.toFixed(0)}%
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
