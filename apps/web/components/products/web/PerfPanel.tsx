"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useProject } from "@/lib/useProject";

type MetricKey = "lcp" | "inp" | "cls" | "fcp" | "tbt";

interface PageMetrics {
  page: string;
  url: string;
  lcp: number; // ms
  inp: number; // ms
  cls: number; // unitless
  fcp: number; // ms
  tbt: number; // ms
  sampleCount: number;
}

interface PerfMetrics {
  pages: PageMetrics[];
  trend: Record<MetricKey, number[]>;
  updatedAt: string;
}

const THRESHOLDS = {
  lcp: { good: 2500, poor: 4000, unit: "ms", label: "LCP", desc: "Largest Contentful Paint" },
  inp: { good: 200,  poor: 500,  unit: "ms", label: "INP", desc: "Interaction to Next Paint" },
  cls: { good: 0.1,  poor: 0.25, unit: "",   label: "CLS", desc: "Cumulative Layout Shift" },
  fcp: { good: 1800, poor: 3000, unit: "ms", label: "FCP", desc: "First Contentful Paint" },
  tbt: { good: 200,  poor: 600,  unit: "ms", label: "TBT", desc: "Total Blocking Time" },
} as const;

const DEMO: PerfMetrics = {
  pages: [
    { page: "Homepage",        url: "/",          lcp: 2100, inp: 180, cls: 0.04, fcp: 1400, tbt: 140, sampleCount: 1284 },
    { page: "Checkout Step 1", url: "/checkout",  lcp: 2900, inp: 240, cls: 0.12, fcp: 1900, tbt: 380, sampleCount: 542 },
    { page: "Product Detail",  url: "/p/:id",     lcp: 3200, inp: 310, cls: 0.18, fcp: 2100, tbt: 520, sampleCount: 743 },
    { page: "Login",           url: "/login",     lcp: 1600, inp: 90,  cls: 0.02, fcp: 1100, tbt: 80,  sampleCount: 412 },
    { page: "Profile",         url: "/profile",   lcp: 2300, inp: 210, cls: 0.08, fcp: 1500, tbt: 180, sampleCount: 287 },
    { page: "Cart",            url: "/cart",      lcp: 4100, inp: 540, cls: 0.31, fcp: 2400, tbt: 720, sampleCount: 198 },
  ],
  trend: {
    lcp: [2.4, 2.5, 2.6, 2.5, 2.7, 2.8, 2.9, 2.9],
    inp: [180, 195, 210, 200, 220, 240, 235, 250],
    cls: [0.08, 0.09, 0.10, 0.11, 0.12, 0.12, 0.13, 0.14],
    fcp: [1.6, 1.7, 1.7, 1.8, 1.8, 1.9, 1.9, 1.9],
    tbt: [320, 340, 350, 360, 380, 400, 410, 420],
  },
  updatedAt: new Date().toISOString(),
};

function status(metric: MetricKey, value: number): "good" | "ni" | "poor" {
  const t = THRESHOLDS[metric];
  if (value <= t.good) return "good";
  if (value <= t.poor) return "ni";
  return "poor";
}

const STATUS_CLS = {
  good: "text-emerald-300",
  ni:   "text-amber-300",
  poor: "text-rose-300",
} as const;

function fmt(metric: MetricKey, v: number): string {
  if (metric === "cls") return v.toFixed(2);
  if (v >= 1000) return `${(v / 1000).toFixed(1)}s`;
  return `${Math.round(v)}ms`;
}

function usePerfMetrics(projectId: string | null | undefined) {
  return useQuery<PerfMetrics>({
    queryKey: ["web-dashboard", "perf-metrics", projectId ?? null],
    queryFn: () =>
      apiFetch<PerfMetrics>(
        `/api/v1/products/web/perf-metrics?project_id=${encodeURIComponent(projectId ?? "")}`,
      ),
    enabled: !!projectId,
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

function TrendChart({ data, metric }: { data: number[]; metric: MetricKey }) {
  const t = THRESHOLDS[metric];
  // CLS skalası farklı, normalize
  const max = Math.max(...data, t.poor * (metric === "cls" ? 1 : 1));
  const min = 0;
  const range = max - min || 1;
  const w = 100;
  const h = 100;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");
  const goodY = h - ((t.good - min) / range) * h;
  const poorY = h - ((t.poor - min) / range) * h;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full h-24">
      <line x1={0} x2={w} y1={goodY} y2={goodY} stroke="#10b981" strokeWidth={0.5} strokeDasharray="2 2" vectorEffect="non-scaling-stroke" opacity={0.5} />
      <line x1={0} x2={w} y1={poorY} y2={poorY} stroke="#f43f5e" strokeWidth={0.5} strokeDasharray="2 2" vectorEffect="non-scaling-stroke" opacity={0.5} />
      <polyline points={points} fill="none" stroke="#7dd3fc" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function PerfPanel() {
  const { projectId } = useProject();
  const { data, isLoading } = usePerfMetrics(projectId);
  const metrics = data ?? DEMO;
  const isDemo = !data && !isLoading;
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>("lcp");

  // Aggregate verdict — herhangi bir page'de poor varsa kötü
  const verdict = metrics.pages.reduce<"good" | "ni" | "poor">((acc, p) => {
    const s = status(selectedMetric, p[selectedMetric]);
    if (s === "poor" || acc === "poor") return "poor";
    if (s === "ni" || acc === "ni") return "ni";
    return "good";
  }, "good");

  if (isLoading) {
    return (
      <section>
        <p className="text-xs font-semibold text-cyan-400 uppercase tracking-widest mb-3">⚡ Performance · Core Web Vitals</p>
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
          <div className="h-64 rounded-2xl bg-slate-900/60 border border-slate-800 animate-pulse" />
          <div className="h-64 rounded-2xl bg-slate-900/60 border border-slate-800 animate-pulse" />
        </div>
      </section>
    );
  }

  const t = THRESHOLDS[selectedMetric];

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <p className="text-xs font-semibold text-cyan-400 uppercase tracking-widest">⚡ Performance · Core Web Vitals</p>
          {isDemo && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/25">
              Demo
            </span>
          )}
          <p className="text-xs text-slate-500">· Son 7 gün</p>
        </div>
        <span className="text-[11px] text-slate-500">{metrics.pages.length} sayfa izleniyor</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
        {/* Sol: Metrik seçici + trend */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 flex flex-col gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Metrik seç</p>
            <div className="grid grid-cols-3 gap-1">
              {(Object.keys(THRESHOLDS) as MetricKey[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setSelectedMetric(m)}
                  className={`px-2 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                    selectedMetric === m
                      ? "bg-cyan-500/20 text-cyan-200 border border-cyan-500/40"
                      : "bg-slate-800/60 text-slate-400 border border-transparent hover:text-slate-200"
                  }`}
                  title={THRESHOLDS[m].desc}
                >
                  {THRESHOLDS[m].label}
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 flex-1 flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-base font-bold text-white">{t.label}</p>
                <p className="text-[11px] text-slate-500">{t.desc}</p>
              </div>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                verdict === "good" ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                : verdict === "ni" ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                : "bg-rose-500/15 text-rose-300 border-rose-500/30"
              }`}>
                {verdict === "good" ? "İYİ" : verdict === "ni" ? "DİKKAT" : "KÖTÜ"}
              </span>
            </div>
            <TrendChart data={metrics.trend[selectedMetric]} metric={selectedMetric} />
            <div className="flex justify-between text-[10px] text-slate-500 mt-1">
              <span>7 gün önce</span>
              <span>bugün</span>
            </div>
            <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between text-[11px]">
              <span className="text-slate-400">
                İyi <span className="text-emerald-400 font-mono">≤{fmt(selectedMetric, t.good)}</span>
              </span>
              <span className="text-slate-400">
                Kötü <span className="text-rose-400 font-mono">&gt;{fmt(selectedMetric, t.poor)}</span>
              </span>
            </div>
          </div>
        </div>

        {/* Sağ: Sayfa tablosu */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-950/60 text-slate-500">
              <tr className="text-left">
                <th className="px-4 py-2.5 font-medium">Sayfa</th>
                {(Object.keys(THRESHOLDS) as MetricKey[]).map((m) => (
                  <th
                    key={m}
                    className={`px-3 py-2.5 font-medium text-right cursor-pointer hover:text-slate-300 ${
                      selectedMetric === m ? "text-cyan-300" : ""
                    }`}
                    onClick={() => setSelectedMetric(m)}
                  >
                    {THRESHOLDS[m].label}
                  </th>
                ))}
                <th className="px-3 py-2.5 font-medium text-right">N</th>
              </tr>
            </thead>
            <tbody>
              {metrics.pages.map((p) => (
                <tr key={p.url} className="border-t border-slate-800/60 hover:bg-slate-800/30">
                  <td className="px-4 py-2.5">
                    <p className="text-white font-medium">{p.page}</p>
                    <p className="text-[11px] text-slate-500 font-mono">{p.url}</p>
                  </td>
                  {(Object.keys(THRESHOLDS) as MetricKey[]).map((m) => {
                    const s = status(m, p[m]);
                    return (
                      <td key={m} className={`px-3 py-2.5 text-right font-mono tabular-nums ${STATUS_CLS[s]}`}>
                        {fmt(m, p[m])}
                      </td>
                    );
                  })}
                  <td className="px-3 py-2.5 text-right text-slate-500 font-mono tabular-nums">{p.sampleCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
