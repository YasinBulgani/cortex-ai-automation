"use client";

import { useProject } from "@/lib/useProject";
import { useDayOverDay, type DayDeltaMetric } from "@/lib/hooks/use-web-dashboard";

const DEMO_METRICS: DayDeltaMetric[] = [
  { key: "pass",     label: "Pass Rate",      today: "94.8%", yesterday: "92.9%", delta: 1.9,  deltaUnit: "pp", goodDirection: "up",   spark: [88,90,89,91,92,92,94,95] },
  { key: "duration", label: "Ort. Süre",      today: "3.2dk", yesterday: "3.6dk", delta: -11,  deltaUnit: "%",  goodDirection: "down", spark: [4.2,4.0,3.9,3.8,3.7,3.6,3.4,3.2] },
  { key: "flaky",    label: "Flaky Test",     today: "17",    yesterday: "23",    delta: -6,             goodDirection: "down", spark: [28,26,25,24,23,22,19,17] },
  { key: "newfail",  label: "Yeni Fail",      today: "4",     yesterday: "1",     delta: 3,              goodDirection: "down", spark: [0,1,2,1,3,2,3,4] },
  { key: "visdiff",  label: "Visual Diff",    today: "4",     yesterday: "6",     delta: -2,             goodDirection: "down", spark: [8,7,7,6,6,5,5,4] },
  { key: "runs",     label: "Toplam Koşu",    today: "1.284", yesterday: "1.156", delta: 11,   deltaUnit: "%",  goodDirection: "up",   spark: [950,1000,1080,1120,1150,1156,1200,1284] },
];

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 100 - ((v - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-8">
      <polyline points={points} fill="none" stroke={color} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 animate-pulse">
      <div className="h-3 w-20 rounded bg-slate-800 mb-2" />
      <div className="h-6 w-16 rounded bg-slate-800 mb-2" />
      <div className="h-8 w-full rounded bg-slate-800/60" />
    </div>
  );
}

export function TodayVsYesterdayStrip() {
  const { projectId } = useProject();
  const { data, isLoading } = useDayOverDay(projectId);
  const metrics = data?.metrics ?? DEMO_METRICS;
  const windowHours = data?.windowHours ?? 24;
  const isDemo = !data && !isLoading;
  const hasData = metrics.length > 0;

  if (isLoading) {
    return (
      <section>
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs font-semibold text-sky-400 uppercase tracking-widest">📊 Bugün vs Dün</p>
          <span className="text-[11px] text-slate-500">Yükleniyor…</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      </section>
    );
  }

  if (!hasData) {
    return (
      <section>
        <p className="text-xs font-semibold text-sky-400 uppercase tracking-widest mb-3">📊 Bugün vs Dün</p>
        <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-6 py-10 text-center">
          <p className="text-sm text-slate-400">Henüz delta hesaplamak için yeterli koşu yok.</p>
          <p className="text-xs text-slate-500 mt-1">İlk 24 saatlik veri toplandıktan sonra burada görünecek.</p>
        </div>
      </section>
    );
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <p className="text-xs font-semibold text-sky-400 uppercase tracking-widest">📊 Bugün vs Dün</p>
          {isDemo && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">
              Demo
            </span>
          )}
          <p className="text-xs text-slate-500">· Son {windowHours} saat — önceki {windowHours} saate göre delta</p>
        </div>
        <span className="text-[11px] text-slate-500">Karşılaştırma penceresi: {windowHours}s</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {metrics.map((m) => {
          const improved =
            m.goodDirection === "up" ? m.delta > 0 : m.delta < 0;
          const flat = m.delta === 0;
          const tone = flat
            ? { fg: "text-slate-300", chip: "bg-slate-800 text-slate-400 border-slate-700", line: "#64748b" }
            : improved
              ? { fg: "text-emerald-300", chip: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", line: "#34d399" }
              : { fg: "text-rose-300",    chip: "bg-rose-500/15 text-rose-300 border-rose-500/30",          line: "#fb7185" };
          const arrow = flat ? "→" : m.delta > 0 ? "▲" : "▼";

          return (
            <div key={m.key} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 flex flex-col gap-1.5">
              <div className="flex items-start justify-between gap-2">
                <p className="text-[11px] uppercase tracking-wider text-slate-500 truncate">{m.label}</p>
                <span className={`shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded border ${tone.chip}`}>
                  {arrow} {Math.abs(m.delta)}{m.deltaUnit ?? ""}
                </span>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className={`text-xl font-bold tabular-nums ${tone.fg}`}>{m.today}</span>
                <span className="text-[10px] text-slate-500">vs {m.yesterday}</span>
              </div>
              <Sparkline data={m.spark} color={tone.line} />
            </div>
          );
        })}
      </div>
    </section>
  );
}
