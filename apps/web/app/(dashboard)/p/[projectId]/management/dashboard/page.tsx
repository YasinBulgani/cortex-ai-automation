"use client";

import Link from "next/link";
import { useMemo, useEffect, useRef, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import {
  useExecutionSummary,
  useManagementAuditEvents,
  useManagementDefects,
  useManagementDashboardSummary,
  useManagementPlans,
  useManagementRepository,
  useManagementRequirements,
  useManagementRuns,
  useReleaseReport,
  useReleaseSignoffs,
  useCreateReleaseSignoff,
  useManagementFlakyTests,
  useReviewQueue,
  useManagementRunTrend,
  type ReleaseBlocker,
  type TestCase,
  type FlakyTestOut,
  type CaseReviewOut,
  type RunTrendPoint,
  type TestRun,
} from "@/lib/hooks/use-management";
import { cn } from "@/lib/utils";
import { QuickSetupWizard } from "../_components/QuickSetupWizard";
import { useProfile } from "@/lib/hooks/use-profile";

const REFETCH_INTERVAL = 30_000; // ms
const STALE_DAYS = 14;

function AutoRefreshBadge() {
  const [countdown, setCountdown] = useState(30);
  const [pulsing, setPulsing] = useState(false);

  useEffect(() => {
    setCountdown(30);
    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          // Trigger pulse animation briefly
          setPulsing(true);
          setTimeout(() => setPulsing(false), 600);
          return 30;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-1.5 rounded-full border border-border bg-surface-raised px-2.5 py-1 text-[10px] text-fg-muted">
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full bg-emerald-400 transition-all",
          pulsing ? "scale-125 opacity-100" : "animate-pulse opacity-70",
        )}
      />
      <span>
        {countdown === 30 ? "30s otomatik yenileniyor" : `${countdown}s sonra yenilenir`}
      </span>
    </div>
  );
}

function asText(value: unknown, fallback = "Tanimsiz") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

const STATUS_TR: Record<string, string> = {
  // test result statuses
  passed:        "Geçti",
  failed:        "Başarısız",
  blocked:       "Engellendi",
  skipped:       "Atlandı",
  not_run:       "Çalıştırılmadı",
  // run / plan / cycle statuses
  in_progress:   "Devam Ediyor",
  running:       "Çalışıyor",
  completed:     "Tamamlandı",
  not_started:   "Başlamadı",
  draft:         "Taslak",
  active:        "Aktif",
  archived:      "Arşivlendi",
  // release decision
  GO:            "GO",
  NO_GO:         "NO GO",
  PENDING:       "Beklemede",
  // priority
  P0:            "P0 — Kritik",
  P1:            "P1 — Yüksek",
  P2:            "P2 — Orta",
  P3:            "P3 — Düşük",
  // test type
  manual:        "Manuel",
  automated:     "Otomatik",
  exploratory:   "Keşif",
  // checklist item status
  ok:            "Tamam",
  warning:       "Uyarı",
  error:         "Hata",
};

function tr(value: string | undefined | null, fallback?: string): string {
  if (!value) return fallback ?? "";
  return STATUS_TR[value] ?? fallback ?? value;
}

// ─── Test Insights Panel ──────────────────────────────────────────────────────

function HorizBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="w-20 shrink-0 truncate text-right text-[10px] text-fg-muted" title={label}>{label}</span>
      <div className="relative flex-1 overflow-hidden rounded-full bg-surface-overlay h-1.5">
        <div className={cn("absolute inset-y-0 left-0 rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-6 text-right text-[10px] tabular-nums text-fg">{count}</span>
    </div>
  );
}

type TestSuiteLocal = { id: string; name: string };

function CoverageHeatmap({ cases, suites }: { cases: TestCase[]; suites: TestSuiteLocal[] }) {
  const rows = useMemo(() => {
    const suiteMap = new Map<string, TestSuiteLocal>(suites.map(s => [s.id, s]));
    const bySuite = new Map<string, TestCase[]>();

    for (const tc of cases) {
      const key = tc.suite_id ?? "__none__";
      if (!bySuite.has(key)) bySuite.set(key, []);
      bySuite.get(key)!.push(tc);
    }

    return [...bySuite.entries()]
      .map(([suiteId, tcs]) => {
        const total = tcs.length;
        const passed  = tcs.filter(t => t.last_run_status === "passed").length;
        const failed  = tcs.filter(t => t.last_run_status === "failed").length;
        const blocked = tcs.filter(t => t.last_run_status === "blocked").length;
        const notRun  = tcs.filter(t => !t.last_run_status || t.last_run_status === "not_run").length;
        const passRate = total > 0 ? Math.round((passed / total) * 100) : null;
        return {
          suiteId,
          name: suiteMap.get(suiteId)?.name ?? "Genel",
          total, passed, failed, blocked, notRun, passRate,
        };
      })
      .sort((a, b) => b.total - a.total)
      .slice(0, 10);
  }, [cases, suites]);

  if (!rows.length) return null;

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-fg">Test Kapsamı Haritası</h2>
        <div className="flex items-center gap-3 text-[10px] text-fg-subtle">
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-emerald-500/70 inline-block"/>Geçti</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-red-500/70 inline-block"/>Başarısız</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-amber-500/60 inline-block"/>Engel</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-surface-overlay border border-border inline-block"/>Çalıştırılmadı</span>
        </div>
      </div>
      <div className="space-y-2">
        {rows.map(row => (
          <div key={row.suiteId} className="flex items-center gap-3">
            <span className="w-32 shrink-0 truncate text-[11px] text-fg-muted" title={row.name}>{row.name}</span>
            <div className="flex h-5 flex-1 overflow-hidden rounded">
              {row.passed  > 0 && <div className="bg-emerald-500/70 flex items-center justify-center transition-all" style={{ width: `${(row.passed  / row.total) * 100}%` }} title={`${row.passed} geçti`}/>}
              {row.failed  > 0 && <div className="bg-red-500/70    flex items-center justify-center transition-all" style={{ width: `${(row.failed  / row.total) * 100}%` }} title={`${row.failed} başarısız`}/>}
              {row.blocked > 0 && <div className="bg-amber-500/60  flex items-center justify-center transition-all" style={{ width: `${(row.blocked / row.total) * 100}%` }} title={`${row.blocked} engel`}/>}
              {row.notRun  > 0 && <div className="bg-surface-overlay border-y border-border flex items-center justify-center transition-all" style={{ width: `${(row.notRun  / row.total) * 100}%` }} title={`${row.notRun} çalıştırılmadı`}/>}
            </div>
            <div className="flex w-28 shrink-0 items-center justify-end gap-2">
              {row.passRate !== null && (
                <span className={cn("font-mono text-[11px] font-semibold tabular-nums",
                  row.passRate >= 80 ? "text-emerald-400" :
                  row.passRate >= 50 ? "text-amber-400" : "text-red-400")}>
                  {row.passRate}%
                </span>
              )}
              <span className="text-[10px] text-fg-subtle">{row.total} case</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function TestInsightsPanel({ cases, runs }: { cases: TestCase[]; runs: TestRun[] }) {
  const typeMap = useMemo(() => {
    const m: Record<string, number> = {};
    for (const tc of cases) {
      const t = tc.type ?? "manual";
      m[t] = (m[t] ?? 0) + 1;
    }
    return m;
  }, [cases]);

  const priorityMap = useMemo(() => {
    const m: Record<string, number> = {};
    for (const tc of cases) {
      const p = tc.priority ?? "P2";
      m[p] = (m[p] ?? 0) + 1;
    }
    return m;
  }, [cases]);

  // Velocity: runs per week for last 4 weeks
  const weeklyVelocity = useMemo(() => {
    const now = Date.now();
    const weeks = [0, 0, 0, 0];
    for (const r of runs) {
      if (!r.created_at) continue;
      const age = (now - new Date(r.created_at).getTime()) / 86_400_000;
      const wi = Math.floor(age / 7);
      if (wi < 4) weeks[wi]++;
    }
    return weeks.reverse(); // oldest → newest
  }, [runs]);

  const total = cases.length;
  if (!total) return null;

  const typeOrder = ["manual", "automated", "exploratory"];
  const typeColors: Record<string, string> = {
    manual: "bg-blue-500",
    automated: "bg-emerald-500",
    exploratory: "bg-violet-500",
  };
  const typeLabels: Record<string, string> = {
    manual: "Manuel",
    automated: "Otomatik",
    exploratory: "Keşif",
  };

  const priorityOrder = ["P0", "P1", "P2", "P3"];
  const priorityColors: Record<string, string> = {
    P0: "bg-red-500",
    P1: "bg-orange-400",
    P2: "bg-amber-400",
    P3: "bg-slate-500",
  };

  const velMax = Math.max(...weeklyVelocity, 1);
  const weekLabels = ["H-3", "H-2", "H-1", "Bu Hafta"];

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {/* Type distribution */}
      <section className="rounded-xl border border-border bg-surface-raised p-4 shadow-sm">
        <p className="mb-3 text-[11px] font-semibold text-fg">Test Tipi Dağılımı</p>
        <div className="mb-3 flex h-2 w-full overflow-hidden rounded-full">
          {typeOrder.filter(t => (typeMap[t] ?? 0) > 0).map(t => (
            <div key={t} className={cn("h-full", typeColors[t] ?? "bg-slate-500")}
              style={{ width: `${((typeMap[t] ?? 0) / total) * 100}%` }}
              title={`${typeLabels[t]}: ${typeMap[t]}`}
            />
          ))}
        </div>
        <div className="space-y-1.5">
          {typeOrder.map(t => (
            <HorizBar key={t} label={typeLabels[t] ?? t} count={typeMap[t] ?? 0} total={total} color={typeColors[t] ?? "bg-slate-500"} />
          ))}
        </div>
        <p className="mt-2 text-[10px] text-fg-subtle">{total} toplam case</p>
      </section>

      {/* Priority breakdown */}
      <section className="rounded-xl border border-border bg-surface-raised p-4 shadow-sm">
        <p className="mb-3 text-[11px] font-semibold text-fg">Öncelik Dağılımı</p>
        <div className="mb-3 flex h-2 w-full overflow-hidden rounded-full">
          {priorityOrder.filter(p => (priorityMap[p] ?? 0) > 0).map(p => (
            <div key={p} className={cn("h-full", priorityColors[p] ?? "bg-slate-500")}
              style={{ width: `${((priorityMap[p] ?? 0) / total) * 100}%` }}
              title={`${p}: ${priorityMap[p]}`}
            />
          ))}
        </div>
        <div className="space-y-1.5">
          {priorityOrder.map(p => (
            <HorizBar key={p} label={p} count={priorityMap[p] ?? 0} total={total} color={priorityColors[p] ?? "bg-slate-500"} />
          ))}
        </div>
        <p className="mt-2 text-[10px] text-fg-subtle">
          {priorityMap["P0"] ? <span className="text-red-400">{priorityMap["P0"]} kritik case — </span> : null}
          risk değerlendirmesi
        </p>
      </section>

      {/* Weekly velocity */}
      <section className="rounded-xl border border-border bg-surface-raised p-4 shadow-sm">
        <p className="mb-3 text-[11px] font-semibold text-fg">Haftalık Run Hızı</p>
        <div className="flex h-24 items-end gap-1.5">
          {weeklyVelocity.map((v, i) => (
            <div key={i} className="flex flex-1 flex-col items-center gap-1">
              <span className="text-[9px] tabular-nums text-fg-muted">{v}</span>
              <div
                className={cn("w-full rounded-t", i === 3 ? "bg-brand" : "bg-blue-500/40")}
                style={{ height: `${(v / velMax) * 72}px` }}
              />
              <span className="text-[9px] text-fg-subtle">{weekLabels[i]}</span>
            </div>
          ))}
        </div>
        <p className="mt-2 text-[10px] text-fg-subtle">
          Ort. {Math.round(weeklyVelocity.reduce((a, b) => a + b, 0) / 4 * 10) / 10} run/hafta
        </p>
      </section>
    </div>
  );
}

function StatCard({ label, value, note, tone = "neutral", href }: {
  label: string;
  value: string | number;
  note: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  href?: string;
}) {
  const toneClass = {
    neutral: "border-border bg-surface-raised",
    success: "border-emerald-500/20 bg-emerald-500/5",
    warning: "border-amber-500/20 bg-amber-500/5",
    danger: "border-red-500/20 bg-red-500/5",
    info: "border-blue-500/20 bg-blue-500/5",
  }[tone];

  const inner = (
    <>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-normal text-fg">{value}</p>
      <p className="mt-1 text-[11px] text-fg-muted">{note}</p>
    </>
  );

  if (href) {
    return (
      <Link href={href} className={cn("block rounded-xl border p-4 shadow-sm transition-colors hover:border-brand/40 hover:brightness-105", toneClass)}>
        {inner}
      </Link>
    );
  }
  return <section className={cn("rounded-xl border p-4 shadow-sm", toneClass)}>{inner}</section>;
}

// ─── Project Health Widget ────────────────────────────────────────────────────

interface HealthCriteria {
  label: string;
  passed: boolean;
  note: string;
}

function ProjectHealthWidget({
  passRatePct,
  coveragePct,
  criticalDefects,
  activeRuns,
}: {
  passRatePct: number;
  coveragePct: number;
  criticalDefects: number;
  activeRuns: number;
}) {
  const criteria: HealthCriteria[] = [
    {
      label: "Test Geçme Oranı",
      passed: passRatePct >= 85,
      note: passRatePct >= 85 ? `${passRatePct}% (hedef 85%)` : `${passRatePct}% (hedef 85%)`,
    },
    {
      label: "Kapsam",
      passed: coveragePct >= 70,
      note: coveragePct >= 70 ? `${coveragePct}% ✓` : `${coveragePct}% (hedef 70%)`,
    },
    {
      label: "Kritik Defect",
      passed: criticalDefects === 0,
      note: criticalDefects === 0 ? "Kritik defect yok" : `${criticalDefects} kritik defect`,
    },
    {
      label: "Aktif Koşum",
      passed: activeRuns > 0,
      note: activeRuns > 0 ? `${activeRuns} aktif koşum var` : "Aktif koşum yok",
    },
  ];

  const score = criteria.filter(c => c.passed).length * 25;
  const barColor =
    score >= 76 ? "bg-emerald-500" :
    score >= 51 ? "bg-amber-500"   : "bg-red-500";
  const scoreColor =
    score >= 76 ? "text-emerald-400" :
    score >= 51 ? "text-amber-400"   : "text-red-400";
  const labelColor =
    score >= 76 ? "Mükemmel" :
    score >= 51 ? "Orta"     : "Kritik";
  const filledBlocks = Math.round(score / 10);

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-fg">Proje Sağlığı</h2>
        <span className={cn("text-[11px] font-semibold", scoreColor)}>{labelColor}</span>
      </div>

      {/* Score bar */}
      <div className="mb-4 flex items-center gap-3">
        <div className="flex gap-0.5">
          {Array.from({ length: 10 }).map((_, i) => (
            <div
              key={i}
              className={cn(
                "h-2.5 w-5 rounded-sm transition-colors",
                i < filledBlocks ? barColor : "bg-surface-accent",
              )}
            />
          ))}
        </div>
        <span className={cn("text-[13px] font-bold tabular-nums", scoreColor)}>
          {score}/100
        </span>
      </div>

      {/* Criteria grid */}
      <div className="grid gap-2 sm:grid-cols-2">
        {criteria.map(c => (
          <div
            key={c.label}
            className={cn(
              "flex items-center gap-2.5 rounded-lg border px-3 py-2",
              c.passed
                ? "border-emerald-500/20 bg-emerald-500/5"
                : "border-red-500/20 bg-red-500/5",
            )}
          >
            <span className={cn("flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[9px] font-bold",
              c.passed ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
            )}>
              {c.passed ? "✓" : "✗"}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-medium text-fg">{c.label}</p>
              <p className={cn("text-[10px]", c.passed ? "text-emerald-400/80" : "text-red-400/80")}>{c.note}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Defect Trend Mini Chart ─────────────────────────────────────────────────

function DefectTrendMini({ defects }: { defects: import("@/lib/hooks/use-management").DefectLink[] }) {
  const weeks = 8;
  const now = Date.now();
  const MS_WEEK = 7 * 24 * 60 * 60 * 1000;

  const buckets: { label: string; open: number; closed: number }[] = Array.from({ length: weeks }, (_, i) => {
    const weekAgo = now - (weeks - 1 - i) * MS_WEEK;
    const d = new Date(weekAgo);
    const label = `${d.getDate()}/${d.getMonth() + 1}`;
    const windowStart = weekAgo - MS_WEEK;
    const windowEnd = weekAgo;
    let open = 0, closed = 0;
    for (const def of defects) {
      const t = Date.parse(def.created_at ?? "");
      if (isNaN(t) || t < windowStart || t >= windowEnd) continue;
      const isClosed = ["closed","done","resolved","fixed","verified"].includes((def.status ?? "").toLowerCase());
      if (isClosed) closed++; else open++;
    }
    return { label, open, closed };
  });

  const maxVal = Math.max(1, ...buckets.map(b => b.open + b.closed));

  if (defects.length === 0) {
    return <p className="text-[12px] text-fg-muted py-4 text-center">Henüz defect verisi yok.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-end gap-1 h-20">
        {buckets.map((b, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-0.5 group">
            <div className="relative w-full flex flex-col-reverse" style={{ height: "64px" }}>
              <div
                className="w-full rounded-t bg-emerald-500/60 transition-all"
                style={{ height: `${(b.closed / maxVal) * 64}px` }}
                title={`Kapalı: ${b.closed}`}
              />
              <div
                className="w-full bg-red-500/60"
                style={{ height: `${(b.open / maxVal) * 64}px` }}
                title={`Açık: ${b.open}`}
              />
            </div>
            <span className="text-[9px] text-fg-disabled">{b.label}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3 text-[10px] text-fg-muted">
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-red-500/60"/> Açık</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-emerald-500/60"/> Kapalı</span>
      </div>
    </div>
  );
}

// ─── Run Trend Chart ─────────────────────────────────────────────────────────

function RunTrendChart({ points }: { points: RunTrendPoint[] }) {
  if (points.length < 2) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-[12px] text-fg-muted">Trend için en az 2 run gerekli.</p>
      </div>
    );
  }

  const WIDTH = 600;
  const HEIGHT = 120;
  const PAD_X = 32;
  const PAD_Y = 12;
  const chartW = WIDTH - PAD_X * 2;
  const chartH = HEIGHT - PAD_Y * 2;

  const coords = points.map((p, i) => ({
    x: PAD_X + (i / (points.length - 1)) * chartW,
    y: PAD_Y + chartH - (p.pass_rate_pct / 100) * chartH,
    pct: p.pass_rate_pct,
    name: p.name,
    passed: p.passed,
    failed: p.failed,
    total: p.total_cases,
    date: p.created_at,
  }));

  const polylinePts = coords.map(c => `${c.x},${c.y}`).join(" ");
  const areaPath =
    `M ${coords[0].x},${PAD_Y + chartH} ` +
    coords.map(c => `L ${c.x},${c.y}`).join(" ") +
    ` L ${coords[coords.length - 1].x},${PAD_Y + chartH} Z`;

  const avg = Math.round(points.reduce((s, p) => s + p.pass_rate_pct, 0) / points.length);
  const last = coords[coords.length - 1];
  const trend = points.length >= 2 ? points[points.length - 1].pass_rate_pct - points[0].pass_rate_pct : 0;
  const trendColor = trend > 0 ? "text-emerald-400" : trend < 0 ? "text-red-400" : "text-fg-muted";

  return (
    <div>
      <div className="mb-3 flex items-center gap-4 text-[11px]">
        <div>
          <span className="text-fg-subtle">Ort. Geçme Oranı</span>
          <span className="ml-1.5 font-semibold text-fg">{avg}%</span>
        </div>
        <div>
          <span className="text-fg-subtle">Son Run</span>
          <span className={cn("ml-1.5 font-semibold", trendColor)}>
            {last.pct}% {trend !== 0 && `(${trend > 0 ? "+" : ""}${trend.toFixed(0)}%)`}
          </span>
        </div>
        <div>
          <span className="text-fg-subtle">{points.length} run</span>
        </div>
      </div>

      <div className="relative w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="w-full"
          style={{ height: 120 }}
        >
          <defs>
            <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* 85% target line */}
          {(() => {
            const yTarget = PAD_Y + chartH - (85 / 100) * chartH;
            return (
              <>
                <line x1={PAD_X} y1={yTarget} x2={WIDTH - PAD_X} y2={yTarget}
                  stroke="#f59e0b" strokeWidth="0.75" strokeDasharray="4 3" opacity="0.4" />
                <text x={WIDTH - PAD_X + 2} y={yTarget + 3} fontSize="8" fill="#f59e0b" opacity="0.7">85%</text>
              </>
            );
          })()}

          {/* Area fill */}
          <path d={areaPath} fill="url(#trendGrad)" />

          {/* Line */}
          <polyline
            points={polylinePts}
            fill="none"
            stroke="#10b981"
            strokeWidth="1.75"
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* Data points with tooltips */}
          {coords.map((c, i) => {
            const dotColor = c.pct >= 85 ? "#10b981" : c.pct >= 60 ? "#f59e0b" : "#ef4444";
            return (
              <g key={i}>
                <title>{c.name}: {c.pct}% ({c.passed}P/{c.failed}F/{c.total}T)</title>
                <circle cx={c.x} cy={c.y} r="3.5" fill={dotColor} stroke="#1a2035" strokeWidth="1.5" />
              </g>
            );
          })}

          {/* Y-axis labels */}
          {[0, 50, 100].map(pct => {
            const y = PAD_Y + chartH - (pct / 100) * chartH;
            return (
              <text key={pct} x={PAD_X - 4} y={y + 3} fontSize="8" fill="#64748b" textAnchor="end">
                {pct}%
              </text>
            );
          })}
        </svg>
      </div>

      {/* X-axis labels — last 5 runs */}
      <div className="mt-1 flex justify-between px-8 text-[10px] text-fg-subtle">
        {points.length > 0 && (
          <>
            <span className="truncate max-w-[100px]">{points[0].name}</span>
            {points.length > 2 && (
              <span className="truncate max-w-[100px]">{points[Math.floor(points.length / 2)].name}</span>
            )}
            <span className="truncate max-w-[100px]">{points[points.length - 1].name}</span>
          </>
        )}
      </div>
    </div>
  );
}

function MiniBar({ label, value, max, tone }: { label: string; value: number; max: number; tone: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-3 text-[12px]">
        <span className="truncate text-fg-muted">{label}</span>
        <span className="font-mono text-fg-subtle">{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-overlay">
        <div className={cn("h-full rounded-full", tone)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function EmptyState({ projectId }: { projectId: string }) {
  return (
    <section className="rounded-xl border border-dashed border-border bg-surface-raised p-8 text-center">
      <p className="text-[14px] font-semibold text-fg">Henüz veri bulunmuyor</p>
      <p className="mx-auto mt-2 max-w-md text-[12px] text-fg-muted">
        Repository üzerinden ilk test suite'inizi ve manuel case'lerinizi ekleyerek Management dashboard'unu doldurmaya baslayin.
      </p>
      <div className="mt-4 flex justify-center gap-2">
        <Link
          href={`/p/${projectId}/management/repository`}
          className="rounded-lg bg-brand px-3 py-2 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105"
        >
          Repository'ye git
        </Link>
        <Link
          href={`/p/${projectId}/management/cases/new`}
          className="rounded-lg border border-border bg-surface-overlay px-3 py-2 text-[12px] font-semibold text-fg-muted transition-colors hover:text-fg"
        >
          Case ekle
        </Link>
      </div>
    </section>
  );
}

// ─── Setup Tracker Widget ─────────────────────────────────────────────────────

interface SetupCriterion {
  label: string;
  done: boolean;
  href: string;
}

function SetupTrackerWidget({
  projectId,
  totalCases,
  plansCount,
  runsCount,
  hasCompletedRun,
  requirementsCount,
}: {
  projectId: string;
  totalCases: number;
  plansCount: number;
  runsCount: number;
  hasCompletedRun: boolean;
  requirementsCount: number;
}) {
  const criteria: SetupCriterion[] = [
    {
      label: "İlk test senaryosu oluşturuldu",
      done: totalCases > 0,
      href: `/p/${projectId}/management/cases/new`,
    },
    {
      label: "İlk test planı var",
      done: plansCount > 0,
      href: `/p/${projectId}/management/plans`,
    },
    {
      label: "İlk test koşumu çalıştırıldı",
      done: runsCount > 0 && hasCompletedRun,
      href: `/p/${projectId}/management/runs`,
    },
    {
      label: "Gereksinim bağlantısı eklendi",
      done: requirementsCount > 0,
      href: `/p/${projectId}/management/requirements`,
    },
  ];

  const doneCount = criteria.filter(c => c.done).length;
  const pct = Math.round((doneCount / criteria.length) * 100);
  const allDone = doneCount === criteria.length;

  if (allDone) {
    return (
      <section className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-xl">🎉</span>
          <div>
            <p className="text-[14px] font-semibold text-emerald-400">Hazırsınız!</p>
            <p className="text-[12px] text-fg-muted">Tüm kurulum adımları tamamlandı.</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-fg">Kurulum Durumu</h2>
        <span className="text-[12px] font-semibold text-fg-muted">{pct}% Tamamlandı</span>
      </div>

      {/* Progress bar */}
      <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-surface-overlay">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="space-y-2">
        {criteria.map(c => (
          <div key={c.label} className="flex items-center gap-3">
            <span
              className={cn(
                "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                c.done
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-surface-overlay text-fg-subtle",
              )}
            >
              {c.done ? "✓" : "○"}
            </span>
            {c.done ? (
              <span className="text-[12px] text-fg-muted line-through">{c.label}</span>
            ) : (
              <Link href={c.href} className="text-[12px] text-fg hover:text-brand transition-colors">
                {c.label}
              </Link>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Blockers Widget ──────────────────────────────────────────────────────────

function BlockersWidget({ blockers, projectId }: { blockers: ReleaseBlocker[]; projectId: string }) {
  if (!blockers.length) {
    return (
      <section className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5 shadow-sm">
        <h2 className="mb-2 text-[14px] font-semibold text-fg">Release Blocker'lar</h2>
        <p className="text-[12px] text-emerald-400">Aktif blocker bulunmuyor — release hazir.</p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-fg">Release Blocker'lar</h2>
        <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-[11px] font-semibold text-red-400">
          {blockers.length} blocker
        </span>
      </div>
      <div className="space-y-2">
        {blockers.map(b => (
          <div key={b.label} className="rounded-lg border border-red-500/20 bg-surface-overlay px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[12px] font-medium text-fg">{b.label}</p>
              <span className="shrink-0 rounded bg-red-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-red-400 tabular-nums">
                {b.value}
              </span>
            </div>
            {b.detail && <p className="mt-0.5 text-[11px] text-fg-subtle">{b.detail}</p>}
          </div>
        ))}
      </div>
      <div className="mt-3">
        <Link
          href={`/p/${projectId}/management/defects`}
          className="text-[11px] text-brand hover:underline"
        >
          Defect listesine git →
        </Link>
      </div>
    </section>
  );
}

// ─── Release Signoff Widget ───────────────────────────────────────────────────

function ReleaseSignoffWidget({
  mpid,
  projectId,
  decision,
  qualitySnapshot,
}: {
  mpid: string;
  projectId: string;
  decision: string;
  qualitySnapshot?: Record<string, unknown>;
}) {
  const signoffsQ = useReleaseSignoffs(mpid);
  const createSignoff = useCreateReleaseSignoff(mpid);
  const [showForm, setShowForm] = useState(false);
  const [role, setRole] = useState("QA Lead");
  const [comment, setComment] = useState("");
  const [approvalDecision, setApprovalDecision] = useState<"approved" | "rejected">("approved");

  const latestSignoff = (signoffsQ.data ?? []).sort(
    (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
  )[0];

  const decisionColor =
    decision === "GO"
      ? "text-emerald-400"
      : decision === "NO_GO"
      ? "text-red-400"
      : "text-amber-400";

  function handleSubmit() {
    void createSignoff.mutateAsync({
      release_name: undefined,
      role,
      decision: approvalDecision,
      comment: comment.trim() || undefined,
      report_snapshot: {
        ...(qualitySnapshot ?? {}),
        signed_at: new Date().toISOString(),
      },
    }).then(() => {
      setShowForm(false);
      setComment("");
    });
  }

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[14px] font-semibold text-fg">Release Signoff</h2>
        <span className={cn("text-[12px] font-semibold", decisionColor)}>
          {tr(decision, "Beklemede")}
        </span>
      </div>

      {latestSignoff && (
        <div className="mb-3 rounded-lg border border-border bg-surface-overlay px-3 py-2">
          <p className="text-[12px] font-medium text-fg">
            {latestSignoff.decision === "approved" ? "Onaylandi" : "Reddedildi"} —{" "}
            {latestSignoff.role ?? "Bilinmeyen Rol"}
          </p>
          {latestSignoff.comment && (
            <p className="mt-0.5 text-[11px] text-fg-muted">{latestSignoff.comment}</p>
          )}
          <p className="mt-0.5 text-[10px] text-fg-subtle tabular-nums">
            {new Date(latestSignoff.signed_at).toLocaleDateString("tr-TR", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })}
          </p>
        </div>
      )}

      {!signoffsQ.data?.length && (
        <p className="mb-3 text-[12px] text-fg-muted">Henuz onay verilmedi.</p>
      )}

      {!showForm ? (
        <button
          onClick={() => setShowForm(true)}
          className="w-full rounded-lg bg-brand px-3 py-2 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105"
        >
          Onayla / Reddet
        </button>
      ) : (
        <div className="space-y-2">
          <div className="flex gap-2">
            <button
              onClick={() => setApprovalDecision("approved")}
              className={cn(
                "flex-1 rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors",
                approvalDecision === "approved"
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                  : "border-border bg-surface-overlay text-fg-muted",
              )}
            >
              Onayla
            </button>
            <button
              onClick={() => setApprovalDecision("rejected")}
              className={cn(
                "flex-1 rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors",
                approvalDecision === "rejected"
                  ? "border-red-500/40 bg-red-500/10 text-red-400"
                  : "border-border bg-surface-overlay text-fg-muted",
              )}
            >
              Reddet
            </button>
          </div>
          <input
            value={role}
            onChange={e => setRole(e.target.value)}
            placeholder="Rol (QA Lead, PM, ...)"
            className="w-full rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[12px] text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-1 focus:ring-brand"
          />
          <textarea
            value={comment}
            onChange={e => setComment(e.target.value)}
            placeholder="Yorum (opsiyonel)"
            rows={2}
            className="w-full resize-none rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[12px] text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-1 focus:ring-brand"
          />
          <div className="flex gap-2">
            <button
              onClick={handleSubmit}
              disabled={createSignoff.isPending}
              className="flex-1 rounded-lg bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg disabled:opacity-50"
            >
              {createSignoff.isPending ? "Gonderiliyor..." : "Gonder"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[12px] text-fg-muted"
            >
              Iptal
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

// ─── Stale Tests Widget ───────────────────────────────────────────────────────

function StaleTestsWidget({ stale, total, projectId }: { stale: TestCase[]; total: number; projectId: string }) {
  if (stale.length === 0) {
    return (
      <section className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-500/15 text-[11px]">🕐</span>
          <h2 className="text-[13px] font-semibold text-fg">Eski Test Verileri</h2>
        </div>
        <p className="text-[12px] text-emerald-400">Tüm testler güncel — son {STALE_DAYS} gün içinde çalıştırılmış.</p>
      </section>
    );
  }

  const PRIO_COLOR: Record<string, string> = {
    P0: "text-red-400",
    P1: "text-orange-400",
    P2: "text-amber-400",
    P3: "text-slate-400",
  };

  return (
    <section className="rounded-xl border border-orange-500/20 bg-orange-500/5 p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-orange-500/15 text-[11px]">🕐</span>
          <h2 className="text-[13px] font-semibold text-fg">Eski Test Verileri</h2>
        </div>
        <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-2 py-0.5 text-[10px] font-medium text-orange-400">
          {total} test
        </span>
      </div>
      <p className="mb-3 text-[11px] text-fg-muted">
        Son {STALE_DAYS} günde çalıştırılmamış veya hiç koşulmamış test case'ler. Kapsam boşluğu riski.
      </p>
      <div className="space-y-1.5">
        {stale.map(tc => {
          const daysSince = tc.last_run_at
            ? Math.floor((Date.now() - new Date(tc.last_run_at).getTime()) / 86_400_000)
            : null;
          const neverRun = daysSince === null;
          return (
            <Link
              key={tc.id}
              href={`/p/${projectId}/management/cases/${tc.id}`}
              className="flex items-center gap-3 rounded-lg border border-border bg-surface-overlay px-3 py-2 hover:border-orange-500/30 transition-colors"
            >
              <span className={cn("shrink-0 text-[10px] font-bold tabular-nums w-6", PRIO_COLOR[tc.priority] ?? "text-fg-subtle")}>
                {tc.priority}
              </span>
              <span className="shrink-0 font-mono text-[9px] text-fg-subtle">{tc.case_key}</span>
              <span className="flex-1 min-w-0 truncate text-[12px] text-fg">{tc.title}</span>
              <span className={cn("shrink-0 text-[10px] tabular-nums", neverRun ? "text-orange-400 font-medium" : "text-fg-muted")}>
                {neverRun ? "Hiç koşulmadı" : `${daysSince}g önce`}
              </span>
            </Link>
          );
        })}
      </div>
      {total > stale.length && (
        <p className="mt-3 text-[11px] text-fg-subtle">
          + {total - stale.length} daha —{" "}
          <Link href={`/p/${projectId}/management/repository`} className="text-brand hover:underline">
            tümünü gör
          </Link>
        </p>
      )}
    </section>
  );
}

export default function ManagementDashboardPage() {
  const router = useRouter();
  const rawProjectId = useRouteParam("projectId");

  useEffect(() => {
    if (!rawProjectId) {
      router.replace("/projects");
    }
  }, [rawProjectId, router]);

  const projectId = rawProjectId ?? "";
  const mpid = useManagementProjectId(rawProjectId || undefined);

  if (!rawProjectId) return null;

  const summaryFast = useManagementDashboardSummary(mpid || undefined);

  const repoQ = useManagementRepository(mpid || undefined);
  const runsQ = useManagementRuns(mpid || undefined);
  const summaryQ = useExecutionSummary(mpid || undefined);
  const defectsQ = useManagementDefects(mpid || undefined);
  const requirementsQ = useManagementRequirements(mpid || undefined);
  const releaseQ = useReleaseReport(mpid || undefined);
  const auditQ = useManagementAuditEvents(mpid || undefined, 10);
  const plansQ = useManagementPlans(mpid || undefined);
  const flakyQ = useManagementFlakyTests(mpid || undefined, { threshold: 0.2, minRuns: 3, limit: 10 });
  const reviewQ = useReviewQueue(mpid || undefined, "pending");
  const trendQ  = useManagementRunTrend(mpid || undefined);

  const { data: membersData } = useQuery({
    queryKey: ["management", "members", projectId],
    queryFn: () =>
      apiFetch<Array<{ user_id: string; email: string; full_name?: string }>>(
        `/api/v1/organizations/projects/${projectId}/members`
      ).then(d => (Array.isArray(d) ? d : [])),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
  const userIdMap = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const m of membersData ?? []) {
      map[m.user_id] = m.full_name?.trim() || m.email;
    }
    return map;
  }, [membersData]);

  // Store latest query refs so the interval closure never goes stale without re-creating the interval
  const queryRefs = useRef({ summaryFast, repoQ, runsQ, summaryQ, defectsQ, requirementsQ, releaseQ, auditQ, plansQ, trendQ });
  queryRefs.current = { summaryFast, repoQ, runsQ, summaryQ, defectsQ, requirementsQ, releaseQ, auditQ, plansQ, trendQ };

  const refreshAll = useCallback(() => {
    const q = queryRefs.current;
    void q.summaryFast.refetch().catch(console.error);
    void q.repoQ.refetch().catch(console.error);
    void q.runsQ.refetch().catch(console.error);
    void q.summaryQ.refetch().catch(console.error);
    void q.defectsQ.refetch().catch(console.error);
    void q.requirementsQ.refetch().catch(console.error);
    void q.releaseQ.refetch().catch(console.error);
    void q.auditQ.refetch().catch(console.error);
    void q.plansQ.refetch().catch(console.error);
    void q.trendQ.refetch().catch(console.error);
  }, []); // stable — reads latest via ref

  // Auto-refetch every 30s
  useEffect(() => {
    if (!mpid) return;
    const id = setInterval(refreshAll, REFETCH_INTERVAL);
    return () => clearInterval(id);
  }, [mpid, refreshAll]);

  const cases = useMemo(() => (repoQ.data?.cases ?? []).filter(tc => !tc.archived), [repoQ.data]);
  const runs = runsQ.data ?? [];
  const defects = defectsQ.data ?? [];
  const requirements = requirementsQ.data ?? [];
  const summary = summaryQ.data;
  const release = releaseQ.data;
  const blockers = release?.blockers ?? [];

  // Use the fast aggregated endpoint when available, fall back to client-side computation
  const activeRuns = summaryFast.data?.active_runs ?? runs.filter(run => ["running", "in_progress", "active"].includes(run.status)).length;
  const failedCases = summaryFast.data?.failed_cases ?? cases.filter(tc => tc.last_run_status === "failed").length;
  const blockedCases = summaryFast.data?.blocked_cases ?? cases.filter(tc => tc.last_run_status === "blocked").length;
  const notRunCases = summaryFast.data?.not_run_cases ?? cases.filter(tc => !tc.last_run_status || tc.last_run_status === "not_run").length;
  const criticalDefects = summaryFast.data?.critical_defects ?? defects.filter(d => ["critical", "blocker", "P0"].includes(d.severity)).length;
  const coveragePct = summaryFast.data?.coverage_pct ?? (requirements.length
    ? Math.round((requirements.filter(r => r.coverage_status === "covered").length / requirements.length) * 100)
    : release?.requirement_coverage_pct ?? 0);
  const totalCases = summaryFast.data?.total_cases ?? cases.length;
  const suiteCount = summaryFast.data?.suite_count ?? (repoQ.data?.suites.length ?? 0);
  const folderCount = summaryFast.data?.folder_count ?? (repoQ.data?.folders.length ?? 0);

  const profile = useProfile();
  const myUserId = profile.data?.id ?? "";

  const myCases = useMemo(() =>
    myUserId
      ? cases.filter(tc => tc.owner_id === myUserId && !tc.archived).slice(0, 8)
      : [],
    [cases, myUserId],
  );

  const myOpenDefects = useMemo(() =>
    myUserId
      ? defects.filter(d => d.assignee_id === myUserId && !["closed","done","resolved","fixed","verified"].includes(d.status.toLowerCase())).slice(0, 5)
      : [],
    [defects, myUserId],
  );

  const pendingRetestCount = useMemo(() =>
    defects.filter(d =>
      ["resolved", "fixed"].includes(d.status.toLowerCase()) &&
      (!d.retest_status || d.retest_status === "pending")
    ).length,
    [defects],
  );

  const staleTestsAll = useMemo(() => {
    const now = Date.now();
    const staleMs = STALE_DAYS * 24 * 60 * 60 * 1000;
    const PRIO: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 };
    return cases
      .filter(tc => {
        if (tc.last_run_at) return now - new Date(tc.last_run_at).getTime() > staleMs;
        // Never run — only flag if created before STALE_DAYS
        return now - new Date(tc.created_at).getTime() > staleMs;
      })
      .sort((a, b) => (PRIO[a.priority] ?? 9) - (PRIO[b.priority] ?? 9));
  }, [cases]);

  const staleTests = staleTestsAll.slice(0, 8);

  const latestCases = [...cases]
    .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
    .slice(0, 5);
  const latestRuns = [...runs]
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .slice(0, 5);

  const workload = useMemo(() => {
    const byOwner = new Map<string, number>();
    cases.forEach(tc => {
      const rawId = tc.owner_id ?? "";
      const displayName = rawId
        ? (userIdMap[rawId] ?? `…${rawId.slice(-8)}`)
        : "Atanmamış";
      byOwner.set(displayName, (byOwner.get(displayName) ?? 0) + 1);
    });
    return [...byOwner.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [cases, userIdMap]);

  const moduleDistribution = useMemo(() => {
    const byModule = new Map<string, number>();
    cases.forEach((tc: TestCase) => {
      const moduleName = asText(tc.custom_fields?.module ?? tc.custom_fields?.module_name ?? tc.suite_id, "Genel");
      byModule.set(moduleName, (byModule.get(moduleName) ?? 0) + 1);
    });
    return [...byModule.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [cases]);

  // If the fast summary endpoint already returned data, skip showing the skeleton
  // Only treat as loading when there is no error — errors must not cause infinite loading
  const hasError =
    summaryFast.isError ||
    repoQ.isError ||
    runsQ.isError ||
    summaryQ.isError ||
    defectsQ.isError ||
    requirementsQ.isError ||
    releaseQ.isError ||
    auditQ.isError ||
    plansQ.isError;

  const isLoading = summaryFast.data
    ? false
    : !hasError && (repoQ.isLoading || runsQ.isLoading || summaryQ.isLoading);

  const hasData = totalCases > 0 || runs.length > 0 || defects.length > 0 || requirements.length > 0;

  // Error fallback — show only when there is no cached data at all
  if (hasError && !summaryFast.data && !repoQ.data) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-sm text-fg-subtle">Veriler yüklenirken bir hata oluştu.</p>
        <button
          onClick={refreshAll}
          className="rounded-lg bg-brand px-4 py-2 text-sm text-brand-fg"
        >
          Tekrar Dene
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-full space-y-5 bg-surface-base px-6 py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Neurex Management</p>
          <h1 className="mt-1 text-[20px] font-semibold tracking-normal text-fg">Dashboard</h1>
          <p className="mt-1 text-[12px] text-fg-muted">Manuel test kapsamı, run sagligi, defect riski ve release hazirligi.</p>
        </div>
        <div className="flex items-center gap-2">
          <AutoRefreshBadge />
          <Link href={`/p/${projectId}/management/repository`} className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-[12px] font-semibold text-fg-muted hover:text-fg">
            Repository
          </Link>
          <Link href={`/p/${projectId}/management/runs`} className="rounded-lg bg-brand px-3 py-2 text-[12px] font-semibold text-brand-fg shadow-sm hover:brightness-105">
            Run baslat
          </Link>
        </div>
      </div>

      {isLoading && !hasError ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-28 animate-pulse rounded-xl border border-border bg-surface-raised" />)}
        </div>
      ) : !hasData ? (
        mpid ? <QuickSetupWizard projectId={projectId} mpid={mpid} /> : <EmptyState projectId={projectId} />
      ) : (
        <>
          <div className="grid gap-5 xl:grid-cols-2">
            <ProjectHealthWidget
              passRatePct={summaryFast.data?.pass_rate_pct ?? summary?.pass_rate_pct ?? release?.pass_rate_pct ?? 0}
              coveragePct={coveragePct}
              criticalDefects={criticalDefects}
              activeRuns={activeRuns}
            />
            <SetupTrackerWidget
              projectId={projectId}
              totalCases={totalCases}
              plansCount={plansQ.data?.length ?? 0}
              runsCount={runs.length}
              hasCompletedRun={runs.some(r => r.status === "completed")}
              requirementsCount={requirements.length}
            />
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Toplam manuel case" value={totalCases} note={`${suiteCount} suite, ${folderCount} klasor`} href={`/p/${projectId}/management/repository`} />
            <StatCard label="Aktif koşum" value={activeRuns} note={`${runs.length} toplam koşum`} tone="info" href={`/p/${projectId}/management/runs`} />
            <StatCard label="Geçme oranı" value={`${summaryFast.data?.pass_rate_pct ?? summary?.pass_rate_pct ?? release?.pass_rate_pct ?? 0}%`} note={`${summary?.passed ?? 0} geçti`} tone="success" href={`/p/${projectId}/management/reports`} />
            <StatCard label="Başarısız case" value={failedCases} note="Acil triage bekleyen case" tone="danger" href={`/p/${projectId}/management/repository`} />
            <StatCard label="Engellenen case" value={blockedCases} note="Ortam veya veri engeli" tone="warning" href={`/p/${projectId}/management/repository`} />
            <StatCard label="Çalıştırılmayan case" value={notRunCases} note="Kapsama alınmış ama çalıştırılmamış" href={`/p/${projectId}/management/repository`} />
            <StatCard label="Kritik defect" value={criticalDefects} note={`${defects.length} toplam defect`} tone={criticalDefects ? "danger" : "success"} href={`/p/${projectId}/management/defects`} />
            <StatCard label="Retest Bekliyor" value={pendingRetestCount} note="Çözüldü, onay bekliyor" tone={pendingRetestCount > 0 ? "warning" : "success"} href={`/p/${projectId}/management/defects`} />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <BlockersWidget blockers={blockers} projectId={projectId} />
            {mpid && (
              <ReleaseSignoffWidget
                mpid={mpid}
                projectId={projectId}
                decision={release?.decision ?? "PENDING"}
                qualitySnapshot={{
                  pass_rate_pct: summaryFast.data?.pass_rate_pct ?? null,
                  failed_cases: failedCases,
                  critical_defects: criticalDefects,
                  coverage_pct: coveragePct,
                  active_runs: activeRuns,
                  total_cases: summaryFast.data?.total_cases ?? cases.length,
                }}
              />
            )}
          </div>

          {/* ── Trend Charts Row ─────────────────────────────────────────────────── */}
          <div className="grid gap-5 lg:grid-cols-2">
            {((trendQ.data && trendQ.data.length >= 2) || trendQ.isLoading) && (
              <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h2 className="text-[14px] font-semibold text-fg">Test Koşum Trendi</h2>
                    <p className="mt-0.5 text-[11px] text-fg-muted">Son koşumlarda geçme oranı</p>
                  </div>
                  <Link href={`/p/${projectId}/management/runs`}
                    className="text-[11px] text-brand hover:underline">
                    Tüm koşumlar →
                  </Link>
                </div>
                {trendQ.isLoading ? (
                  <div className="h-32 animate-pulse rounded-lg bg-surface-overlay" />
                ) : (
                  <RunTrendChart points={trendQ.data ?? []} />
                )}
              </section>
            )}
            {(!defectsQ.isLoading || defects.length > 0) && (
              <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h2 className="text-[14px] font-semibold text-fg">Defect Trendi</h2>
                    <p className="mt-0.5 text-[11px] text-fg-muted">Son 8 haftada açılan/kapanan defectler</p>
                  </div>
                  <Link href={`/p/${projectId}/management/defects`}
                    className="text-[11px] text-brand hover:underline">
                    Tüm defectler →
                  </Link>
                </div>
                {defectsQ.isLoading ? (
                  <div className="h-24 animate-pulse rounded-lg bg-surface-overlay" />
                ) : (
                  <DefectTrendMini defects={defects} />
                )}
              </section>
            )}
          </div>

          {/* Test type/priority distribution + velocity */}
          <TestInsightsPanel cases={cases} runs={runs} />

          {/* Coverage Heatmap */}
          {(repoQ.data?.suites ?? []).length > 0 && (
            <CoverageHeatmap cases={cases} suites={repoQ.data!.suites} />
          )}

          <div className="grid gap-5 xl:grid-cols-3">
            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm xl:col-span-2">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-[14px] font-semibold text-fg">Regresyon ve release hazirligi</h2>
                <span className="rounded-full border border-border bg-surface-overlay px-2 py-1 text-[11px] text-fg-muted">
                  {tr(release?.decision, "Beklemede")}
                </span>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <MiniBar label="Koşum ilerlemesi" value={summary?.progress_pct ?? release?.progress_pct ?? 0} max={100} tone="bg-blue-500" />
                <MiniBar label="Geçme oranı" value={summary?.pass_rate_pct ?? release?.pass_rate_pct ?? 0} max={100} tone="bg-emerald-500" />
                <MiniBar label="Gereksinim kapsamı" value={coveragePct} max={100} tone="bg-teal-500" />
              </div>
              <div className="mt-5 grid gap-2 md:grid-cols-2">
                {(release?.checklist ?? []).slice(0, 4).map(item => (
                  <div key={item.label} className="rounded-lg border border-border bg-surface-overlay px-3 py-2">
                    <p className="text-[12px] font-medium text-fg">{item.label}</p>
                    <p className="text-[11px] text-fg-subtle">{item.metric} · {tr(item.status, item.status)}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <h2 className="mb-4 text-[14px] font-semibold text-fg">Test uzmanı iş yükü</h2>
              <div className="space-y-3">
                {workload.length ? workload.map(([owner, count]) => (
                  <MiniBar key={owner} label={owner} value={count} max={cases.length} tone="bg-violet-500" />
                )) : <p className="py-8 text-center text-[12px] text-fg-muted">Henüz atama bulunmuyor</p>}
              </div>
            </section>
          </div>

          {/* Quick Actions */}
          <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
            <h2 className="mb-3 text-[12px] font-medium uppercase tracking-wider text-fg-subtle">Hızlı Aksiyonlar</h2>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "+ Yeni Case",       href: `/p/${projectId}/management/cases/new`,         color: "bg-brand text-brand-fg hover:brightness-105"               },
                { label: "▶ Run Başlat",      href: `/p/${projectId}/management/runs`,               color: "bg-blue-600 text-white hover:bg-blue-500"                   },
                { label: "Regresyon Seti",    href: `/p/${projectId}/management/regression`,         color: "bg-purple-600 text-white hover:bg-purple-500"               },
                { label: "Plan Oluştur",      href: `/p/${projectId}/management/plans`,              color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
                { label: "Defect Ekle",       href: `/p/${projectId}/management/defects`,             color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
                { label: "Import",            href: `/p/${projectId}/management/import-export`,      color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
                { label: "Raporlar",          href: `/p/${projectId}/management/reports`,            color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
                { label: "Standup",           href: `/p/${projectId}/management/standup`,            color: "border border-border bg-surface-overlay text-fg-muted hover:text-fg" },
              ].map(({ label, href, color }) => (
                <Link key={label} href={href}
                  className={`rounded-lg px-3 py-1.5 text-[12px] font-medium shadow-sm transition-all ${color}`}>
                  {label}
                </Link>
              ))}
            </div>
          </section>

          {/* My Work Widget */}
          {myUserId && (myCases.length > 0 || myOpenDefects.length > 0) && (
            <section className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-500/15 text-[11px]">👤</span>
                  <h2 className="text-[13px] font-semibold text-fg">Benim İşlerim</h2>
                </div>
                <span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-400">
                  {myCases.length} case{myOpenDefects.length > 0 ? ` · ${myOpenDefects.length} defect` : ""}
                </span>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {/* My Cases */}
                <div>
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Atanan Case'ler</p>
                  {myCases.length === 0 ? (
                    <p className="py-4 text-center text-[12px] text-fg-muted">Size atanmış case yok.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {myCases.map(tc => {
                        const statusColor =
                          tc.last_run_status === "failed" ? "bg-red-500/10 border-red-500/20 text-red-400" :
                          tc.last_run_status === "passed" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" :
                          tc.last_run_status === "blocked" ? "bg-amber-500/10 border-amber-500/20 text-amber-400" :
                          "bg-surface-overlay border-border text-fg-muted";
                        return (
                          <Link
                            key={tc.id}
                            href={`/p/${projectId}/management/cases/${tc.id}`}
                            className="flex items-center gap-2 rounded-lg border border-border bg-surface-overlay px-3 py-2 hover:border-blue-500/30 transition-colors"
                          >
                            <span className="shrink-0 font-mono text-[9px] text-fg-subtle">{tc.case_key}</span>
                            <span className="flex-1 min-w-0 truncate text-[12px] text-fg">{tc.title}</span>
                            {tc.last_run_status && (
                              <span className={cn("shrink-0 rounded border px-1.5 py-0.5 text-[9px] font-medium", statusColor)}>
                                {tr(tc.last_run_status)}
                              </span>
                            )}
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
                {/* My Open Defects */}
                <div>
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Açık Defektlerim</p>
                  {myOpenDefects.length === 0 ? (
                    <div className="flex flex-col items-center gap-2 py-4 text-center">
                      <span className="text-xl">✅</span>
                      <p className="text-[12px] text-fg-muted">Açık defektiniz yok.</p>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {myOpenDefects.map(d => {
                        const sevColor =
                          ["blocker","critical"].includes(d.severity.toLowerCase()) ? "text-red-400" :
                          d.severity.toLowerCase() === "major" ? "text-orange-400" : "text-fg-muted";
                        return (
                          <Link
                            key={d.id}
                            href={`/p/${projectId}/management/defects`}
                            className="flex items-center gap-2 rounded-lg border border-border bg-surface-overlay px-3 py-2 hover:border-red-500/20 transition-colors"
                          >
                            <span className={cn("shrink-0 text-[10px] font-semibold", sevColor)}>{d.severity}</span>
                            <span className="flex-1 min-w-0 truncate text-[12px] text-fg">{d.title}</span>
                            <span className="shrink-0 text-[10px] text-fg-muted">{d.status.replace(/_/g, " ")}</span>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}

          <div className="grid gap-5 xl:grid-cols-3">
            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <h2 className="mb-4 text-[14px] font-semibold text-fg">Son calistirilan testler</h2>
              <div className="space-y-2">
                {latestRuns.length ? latestRuns.map(run => (
                  <Link key={run.id} href={`/p/${projectId}/management/runs/${run.id}/execute`} className="block rounded-lg border border-border bg-surface-overlay px-3 py-2 hover:border-brand/30">
                    <p className="truncate text-[12px] font-medium text-fg">{run.name}</p>
                    <p className="mt-0.5 text-[11px] text-fg-subtle">{tr(run.status)} · {run.environment ?? "ortam yok"}</p>
                  </Link>
                )) : <p className="py-8 text-center text-[12px] text-fg-muted">Henüz test run bulunmuyor</p>}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <h2 className="mb-4 text-[14px] font-semibold text-fg">Son guncellenen case'ler</h2>
              <div className="space-y-2">
                {latestCases.length ? latestCases.map(tc => (
                  <Link key={tc.id} href={`/p/${projectId}/management/cases/${tc.id}`} className="block rounded-lg border border-border bg-surface-overlay px-3 py-2 hover:border-brand/30">
                    <p className="truncate text-[12px] font-medium text-fg">{tc.case_key} · {tc.title}</p>
                    <p className="mt-0.5 text-[11px] text-fg-subtle">{tr(tc.priority)} · {tr(tc.type)} · {tr(tc.status)}</p>
                  </Link>
                )) : <p className="py-8 text-center text-[12px] text-fg-muted">Repository uzerinden case ekleyin</p>}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <h2 className="mb-4 text-[14px] font-semibold text-fg">Modul dagilimi</h2>
              <div className="space-y-3">
                {moduleDistribution.length ? moduleDistribution.map(([moduleName, count]) => (
                  <MiniBar key={moduleName} label={moduleName} value={count} max={cases.length} tone="bg-cyan-500" />
                )) : <p className="py-8 text-center text-[12px] text-fg-muted">Modul bilgisi bulunmuyor</p>}
              </div>
            </section>
          </div>

          {/* ── Flaky Tests + Review Queue ──────────────────────────────────── */}
          <div className="grid gap-5 xl:grid-cols-2">
            {/* Flaky Tests Widget */}
            <section className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-amber-500/15 text-[11px]">⚡</span>
                  <h2 className="text-[13px] font-semibold text-fg">Kararsız (Flaky) Testler</h2>
                </div>
                {flakyQ.data && flakyQ.data.total > 0 && (
                  <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-400">
                    {flakyQ.data.total} test
                  </span>
                )}
              </div>
              <p className="mb-3 text-[11px] text-fg-muted">Birden fazla koşumda tutarsız sonuç veren <span className="text-fg">otomasyonlu</span> testler (skor ≥ 0.2). Saf manuel case&apos;ler hariç tutulur.</p>
              {flakyQ.isLoading ? (
                <div className="space-y-2">
                  {[1,2,3].map(i => <div key={i} className="h-10 animate-pulse rounded-lg bg-surface-accent" />)}
                </div>
              ) : !flakyQ.data || flakyQ.data.items.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-6 text-center">
                  <span className="text-2xl">✅</span>
                  <p className="text-[12px] text-fg-muted">Flaky test tespit edilmedi.</p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {flakyQ.data.items.map((t: FlakyTestOut) => {
                    const pct = Math.round(t.flakiness_score * 100);
                    return (
                      <Link
                        key={t.id}
                        href={`/p/${projectId}/management/cases/${t.id}`}
                        className="flex items-center gap-3 rounded-lg border border-border bg-surface-overlay px-3 py-2 hover:border-amber-500/30 transition-colors"
                      >
                        <span className="shrink-0 font-mono text-[10px] text-fg-subtle">{t.case_key}</span>
                        <span className="flex-1 min-w-0 truncate text-[12px] text-fg">{t.title}</span>
                        <span className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold tabular-nums"
                          style={{ background: `rgba(245,158,11,${Math.min(0.3, pct / 100)})`, color: "#f59e0b" }}>
                          {pct}% flaky
                        </span>
                        <span className="shrink-0 text-[10px] text-fg-subtle">{t.run_count} run</span>
                      </Link>
                    );
                  })}
                </div>
              )}
            </section>

            {/* Review Queue Widget */}
            <section className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-md bg-purple-500/15 text-[11px]">👁</span>
                  <h2 className="text-[13px] font-semibold text-fg">İnceleme Kuyruğu</h2>
                </div>
                {reviewQ.data && reviewQ.data.length > 0 && (
                  <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[10px] font-medium text-purple-400">
                    {reviewQ.data.length} bekleyen
                  </span>
                )}
              </div>
              <p className="mb-3 text-[11px] text-fg-muted">İnceleme onayı bekleyen test case'ler.</p>
              {reviewQ.isLoading ? (
                <div className="space-y-2">
                  {[1,2,3].map(i => <div key={i} className="h-10 animate-pulse rounded-lg bg-surface-accent" />)}
                </div>
              ) : !reviewQ.data || reviewQ.data.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-6 text-center">
                  <span className="text-2xl">✅</span>
                  <p className="text-[12px] text-fg-muted">Bekleyen inceleme yok.</p>
                </div>
              ) : (
                <div className="space-y-1.5">
                  {reviewQ.data.map((c: CaseReviewOut) => (
                    <Link
                      key={c.id}
                      href={`/p/${projectId}/management/cases/${c.id}`}
                      className="flex items-center gap-3 rounded-lg border border-border bg-surface-overlay px-3 py-2 hover:border-purple-500/30 transition-colors"
                    >
                      <span className="shrink-0 font-mono text-[10px] text-fg-subtle">{c.case_key}</span>
                      <span className="flex-1 min-w-0 truncate text-[12px] text-fg">{c.title}</span>
                      <span className="shrink-0 rounded-full border border-purple-500/20 bg-purple-500/10 px-2 py-0.5 text-[10px] text-purple-400">
                        İnceleme Bekliyor
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* Stale Tests Widget */}
          {!repoQ.isLoading && (staleTestsAll.length > 0 || cases.length > 0) && (
            <StaleTestsWidget stale={staleTests} total={staleTestsAll.length} projectId={projectId} />
          )}

          {/* Activity Feed */}
          {auditQ.data && auditQ.data.length > 0 && (
            <section className="rounded-xl border border-border bg-surface-raised p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-[14px] font-semibold text-fg">Son Aktiviteler</h2>
                <Link href={`/p/${projectId}/management/audit`}
                  className="text-[11px] text-brand hover:underline">Tümünü gör →</Link>
              </div>
              <div className="space-y-2">
                {auditQ.data.slice(0, 8).map(ev => {
                  const actorName = ev.actor_id
                    ? (userIdMap[ev.actor_id] ?? `${ev.actor_id.slice(0, 6)}…`)
                    : "Sistem";
                  return (
                    <div key={ev.id} className="flex items-center gap-3 rounded-lg border border-border bg-surface-overlay px-3 py-2">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-accent text-[9px] font-bold text-fg-subtle" title={actorName}>
                        {actorName[0]?.toUpperCase() ?? "?"}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-[12px] text-fg-muted">{ev.action}</p>
                        <p className="text-[10px] text-fg-subtle">{actorName}</p>
                      </div>
                      <span className="shrink-0 text-[10px] text-fg-subtle tabular-nums">
                        {new Date(ev.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
                        {" "}
                        {new Date(ev.created_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
