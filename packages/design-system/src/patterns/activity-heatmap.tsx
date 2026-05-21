"use client";

import { useMemo } from "react";
import { cn } from "../utils/cn";
import { Tooltip } from "../primitives/tooltip";

export interface HeatmapCell {
  date: string;     // ISO date
  value: number;
}

export interface ActivityHeatmapProps {
  data: HeatmapCell[];
  weeks?: number;
  className?: string;
  title?: string;
  label?: string;   // "Test koşusu", "Senaryo" gibi
}

/**
 * ActivityHeatmap — GitHub tarzı yıllık aktivite görseli.
 *
 * 53 hafta × 7 gün grid. Yoğunluğa göre 0-4 ton.
 */
export function ActivityHeatmap({
  data,
  weeks = 26,
  className,
  title = "Aktivite",
  label = "aktivite",
}: ActivityHeatmapProps) {
  const grid = useMemo(() => {
    // Tarih → değer haritası
    const map = new Map(data.map(d => [d.date.slice(0, 10), d.value]));
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const totalDays = weeks * 7;
    const cells: { date: Date; value: number; level: 0|1|2|3|4 }[] = [];
    const max = Math.max(1, ...data.map(d => d.value));

    for (let i = totalDays - 1; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      const value = map.get(key) ?? 0;
      const ratio = value / max;
      const level: 0|1|2|3|4 =
        value === 0   ? 0 :
        ratio < 0.25  ? 1 :
        ratio < 0.5   ? 2 :
        ratio < 0.75  ? 3 : 4;
      cells.push({ date: d, value, level });
    }

    // 7 satır × N sütun olarak yeniden düzenle
    const rows: typeof cells[] = [[], [], [], [], [], [], []];
    cells.forEach(c => {
      const dayIdx = (c.date.getDay() + 6) % 7; // Pazartesi 0
      rows[dayIdx].push(c);
    });
    return rows;
  }, [data, weeks]);

  const total = data.reduce((acc, d) => acc + d.value, 0);

  const LEVEL_CLASSES = {
    0: "bg-surface-overlay",
    1: "bg-brand-primary/20",
    2: "bg-brand-primary/40",
    3: "bg-brand-primary/70",
    4: "bg-brand-primary",
  } as const;

  return (
    <div className={cn("rounded-xl border border-border bg-surface-raised p-4", className)}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-fg">{title}</h3>
          <p className="text-[10px] text-fg-subtle mt-0.5">{weeks} haftada {total} {label}</p>
        </div>
        {/* Legend */}
        <div className="flex items-center gap-1 text-[10px] text-fg-subtle">
          <span>az</span>
          {([0, 1, 2, 3, 4] as const).map(l => (
            <span key={l} className={cn("h-2.5 w-2.5 rounded-sm", LEVEL_CLASSES[l])} />
          ))}
          <span>çok</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <div className="inline-flex flex-col gap-0.5">
          {grid.map((row, rowIdx) => (
            <div key={rowIdx} className="flex gap-0.5">
              {row.map((cell, i) => (
                <Tooltip
                  key={i}
                  delay={100}
                  content={
                    <div className="text-[10px]">
                      <span className="font-semibold">{cell.value}</span> {label}
                      <span className="text-fg-subtle ml-1">
                        {cell.date.toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}
                      </span>
                    </div>
                  }
                >
                  <span className={cn("h-2.5 w-2.5 rounded-sm cursor-pointer transition-transform hover:scale-125", LEVEL_CLASSES[cell.level])} />
                </Tooltip>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
