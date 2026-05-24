"use client";

import { useEffect, useState } from "react";

type VelocityPoint = { week_start: string; tc_created: number; tc_updated: number; runs_executed: number };
type TrendPoint = { date: string; total: number; passed: number; failed: number; pass_rate: number };
type OwnerStat = { owner: string; tc_count: number; automation_pct: number; suites: string[] };
type TopFailing = { tc: string; fail_count: number; run_count: number; fail_rate: number; last_run: string; last_status: string };

type Insights = {
  velocity: VelocityPoint[];
  trend: TrendPoint[];
  owners: OwnerStat[];
  top_failing: TopFailing[];
  coverage_by_priority: Record<string, number>;
  generated_at: string;
};

export default function InsightsView() {
  const [data, setData] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/qa/insights")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="py-12 text-center text-gray-400">Yükleniyor...</div>;
  if (error) return <div className="rounded border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>;
  if (!data) return null;

  return (
    <div className="space-y-8">
      <PriorityDonut counts={data.coverage_by_priority} />

      <Section title="Velocity (Son 12 Hafta)" subtitle="Haftalık TC create/update + run sayısı">
        <VelocityChart data={data.velocity} />
      </Section>

      <Section title="Pass Rate Trend (Son 30 Gün)" subtitle="Günlük başarı oranı">
        <TrendChart data={data.trend} />
      </Section>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Section title="Top Failing TCs" subtitle="En çok fail eden test case'ler">
          <TopFailingTable data={data.top_failing} />
        </Section>
        <Section title="Owner Breakdown" subtitle="Per-owner TC count + automation %">
          <OwnerTable data={data.owners} />
        </Section>
      </div>

      <footer className="border-t border-gray-100 pt-3 text-center text-xs text-gray-400">
        Generated: {data.generated_at}
      </footer>
    </div>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="rounded border border-gray-200 bg-white p-5">
      <header className="mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-700">{title}</h2>
        {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
      </header>
      {children}
    </section>
  );
}

function PriorityDonut({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  const palette = { P0: "#ef4444", P1: "#f59e0b", P2: "#3b82f6", P3: "#9ca3af" };
  let acc = 0;
  const radius = 36;
  const circ = 2 * Math.PI * radius;

  return (
    <section className="rounded border border-gray-200 bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-700">Coverage by Priority</h2>
      <div className="flex items-center gap-8">
        <svg width="100" height="100" viewBox="0 0 100 100" className="-rotate-90">
          {Object.entries(counts).map(([p, c]) => {
            const pct = c / total;
            const offset = acc * circ;
            acc += pct;
            return (
              <circle
                key={p}
                cx="50" cy="50" r={radius}
                fill="none"
                stroke={palette[p as keyof typeof palette] || "#ccc"}
                strokeWidth="14"
                strokeDasharray={`${pct * circ} ${circ}`}
                strokeDashoffset={-offset}
              />
            );
          })}
        </svg>
        <div className="grid grid-cols-2 gap-3 text-sm">
          {Object.entries(counts).map(([p, c]) => (
            <div key={p} className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded" style={{ background: palette[p as keyof typeof palette] || "#ccc" }} />
              <span className="font-mono font-semibold">{p}</span>
              <span className="tabular-nums text-gray-600">{c}</span>
              <span className="text-xs text-gray-400">({Math.round((c / total) * 100)}%)</span>
            </div>
          ))}
        </div>
        <div className="ml-auto text-right">
          <div className="text-3xl font-semibold tabular-nums">{total}</div>
          <div className="text-xs uppercase tracking-wider text-gray-500">Total TC</div>
        </div>
      </div>
    </section>
  );
}

function VelocityChart({ data }: { data: VelocityPoint[] }) {
  const max = Math.max(1, ...data.flatMap((d) => [d.tc_created, d.tc_updated, d.runs_executed]));
  const w = 60;
  const h = 120;

  return (
    <div className="overflow-x-auto">
      <div className="flex items-end gap-1 pb-1">
        {data.map((d) => (
          <div key={d.week_start} className="flex flex-col items-center" style={{ minWidth: `${w}px` }}>
            <div className="flex items-end gap-0.5" style={{ height: `${h}px` }}>
              <div title={`Created: ${d.tc_created}`} className="w-3 rounded-t bg-blue-500" style={{ height: `${(d.tc_created / max) * h}px` }} />
              <div title={`Updated: ${d.tc_updated}`} className="w-3 rounded-t bg-amber-400" style={{ height: `${(d.tc_updated / max) * h}px` }} />
              <div title={`Runs: ${d.runs_executed}`} className="w-3 rounded-t bg-green-500" style={{ height: `${(d.runs_executed / max) * h}px` }} />
            </div>
            <div className="mt-1 text-[10px] text-gray-400">
              {d.week_start.slice(5)}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-4 text-xs">
        <Legend color="bg-blue-500" label="TC created" />
        <Legend color="bg-amber-400" label="TC updated" />
        <Legend color="bg-green-500" label="Runs" />
      </div>
    </div>
  );
}

function TrendChart({ data }: { data: TrendPoint[] }) {
  if (data.length === 0) return <div className="py-8 text-center text-gray-400">Henüz koşum yok</div>;
  const w = 800;
  const h = 200;
  const padding = 30;
  const inner = { w: w - padding * 2, h: h - padding * 2 };

  const xStep = inner.w / Math.max(1, data.length - 1);
  const points = data.map((d, i) => ({
    x: padding + i * xStep,
    y: padding + (1 - d.pass_rate / 100) * inner.h,
    d,
  }));

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  return (
    <div className="overflow-x-auto">
      <svg width={w} height={h} className="block">
        {/* Y axis grid */}
        {[0, 25, 50, 75, 100].map((y) => (
          <g key={y}>
            <line x1={padding} y1={padding + (1 - y / 100) * inner.h} x2={w - padding} y2={padding + (1 - y / 100) * inner.h} stroke="#f3f4f6" strokeWidth="1" />
            <text x={padding - 4} y={padding + (1 - y / 100) * inner.h + 3} fontSize="10" fill="#9ca3af" textAnchor="end">{y}%</text>
          </g>
        ))}
        {/* Line */}
        <path d={path} fill="none" stroke="#3b82f6" strokeWidth="2" />
        {/* Points */}
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="3" fill="#3b82f6">
            <title>{p.d.date}: {p.d.pass_rate}% ({p.d.passed}/{p.d.total})</title>
          </circle>
        ))}
        {/* X axis labels (every 5th) */}
        {points.filter((_, i) => i % 5 === 0).map((p) => (
          <text key={p.d.date} x={p.x} y={h - 5} fontSize="10" fill="#9ca3af" textAnchor="middle">
            {p.d.date.slice(5)}
          </text>
        ))}
      </svg>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`inline-block h-3 w-3 rounded ${color}`} />
      <span className="text-gray-600">{label}</span>
    </span>
  );
}

function TopFailingTable({ data }: { data: TopFailing[] }) {
  if (data.length === 0) return <div className="py-6 text-center text-sm text-gray-400">✓ Hiç fail yok</div>;
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs uppercase tracking-wider text-gray-500">
        <tr>
          <th className="py-2">TC</th>
          <th className="py-2 text-right">Fail</th>
          <th className="py-2 text-right">Rate</th>
          <th className="py-2">Son durum</th>
        </tr>
      </thead>
      <tbody>
        {data.map((d) => (
          <tr key={d.tc} className="border-t border-gray-100">
            <td className="py-1.5 font-mono text-xs">{d.tc}</td>
            <td className="py-1.5 text-right tabular-nums">{d.fail_count} / {d.run_count}</td>
            <td className="py-1.5 text-right tabular-nums">
              <span className={d.fail_rate >= 30 ? "font-semibold text-red-600" : "text-amber-600"}>
                {d.fail_rate}%
              </span>
            </td>
            <td className="py-1.5">
              <span className={`rounded px-1.5 py-0.5 text-xs ${d.last_status === "fail" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"}`}>
                {d.last_status}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function OwnerTable({ data }: { data: OwnerStat[] }) {
  if (data.length === 0) return <div className="py-6 text-center text-sm text-gray-400">Owner kaydı yok</div>;
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs uppercase tracking-wider text-gray-500">
        <tr>
          <th className="py-2">Owner</th>
          <th className="py-2 text-right">TC</th>
          <th className="py-2">Auto %</th>
          <th className="py-2">Suites</th>
        </tr>
      </thead>
      <tbody>
        {data.map((o) => (
          <tr key={o.owner} className="border-t border-gray-100">
            <td className="py-1.5 font-mono text-xs">{o.owner}</td>
            <td className="py-1.5 text-right font-semibold tabular-nums">{o.tc_count}</td>
            <td className="py-1.5">
              <div className="flex items-center gap-2">
                <div className="h-2 w-16 overflow-hidden rounded bg-gray-100">
                  <div className="h-full bg-green-500" style={{ width: `${o.automation_pct}%` }} />
                </div>
                <span className="text-xs tabular-nums text-gray-500">{o.automation_pct}%</span>
              </div>
            </td>
            <td className="py-1.5 text-xs text-gray-500">
              {o.suites.slice(0, 3).join(", ")}{o.suites.length > 3 ? ` +${o.suites.length - 3}` : ""}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
