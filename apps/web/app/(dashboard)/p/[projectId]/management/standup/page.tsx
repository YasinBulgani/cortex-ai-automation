"use client";

import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { useManagementStandup, useManagementRuns } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

// ─── Types ───────────────────────────────────────────────────────────────────

interface StandupData {
  health_score: number;
  summary_health: "healthy" | "at_risk" | "critical";
  eta_hours: number | null;
  remaining_cases: number;
  total_cases: number;
  completed_cases: number;
  pass_rate: number;
  blocked: number;
  failed: number;
  not_run: number;
  passed: number;
  velocity_per_hour: number;
  anomalies: { severity: string; title: string }[];
  run_name: string;
  predicted_completion: string | null;
  will_meet_gate: boolean;
  blocking_factors: string[];
}

// ─── Config ──────────────────────────────────────────────────────────────────

const HEALTH_CONFIG = {
  healthy: {
    bg: "from-emerald-950 to-slate-950",
    ring: "border-emerald-500",
    label: "SAĞLIKLI",
    color: "text-emerald-400",
    dot: "bg-emerald-500",
    gradientFrom: "from-emerald-500",
  },
  at_risk: {
    bg: "from-amber-950 to-slate-950",
    ring: "border-amber-500",
    label: "RİSKLİ",
    color: "text-amber-400",
    dot: "bg-amber-500",
    gradientFrom: "from-amber-500",
  },
  critical: {
    bg: "from-red-950 to-slate-950",
    ring: "border-red-500",
    label: "KRİTİK",
    color: "text-red-400",
    dot: "bg-red-500",
    gradientFrom: "from-red-500",
  },
};

// ─── useAnimatedCount ─────────────────────────────────────────────────────────

function useAnimatedCount(target: number, duration: number = 800): number {
  const startRef = useRef<number | null>(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    startRef.current = null;

    const step = (timestamp: number) => {
      if (startRef.current === null) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * target));
      if (progress < 1) requestAnimationFrame(step);
    };

    const raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return count;
}

// ─── LiveClock ────────────────────────────────────────────────────────────────

function LiveClock() {
  const [time, setTime] = useState("");

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, "0");
      const mm = String(now.getMinutes()).padStart(2, "0");
      const ss = String(now.getSeconds()).padStart(2, "0");
      setTime(`${hh}:${mm}:${ss}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <span className="text-3xl font-mono tracking-widest text-white">{time}</span>
  );
}

// ─── CountdownRing ────────────────────────────────────────────────────────────

function CountdownRing({ seconds, size = 56 }: { seconds: number; size?: number }) {
  const r = (size - 8) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;
  const fill = Math.min(seconds / 60, 1);
  const offset = circumference - fill * circumference;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="#1e293b"
        strokeWidth="4"
      />
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="#22c55e"
        strokeWidth="4"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dashoffset 1s linear" }}
      />
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        fill="white"
        fontSize={size * 0.25}
        fontWeight="600"
        fontFamily="monospace"
      >
        {seconds}
      </text>
    </svg>
  );
}

// ─── PageHeader ───────────────────────────────────────────────────────────────

function PageHeader({
  runName,
  health,
  cfg,
  countdown,
  activeRuns,
  selectedRunId,
  onSelectRun,
}: {
  runName: string;
  health: "healthy" | "at_risk" | "critical";
  cfg: (typeof HEALTH_CONFIG)[keyof typeof HEALTH_CONFIG];
  countdown: number;
  activeRuns?: { id: string; name: string }[];
  selectedRunId?: string;
  onSelectRun?: (id: string) => void;
}) {
  return (
    <div className="flex justify-between items-center px-8 py-4 border-b border-border/80">
      <div className="flex flex-col gap-0.5">
        <span className="text-xs font-semibold uppercase tracking-widest text-fg-subtle">
          Stand-up
        </span>
        {/* Run seçici — birden fazla aktif run varsa göster */}
        {activeRuns && activeRuns.length > 1 && onSelectRun ? (
          <select
            value={selectedRunId ?? ""}
            onChange={e => onSelectRun(e.target.value)}
            className="mt-0.5 rounded-lg border border-border bg-surface-raised px-2 py-1 text-[13px] font-bold text-white outline-none focus:border-teal-500/50 max-w-xs"
          >
            {activeRuns.map(r => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        ) : (
          <span className="text-white font-bold text-lg leading-tight truncate max-w-xs">
            {runName}
          </span>
        )}
      </div>

      <LiveClock />

      <div className="flex items-center gap-3">
        <div
          className={`flex items-center gap-1.5 rounded-full border ${cfg.ring} px-3 py-1.5`}
        >
          <span className={`w-2 h-2 rounded-full animate-pulse ${cfg.dot}`} />
          <span className={`text-xs font-bold ${cfg.color}`}>{cfg.label}</span>
        </div>
        <CountdownRing seconds={countdown} size={56} />
      </div>
    </div>
  );
}

// ─── BigHealthGauge ───────────────────────────────────────────────────────────

function BigHealthGauge({
  score,
  health,
}: {
  score: number;
  health: string;
}) {
  const cx = 140;
  const cy = 155;
  const r = 110;
  const perimeter = Math.PI * r;
  const strokeColor =
    health === "healthy" ? "#10b981" : health === "at_risk" ? "#f59e0b" : "#f43f5e";

  const clamped = Math.max(0, Math.min(100, score));
  const fill = perimeter * (clamped / 100);
  const gap = perimeter - fill + 9999;

  const ticks = [0, 25, 50, 75, 100];

  return (
    <svg
      width="280"
      height="160"
      viewBox="0 0 280 160"
      aria-label={`Health gauge: ${score}`}
    >
      <path
        d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none"
        stroke="#1e293b"
        strokeWidth="20"
        strokeLinecap="round"
      />
      <path
        d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none"
        stroke={strokeColor}
        strokeWidth="20"
        strokeLinecap="round"
        strokeDasharray={`${fill} ${gap}`}
        style={{ transition: "stroke-dasharray 1s ease" }}
      />
      {ticks.map((t) => {
        const angleDeg = -180 + t * 1.8;
        const rad = (angleDeg * Math.PI) / 180;
        const x1 = cx + (r - 14) * Math.cos(rad);
        const y1 = cy + (r - 14) * Math.sin(rad);
        const x2 = cx + (r + 4) * Math.cos(rad);
        const y2 = cy + (r + 4) * Math.sin(rad);
        const lx = cx + (r + 20) * Math.cos(rad);
        const ly = cy + (r + 20) * Math.sin(rad);
        return (
          <g key={t}>
            <line
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="#475569" strokeWidth="2" strokeLinecap="round"
            />
            <text
              x={lx} y={ly + 4}
              textAnchor="middle"
              fill="#64748b"
              fontSize="10"
              fontWeight="500"
            >
              {t}
            </text>
          </g>
        );
      })}
      <text
        x={cx} y={cy - 18}
        textAnchor="middle"
        fill="white"
        fontSize="56"
        fontWeight="bold"
      >
        {Math.round(score)}
      </text>
      <text
        x={cx} y={cy + 10}
        textAnchor="middle"
        fill={strokeColor}
        fontSize="13"
        fontWeight="600"
        letterSpacing="2"
      >
        {health === "healthy" ? "SAĞLIKLI" : health === "at_risk" ? "RİSKLİ" : "KRİTİK"}
      </text>
    </svg>
  );
}

// ─── ExecutionDonut ───────────────────────────────────────────────────────────

function ExecutionDonut({
  passed,
  failed,
  blocked,
  notRun,
  total,
}: {
  passed: number;
  failed: number;
  blocked: number;
  notRun: number;
  total: number;
}) {
  const cx = 100;
  const cy = 100;
  const r = 72;
  const sw = 28;
  const circumference = 2 * Math.PI * r;

  const segments = [
    { key: "passed",  value: passed,  color: "#10b981", label: "Geçti" },
    { key: "failed",  value: failed,  color: "#ef4444", label: "Başarısız" },
    { key: "blocked", value: blocked, color: "#f59e0b", label: "Engellendi" },
    { key: "notRun",  value: notRun,  color: "#475569", label: "Bekliyor" },
  ];

  const safeTotal = total > 0 ? total : 1;
  let cumulative = 0;

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width="200" height="200" viewBox="0 0 200 200" aria-label="Yürütme dağılımı grafiği">
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke="#1e293b"
          strokeWidth={sw}
        />
        {segments.map((seg) => {
          if (seg.value <= 0) return null;
          const segLength = (seg.value / safeTotal) * circumference;
          const offset = circumference - cumulative;
          cumulative += segLength;
          return (
            <circle
              key={seg.key}
              cx={cx} cy={cy} r={r}
              fill="none"
              stroke={seg.color}
              strokeWidth={sw}
              strokeDasharray={`${segLength} ${circumference - segLength}`}
              strokeDashoffset={offset}
              transform={`rotate(-90 ${cx} ${cy})`}
              style={{ transition: "stroke-dasharray 0.8s ease" }}
            />
          );
        })}
        <text
          x={cx} y={cy - 6}
          textAnchor="middle"
          fill="white"
          fontSize="28"
          fontWeight="bold"
        >
          {total}
        </text>
        <text
          x={cx} y={cy + 14}
          textAnchor="middle"
          fill="#64748b"
          fontSize="12"
          fontWeight="600"
          letterSpacing="1"
        >
          TEST
        </text>
      </svg>
      <div className="flex gap-4 flex-wrap justify-center">
        {segments.map((seg) => (
          <div key={seg.key} className="flex items-center gap-1.5">
            <span
              className="inline-block w-2.5 h-2.5 rounded-sm shrink-0"
              style={{ backgroundColor: seg.color }}
            />
            <span className="text-[11px] text-fg-muted font-medium">{seg.label}</span>
            <span className="text-[11px] text-fg font-bold">{seg.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── StackedBar ───────────────────────────────────────────────────────────────

function StackedBar({
  passed,
  failed,
  blocked,
  notRun,
  total,
}: {
  passed: number;
  failed: number;
  blocked: number;
  notRun: number;
  total: number;
}) {
  const safeTotal = total > 0 ? total : 1;

  const segments = [
    { key: "passed",  value: passed,  color: "#10b981", label: "Geçti" },
    { key: "failed",  value: failed,  color: "#ef4444", label: "Başarısız" },
    { key: "blocked", value: blocked, color: "#f59e0b", label: "Engellendi" },
    { key: "notRun",  value: notRun,  color: "#475569", label: "Bekliyor" },
  ];

  return (
    <div className="flex flex-col gap-2 w-full">
      <div className="h-8 flex rounded-full overflow-hidden bg-surface-raised">
        {segments.map((seg) => {
          const pct = (seg.value / safeTotal) * 100;
          if (pct <= 0) return null;
          return (
            <div
              key={seg.key}
              style={{
                width: `${pct}%`,
                backgroundColor: seg.color,
                transition: "width 0.7s ease",
                flexShrink: 0,
              }}
              title={`${seg.label}: ${seg.value}`}
            />
          );
        })}
      </div>
      <div className="flex gap-4 flex-wrap">
        {segments.map((seg) => {
          const pct = Math.round((seg.value / safeTotal) * 100);
          return (
            <div key={seg.key} className="flex items-center gap-1.5">
              <span
                className="inline-block w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: seg.color }}
              />
              <span className="text-[11px] text-fg-muted">{seg.label}</span>
              <span className="text-[11px] font-bold text-fg">
                {seg.value}
                <span className="text-fg-disabled font-normal"> ({pct}%)</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── VelocitySparkline ────────────────────────────────────────────────────────

function VelocitySparkline({ velocityPerHour }: { velocityPerHour: number }) {
  const w = 220;
  const h = 90;
  // Sıfıra bölünme koruması: velocity 0 ise grafik yerine mesaj göster
  const hasData = velocityPerHour > 0;
  const multipliers = [0.5, 0.7, 0.6, 0.8, 0.9, 1.0, 1.1];
  const values = multipliers.map((m) => velocityPerHour * m);
  // maxV en az 1 — sıfıra bölünme koruması
  const maxV = Math.max(...values, 1);
  const padX = 10;
  const padY = 10;
  const innerW = w - padX * 2;
  const innerH = h - padY * 2;

  const points = values.map((v, i) => {
    const x = padX + (i / (values.length - 1)) * innerW;
    const y = padY + innerH - (v / maxV) * innerH;
    return `${x},${y}`;
  });

  const polylineStr = points.join(" ");
  const lastPt = points[points.length - 1].split(",");
  const lx = parseFloat(lastPt[0]);
  const ly = parseFloat(lastPt[1]);

  const firstPt = points[0].split(",");
  const fx = parseFloat(firstPt[0]);
  const fy = parseFloat(firstPt[1]);

  const areaPath = `M ${fx},${fy} ${points
    .slice(1)
    .map((p) => `L ${p}`)
    .join(" ")} L ${lx},${padY + innerH} L ${fx},${padY + innerH} Z`;

  return (
    <div className="rounded-xl border border-border bg-surface-raised/60 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold uppercase tracking-widest text-fg-muted">HIZ</span>
        <span className={`text-lg font-black ${hasData ? "text-teal-400" : "text-fg-subtle"}`}>
          {velocityPerHour.toFixed(1)}{" "}
          <span className="text-xs font-medium text-fg-subtle">case/saat</span>
        </span>
      </div>
      {!hasData ? (
        <div className="flex items-center justify-center" style={{ width: w, height: h }}>
          <span className="text-sm text-fg-disabled font-medium">Henüz hız verisi yok</span>
        </div>
      ) : (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <defs>
            <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#14b8a6" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#14b8a6" stopOpacity="0.02" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <path d={areaPath} fill="url(#sparkGrad)" />
          <polyline
            points={polylineStr}
            fill="none"
            stroke="#14b8a6"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#glow)"
          />
          <circle cx={lx} cy={ly} r="5" fill="#14b8a6" opacity="0.4">
            <animate
              attributeName="r"
              values="5;9;5"
              dur="1.8s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              values="0.4;0;0.4"
              dur="1.8s"
              repeatCount="indefinite"
            />
          </circle>
          <circle cx={lx} cy={ly} r="4" fill="#14b8a6" />
        </svg>
      )}
    </div>
  );
}

// ─── EtaDisplay ───────────────────────────────────────────────────────────────

function EtaDisplay({
  etaHours,
  predictedCompletion,
}: {
  etaHours: number | null;
  predictedCompletion: string | null;
}) {
  // Geçmiş tarih kontrolü: predicted_completion geçmiş mi?
  const isOverdue = useMemo(() => {
    if (!predictedCompletion) return false;
    try {
      return new Date(predictedCompletion).getTime() < Date.now();
    } catch {
      return false;
    }
  }, [predictedCompletion]);

  const { borderColor, bgColor, pulse, textColor } = useMemo(() => {
    if (etaHours === null)
      return {
        borderColor: "border-border",
        bgColor: "bg-surface-raised/30",
        pulse: "",
        textColor: "text-fg-muted",
      };
    // Gecikmiş: eta <= 0 veya predicted_completion geçmiş
    if (etaHours <= 0 || isOverdue)
      return {
        borderColor: "border-red-500",
        bgColor: "bg-red-950/40",
        pulse: "animate-pulse",
        textColor: "text-red-400",
      };
    if (etaHours < 2)
      return {
        borderColor: "border-red-500",
        bgColor: "bg-red-950/30",
        pulse: "animate-pulse",
        textColor: "text-red-400",
      };
    if (etaHours < 8)
      return {
        borderColor: "border-amber-500",
        bgColor: "bg-amber-950/30",
        pulse: "",
        textColor: "text-amber-400",
      };
    return {
      borderColor: "border-emerald-500",
      bgColor: "bg-emerald-950/30",
      pulse: "",
      textColor: "text-emerald-400",
    };
  }, [etaHours, isOverdue]);

  const completionTime = useMemo(() => {
    if (!predictedCompletion) return null;
    try {
      const d = new Date(predictedCompletion);
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      return `${hh}:${mm}`;
    } catch {
      return null;
    }
  }, [predictedCompletion]);

  return (
    <div
      className={`rounded-xl border ${borderColor} ${bgColor} ${pulse} p-4`}
    >
      <p className="text-xs font-bold uppercase tracking-widest text-fg-subtle mb-1">ETA</p>
      {etaHours === null ? (
        <>
          <p className={`text-2xl font-black ${textColor}`}>Bilinmiyor</p>
          <p className="text-xs text-fg-disabled mt-0.5">Yeterli veri yok</p>
        </>
      ) : isOverdue || etaHours <= 0 ? (
        <>
          <p className={`text-2xl font-black ${textColor}`}>GECİKMİŞ</p>
          {completionTime && (
            <p className="text-xs text-red-500/80 mt-0.5">
              Hedef: {completionTime} — geçti
            </p>
          )}
        </>
      ) : (
        <>
          <p className={`text-2xl font-black ${textColor}`}>
            {etaHours.toFixed(1)}s
          </p>
          {completionTime && (
            <p className="text-xs text-fg-subtle mt-0.5">
              Tahmini: {completionTime}
            </p>
          )}
        </>
      )}
    </div>
  );
}

// ─── MetricCard ───────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  accent,
  trend,
}: {
  label: string;
  value: string | number;
  accent?: string;
  trend?: "up" | "down" | "flat";
}) {
  const isNumeric = typeof value === "number";
  const animated = useAnimatedCount(isNumeric ? (value as number) : 0);
  const display = isNumeric ? animated : value;

  const trendIcon =
    trend === "up" ? "↑" : trend === "down" ? "↓" : trend === "flat" ? "→" : null;
  const trendColor =
    trend === "up"
      ? "text-emerald-400"
      : trend === "down"
      ? "text-red-400"
      : "text-fg-muted";

  return (
    <div className="w-full rounded-xl border border-border bg-surface-raised/60 p-5">
      <div className="flex items-start justify-between gap-2">
        <span
          className="text-5xl font-black leading-none"
          style={accent ? { color: accent } : undefined}
        >
          {display}
        </span>
        {trendIcon && (
          <span className={`mt-1 text-2xl font-bold ${trendColor}`}>{trendIcon}</span>
        )}
      </div>
      <p className="mt-2 text-sm font-medium uppercase tracking-widest text-fg-muted">
        {label}
      </p>
    </div>
  );
}

// ─── PassRateRing ─────────────────────────────────────────────────────────────

function PassRateRing({ rate }: { rate: number }) {
  const r = 48;
  const cx = 60;
  const cy = 60;
  const strokeWidth = 14;
  const circumference = 2 * Math.PI * r;
  const filled = (rate / 100) * circumference;

  const color =
    rate >= 90 ? "#34d399" : rate >= 70 ? "#fbbf24" : "#f87171";

  return (
    <svg width={120} height={120} viewBox="0 0 120 120">
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="#1e293b"
        strokeWidth={strokeWidth}
      />
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={`${filled} ${circumference - filled}`}
        strokeDashoffset={circumference / 4}
        strokeLinecap="round"
        style={{ transition: "stroke-dasharray 0.8s cubic-bezier(0.4,0,0.2,1)" }}
      />
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize="18"
        fontWeight="900"
        fill={color}
      >
        {rate}%
      </text>
    </svg>
  );
}

// ─── AnomalyList ──────────────────────────────────────────────────────────────

const ANOMALY_SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

function AnomalyList({
  anomalies,
}: {
  anomalies: { severity: string; title: string }[];
}) {
  // critical > warning > info sıralaması
  const sorted = useMemo(
    () =>
      [...anomalies].sort((a, b) => {
        const ao = ANOMALY_SEVERITY_ORDER[a.severity] ?? 99;
        const bo = ANOMALY_SEVERITY_ORDER[b.severity] ?? 99;
        return ao - bo;
      }),
    [anomalies]
  );

  const borderColor = (severity: string) => {
    if (severity === "critical") return "border-red-500";
    if (severity === "warning") return "border-amber-500";
    return "border-blue-500";
  };

  const dotColor = (severity: string) => {
    if (severity === "critical") return "bg-red-500";
    if (severity === "warning") return "bg-amber-500";
    return "bg-blue-500";
  };

  const severityLabel = (severity: string) => {
    if (severity === "critical") return "KRİTİK";
    if (severity === "warning") return "UYARI";
    return "BİLGİ";
  };

  return (
    <div className="rounded-xl border border-border bg-surface-raised/60">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <span className="text-xs font-bold uppercase tracking-widest text-fg">
          ANOMALİLER
        </span>
        {sorted.length > 0 && (
          <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-xs font-bold text-red-400">
            {sorted.length}
          </span>
        )}
      </div>
      <div className="max-h-48 overflow-y-auto">
        {sorted.length === 0 ? (
          <div className="flex items-center justify-center gap-2 py-6 text-sm font-semibold text-emerald-400">
            <span className="text-emerald-500">✓</span>
            Anomali tespit edilmedi
          </div>
        ) : (
          <ul>
            {sorted.map((a, i) => (
              <li
                key={i}
                className={`flex items-center gap-3 border-l-4 px-4 py-3 ${borderColor(a.severity)} ${
                  i < sorted.length - 1 ? "border-b border-border/60" : ""
                }`}
              >
                <span
                  className={`h-2 w-2 shrink-0 rounded-full ${dotColor(a.severity)}`}
                />
                <div className="flex flex-col min-w-0">
                  <span className="text-sm text-fg truncate">{a.title}</span>
                  <span className={`text-[10px] font-bold tracking-wider ${
                    a.severity === "critical" ? "text-red-500" :
                    a.severity === "warning" ? "text-amber-500" : "text-blue-400"
                  }`}>
                    {severityLabel(a.severity)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ─── BlockerList ──────────────────────────────────────────────────────────────

function BlockerList({
  factors,
  willMeetGate,
}: {
  factors: string[];
  willMeetGate: boolean;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised/60 p-5">
      <div className="mb-4 flex items-center gap-3">
        <span
          className={`rounded-lg px-4 py-1.5 text-lg font-black tracking-widest ${
            willMeetGate
              ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40"
              : "bg-red-500/20 text-red-400 ring-1 ring-red-500/40"
          }`}
        >
          {willMeetGate ? "GO" : "NO-GO"}
        </span>
        <span className="text-sm font-semibold uppercase tracking-wider text-fg-muted">
          Sürüm Kapısı
        </span>
      </div>
      {factors.length === 0 ? (
        <p className="text-sm font-semibold text-emerald-400">Aktif blocker yok</p>
      ) : (
        <ul className="space-y-2">
          {factors.map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-fg">
              <span className="mt-0.5 shrink-0 text-red-400">●</span>
              <span>{f}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── ReleaseGate ──────────────────────────────────────────────────────────────

function ReleaseGate({ willMeetGate, blockingFactors }: { willMeetGate: boolean; blockingFactors: string[] }) {
  return (
    <div
      className={`flex items-center justify-between px-10 py-6 rounded-2xl border ${
        willMeetGate
          ? "bg-gradient-to-r from-emerald-950/60 to-transparent border-emerald-800/50"
          : "bg-gradient-to-r from-red-950/60 to-transparent border-red-800/50"
      }`}
    >
      <div className="flex items-center gap-6">
        <span
          className={`text-7xl font-black leading-none ${
            willMeetGate ? "text-emerald-400" : "text-red-400"
          }`}
        >
          {willMeetGate ? "✓ GO" : "✗ NO-GO"}
        </span>
        <span
          className={`text-xl font-semibold tracking-widest uppercase ${
            willMeetGate ? "text-emerald-300" : "text-red-300"
          }`}
        >
          {willMeetGate ? "RELEASE HAZIR" : "RELEASE HAZIR DEĞİL"}
        </span>
      </div>
      {blockingFactors.length > 0 && (
        <div className="flex flex-wrap gap-2 max-w-xl justify-end">
          {blockingFactors.map((factor, i) => (
            <span
              key={i}
              className={`text-xs font-medium px-3 py-1 rounded-full border ${
                willMeetGate
                  ? "bg-emerald-900/40 border-emerald-700/50 text-emerald-300"
                  : "bg-red-900/40 border-red-700/50 text-red-300"
              }`}
            >
              {factor}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── BottomBar ────────────────────────────────────────────────────────────────

function BottomBar({
  lastUpdateStr,
  countdown,
  onRefresh,
  onCopyMarkdown,
}: {
  lastUpdateStr: string | null;
  countdown: number;
  onRefresh: () => void;
  onCopyMarkdown?: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const progressPct = Math.min(100, Math.max(0, (countdown / 60) * 100));

  const handleCopy = () => {
    navigator.clipboard.writeText(document.body.innerText).catch(() => {});
  };

  const handleCopyMarkdown = () => {
    onCopyMarkdown?.();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="border-t border-border bg-surface-base/90 px-6 py-3 flex items-center justify-between gap-4">
      <span className="text-xs text-fg-subtle whitespace-nowrap min-w-[120px]">
        {lastUpdateStr ? `Son: ${lastUpdateStr}` : "—"}
      </span>
      <div className="flex-1 flex items-center gap-2">
        <div className="w-full h-1 bg-surface-raised rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-1000"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className="text-xs text-fg-disabled tabular-nums w-6 text-right">
          {countdown}s
        </span>
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={onRefresh}
          className="flex items-center gap-1.5 text-xs text-fg-muted hover:text-fg px-3 py-1.5 rounded-lg hover:bg-surface-raised transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Yenile
        </button>
        {onCopyMarkdown && (
          <button
            onClick={handleCopyMarkdown}
            className="flex items-center gap-1.5 text-xs text-fg-muted hover:text-fg px-3 py-1.5 rounded-lg hover:bg-surface-raised transition-colors"
            title="Slack/Teams için Markdown olarak kopyala"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/>
            </svg>
            {copied ? "Kopyalandı!" : "Slack/Teams"}
          </button>
        )}
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-fg-muted hover:text-fg px-3 py-1.5 rounded-lg hover:bg-surface-raised transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Kopyala
        </button>
        <button
          onClick={handlePrint}
          className="flex items-center gap-1.5 text-xs text-fg-muted hover:text-fg px-3 py-1.5 rounded-lg hover:bg-surface-raised transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
          Yazdır
        </button>
      </div>
    </div>
  );
}

// ─── LoadingScreen ────────────────────────────────────────────────────────────

function LoadingScreen() {
  return (
    <div className="h-[calc(100vh-48px)] flex items-center justify-center bg-[#080c14]">
      <div className="flex flex-col items-center gap-5">
        <svg
          className="w-12 h-12 text-emerald-500 animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-20"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
          />
          <path
            className="opacity-90"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <p className="text-fg-muted text-sm tracking-wide">
          Standup verisi yükleniyor...
        </p>
      </div>
    </div>
  );
}

// ─── ErrorScreen ──────────────────────────────────────────────────────────────

function ErrorScreen({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="h-[calc(100vh-48px)] flex items-center justify-center bg-[#080c14]">
      <div className="flex flex-col items-center gap-5 max-w-sm w-full mx-4 border border-red-800/60 bg-red-950/20 rounded-2xl px-8 py-10">
        <div className="w-12 h-12 rounded-full bg-red-900/40 border border-red-700/50 flex items-center justify-center">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-6 h-6 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <div className="text-center">
          <p className="text-red-300 font-semibold text-base">Veri yüklenemedi</p>
          <p className="text-fg-subtle text-sm mt-1">
            Standup verisi alınırken bir hata oluştu.
          </p>
        </div>
        <button
          onClick={onRetry}
          className="flex items-center gap-2 text-sm font-medium text-fg bg-surface-raised hover:bg-surface-overlay border border-border px-5 py-2 rounded-lg transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Yeniden Dene
        </button>
      </div>
    </div>
  );
}

// ─── StandupPage ──────────────────────────────────────────────────────────────

export default function StandupPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid = useManagementProjectId(projectId || undefined);

  // Aktif run seçimi
  const runsQ = useManagementRuns(mpid || undefined, "in_progress");
  const activeRuns = runsQ.data ?? [];
  const [selectedRunId, setSelectedRunId] = useState<string | undefined>(undefined);

  // İlk yüklemede aktif run varsa otomatik seç
  useEffect(() => {
    if (selectedRunId) return;
    const first = activeRuns[0];
    if (first) setSelectedRunId(first.id);
  }, [activeRuns]); // eslint-disable-line react-hooks/exhaustive-deps

  const standupQ = useManagementStandup(mpid || undefined, selectedRunId);

  const [countdown, setCountdown] = useState(60);
  const [lastUpdateStr, setLastUpdateStr] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // standupQ refetch'i ref'te tut — interval closure'ında stale capture'ı önle
  const refetchRef = useRef(standupQ.refetch);
  useEffect(() => { refetchRef.current = standupQ.refetch; }, [standupQ.refetch]);

  useEffect(() => {
    if (!standupQ.isLoading && standupQ.data) {
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, "0");
      const mm = String(now.getMinutes()).padStart(2, "0");
      const ss = String(now.getSeconds()).padStart(2, "0");
      setLastUpdateStr(`${hh}:${mm}:${ss}`);
    }
  }, [standupQ.data, standupQ.isLoading]);

  const startInterval = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          void refetchRef.current().catch((err: unknown) =>
            console.error("[Standup] Auto-refresh failed:", err)
          );
          return 60;
        }
        return c - 1;
      });
    }, 1000);
  }, []);

  // Otomatik yenileme: 60sn interval, tab inactive olunca durdur
  useEffect(() => {
    startInterval();

    const handleVisibility = () => {
      if (document.hidden) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } else {
        // Sekmeye dönünce hemen yenile + interval başlat
        void refetchRef.current().catch(() => {});
        setCountdown(60);
        startInterval();
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [startInterval]);

  const handleRefresh = () => {
    void standupQ.refetch();
    setCountdown(60);
  };

  const data = standupQ.data;
  const health = data?.summary_health ?? "at_risk";
  const cfg = HEALTH_CONFIG[health];

  const total = data?.total_cases ?? 0;
  const passed = data?.passed ?? data?.completed_cases ?? 0;
  const failed = data?.failed ?? 0;
  const blocked = data?.blocked ?? 0;
  // data.not_run backend'den geliyor — yoksa hesapla
  const notRun = data?.not_run ?? Math.max(0, total - passed - failed - blocked);

  if (standupQ.isLoading) return <LoadingScreen />;
  if (standupQ.isError) return <ErrorScreen onRetry={handleRefresh} />;

  return (
    <div data-standup-root className="h-[calc(100vh-48px)] flex flex-col overflow-hidden bg-[#080c14] text-white">
      {/* Print-friendly global styles */}
      <style>{`
        @media print {
          body { background: #fff !important; color: #000 !important; }
          .no-print { display: none !important; }
          /* Overflow kaldır, tam sayfa bas */
          html, body { overflow: visible !important; height: auto !important; }
          /* Ana container scrolldan çık */
          [data-standup-root] {
            height: auto !important;
            overflow: visible !important;
            background: #fff !important;
            color: #000 !important;
          }
          /* Koyu arka planları temizle */
          [data-standup-root] * {
            background-color: transparent !important;
            border-color: #ccc !important;
            color: #000 !important;
          }
          /* Renk vurgularını koru */
          [data-standup-root] svg text { fill: #000 !important; }
          /* Grid-scroll kaldır */
          [data-standup-grid] {
            overflow: visible !important;
            display: block !important;
          }
          /* BottomBar gizle */
          [data-standup-bottombar] { display: none !important; }
        }
      `}</style>
      {/* PageHeader — fixed top */}
      <PageHeader
        runName={data?.run_name ?? "—"}
        health={health}
        cfg={cfg}
        countdown={countdown}
        activeRuns={activeRuns.map(r => ({ id: r.id, name: r.name }))}
        selectedRunId={selectedRunId}
        onSelectRun={id => { setSelectedRunId(id); setCountdown(60); }}
      />

      {/* Main grid — flex-1, overflow-hidden */}
      <div data-standup-grid className="flex-1 grid grid-cols-12 gap-4 p-4 overflow-hidden">
        {/* Sol: col-span-3 — MetricCard dikey liste */}
        <div className="col-span-3 flex flex-col gap-3 overflow-hidden">
          <MetricCard
            label="Geçme Oranı"
            value={`${Math.round(data?.pass_rate ?? 0)}%`}
            accent={
              (data?.pass_rate ?? 0) >= 90
                ? "#34d399"
                : (data?.pass_rate ?? 0) >= 70
                ? "#fbbf24"
                : "#f87171"
            }
          />
          <MetricCard
            label="Engellenmiş"
            value={data?.blocked ?? 0}
            accent={(data?.blocked ?? 0) === 0 ? "#34d399" : "#f59e0b"}
          />
          <MetricCard
            label="Başarısız"
            value={data?.failed ?? 0}
            accent={(data?.failed ?? 0) === 0 ? "#34d399" : "#f87171"}
            trend={(data?.failed ?? 0) === 0 ? "flat" : "down"}
          />
          <MetricCard
            label="Bekleyen"
            value={data?.remaining_cases ?? 0}
            accent="#94a3b8"
          />
          <div className="flex justify-center mt-2">
            <PassRateRing rate={Math.round(data?.pass_rate ?? 0)} />
          </div>
        </div>

        {/* Orta: col-span-6 — BigHealthGauge + ExecutionDonut + StackedBar */}
        <div className="col-span-6 flex flex-col gap-4 overflow-hidden">
          <div className="flex justify-center">
            <BigHealthGauge score={data?.health_score ?? 0} health={health} />
          </div>
          <div className="rounded-xl border border-border bg-surface-raised/60 p-4">
            <p className="text-xs text-fg-subtle uppercase tracking-widest font-semibold mb-3">
              Yürütme Dağılımı
            </p>
            <ExecutionDonut
              passed={passed}
              failed={failed}
              blocked={blocked}
              notRun={notRun}
              total={total}
            />
          </div>
          <div className="rounded-xl border border-border bg-surface-raised/60 p-4">
            <p className="text-xs text-fg-subtle uppercase tracking-widest font-semibold mb-3">
              Test Durumu
            </p>
            <StackedBar
              passed={passed}
              failed={failed}
              blocked={blocked}
              notRun={notRun}
              total={total}
            />
          </div>
        </div>

        {/* Sağ: col-span-3 — EtaDisplay + VelocitySparkline + AnomalyList */}
        <div className="col-span-3 flex flex-col gap-3 overflow-hidden">
          <EtaDisplay
            etaHours={data?.eta_hours ?? null}
            predictedCompletion={data?.predicted_completion ?? null}
          />
          <VelocitySparkline velocityPerHour={data?.velocity_per_hour ?? 0} />
          <div className="flex-1 overflow-hidden">
            <AnomalyList anomalies={data?.anomalies ?? []} />
          </div>
          <BlockerList
            factors={data?.blocking_factors ?? []}
            willMeetGate={data?.will_meet_gate ?? false}
          />
        </div>
      </div>

      {/* ReleaseGate — fixed alt */}
      <div className="px-4 pb-2">
        <ReleaseGate
          willMeetGate={data?.will_meet_gate ?? false}
          blockingFactors={data?.blocking_factors ?? []}
        />
      </div>

      {/* BottomBar — en alt */}
      <div data-standup-bottombar>
        <BottomBar
          lastUpdateStr={lastUpdateStr}
          countdown={countdown}
          onRefresh={handleRefresh}
          onCopyMarkdown={() => {
            if (!data) return;
            const healthLabel = { healthy: "SAĞLIKLI", at_risk: "RİSKTE", critical: "KRİTİK" }[data.summary_health] ?? data.summary_health.toUpperCase();
            const lines: string[] = [
              `*QA Stand-up — ${data.run_name}*`,
              `Sağlık: ${healthLabel} (${data.health_score}/100)${data.will_meet_gate ? " ✓ Gate geçer" : " ✗ Gate riski"}`,
              `Pass Rate: %${Math.round(data.pass_rate ?? 0)} · Geçti: ${data.passed ?? 0} · Başarısız: ${data.failed ?? 0} · Engellendi: ${data.blocked ?? 0} · Kalan: ${data.remaining_cases}`,
            ];
            if (data.eta_hours != null) {
              lines.push(`ETA: ~${data.eta_hours.toFixed(1)} saat · Hız: ${data.velocity_per_hour.toFixed(1)} TC/saat`);
            }
            if (data.blocking_factors?.length) {
              lines.push("", "*Engelleyiciler:*");
              data.blocking_factors.forEach(f => lines.push(`• ${f}`));
            }
            if (data.anomalies?.length) {
              lines.push("", "*Anomaliler:*");
              data.anomalies.forEach(a => lines.push(`• [${a.severity.toUpperCase()}] ${a.title}`));
            }
            navigator.clipboard.writeText(lines.join("\n")).catch(() => {});
          }}
        />
      </div>
    </div>
  );
}
